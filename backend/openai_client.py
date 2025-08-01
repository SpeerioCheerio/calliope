import os
import json
from typing import Dict, List, Optional
from openai import OpenAI, NotFoundError
from dotenv import load_dotenv
import asyncio
from tenacity import retry, stop_after_attempt, wait_exponential

# Load environment variables from .env file with override
# This will override any existing environment variables with values from .env
load_dotenv(override=True)

# Initialize OpenAI API with better error handling
api_key = os.environ.get("OPENAI_API_KEY")
if not api_key:
    print("[ERROR] FATAL: No OpenAI API key found in environment variables!")
    print("[ERROR] Please ensure OPENAI_API_KEY is set in your environment or .env file.")
    raise EnvironmentError("[FATAL] No OpenAI API key found in environment variables!")
else:
    print(f"[INFO] OpenAI API key loaded successfully. Length: {len(api_key)} characters")
    print(f"[INFO] API key preview: {api_key[:20]}...{api_key[-4:]}")
    
    # Additional validation for placeholder keys
    if api_key.startswith("sk-<") or len(api_key) < 40:
        print("[ERROR] FATAL: Invalid OpenAI API key detected (appears to be placeholder)")
        print("[ERROR] Please ensure you have set a real OpenAI API key in your .env file.")
        raise EnvironmentError("[FATAL] Invalid or placeholder OpenAI API key")

# Initialize OpenAI client
client = OpenAI(api_key=api_key)

# System prompts
DEFINITION_SYSTEM_PROMPT = """You are a precise dictionary augmentation tool.
Return STRICT minified JSON with keys: pos, definition, example_sentence, rarity, sentiment.

Rarity labels (exact spelling):
  notty → common advanced (~80%).
  luke  → less common, high‑level (~15%).
  alex  → rare, exotic, archaic (~5%).

Sentiment labels (exact spelling): positive, negative, neutral, formal.
No extra keys. No extra text."""

THESAURUS_SYSTEM_PROMPT = """You are a thesaurus tool. Given a word and a list of vocabulary words, return only the words from the vocabulary list that are synonyms or closely related to the input word. Return as a JSON array of strings."""

PREDICTION_SYSTEM_PROMPT = """You are a vocabulary prediction tool. Given a sentence with a blank (marked by |) and a vocabulary list, suggest 5 words from the vocabulary list that would best fill the blank. Return as a JSON object with key 'suggestions' containing an array of word strings."""

POS_ANALYSIS_SYSTEM_PROMPT = """You are a linguistic analysis tool. Given a text, identify the part of speech (POS) for each word. 

Return JSON with key 'word_pos' containing an array of objects with 'word' and 'pos' fields.
Use these POS categories: noun, verb, adjective, adverb, pronoun, preposition, conjunction, determiner, interjection, other.

Focus on content words (nouns, verbs, adjectives, adverbs) that could potentially be enhanced."""

PARAGRAPH_ANALYSIS_SYSTEM_PROMPT = """You are a vocabulary enhancement tool. Your goal is to find AS MANY enhancement opportunities as possible in the given paragraph. Be thorough and comprehensive.

CRITICAL REQUIREMENTS:
1. ONLY suggest words that are EXACTLY in the provided vocabulary list (case-insensitive matching)
2. ONLY suggest words that have the EXACT SAME part of speech (POS) as the original word
3. Consider the full sentence context when suggesting replacements
4. The suggested words must fit naturally in the sentence and maintain the original meaning and tone
5. Ensure grammatical correctness and contextual appropriateness
6. Do NOT suggest words that are not in the vocabulary list
7. Do NOT suggest words with different POS tags (e.g., don't suggest an adjective to replace a verb)

ENHANCEMENT STRATEGY:
1. Scan EVERY word in the text - don't be selective
2. Look for common/simple words that can be upgraded: "good" → "excellent", "big" → "enormous", "said" → "proclaimed"
3. Focus on content words: nouns, verbs, adjectives, adverbs
4. For EACH enhanceable word, provide 2-5 suggestions when possible
5. Be generous - if a word CAN be enhanced, include it
6. Target at least 10-20% of content words for enhancement

PROCESS:
1. Identify ALL content words (nouns, verbs, adjectives, adverbs) in the text
2. For each content word, check if there are vocabulary alternatives with the same POS
3. Provide multiple suggestions per word when available
4. Prioritize words that have 3+ alternatives in the vocabulary list

Return JSON with key 'enhancements' containing an array of objects with:
- 'original_word': the word to be replaced
- 'original_pos': the POS of the original word (noun, verb, adjective, adverb, etc.)
- 'suggested_words': array of replacement words from vocabulary list (aim for 2-5 per word when possible)
- 'context': the full sentence containing the word

MAXIMIZE RESULTS - Be comprehensive, not conservative."""


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
def call_openai(messages: List[Dict], model: str = "gpt-4o-mini", temperature: float = 0.2, max_tokens: int = 250):
    """Make OpenAI API call with retry logic and model fallback"""
    try:
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content.strip()
    except NotFoundError:
        if model != "gpt-3.5-turbo":
            print(f"[WARN] Model '{model}' not available. Falling back to 'gpt-3.5-turbo'.")
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            return response.choices[0].message.content.strip()
        else:
            raise
    except Exception as e:
        print(f"OpenAI API error: {e}")
        raise


