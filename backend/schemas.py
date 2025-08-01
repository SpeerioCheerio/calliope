from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from enum import Enum


class RarityEnum(str, Enum):
    notty = "notty"
    luke = "luke"
    alex = "alex"


class SentimentEnum(str, Enum):
    positive = "positive"
    negative = "negative"
    neutral = "neutral"
    formal = "formal"


class WordBase(BaseModel):
    word: str = Field(..., min_length=1, max_length=100)
    pos: str = Field(..., min_length=1, max_length=50)
    definition: str = Field(..., min_length=1)
    example_sentence: str = Field(..., min_length=1)
    rarity: RarityEnum
    sentiment: SentimentEnum


class WordCreate(WordBase):
    pass


class UpdateWordRequest(WordBase):
    pass


class WordResponse(WordBase):
    id: int
    date_added: datetime

    class Config:
        from_attributes = True


class AddWordRequest(BaseModel):
    word: str = Field(..., min_length=1, max_length=100)


class AddWordResponse(BaseModel):
    success: bool
    message: str
    word_data: Optional[WordResponse] = None


class ThesaurusRequest(BaseModel):
    word: str = Field(..., min_length=1, max_length=100)


class ThesaurusResponse(BaseModel):
    word: str
    synonyms: List[WordResponse]


class PredictionRequest(BaseModel):
    sentence: str = Field(..., min_length=1)
    delimiter_position: int = Field(..., ge=0)
    sentiment: Optional[SentimentEnum] = None
    pos: Optional[str] = None


class PredictionResponse(BaseModel):
    sentence: str
    suggestions: List[WordResponse]


class ParagraphAnalysisRequest(BaseModel):
    text: str = Field(..., min_length=1)


class WordSuggestion(BaseModel):
    original_word: str
    suggested_word: WordResponse
    context: str


class WordEnhancement(BaseModel):
    original_word: str
    suggested_words: List[WordResponse]
    context: str
    original_pos: Optional[str] = None


class ParagraphAnalysisResponse(BaseModel):
    original_text: str
    suggestions: List[WordSuggestion]  # Keep for backward compatibility if needed
    enhancements: List[WordEnhancement]


class FlashcardFilter(BaseModel):
    pos: Optional[str] = None
    rarity: Optional[RarityEnum] = None
    sentiment: Optional[SentimentEnum] = None
    limit: Optional[int] = Field(default=50, ge=1, le=500)
    offset: Optional[int] = Field(default=0, ge=0)


class DatabaseFilter(BaseModel):
    pos: Optional[str] = None
    rarity: Optional[RarityEnum] = None
    sentiment: Optional[SentimentEnum] = None
    search: Optional[str] = None
    limit: Optional[int] = Field(default=20, ge=1, le=1000)
    offset: Optional[int] = Field(default=0, ge=0)


class PaginatedDatabaseResponse(BaseModel):
    words: List[WordResponse]
    total_count: int
    current_page: int
    total_pages: int
    items_per_page: int
    has_next: bool
    has_previous: bool


class WordOfTheDayResponse(BaseModel):
    word_data: WordResponse
    is_new_day: bool


class SpellCheckRequest(BaseModel):
    word: str = Field(..., min_length=1, max_length=100)


class SpellSuggestion(BaseModel):
    word: str
    confidence: float = Field(..., ge=0.0, le=1.0)


class SpellCheckResponse(BaseModel):
    original_word: str
    suggestions: List[SpellSuggestion]
    found_exact_match: bool 