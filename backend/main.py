from fastapi import FastAPI, Depends, HTTPException, status, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from typing import List, Dict, Optional
import json
from pathlib import Path

# Local imports
from db import get_db, init_database, get_word_by_name, add_word, get_words_by_filter, get_words_for_flashcards
from db import get_word_of_the_day, search_words_by_similarity, get_all_words, get_words_for_prediction
from db import update_word, delete_word, get_word_by_id, get_words_by_filter_with_count
from db import get_words_added_today, get_current_streak
from models import Word
from schemas import (
    AddWordRequest, AddWordResponse, WordResponse, ThesaurusRequest, ThesaurusResponse,
    PredictionRequest, PredictionResponse, ParagraphAnalysisRequest, ParagraphAnalysisResponse,
    FlashcardFilter, DatabaseFilter, WordOfTheDayResponse, WordCreate, WordSuggestion,
    SpellCheckRequest, SpellCheckResponse, SpellSuggestion, UpdateWordRequest, PaginatedDatabaseResponse,
    WordEnhancement
)
from openai_client import get_word_definition, find_synonyms, predict_words, analyze_paragraph
from utils import clean_word, validate_word_input, sanitize_text_input, insert_delimiter_in_sentence, get_spell_suggestions

# Initialize FastAPI app
app = FastAPI(
    title="Calliope Vocabulary App",
    description="Advanced vocabulary learning and enhancement tool",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory="../frontend"), name="static")

# Initialize database on startup
@app.on_event("startup")
async def startup_event():
    init_database()

# Root endpoint
@app.get("/", response_class=HTMLResponse)
async def root():
    return """
    <html>
        <head>
            <title>Calliope Vocabulary App</title>
        </head>
        <body>
            <h1>Calliope Vocabulary App</h1>
            <p>API is running! Visit the frontend at /static/index.html</p>
            <p>API Documentation: <a href="/docs">/docs</a></p>
        </body>
    </html>
    """

# Health check endpoint
@app.get("/health")
async def health_check():
    return {"status": "healthy", "message": "Calliope API is running"}

# Word of the Day endpoint
@app.get("/api/word-of-the-day", response_model=WordOfTheDayResponse)
async def get_word_of_the_day_endpoint(db: Session = Depends(get_db)):
    """Get the word of the day"""
    try:
        wotd_data = get_word_of_the_day(db)
        if not wotd_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No words available for word of the day"
            )
        
        return WordOfTheDayResponse(
            word_data=WordResponse.model_validate(wotd_data["word"]),
            is_new_day=wotd_data["is_new_day"]
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting word of the day: {str(e)}"
        )

# Add word endpoint
@app.post("/api/add-word", response_model=AddWordResponse)
async def add_word_endpoint(request: AddWordRequest, db: Session = Depends(get_db)):
    """Add a new word to the database"""
    try:
        # Validate word input
        is_valid, error_message = validate_word_input(request.word)
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_message
            )
        
        # Clean word input
        word = clean_word(request.word)
        
        # Check if word already exists
        existing_word = get_word_by_name(db, word)
        if existing_word:
            return AddWordResponse(
                success=False,
                message=f"Word '{word}' already exists in the database",
                word_data=WordResponse.model_validate(existing_word)
            )
        
        # FIRST: Check spelling before calling OpenAI
        spell_suggestions = get_spell_suggestions(word)
        
        # If spell checker returns suggestions AND the top suggestion is different from input,
        # then the input word is likely misspelled
        if (spell_suggestions and len(spell_suggestions) > 0 and 
            spell_suggestions[0]['word'].lower() != word.lower()):
            # This means the word is misspelled - trigger spell checking on frontend
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Word '{word}' may be misspelled. Please check spelling or try a different word."
            )
        # If suggestions are empty OR top suggestion matches input word, proceed to OpenAI
        
        # Get word definition from OpenAI (only if spelling is correct)
        word_data = get_word_definition(word)
        if not word_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Word '{word}' not found in dictionary. Please check spelling or try a different word."
            )
        
        # Create word object
        word_create = WordCreate(
            word=word,
            pos=word_data["pos"],
            definition=word_data["definition"],
            example_sentence=word_data["example_sentence"],
            rarity=word_data["rarity"],
            sentiment=word_data["sentiment"]
        )
        
        # Add to database
        db_word = add_word(db, word_create)
        
        return AddWordResponse(
            success=True,
            message=f"Word '{word}' added successfully",
            word_data=WordResponse.model_validate(db_word)
        )
    
    except IntegrityError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Word already exists in the database"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error adding word: {str(e)}"
        )

