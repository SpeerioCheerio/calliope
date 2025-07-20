from sqlalchemy import Column, Integer, String, DateTime, Text, CheckConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from datetime import datetime

Base = declarative_base()


class Word(Base):
    __tablename__ = "words"

    id = Column(Integer, primary_key=True, index=True)
    word = Column(String, unique=True, index=True, nullable=False)
    pos = Column(String, nullable=False)
    definition = Column(Text, nullable=False)
    example_sentence = Column(Text, nullable=False)
    rarity = Column(String, nullable=False)
    sentiment = Column(String, nullable=False)
    date_added = Column(DateTime, default=func.now())

    __table_args__ = (
        CheckConstraint(
            "rarity IN ('notty', 'luke', 'alex')",
            name="check_rarity"
        ),
        CheckConstraint(
            "sentiment IN ('positive', 'negative', 'neutral', 'formal')",
            name="check_sentiment"
        ),
    )


class Config(Base):
    __tablename__ = "config"

    key = Column(String, primary_key=True)
    value = Column(String, nullable=False) 