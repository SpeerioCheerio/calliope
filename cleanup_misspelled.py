#!/usr/bin/env python3
"""
Simple script to clean up misspelled words from database
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

def cleanup_misspelled():
    try:
        from db import get_db, get_word_by_name
        from sqlalchemy.orm import Session
        
        # Get database session
        db = next(get_db())
        
        # Remove the specific misspelled word "acommodate"
        misspelled_word = get_word_by_name(db, "Acommodate")
        
        if misspelled_word:
            print(f"Found misspelled word: {misspelled_word.word}")
            print(f"Definition: {misspelled_word.definition}")
            print("Removing from database...")
            
            db.delete(misspelled_word)
            db.commit()
            print("✅ Successfully removed!")
        else:
            print("No misspelled 'acommodate' found in database.")
        
        db.close()
        
    except Exception as e:
        print(f"Error: {e}")
        print("Make sure you're running this from the project root directory.")

if __name__ == "__main__":
    cleanup_misspelled() 