"""SQLAlchemy ORM models for metadata storage."""

import uuid
from datetime import datetime

from sqlalchemy import (
    Column, String, Float, Integer, DateTime, Text, ForeignKey, JSON
)
from sqlalchemy.orm import relationship

from app.core.database import Base


def generate_uuid() -> str:
    return str(uuid.uuid4())


class CaptureSession(Base):
    """A screen capture session (one 'watch' session)."""
    __tablename__ = "capture_sessions"

    id = Column(String, primary_key=True, default=generate_uuid)
    title = Column(String, nullable=False, default="Untitled Session")
    started_at = Column(DateTime, default=datetime.utcnow)
    ended_at = Column(DateTime, nullable=True)
    total_frames = Column(Integer, default=0)
    status = Column(String, default="idle")  # idle | capturing | processing | done

    scenes = relationship("Scene", back_populates="session", cascade="all, delete-orphan")


class Character(Base):
    """A detected and tracked character entity."""
    __tablename__ = "characters"

    id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String, nullable=False, default="Unknown")
    description = Column(Text, nullable=True)
    first_seen_at = Column(DateTime, default=datetime.utcnow)
    appearance_count = Column(Integer, default=1)
    chroma_id = Column(String, nullable=True)  # ID in ChromaDB vector store
    thumbnail_path = Column(String, nullable=True)
    metadata_ = Column("metadata", JSON, nullable=True)

    appearances = relationship("CharacterAppearance", back_populates="character", cascade="all, delete-orphan")


class Scene(Base):
    """A detected scene (between scene cuts)."""
    __tablename__ = "scenes"

    id = Column(String, primary_key=True, default=generate_uuid)
    session_id = Column(String, ForeignKey("capture_sessions.id"), nullable=False)
    scene_index = Column(Integer, nullable=False)
    start_time = Column(Float, nullable=False)
    end_time = Column(Float, nullable=True)
    thumbnail_path = Column(String, nullable=True)
    description = Column(Text, nullable=True)
    location = Column(String, nullable=True)
    metadata_ = Column("metadata", JSON, nullable=True)

    session = relationship("CaptureSession", back_populates="scenes")
    character_appearances = relationship("CharacterAppearance", back_populates="scene", cascade="all, delete-orphan")
    items = relationship("DetectedItem", back_populates="scene", cascade="all, delete-orphan")


class CharacterAppearance(Base):
    """Links a character to a specific scene."""
    __tablename__ = "character_appearances"

    id = Column(String, primary_key=True, default=generate_uuid)
    character_id = Column(String, ForeignKey("characters.id"), nullable=False)
    scene_id = Column(String, ForeignKey("scenes.id"), nullable=False)
    timestamp = Column(Float, nullable=False)
    confidence = Column(Float, default=0.0)
    bbox = Column(JSON, nullable=True)  # [x1, y1, x2, y2]

    character = relationship("Character", back_populates="appearances")
    scene = relationship("Scene", back_populates="character_appearances")


class DetectedItem(Base):
    """An item or location detected in a scene."""
    __tablename__ = "detected_items"

    id = Column(String, primary_key=True, default=generate_uuid)
    scene_id = Column(String, ForeignKey("scenes.id"), nullable=False)
    label = Column(String, nullable=False)
    category = Column(String, default="item")  # item | location | weapon | vehicle
    confidence = Column(Float, default=0.0)
    bbox = Column(JSON, nullable=True)
    chroma_id = Column(String, nullable=True)
    timestamp = Column(Float, nullable=False)

    scene = relationship("Scene", back_populates="items")


class StoryArc(Base):
    """An LLM-generated story arc summary."""
    __tablename__ = "story_arcs"

    id = Column(String, primary_key=True, default=generate_uuid)
    session_id = Column(String, ForeignKey("capture_sessions.id"), nullable=False)
    title = Column(String, nullable=False)
    summary = Column(Text, nullable=False)
    character_ids = Column(JSON, nullable=True)
    scene_ids = Column(JSON, nullable=True)
    generated_at = Column(DateTime, default=datetime.utcnow)
