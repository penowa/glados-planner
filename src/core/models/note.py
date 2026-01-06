# src/core/models/note.py
from sqlalchemy import Column, String, Text, Integer, ForeignKey, Enum
from sqlalchemy.orm import relationship
import enum

from .base import BaseModel

class NoteType(enum.Enum):
    BOOK_SUMMARY = "book_summary"
    CLASS_NOTE = "class_note"
    CONCEPT = "concept"
    QUOTE = "quote"
    IDEA = "idea"

class Note(BaseModel):
    __tablename__ = "notes"
    
    title = Column(String(500), nullable=False)
    content = Column(Text, nullable=False)
    note_type = Column(Enum(NoteType), nullable=False)
    book_id = Column(Integer, ForeignKey("books.id"), nullable=True)
    # Usando backref para simplificar e evitar problemas circulares
    book = relationship("Book", backref="book_notes")
    
    # Campos adicionais
    obsidian_path = Column(String(500), nullable=True)
    tags = Column(Text, nullable=True)  # JSON string
    is_processed = Column(Integer, default=0)  # 0=pendente, 1=processado
    
    def __repr__(self):
        return f"<Note(title='{self.title}', type='{self.note_type}')>"
