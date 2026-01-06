# src/core/repositories/book_repository.py
from typing import List, Optional, Dict, Any
from datetime import date
from sqlalchemy import and_, or_, func, select

from ..database.repository import BaseRepository
from ..models.book import Book, BookStatus, ReadingPriority

class BookRepository(BaseRepository[Book]):
    """Repositório especializado para operações com livros."""
    
    def __init__(self, session=None):
        super().__init__(Book, session)
    
    def find_by_status(self, status: BookStatus) -> List[Book]:
        """Busca livros por status."""
        return self.find(status=status)
    
    def find_by_author(self, author: str) -> List[Book]:
        """Busca livros por autor."""
        return self.find(author=author)
    
    def find_by_discipline(self, discipline: str) -> List[Book]:
        """Busca livros por disciplina."""
        return self.find(discipline=discipline)
    
    def find_with_deadline_approaching(self, days: int = 7) -> List[Book]:
        """Busca livros com deadline se aproximando."""
        from datetime import date, timedelta
        today = date.today()
        deadline_limit = today + timedelta(days=days)
        
        stmt = select(self.model).where(
            and_(
                self.model.deadline.isnot(None),
                self.model.deadline <= deadline_limit,
                self.model.status != BookStatus.COMPLETED
            )
        ).order_by(self.model.deadline)
        
        result = self.session.execute(stmt)
        return result.scalars().all()
    
    def get_reading_progress(self) -> Dict[str, Any]:
        """Retorna estatísticas de progresso de leitura."""
        stmt = select(
            func.count(self.model.id).label("total"),
            func.sum(self.model.total_pages).label("total_pages"),
            func.sum(self.model.current_page).label("read_pages"),
            func.avg(self.model.current_page / self.model.total_pages * 100).label("avg_progress")
        ).where(self.model.status != BookStatus.NOT_STARTED)
        
        result = self.session.execute(stmt).first()
        
        return {
            "total_books": result.total or 0,
            "total_pages": result.total_pages or 0,
            "read_pages": result.read_pages or 0,
            "avg_progress": round(result.avg_progress or 0, 2)
        }
    
    def update_progress(self, book_id: int, current_page: int) -> Optional[Book]:
        """Atualiza o progresso de leitura de um livro."""
        book = self.get(book_id)
        if not book:
            return None
        
        # Atualiza status se necessário
        if current_page >= book.total_pages:
            return self.update(book_id, 
                current_page=current_page,
                status=BookStatus.COMPLETED,
                finish_date=date.today()
            )
        elif current_page > 0 and book.status == BookStatus.NOT_STARTED:
            return self.update(book_id,
                current_page=current_page,
                status=BookStatus.IN_PROGRESS,
                start_date=date.today()
            )
        else:
            return self.update(book_id, current_page=current_page)
    
    def get_recommended_daily_pages(self, book_id: int) -> int:
        """Calcula páginas diárias recomendadas para cumprir o prazo."""
        book = self.get(book_id)
        if not book or not book.deadline:
            return 0
        
        from datetime import date
        days_left = (book.deadline - date.today()).days
        
        if days_left <= 0:
            return book.total_pages - book.current_page
        
        remaining_pages = book.total_pages - book.current_page
        return max(1, remaining_pages // max(1, days_left))