def get_word_definition(word: str) -> Optional[Dict]:
    """Get word definition, POS, example, rarity, and sentiment from OpenAI"""
    messages = [
        {"role": "system", "content": DEFINITION_SYSTEM_PROMPT},
        {"role": "user", "content": f"Provide the data for the word '{word}'."}
    ]
    
    try:
        response = call_openai(messages)
        data = json.loads(response)
        
        # Validate required fields
        required_fields = ["pos", "definition", "example_sentence", "rarity", "sentiment"]
        for field in required_fields:
            if field not in data:
                data[field] = get_default_value(field)
        
        # Validate rarity and sentiment values
        if data["rarity"] not in ["notty", "luke", "alex"]:
            data["rarity"] = "notty"
        
        if data["sentiment"] not in ["positive", "negative", "neutral", "formal"]:
            data["sentiment"] = "neutral"
        
        return data
    except (json.JSONDecodeError, KeyError, Exception) as e:
        print(f"Error processing word '{word}': {e}")
        return {
            "pos": "unknown",
            "definition": "Definition unavailable.",
            "example_sentence": "Example unavailable.",
            "rarity": "notty",
            "sentiment": "neutral"
        }


def get_default_value(field: str) -> str:
    """Get default value for missing fields"""
    defaults = {
        "pos": "unknown",
        "definition": "Definition unavailable.",
        "example_sentence": "Example unavailable.",
        "rarity": "notty",
        "sentiment": "neutral"
    }
    return defaults.get(field, "")


def find_synonyms(word: str, vocabulary_list: List[str]) -> List[str]:
    """Find synonyms from vocabulary list using OpenAI"""
    vocabulary_str = ", ".join(vocabulary_list)
    
    messages = [
        {"role": "system", "content": THESAURUS_SYSTEM_PROMPT},
        {"role": "user", "content": f"Find synonyms for '{word}' from this vocabulary list: {vocabulary_str}"}
    ]
    
    try:
        response = call_openai(messages)
        
        # Handle markdown-wrapped JSON response
        json_content = response.strip()
        if json_content.startswith("```json"):
            # Extract JSON from markdown code block
            json_content = json_content[7:]  # Remove ```json
            if json_content.endswith("```"):
                json_content = json_content[:-3]  # Remove ```
            json_content = json_content.strip()
        elif json_content.startswith("```"):
            # Handle generic code block
            lines = json_content.split('\n')
            if len(lines) > 1:
                json_content = '\n'.join(lines[1:-1])  # Remove first and last lines
            else:
                json_content = json_content[3:-3]  # Remove ```
        
        synonyms = json.loads(json_content)
        return synonyms if isinstance(synonyms, list) else []
    except (json.JSONDecodeError, Exception) as e:
        print(f"Error finding synonyms for '{word}': {e}")
        return []