# View database endpoint
@app.get("/api/database", response_model=PaginatedDatabaseResponse)
async def get_database_words(
    pos: Optional[str] = None,
    rarity: Optional[str] = None,
    sentiment: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = Query(default=20, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db)
):
    """Get words from database with filtering options and pagination info"""
    try:
        filter_params = DatabaseFilter(
            pos=pos,
            rarity=rarity,
            sentiment=sentiment,
            search=search,
            limit=limit,
            offset=offset
        )
        
        result = get_words_by_filter_with_count(db, filter_params)
        
        return PaginatedDatabaseResponse(
            words=[WordResponse.model_validate(word) for word in result["words"]],
            total_count=result["total_count"],
            current_page=result["current_page"],
            total_pages=result["total_pages"],
            items_per_page=result["items_per_page"],
            has_next=result["has_next"],
            has_previous=result["has_previous"]
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting database words: {str(e)}"
        )

# Update word endpoint
@app.put("/api/update-word/{word_id}", response_model=WordResponse)
async def update_word_endpoint(word_id: int, request: UpdateWordRequest, db: Session = Depends(get_db)):
    """Update an existing word in the database"""
    try:
        # First check if the word exists
        existing_word = get_word_by_id(db, word_id)
        if not existing_word:
            # Log the word ID that was not found for debugging
            print(f"DEBUG: Word with ID {word_id} not found in database")
            
            # Check if any words exist at all
            total_words = db.query(Word).count()
            print(f"DEBUG: Total words in database: {total_words}")
            
            # Get the actual word IDs that exist
            existing_ids = [w.id for w in db.query(Word.id).limit(10).all()]
            print(f"DEBUG: Sample existing word IDs: {existing_ids}")
            
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Word with ID {word_id} not found. The word may have been deleted or the database may have been reset."
            )
        
        # Create WordCreate object from request
        word_data = WordCreate(
            word=request.word,
            pos=request.pos,
            definition=request.definition,
            example_sentence=request.example_sentence,
            rarity=request.rarity,
            sentiment=request.sentiment
        )
        
        # Log the update attempt
        print(f"DEBUG: Attempting to update word ID {word_id} with data: {request.word}")
        
        updated_word = update_word(db, word_id, word_data)
        if not updated_word:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Failed to update word with ID {word_id}"
            )
        
        print(f"DEBUG: Successfully updated word ID {word_id}")
        return WordResponse.model_validate(updated_word)
    
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        print(f"DEBUG: Unexpected error updating word {word_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating word: {str(e)}"
        )

# Delete word endpoint
@app.delete("/api/delete-word/{word_id}")
async def delete_word_endpoint(word_id: int, db: Session = Depends(get_db)):
    """Delete a word from the database"""
    try:
        # Get the word first to return it
        db_word = get_word_by_id(db, word_id)
        if not db_word:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Word with ID {word_id} not found"
            )
        
        # Store the word data before deletion
        word_data = WordResponse.model_validate(db_word)
        
        # Delete the word
        success = delete_word(db, word_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to delete word with ID {word_id}"
            )
        
        return {"success": True, "message": f"Word '{word_data.word}' deleted successfully", "deleted_word": word_data}
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting word: {str(e)}"
        )

# Debug endpoint to check database state
@app.get("/api/debug/database-info")
async def get_database_debug_info(db: Session = Depends(get_db)):
    """Debug endpoint to check database state"""
    try:
        total_words = db.query(Word).count()
        
        # Get first 20 word IDs and words
        sample_words = db.query(Word.id, Word.word).limit(20).all()
        
        # Get the latest words
        latest_words = db.query(Word.id, Word.word, Word.date_added).order_by(Word.date_added.desc()).limit(10).all()
        
        return {
            "total_words": total_words,
            "sample_words": [{"id": w.id, "word": w.word} for w in sample_words],
            "latest_words": [{"id": w.id, "word": w.word, "date_added": w.date_added} for w in latest_words]
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting debug info: {str(e)}"
        )

