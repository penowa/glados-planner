# src/core/repositories/reading_session_repository.py
from typing import List, Optional, Dict, Any
from datetime import datetime, date, timedelta
from sqlalchemy import select, func, and_

from ..database.repository import BaseRepository
from ..models.reading_session import ReadingSession

class ReadingSessionRepository(BaseRepository[ReadingSession]):
    """Repositório especializado para sessões de leitura."""
    
    def __init__(self, session=None):
        super().__init__(ReadingSession, session)
    
    def find_by_book(self, book_id: int) -> List[ReadingSession]:
        """Busca sessões de leitura de um livro específico."""
        return self.find(book_id=book_id)
    
    def find_by_date_range(self, start_date: date, end_date: date) -> List[ReadingSession]:
        """Busca sessões em um intervalo de datas."""
        start_datetime = datetime.combine(start_date, datetime.min.time())
        end_datetime = datetime.combine(end_date, datetime.max.time())
        
        stmt = select(self.model).where(
            and_(
                self.model.start_time >= start_datetime,
                self.model.start_time <= end_datetime
            )
        ).order_by(self.model.start_time)
        
        result = self.session.execute(stmt)
        return result.scalars().all()
    
    def find_today_sessions(self) -> List[ReadingSession]:
        """Busca sessões de hoje."""
        today = date.today()
        return self.find_by_date_range(today, today)
    
    def find_last_week_sessions(self) -> List[ReadingSession]:
        """Busca sessões da última semana."""
        today = date.today()
        week_ago = today - timedelta(days=7)
        return self.find_by_date_range(week_ago, today)
    
    def get_reading_stats(self, book_id: Optional[int] = None) -> Dict[str, Any]:
        """Retorna estatísticas de leitura."""
        stmt = select(
            func.count(self.model.id).label("total_sessions"),
            func.sum(self.model.pages_read).label("total_pages"),
            func.sum(self.model.duration_minutes).label("total_minutes"),
            func.avg(self.model.pages_read / (self.model.duration_minutes / 60)).label("avg_pages_per_hour")
        )
        
        if book_id:
            stmt = stmt.where(self.model.book_id == book_id)
        
        result = self.session.execute(stmt).first()
        
        return {
            "total_sessions": result.total_sessions or 0,
            "total_pages": result.total_pages or 0,
            "total_hours": round((result.total_minutes or 0) / 60, 2),
            "avg_pages_per_hour": round(result.avg_pages_per_hour or 0, 2)
        }
    
    def start_session(self, book_id: int, **kwargs) -> ReadingSession:
        """Inicia uma nova sessão de leitura."""
        session_data = {
            "book_id": book_id,
            "start_time": datetime.now(),
            **kwargs
        }
        return self.create(**session_data)
    
    def end_session(self, session_id: int, pages_read: int, **kwargs) -> Optional[ReadingSession]:
        """Finaliza uma sessão de leitura."""
        session = self.get(session_id)
        if not session:
            return None
        
        update_data = {
            "end_time": datetime.now(),
            "pages_read": pages_read,
            "duration_minutes": (datetime.now() - session.start_time).total_seconds() / 60,
            **kwargs
        }
        
        return self.update(session_id, **update_data)
    
    def get_daily_reading_time(self, target_date: date = None) -> float:
        """Retorna tempo total de leitura no dia."""
        if target_date is None:
            target_date = date.today()
        
        sessions = self.find_by_date_range(target_date, target_date)
        total_minutes = sum(session.calculate_duration() for session in sessions)
        
        return round(total_minutes / 60, 2)