def predict_words(sentence: str, vocabulary_list: List[str]) -> List[str]:
    """Predict words to fill blank in sentence using OpenAI"""
    vocabulary_str = ", ".join(vocabulary_list)
    
    messages = [
        {"role": "system", "content": PREDICTION_SYSTEM_PROMPT},
        {"role": "user", "content": f"Sentence: '{sentence}'. Vocabulary list: {vocabulary_str}"}
    ]
    
    try:
        response = call_openai(messages)
        
        # Handle markdown-wrapped JSON response
        json_content = response.strip()
        if json_content.startswith("```json"):
            # Extract JSON from markdown code block
            json_content = json_content[7:]  # Remove ```json
            if json_content.endswith("```"):
                json_content = json_content[:-3]  # Remove ```
            json_content = json_content.strip()
        elif json_content.startswith("```"):
            # Handle generic code block
            lines = json_content.split('\n')
            if len(lines) > 1:
                json_content = '\n'.join(lines[1:-1])  # Remove first and last lines
            else:
                json_content = json_content[3:-3]  # Remove ```
        
        data = json.loads(json_content)
        return data.get("suggestions", [])
    except (json.JSONDecodeError, Exception) as e:
        print(f"Error predicting words for sentence: {e}")
        return []


def get_pos_analysis(text: str) -> Dict[str, str]:
    """Get POS analysis for text using OpenAI"""
    messages = [
        {"role": "system", "content": POS_ANALYSIS_SYSTEM_PROMPT},
        {"role": "user", "content": f"Analyze this text: '{text}'"}
    ]
    
    try:
        response = call_openai(messages, max_tokens=400)
        print(f"[DEBUG] POS analysis raw response: {response}")
        
        # Handle markdown-wrapped JSON response
        json_content = response.strip()
        if json_content.startswith("```json"):
            json_content = json_content[7:]
            if json_content.endswith("```"):
                json_content = json_content[:-3]
            json_content = json_content.strip()
        elif json_content.startswith("```"):
            lines = json_content.split('\n')
            if len(lines) > 1:
                json_content = '\n'.join(lines[1:-1])
            else:
                json_content = json_content[3:-3]
        
        data = json.loads(json_content)
        word_pos_list = data.get("word_pos", [])
        
        # Convert to dictionary for easier lookup
        word_pos_map = {}
        for item in word_pos_list:
            if isinstance(item, dict) and 'word' in item and 'pos' in item:
                word_pos_map[item['word'].lower()] = item['pos'].lower()
        
        print(f"[DEBUG] POS analysis result: {word_pos_map}")
        return word_pos_map
        
    except (json.JSONDecodeError, Exception) as e:
        print(f"[DEBUG] Error in POS analysis: {e}")
        return {}


