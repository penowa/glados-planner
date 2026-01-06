# src/core/models/reading_session.py
from sqlalchemy import Column, Integer, Float, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime

from .base import BaseModel

class ReadingSession(BaseModel):
    """Modelo para sessões de leitura."""
    __tablename__ = "reading_sessions"
    
    # Relacionamentos
    book_id = Column(Integer, ForeignKey("books.id"), nullable=False)
    book = relationship("Book", back_populates="reading_sessions")
    
    # Dados da sessão
    start_time = Column(DateTime, default=datetime.now, nullable=False)
    end_time = Column(DateTime, nullable=True)
    duration_minutes = Column(Float, nullable=True)  # Duração em minutos
    pages_read = Column(Integer, default=0)
    
    # Métricas
    focus_score = Column(Integer, nullable=True)  # 1-10
    comprehension_score = Column(Integer, nullable=True)  # 1-10
    notes = Column(Text, nullable=True)  # Notas sobre a sessão
    
    # Metadados
    location = Column(Text, nullable=True)  # Onde leu
    mood = Column(Text, nullable=True)  # Estado de espírito
    
    def calculate_duration(self) -> float:
        """Calcula duração da sessão em minutos."""
        if self.end_time and self.start_time:
            duration = self.end_time - self.start_time
            return duration.total_seconds() / 60
        return 0.0
    
    def pages_per_hour(self) -> float:
        """Calcula páginas por hora."""
        duration_hours = self.calculate_duration() / 60
        if duration_hours > 0:
            return self.pages_read / duration_hours
        return 0.0
    
    def __repr__(self):
        return f"<ReadingSession(book='{self.book.title if self.book else None}', pages={self.pages_read})>"
