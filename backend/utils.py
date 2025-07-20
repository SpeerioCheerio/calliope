from typing import List, Dict, Optional
import re
import string
from datetime import datetime
from spellchecker import SpellChecker


def clean_word(word: str) -> str:
    """Clean and normalize word input"""
    return word.strip().lower().title()


def validate_sentence_with_delimiter(sentence: str, delimiter_position: int) -> bool:
    """Validate sentence and delimiter position"""
    if not sentence or delimiter_position < 0:
        return False
    
    words = sentence.split()
    return delimiter_position < len(words)


def insert_delimiter_in_sentence(sentence: str, delimiter_position: int) -> str:
    """Insert delimiter (|) in sentence at specified position"""
    words = sentence.split()
    if delimiter_position >= len(words):
        return sentence
    
    words.insert(delimiter_position, "|")
    return " ".join(words)


def extract_words_from_text(text: str) -> List[str]:
    """Extract words from text, removing punctuation"""
    # Remove punctuation and convert to lowercase
    text = text.translate(str.maketrans('', '', string.punctuation))
    words = text.lower().split()
    
    # Filter out very short words and common words
    common_words = {
        'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with',
        'by', 'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had',
        'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might', 'must',
        'can', 'this', 'that', 'these', 'those', 'i', 'you', 'he', 'she', 'it', 'we', 'they'
    }
    
    return [word for word in words if len(word) > 2 and word not in common_words]


def format_word_for_display(word_data: Dict) -> Dict:
    """Format word data for frontend display"""
    return {
        'id': word_data.get('id'),
        'word': word_data.get('word', '').title(),
        'pos': word_data.get('pos', '').upper(),
        'definition': word_data.get('definition', ''),
        'example_sentence': word_data.get('example_sentence', ''),
        'rarity': word_data.get('rarity', 'notty'),
        'sentiment': word_data.get('sentiment', 'neutral'),
        'date_added': word_data.get('date_added')
    }


def get_rarity_color(rarity: str) -> str:
    """Get color code for rarity display"""
    colors = {
        'notty': '#4CAF50',  # Green
        'luke': '#FF9800',   # Orange
        'alex': '#F44336'    # Red
    }
    return colors.get(rarity, '#9E9E9E')


def get_sentiment_icon(sentiment: str) -> str:
    """Get icon for sentiment display"""
    icons = {
        'positive': '',
        'negative': '',
        'neutral': '',
        'formal': ''
    }
    return icons.get(sentiment, '')


def validate_openai_response(response: Dict, required_fields: List[str]) -> bool:
    """Validate OpenAI API response has required fields"""
    if not isinstance(response, dict):
        return False
    
    for field in required_fields:
        if field not in response:
            return False
    
    return True


def sanitize_text_input(text: str) -> str:
    """Sanitize text input to prevent injection attacks"""
    # Remove potentially dangerous characters
    text = re.sub(r'[<>"\']', '', text)
    return text.strip()


def chunk_list(lst: List, chunk_size: int) -> List[List]:
    """Split list into chunks of specified size"""
    return [lst[i:i + chunk_size] for i in range(0, len(lst), chunk_size)]


def calculate_word_frequency(words: List[str]) -> Dict[str, int]:
    """Calculate frequency of words in a list"""
    frequency = {}
    for word in words:
        word = word.lower()
        frequency[word] = frequency.get(word, 0) + 1
    return frequency


def get_unique_pos_list(words: List[Dict]) -> List[str]:
    """Get unique parts of speech from word list"""
    pos_set = set()
    for word in words:
        pos = word.get('pos', '').upper()
        if pos:
            pos_set.add(pos)
    return sorted(list(pos_set))


def format_date_for_display(date_obj) -> str:
    """Format datetime object for display"""
    if isinstance(date_obj, datetime):
        return date_obj.strftime("%Y-%m-%d %H:%M")
    return str(date_obj)


def generate_flashcard_stats(words: List[Dict]) -> Dict:
    """Generate statistics for flashcard session"""
    total_words = len(words)
    rarity_counts = {}
    sentiment_counts = {}
    pos_counts = {}
    
    for word in words:
        rarity = word.get('rarity', 'notty')
        sentiment = word.get('sentiment', 'neutral')
        pos = word.get('pos', 'unknown').upper()
        
        rarity_counts[rarity] = rarity_counts.get(rarity, 0) + 1
        sentiment_counts[sentiment] = sentiment_counts.get(sentiment, 0) + 1
        pos_counts[pos] = pos_counts.get(pos, 0) + 1
    
    return {
        'total_words': total_words,
        'rarity_distribution': rarity_counts,
        'sentiment_distribution': sentiment_counts,
        'pos_distribution': pos_counts
    }


def escape_sql_wildcards(text: str) -> str:
    """Escape SQL wildcard characters in text"""
    return text.replace('%', '\\%').replace('_', '\\_')


def validate_word_input(word: str) -> tuple[bool, str]:
    """Validate word input and return (is_valid, error_message)"""
    if not word:
        return False, "Word cannot be empty"
    
    if len(word) > 100:
        return False, "Word is too long (max 100 characters)"
    
    if not re.match(r'^[a-zA-Z\s\-\']+$', word):
        return False, "Word contains invalid characters"
    
    return True, "" 


def get_spell_suggestions(word: str, max_suggestions: int = 5) -> List[Dict[str, any]]:
    """Get spell suggestions for a potentially misspelled word"""
    try:
        # Initialize spell checker
        spell = SpellChecker()
        
        # Clean the word
        cleaned_word = word.strip().lower()
        
        # Check if the word is known (correctly spelled)
        if cleaned_word in spell:
            return [{
                'word': cleaned_word.title(),
                'confidence': 1.0
            }]
        
        # Get suggestions for unknown words
        suggestions = spell.candidates(cleaned_word)
        
        if not suggestions:
            return []
        
        # Convert to list and limit results
        suggestion_list = list(suggestions)[:max_suggestions]
        
        # Calculate confidence scores (simple distance-based scoring)
        results = []
        for suggestion in suggestion_list:
            # Calculate simple confidence based on edit distance
            distance = len(set(cleaned_word) ^ set(suggestion))
            max_len = max(len(cleaned_word), len(suggestion))
            confidence = max(0.1, 1.0 - (distance / max_len))
            
            results.append({
                'word': suggestion.title(),
                'confidence': round(confidence, 2)
            })
        
        # Sort by confidence (highest first)
        results.sort(key=lambda x: x['confidence'], reverse=True)
        
        return results
        
    except Exception as e:
        print(f"Error in spell checking: {str(e)}")
        return [] 