# src/core/repositories/note_repository.py
from typing import List, Optional, Dict, Any
from sqlalchemy import select, or_

from ..database.repository import BaseRepository
from ..models.note import Note, NoteType

class NoteRepository(BaseRepository[Note]):
    """Repositório especializado para operações com anotações."""
    
    def __init__(self, session=None):
        super().__init__(Note, session)
    
    def find_by_type(self, note_type: NoteType) -> List[Note]:
        """Busca anotações por tipo."""
        return self.find(note_type=note_type)
    
    def find_by_book(self, book_id: int) -> List[Note]:
        """Busca anotações de um livro específico."""
        return self.find(book_id=book_id)
    
    def find_with_content_like(self, search_term: str) -> List[Note]:
        """Busca anotações com conteúdo similar."""
        stmt = select(self.model).where(
            or_(
                self.model.title.ilike(f"%{search_term}%"),
                self.model.content.ilike(f"%{search_term}%")
            )
        )
        
        result = self.session.execute(stmt)
        return result.scalars().all()
    
    def find_unprocessed(self) -> List[Note]:
        """Busca anotações não processadas."""
        return self.find(is_processed=0)
    
    def mark_as_processed(self, note_id: int) -> Optional[Note]:
        """Marca uma anotação como processada."""
        return self.update(note_id, is_processed=1)
    
    def get_stats_by_type(self) -> Dict[str, int]:
        """Retorna estatísticas de anotações por tipo."""
        stmt = select(
            self.model.note_type,
            func.count(self.model.id).label("count")
        ).group_by(self.model.note_type)
        
        result = self.session.execute(stmt)
        
        stats = {}
        for row in result:
            stats[row.note_type.value] = row.count
        
        return stats
    
    def link_to_book(self, note_id: int, book_id: int) -> Optional[Note]:
        """Associa uma anotação a um livro."""
        return self.update(note_id, book_id=book_id)
