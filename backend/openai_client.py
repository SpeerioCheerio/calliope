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

PARAGRAPH_ANALYSIS_SYSTEM_PROMPT = """You are a vocabulary enhancement tool. Given a paragraph and a vocabulary list, identify simple words that can be upgraded using words from the vocabulary list. 

CRITICAL REQUIREMENTS:
1. ONLY suggest words that are EXACTLY in the provided vocabulary list (case-insensitive matching)
2. Consider the full sentence context when suggesting replacements
3. The suggested words must fit naturally in the sentence and maintain the original meaning and tone
4. Ensure grammatical correctness and contextual appropriateness
5. Do NOT suggest words that are not in the vocabulary list

For each word that can be enhanced, provide 1-5 alternative words from the vocabulary list that would work well in that specific sentence context. Return as JSON with key 'enhancements' containing an array of objects with 'original_word', 'suggested_words' (array of word strings that MUST be from the vocabulary list), and 'context' (the full sentence containing the word)."""


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


def analyze_paragraph(text: str, vocabulary_list: List[str]) -> List[Dict]:
    """Analyze paragraph for vocabulary enhancement opportunities"""
    vocabulary_str = ", ".join(vocabulary_list)
    
    # Debug prints
    print(f"[DEBUG] Analyzing paragraph: '{text[:100]}...' (len={len(text)})")
    print(f"[DEBUG] Vocabulary list has {len(vocabulary_list)} words")
    print(f"[DEBUG] First 10 vocab words: {vocabulary_list[:10]}")
    
    messages = [
        {"role": "system", "content": PARAGRAPH_ANALYSIS_SYSTEM_PROMPT},
        {"role": "user", "content": f"Paragraph: '{text}'. Vocabulary list: {vocabulary_str}"}
    ]
    
    try:
        response = call_openai(messages, max_tokens=500)  # Increase token limit for paragraph analysis
        print(f"[DEBUG] OpenAI raw response: {response}")
        
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
        
        print(f"[DEBUG] Cleaned JSON content: {json_content}")
        
        data = json.loads(json_content)
        print(f"[DEBUG] Parsed data: {data}")
        
        result = data.get("enhancements", [])
        print(f"[DEBUG] Returning {len(result)} enhancements")
        return result
    except (json.JSONDecodeError, Exception) as e:
        print(f"[DEBUG] Error analyzing paragraph: {e}")
        print(f"[DEBUG] Raw response that caused error: {response}")
        return []


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