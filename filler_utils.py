"""
Filler Word Filtering Utilities
Database management and filtering logic for filler words.
"""

import logging
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

logger = logging.getLogger("filler-utils")

# SQLAlchemy setup for SQLite database
Base = declarative_base()
engine = create_engine('sqlite:///filler_words.db', echo=False)
Session = sessionmaker(bind=engine)


class FillerWord(Base):
    """SQLAlchemy model for filler words."""
    __tablename__ = 'filler_words'

    id = Column(Integer, primary_key=True)
    word = Column(String, unique=True, nullable=False)


# Create tables if they don't exist
Base.metadata.create_all(engine)


def initialize_filler_words():
    """Initialize the database with default filler words if empty."""
    session = Session()
    try:
        # Check if database is empty
        if session.query(FillerWord).count() == 0:
            # Default filler words (English and Hindi)
            default_words = [
                "umm", "uh", "um", "so",
                "hmm", "hm", "ah", "er", "erm", "ok", "ahhh", "hmmm",
                "eh", "ehh", "uhh", "haan", "acha","uh-huh"
            ]

            for word in default_words:
                session.add(FillerWord(word=word.lower()))

            session.commit()
            logger.info(f"Initialized database with {len(default_words)} filler words")
    except Exception as e:
        logger.error(f"Error initializing filler words: {e}")
        session.rollback()
    finally:
        session.close()


def get_filler_words() -> set:
    """Fetch all filler words from the database."""
    session = Session()
    try:
        words = session.query(FillerWord.word).all()
        return {word[0].lower() for word in words}
    except Exception as e:
        logger.error(f"Error fetching filler words: {e}")
        # Return default set if database fails
        return {"umm", "uh", "um", "hmm", "hm", "ah", "er"}
    finally:
        session.close()


def is_only_filler_words(text: str) -> bool:
    """
    Check if the text contains only filler words.

    Args:
        text: The transcribed text to check

    Returns:
        True if text contains only filler words, False otherwise
    """
    if not text:
        return True

    # Normalize the text
    text_lower = text.lower().strip()

    # Remove common punctuation
    text_clean = text_lower.replace(".", "").replace(",", "").replace("?", "").replace("!", "")

    # Split into words
    words = text_clean.split()

    if not words:
        return True

    # Reload filler words from database to get latest changes
    current_filler_words = get_filler_words()

    # Check if all words are filler words
    for word in words:
        if word not in current_filler_words:
            # Found a real word - not just filler
            return False

    # All words are filler words
    logger.info(f"🛑 Detected only filler words: '{text}' - will be filtered")
    return True


# Initialize database with default words on module import
initialize_filler_words()

# Cache filler words (will be loaded from DB at startup)
FILLER_WORDS = get_filler_words()