def analyze_paragraph(text: str, vocabulary_list: List[str], vocabulary_pos_map: Dict[str, str] = None) -> List[Dict]:
    """Analyze paragraph for vocabulary enhancement opportunities with OpenAI-based POS matching"""
    
    # Debug prints
    print(f"[DEBUG] Analyzing paragraph: '{text[:100]}...' (len={len(text)})")
    print(f"[DEBUG] Vocabulary list has {len(vocabulary_list)} words")
    print(f"[DEBUG] First 10 vocab words: {vocabulary_list[:10]}")
    
    # Create vocabulary list with POS information for OpenAI
    vocabulary_with_pos = []
    if vocabulary_pos_map:
        for word in vocabulary_list:
            word_pos = vocabulary_pos_map.get(word.lower(), 'unknown')
            vocabulary_with_pos.append(f"{word} ({word_pos})")
        vocabulary_str = ", ".join(vocabulary_with_pos)
    else:
        vocabulary_str = ", ".join(vocabulary_list)
    
    print(f"[DEBUG] Vocabulary with POS sample: {vocabulary_str[:200]}...")
    
    messages = [
        {"role": "system", "content": PARAGRAPH_ANALYSIS_SYSTEM_PROMPT},
        {"role": "user", "content": f"Text to analyze: '{text}'\n\nVocabulary list with POS information: {vocabulary_str}\n\nIMPORTANT: For each word you enhance, provide 2-5 alternative suggestions when possible. Aim to enhance at least 15% of content words. Be thorough and comprehensive - find every enhancement opportunity. ONLY suggest words that have the SAME part of speech as the original word, and ONLY use words from the provided vocabulary list."}
    ]
    
    try:
        response = call_openai(messages, max_tokens=1200, temperature=0.1)  # Lower temperature for consistency
        print(f"[DEBUG] OpenAI raw response: {response}")
        
        # Handle markdown-wrapped JSON response
        json_content = response.strip()
        if json_content.startswith("```json"):
            json_content = json_content[7:]
            if json_content.endswith("```"):
                json_content = json_content[:-3]
            json_content = json_content.strip()
        elif json_content.startswith("```"):
            lines = json_content.split('\n')
            if len(lines) > 1:
                json_content = '\n'.join(lines[1:-1])
            else:
                json_content = json_content[3:-3]
        
        print(f"[DEBUG] Cleaned JSON content: {json_content}")
        
        data = json.loads(json_content)
        print(f"[DEBUG] Parsed data: {data}")
        
        raw_result = data.get("enhancements", [])
        
        # Additional backend filtering for POS matching as safety net
        filtered_result = []
        if vocabulary_pos_map:
            for enhancement in raw_result:
                original_word = enhancement.get("original_word", "").lower()
                suggested_words = enhancement.get("suggested_words", [])
                original_pos = enhancement.get("original_pos", "").lower()
                
                # Filter suggested words to ensure they match POS and are in vocabulary
                filtered_suggestions = []
                for suggested_word in suggested_words:
                    # Check if word is in vocabulary list (case-insensitive)
                    word_in_vocab = any(w.lower() == suggested_word.lower() for w in vocabulary_list)
                    if not word_in_vocab:
                        continue
                    
                    # Check POS matching
                    suggested_pos = vocabulary_pos_map.get(suggested_word.lower(), "").lower()
                    if suggested_pos == original_pos or (not original_pos and suggested_pos):
                        filtered_suggestions.append(suggested_word)
                
                # Only keep enhancements with valid suggestions
                if filtered_suggestions:
                    enhancement_copy = enhancement.copy()
                    enhancement_copy["suggested_words"] = filtered_suggestions
                    filtered_result.append(enhancement_copy)
        else:
            # If no POS map available, just ensure words are in vocabulary
            for enhancement in raw_result:
                suggested_words = enhancement.get("suggested_words", [])
                filtered_suggestions = [
                    word for word in suggested_words
                    if any(w.lower() == word.lower() for w in vocabulary_list)
                ]
                if filtered_suggestions:
                    enhancement_copy = enhancement.copy()
                    enhancement_copy["suggested_words"] = filtered_suggestions
                    filtered_result.append(enhancement_copy)
        
        print(f"[DEBUG] Returning {len(filtered_result)} filtered enhancements")
        
        # If we got very few results, try a fallback approach
        if len(filtered_result) < 2:
            print(f"[DEBUG] Only got {len(filtered_result)} enhancements, trying fallback approach...")
            fallback_result = try_fallback_analysis(text, vocabulary_list, vocabulary_pos_map)
            if len(fallback_result) > len(filtered_result):
                print(f"[DEBUG] Fallback yielded {len(fallback_result)} enhancements, using fallback")
                return fallback_result
        
        # Enhance suggestions by ensuring multiple alternatives per word when possible
        enhanced_result = enhance_suggestion_count(filtered_result, vocabulary_list, vocabulary_pos_map)
        return enhanced_result
        
    except (json.JSONDecodeError, Exception) as e:
        print(f"[DEBUG] Error analyzing paragraph: {e}")
        if 'response' in locals():
            print(f"[DEBUG] Raw response that caused error: {response}")
        
        # Try fallback on error
        print(f"[DEBUG] Attempting fallback analysis due to error...")
        return try_fallback_analysis(text, vocabulary_list, vocabulary_pos_map)