# Thesaurus endpoint
@app.post("/api/thesaurus", response_model=ThesaurusResponse)
async def get_thesaurus_results(request: ThesaurusRequest, db: Session = Depends(get_db)):
    """Get synonyms for a word from the database"""
    try:
        word = clean_word(request.word)
        
        # Get all words from database for vocabulary list
        all_words = get_all_words(db)
        vocabulary_list = [w.word for w in all_words]
        
        # Find synonyms using OpenAI
        synonym_words = find_synonyms(word, vocabulary_list)
        
        # Get full word data for synonyms
        synonyms = []
        for synonym in synonym_words:
            db_word = get_word_by_name(db, synonym)
            if db_word:
                synonyms.append(WordResponse.model_validate(db_word))
        
        return ThesaurusResponse(
            word=word,
            synonyms=synonyms
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting thesaurus results: {str(e)}"
        )

# Prediction endpoint
@app.post("/api/predict", response_model=PredictionResponse)
async def predict_word_fill(request: PredictionRequest, db: Session = Depends(get_db)):
    """Predict words to fill blank in sentence"""
    try:
        # Sanitize input
        sentence = sanitize_text_input(request.sentence)
        
        # Insert delimiter in sentence
        sentence_with_blank = insert_delimiter_in_sentence(sentence, request.delimiter_position)
        
        # Get words from database for vocabulary list, filtered by sentiment and POS if provided
        query = db.query(Word)
        
        if request.sentiment:
            query = query.filter(Word.sentiment == request.sentiment)
        
        if request.pos:
            query = query.filter(Word.pos == request.pos.lower())
        
        filtered_words = query.all()
        vocabulary_list = [w.word for w in filtered_words]
        
        # Get predictions from OpenAI
        predicted_words = predict_words(sentence_with_blank, vocabulary_list)
        
        # Get full word data for predictions, ensuring they match the filters
        suggestions = []
        for word in predicted_words:
            db_word = get_word_by_name(db, word)
            if db_word:
                # Double-check that the word matches our filters
                matches_filters = True
                
                if request.sentiment and db_word.sentiment != request.sentiment:
                    matches_filters = False
                
                if request.pos and db_word.pos.lower() != request.pos.lower():
                    matches_filters = False
                
                if matches_filters:
                    suggestions.append(WordResponse.model_validate(db_word))
        
        return PredictionResponse(
            sentence=sentence,
            suggestions=suggestions
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error predicting words: {str(e)}"
        )

# Paragraph analysis endpoint
@app.post("/api/analyze-paragraph", response_model=ParagraphAnalysisResponse)
async def analyze_paragraph_endpoint(request: ParagraphAnalysisRequest, db: Session = Depends(get_db)):
    """Analyze paragraph for vocabulary enhancement opportunities"""
    try:
        # Sanitize input
        text = sanitize_text_input(request.text)
        
        # Get all words from database for vocabulary list
        all_words = get_all_words(db)
        vocabulary_list = [w.word for w in all_words]
        
        # Create POS mapping for vocabulary words to enable POS matching
        vocabulary_pos_map = {w.word.lower(): w.pos for w in all_words}
        
        # Debug print
        print(f"[DEBUG] Retrieved {len(all_words)} words from database")
        print(f"[DEBUG] Vocabulary list: {vocabulary_list[:10]}...")
        print(f"[DEBUG] POS map sample: {dict(list(vocabulary_pos_map.items())[:5])}")
        
        # Analyze paragraph using OpenAI with POS information
        analysis_results = analyze_paragraph(text, vocabulary_list, vocabulary_pos_map)
        
        # Debug print
        print(f"[DEBUG] OpenAI analysis_results: {analysis_results}")
        
        # Format suggestions (backward compatibility)
        suggestions = []
        enhancements = []
        
        for result in analysis_results:
            original_word = result.get("original_word", "")
            suggested_words = result.get("suggested_words", [])
            context = result.get("context", "")
            

            
            # Get full word data for suggested words
            enhancement_words = []
            for suggested_word in suggested_words:
                # Clean the suggested word (remove extra spaces, handle case)
                clean_word = suggested_word.strip().lower()
                db_word = get_word_by_name(db, clean_word)
                if db_word:
                    word_response = WordResponse.model_validate(db_word)
                    enhancement_words.append(word_response)
                else:
                    # Try with different cases if not found
                    db_word = get_word_by_name(db, suggested_word.strip())
                    if db_word:
                        word_response = WordResponse.model_validate(db_word)
                        enhancement_words.append(word_response)
            
            # Process enhancement_words for backward compatibility 
            for db_word in enhancement_words:
                # Also add to suggestions for backward compatibility (use first suggestion)
                if not suggestions or suggestions[-1].original_word != original_word:
                    suggestions.append(WordSuggestion(
                        original_word=original_word,
                        suggested_word=db_word,
                        context=context
                    ))
                    break  # Only add one to suggestions for backward compatibility
            
            # Add to enhancements if we have words
            if enhancement_words:
                enhancements.append(WordEnhancement(
                    original_word=original_word,
                    suggested_words=enhancement_words,
                    context=context
                ))
        
        return ParagraphAnalysisResponse(
            original_text=text,
            suggestions=suggestions,
            enhancements=enhancements
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error analyzing paragraph: {str(e)}"
        )

