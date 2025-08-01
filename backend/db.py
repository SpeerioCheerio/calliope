import os
import json
from pathlib import Path
from sqlalchemy import create_engine, func, or_
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import IntegrityError
from models import Base, Word, Config
from schemas import WordCreate, DatabaseFilter, FlashcardFilter
from typing import List, Optional, Dict
from datetime import datetime, timedelta
import random


# Database setup
DATABASE_URL = "sqlite:///./calliope.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_tables():
    """Create database tables"""
    Base.metadata.create_all(bind=engine)


def init_database():
    """Initialize database with starting words if empty"""
    create_tables()
    db = SessionLocal()
    
    try:
        # Check if database is empty
        word_count = db.query(Word).count()
        if word_count == 0:
            # Load starting words
            starting_words_path = Path("../starting_words.json")
            if starting_words_path.exists():
                with open(starting_words_path, 'r', encoding='utf-8') as f:
                    words_data = json.load(f)
                
                for word_data in words_data:
                    word = Word(
                        word=word_data["word"],
                        pos=word_data["pos"],
                        definition=word_data["definition"],
                        example_sentence=word_data["example_sentence"],
                        rarity=word_data["rarity"],
                        sentiment=word_data["sentiment"],
                        date_added=datetime.fromisoformat(word_data["date_added"].replace('Z', '+00:00'))
                    )
                    db.add(word)
                
                db.commit()
                print(f"Loaded {len(words_data)} starting words into database")
            
            # Initialize config for Word of the Day
            set_config_value(db, "wotd_date", datetime.now().strftime("%Y-%m-%d"))
            set_config_value(db, "wotd_index", "0")
            
    except Exception as e:
        db.rollback()
        print(f"Error initializing database: {e}")
    finally:
        db.close()


def get_word_by_name(db: Session, word: str) -> Optional[Word]:
    """Get word by name (exact match, case insensitive)"""
    return db.query(Word).filter(Word.word.ilike(word)).first()


def add_word(db: Session, word_data: WordCreate) -> Word:
    """Add new word to database"""
    db_word = Word(**word_data.dict())
    db.add(db_word)
    db.commit()
    db.refresh(db_word)
    return db_word


def get_words_by_filter(db: Session, filter_params: DatabaseFilter) -> List[Word]:
    """Get words with filtering"""
    query = db.query(Word)
    
    if filter_params.pos:
        query = query.filter(Word.pos.ilike(f"%{filter_params.pos}%"))
    if filter_params.rarity:
        query = query.filter(Word.rarity == filter_params.rarity)
    if filter_params.sentiment:
        query = query.filter(Word.sentiment == filter_params.sentiment)
    
    return query.order_by(Word.date_added.desc()).offset(filter_params.offset).limit(filter_params.limit).all()


