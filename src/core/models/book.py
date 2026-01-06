# src/core/models/book.py
from sqlalchemy import Column, String, Text, Integer, Date, Enum, ForeignKey
from sqlalchemy.orm import relationship
import enum

from .base import BaseModel

class BookStatus(enum.Enum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    PAUSED = "paused"

class ReadingPriority(enum.Enum):
    LOW = 1
    MEDIUM_LOW = 2
    MEDIUM = 3
    MEDIUM_HIGH = 4
    HIGH = 5

class Book(BaseModel):
    """Modelo para livros/leituras."""
    __tablename__ = "books"
    
    # Informações básicas
    title = Column(String(500), nullable=False, index=True)
    author = Column(String(200), nullable=False, index=True)
    isbn = Column(String(20), nullable=True, unique=True)
    publisher = Column(String(200), nullable=True)
    year = Column(Integer, nullable=True)
    edition = Column(String(50), nullable=True)
    
    # Metadados de leitura
    total_pages = Column(Integer, nullable=False)
    current_page = Column(Integer, default=0)
    total_chapters = Column(Integer, nullable=True)
    current_chapter = Column(String(100), nullable=True)
    
    # Status e prioridade
    status = Column(Enum(BookStatus), default=BookStatus.NOT_STARTED)
    priority = Column(Integer, default=3)  # 1-5
    difficulty = Column(Integer, default=3)  # 1-5
    
    # Classificação - CORRIGIDO: notes -> tags
    discipline = Column(String(100), nullable=True)  # Ética, Metafísica, etc.
    historical_period = Column(String(100), nullable=True)  # Antiga, Medieval, etc.
    tags = Column(Text, nullable=True)  # JSON string - NOME CORRIGIDO
    
    # Datas
    start_date = Column(Date, nullable=True)
    deadline = Column(Date, nullable=True)
    finish_date = Column(Date, nullable=True)
    
    # Integração
    obsidian_path = Column(String(500), nullable=True)
    cover_image_path = Column(String(500), nullable=True)
    
    # Relacionamentos
    reading_sessions = relationship("ReadingSession", back_populates="book", cascade="all, delete-orphan")
    # Mantemos como 'notes' para a relação, mas não conflita mais
    notes = relationship("Note", back_populates="book", cascade="all, delete-orphan")
    
    def progress_percentage(self) -> float:
        """Calcula porcentagem de progresso."""
        if self.total_pages == 0:
            return 0.0
        return (self.current_page / self.total_pages) * 100
    
    def days_remaining(self) -> int:
        """Calcula dias restantes até o deadline."""
        from datetime import date
        if not self.deadline:
            return None
        return (self.deadline - date.today()).days
    
    def total_reading_time(self) -> float:
        """Calcula tempo total de leitura em horas."""
        if not self.reading_sessions:
            return 0.0
        total_minutes = sum(session.calculate_duration() for session in self.reading_sessions)
        return total_minutes / 60
    
    def average_pages_per_hour(self) -> float:
        """Calcula média de páginas por hora."""
        total_time = self.total_reading_time()
        if total_time == 0:
            return 0.0
        
        total_pages_read = sum(session.pages_read for session in self.reading_sessions)
        return total_pages_read / total_time