# Flashcards endpoint
@app.get("/api/flashcards", response_model=List[WordResponse])
async def get_flashcards(
    pos: Optional[str] = None,
    rarity: Optional[str] = None,
    sentiment: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db)
):
    """Get words for flashcard practice"""
    try:
        filter_params = FlashcardFilter(
            pos=pos,
            rarity=rarity,
            sentiment=sentiment,
            limit=limit,
            offset=offset
        )
        
        words = get_words_for_flashcards(db, filter_params)
        return [WordResponse.model_validate(word) for word in words]
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting flashcards: {str(e)}"
        )

# Get unique parts of speech
@app.get("/api/parts-of-speech")
async def get_parts_of_speech(db: Session = Depends(get_db)):
    """Get unique parts of speech from database"""
    try:
        words = get_all_words(db)
        pos_set = set()
        for word in words:
            pos_set.add(word.pos.lower())
        
        return {"parts_of_speech": sorted(list(pos_set))}
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting parts of speech: {str(e)}"
        )

# Get database statistics
@app.get("/api/stats")
async def get_database_stats(db: Session = Depends(get_db)):
    """Get database statistics"""
    try:
        all_words = get_all_words(db)
        total_words = len(all_words)
        
        # Count by rarity
        rarity_counts = {}
        sentiment_counts = {}
        pos_counts = {}
        
        for word in all_words:
            rarity = word.rarity
            sentiment = word.sentiment
            pos = word.pos.lower()
            
            rarity_counts[rarity] = rarity_counts.get(rarity, 0) + 1
            sentiment_counts[sentiment] = sentiment_counts.get(sentiment, 0) + 1
            pos_counts[pos] = pos_counts.get(pos, 0) + 1
        
        # Get words added today and current streak
        words_added_today = get_words_added_today(db)
        current_streak = get_current_streak(db)
        
        return {
            "total_words": total_words,
            "words_added_today": words_added_today,
            "current_streak": current_streak,
            "rarity_distribution": rarity_counts,
            "sentiment_distribution": sentiment_counts,
            "pos_distribution": pos_counts
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting database stats: {str(e)}"
        )

# Search words
@app.get("/api/search")
async def search_words(q: str, limit: int = 10, db: Session = Depends(get_db)):
    """Search words in database"""
    try:
        words = search_words_by_similarity(db, q, limit)
        return [WordResponse.model_validate(word) for word in words]
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error searching words: {str(e)}"
        )


# Spell checking endpoint
@app.post("/api/spell-check", response_model=SpellCheckResponse)
async def spell_check_word(request: SpellCheckRequest):
    """Check spelling of a word and provide suggestions"""
    try:
        # Validate word input
        is_valid, error_message = validate_word_input(request.word)
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_message
            )
        
        # Get spell suggestions
        suggestions = get_spell_suggestions(request.word)
        
        # Check if exact match was found
        found_exact_match = len(suggestions) > 0 and suggestions[0]['confidence'] == 1.0
        
        # Convert to SpellSuggestion objects
        spell_suggestions = [
            SpellSuggestion(
                word=suggestion['word'],
                confidence=suggestion['confidence']
            )
            for suggestion in suggestions
        ]
        
        return SpellCheckResponse(
            original_word=request.word,
            suggestions=spell_suggestions,
            found_exact_match=found_exact_match
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error checking spelling: {str(e)}"
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 