# src/core/models/task.py
from sqlalchemy import Column, String, Text, Integer, DateTime, Enum, ForeignKey, Boolean
from sqlalchemy.orm import relationship
import enum
from datetime import datetime, time

from .base import BaseModel

class TaskType(enum.Enum):
    READING = "reading"
    WRITING = "writing"
    REVISION = "revision"
    RESEARCH = "research"
    MEETING = "meeting"
    EXAM = "exam"
    OTHER = "other"

class TaskPriority(enum.Enum):
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    URGENT = 4

class RecurrencePattern(enum.Enum):
    NONE = "none"
    DAILY = "daily"
    WEEKLY = "weekly"
    BIWEEKLY = "biweekly"
    MONTHLY = "monthly"

class Task(BaseModel):
    """Modelo para tarefas/agenda."""
    __tablename__ = "tasks"
    
    # Informações básicas
    title = Column(String(500), nullable=False, index=True)
    description = Column(Text, nullable=True)
    task_type = Column(Enum(TaskType), nullable=False)
    
    # Datas e horários
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    all_day = Column(Boolean, default=False)
    
    # Status e prioridade
    priority = Column(Integer, default=2)  # 1-4
    completed = Column(Boolean, default=False)
    completion_date = Column(DateTime, nullable=True)
    
    # Recurrence
    recurrence = Column(Enum(RecurrencePattern), default=RecurrencePattern.NONE)
    recurrence_end = Column(DateTime, nullable=True)
    
    # Categorização
    discipline = Column(String(100), nullable=True)
    course = Column(String(200), nullable=True)
    professor = Column(String(200), nullable=True)
    location = Column(String(200), nullable=True)
    
    # Relacionamentos
    parent_task_id = Column(Integer, ForeignKey("tasks.id"), nullable=True)
    subtasks = relationship("Task", backref="parent", remote_side="Task.id")
    book_id = Column(Integer, ForeignKey("books.id"), nullable=True)
    book = relationship("Book", backref="related_tasks")
    
    # Integração
    calendar_event_id = Column(String(200), nullable=True)  # Para integração externa
    obsidian_note_path = Column(String(500), nullable=True)
    
    def duration_hours(self) -> float:
        """Calcula duração em horas."""
        duration = self.end_time - self.start_time
        return duration.total_seconds() / 3600