def get_words_by_filter_with_count(db: Session, filter_params: DatabaseFilter) -> Dict:
    """Get words with filtering and return total count for pagination"""
    query = db.query(Word)
    
    if filter_params.pos:
        query = query.filter(Word.pos.ilike(f"%{filter_params.pos}%"))
    if filter_params.rarity:
        query = query.filter(Word.rarity == filter_params.rarity)
    if filter_params.sentiment:
        query = query.filter(Word.sentiment == filter_params.sentiment)
    if filter_params.search:
        search_term = f"%{filter_params.search}%"
        query = query.filter(
            or_(
                Word.word.ilike(search_term),
                Word.definition.ilike(search_term),
                Word.example_sentence.ilike(search_term)
            )
        )
    
    # Get total count before applying limit/offset
    total_count = query.count()
    
    # Get the actual words with pagination
    words = query.order_by(Word.date_added.desc()).offset(filter_params.offset).limit(filter_params.limit).all()
    
    return {
        "words": words,
        "total_count": total_count,
        "current_page": (filter_params.offset // filter_params.limit) + 1 if filter_params.limit > 0 else 1,
        "total_pages": (total_count + filter_params.limit - 1) // filter_params.limit if filter_params.limit > 0 else 1,
        "items_per_page": filter_params.limit,
        "has_next": filter_params.offset + filter_params.limit < total_count,
        "has_previous": filter_params.offset > 0
    }


def get_words_for_flashcards(db: Session, filter_params: FlashcardFilter) -> List[Word]:
    """Get words for flashcards with filtering"""
    query = db.query(Word)
    
    if filter_params.pos:
        query = query.filter(Word.pos.ilike(f"%{filter_params.pos}%"))
    if filter_params.rarity:
        query = query.filter(Word.rarity == filter_params.rarity)
    if filter_params.sentiment:
        query = query.filter(Word.sentiment == filter_params.sentiment)
    
    # If we have a specific small limit (like last 10, 20, 30, etc.), order by most recent
    # Otherwise, randomize for variety
    if filter_params.limit and filter_params.limit <= 100:
        query = query.order_by(Word.date_added.desc())
    else:
        query = query.order_by(func.random())
    
    return query.offset(filter_params.offset).limit(filter_params.limit).all()


def get_words_by_pos(db: Session, pos: str) -> List[Word]:
    """Get words by part of speech"""
    return db.query(Word).filter(Word.pos.ilike(f"%{pos}%")).all()


def get_all_words(db: Session) -> List[Word]:
    """Get all words"""
    return db.query(Word).all()


def get_random_word(db: Session) -> Optional[Word]:
    """Get random word"""
    return db.query(Word).order_by(func.random()).first()


def get_config_value(db: Session, key: str) -> Optional[str]:
    """Get config value"""
    config = db.query(Config).filter(Config.key == key).first()
    return config.value if config else None


def set_config_value(db: Session, key: str, value: str):
    """Set config value"""
    config = db.query(Config).filter(Config.key == key).first()
    if config:
        config.value = value
    else:
        config = Config(key=key, value=value)
        db.add(config)
    db.commit()


def get_word_of_the_day(db: Session) -> Dict:
    """Get word of the day with cycling logic"""
    today = datetime.now().strftime("%Y-%m-%d")
    last_wotd_date = get_config_value(db, "wotd_date")
    wotd_index = int(get_config_value(db, "wotd_index") or 0)
    
    is_new_day = last_wotd_date != today
    
    if is_new_day:
        # Get total word count
        total_words = db.query(Word).count()
        
        if total_words == 0:
            return None
        
        # Cycle through all words
        if wotd_index >= total_words:
            wotd_index = 0
        
        # Get the word at current index
        word = db.query(Word).offset(wotd_index).first()
        
        # Update config
        set_config_value(db, "wotd_date", today)
        set_config_value(db, "wotd_index", str(wotd_index + 1))
        
        return {"word": word, "is_new_day": True}
    else:
        # Return previous word (index - 1)
        if wotd_index > 0:
            word = db.query(Word).offset(wotd_index - 1).first()
        else:
            word = db.query(Word).first()
        
        return {"word": word, "is_new_day": False}


def search_words_by_similarity(db: Session, word: str, limit: int = 10) -> List[Word]:
    """Search for words similar to input word (for thesaurus)"""
    # Simple similarity search - can be enhanced with more sophisticated matching
    return db.query(Word).filter(
        Word.word.ilike(f"%{word}%") | 
        Word.definition.ilike(f"%{word}%")
    ).limit(limit).all()


def get_word_count(db: Session) -> int:
    """Get total word count"""
    return db.query(Word).count()


def get_words_for_prediction(db: Session, context: str, limit: int = 5) -> List[Word]:
    """Get words suitable for prediction based on context"""
    # Simple implementation - can be enhanced with more sophisticated matching
    return db.query(Word).filter(
        Word.definition.ilike(f"%{context}%") | 
        Word.word.ilike(f"%{context}%")
    ).limit(limit).all()


def update_word(db: Session, word_id: int, word_data: WordCreate) -> Optional[Word]:
    """Update an existing word in the database"""
    db_word = db.query(Word).filter(Word.id == word_id).first()
    if not db_word:
        return None
    
    # Update all fields
    for key, value in word_data.dict().items():
        setattr(db_word, key, value)
    
    db.commit()
    db.refresh(db_word)
    return db_word


def delete_word(db: Session, word_id: int) -> bool:
    """Delete a word from the database"""
    db_word = db.query(Word).filter(Word.id == word_id).first()
    if not db_word:
        return False
    
    db.delete(db_word)
    db.commit()
    return True


def get_word_by_id(db: Session, word_id: int) -> Optional[Word]:
    """Get word by ID"""
    return db.query(Word).filter(Word.id == word_id).first()


def get_words_added_today(db: Session) -> int:
    """Get count of words added today"""
    today = datetime.utcnow().date()
    return db.query(Word).filter(
        func.date(Word.date_added) == today
    ).count()


def get_current_streak(db: Session) -> int:
    """Calculate current streak of consecutive days with word additions"""
    today = datetime.utcnow().date()
    current_date = today
    streak = 0
    
    while True:
        # Check if any words were added on this date
        words_on_date = db.query(Word).filter(
            func.date(Word.date_added) == current_date
        ).count()
        
        if words_on_date > 0:
            streak += 1
            current_date -= timedelta(days=1)
        else:
            break
    
    return streak 