def try_fallback_analysis(text: str, vocabulary_list: List[str], vocabulary_pos_map: Dict[str, str]) -> List[Dict]:
    """Fallback analysis with more aggressive enhancement detection"""
    print(f"[DEBUG] Starting fallback analysis...")
    
    fallback_prompt = """You are a vocabulary enhancement tool with a mandate to find enhancement opportunities.

RELAXED STRATEGY - Find enhancements even if they're subtle:
1. Look for ANY word that could be made more sophisticated, descriptive, or precise
2. Consider synonyms, more specific terms, and elevated vocabulary
3. Don't be conservative - if there's a more interesting word in the vocabulary, suggest it
4. Focus on these common words that are often enhanceable:
   - Simple adjectives: good, bad, big, small, nice, fine, great, awful
   - Common verbs: go, do, make, get, put, take, come, give, say, think
   - Basic nouns: thing, person, place, way, time, day, work, life
   - Simple adverbs: very, really, quite, pretty, rather

For EACH enhancement, provide 3-5 alternatives when possible.
Be thorough - scan every content word.

Return JSON with key 'enhancements' containing an array of objects with:
- 'original_word': the word to be replaced
- 'original_pos': the POS of the original word
- 'suggested_words': array of replacement words (aim for 3+ per word)
- 'context': the full sentence containing the word"""

    messages = [
        {"role": "system", "content": fallback_prompt},
        {"role": "user", "content": f"Find ALL possible enhancements in this text: '{text}'\n\nVocabulary list: {', '.join(vocabulary_list[:100])}{'...' if len(vocabulary_list) > 100 else ''}"}
    ]
    
    try:
        response = call_openai(messages, max_tokens=1200, temperature=0.3)  # Slightly higher temperature for creativity
        print(f"[DEBUG] Fallback OpenAI response: {response}")
        
        # Handle markdown-wrapped JSON response
        json_content = response.strip()
        if json_content.startswith("```json"):
            json_content = json_content[7:]
            if json_content.endswith("```"):
                json_content = json_content[:-3]
            json_content = json_content.strip()
        elif json_content.startswith("```"):
            lines = json_content.split('\n')
            if len(lines) > 1:
                json_content = '\n'.join(lines[1:-1])
            else:
                json_content = json_content[3:-3]
        
        data = json.loads(json_content)
        raw_result = data.get("enhancements", [])
        
        # Apply same filtering but be more lenient
        filtered_result = []
        for enhancement in raw_result:
            original_word = enhancement.get("original_word", "").lower()
            suggested_words = enhancement.get("suggested_words", [])
            
            # Filter suggestions but be more permissive
            filtered_suggestions = []
            for suggested_word in suggested_words:
                # Check if word is in vocabulary list (case-insensitive)
                word_in_vocab = any(w.lower() == suggested_word.lower() for w in vocabulary_list)
                if word_in_vocab:
                    filtered_suggestions.append(suggested_word)
            
            # Keep enhancement if we have any valid suggestions
            if filtered_suggestions:
                enhancement_copy = enhancement.copy()
                enhancement_copy["suggested_words"] = filtered_suggestions
                filtered_result.append(enhancement_copy)
        
        print(f"[DEBUG] Fallback analysis found {len(filtered_result)} enhancements")
        return filtered_result
        
    except Exception as e:
        print(f"[DEBUG] Fallback analysis failed: {e}")
        return []


def enhance_suggestion_count(enhancements: List[Dict], vocabulary_list: List[str], vocabulary_pos_map: Dict[str, str]) -> List[Dict]:
    """Enhance the suggestion count for each word by finding additional vocabulary matches"""
    print(f"[DEBUG] Enhancing suggestion counts...")
    
    # This function operates on the raw OpenAI results (before database lookup)
    # We just add more word strings here, and the main function will look them up in the database
    enhanced_enhancements = []
    for enhancement in enhancements:
        original_word = enhancement.get("original_word", "").lower()
        current_suggestions = enhancement.get("suggested_words", [])
        original_pos = enhancement.get("original_pos", "").lower()
        
        # If we already have 3+ suggestions, keep as-is
        if len(current_suggestions) >= 3:
            enhanced_enhancements.append(enhancement)
            continue
        
        # Try to find more suggestions of the same POS
        additional_suggestions = []
        if vocabulary_pos_map and original_pos:
            # Find all words with the same POS
            same_pos_words = [word for word, pos in vocabulary_pos_map.items() 
                            if pos.lower() == original_pos and word.lower().strip() not in [s.lower().strip() for s in current_suggestions] 
                            and word.lower().strip() != original_word.lower().strip()]
            
            # Add up to 2 more suggestions (to reach ~5 total)
            needed = min(3 - len(current_suggestions), len(same_pos_words))
            # Take only the word names, maintaining original capitalization from database
            additional_suggestions = same_pos_words[:needed]
        
        # Create enhanced suggestion list - just word strings, database lookup happens later
        all_suggestions = current_suggestions + additional_suggestions
        
        enhanced_enhancement = enhancement.copy()
        enhanced_enhancement["suggested_words"] = all_suggestions
        enhanced_enhancements.append(enhanced_enhancement)
    
    print(f"[DEBUG] Enhanced {len(enhanced_enhancements)} enhancements with additional suggestions")
    return enhanced_enhancements


def test_openai_connection() -> bool:
    """Test OpenAI API connection"""
    try:
        response = call_openai([
            {"role": "user", "content": "Test connection"}
        ], max_tokens=5)
        return True
    except Exception as e:
        print(f"OpenAI connection test failed: {e}")
        return False 