"""
Ponte para o sistema de banco de dados.
"""
import logging
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

class DatabaseBridge:
    def __init__(self, backend_integration):
        self.backend = backend_integration
        self._session = None
        
    @property
    def session(self):
        if self._session is None:
            try:
                from src.core.database.session import SessionLocal
                self._session = SessionLocal()
            except ImportError as e:
                logger.error(f"Banco de dados não disponível: {e}")
                self._session = None
        return self._session
    
    def is_available(self) -> bool:
        """Verifica se o módulo está disponível."""
        return self.session is not None
    
    # API pública para a interface CLI
    
    def get_book_count(self) -> Dict[str, Any]:
        """Obtém contagem de livros por status."""
        if not self.is_available():
            return self._get_fallback_book_count()
        
        try:
            from src.core.models import Book
            
            status_counts = {}
            with self.session as session:
                books = session.query(Book).all()
                
                for book in books:
                    status = book.status or 'unknown'
                    status_counts[status] = status_counts.get(status, 0) + 1
            
            return {
                "counts": status_counts,
                "total": sum(status_counts.values()),
                "is_fallback": False
            }
            
        except Exception as e:
            logger.error(f"Erro ao obter contagem de livros: {e}")
            return self._get_fallback_book_count()
    
    def get_recent_notes(self, limit: int = 10) -> Dict[str, Any]:
        """Obtém notas mais recentes."""
        if not self.is_available():
            return self._get_fallback_recent_notes()
        
        try:
            from src.core.models import Note
            from sqlalchemy import desc
            
            recent_notes = []
            with self.session as session:
                notes = session.query(Note).order_by(desc(Note.created_at)).limit(limit).all()
                
                for note in notes:
                    recent_notes.append({
                        "id": note.id,
                        "title": note.title or "Sem título",
                        "content_preview": (note.content or "")[:100] + "..." if note.content else "",
                        "created_at": note.created_at,
                        "book_title": note.book.title if note.book else None
                    })
            
            return {
                "notes": recent_notes,
                "total": len(recent_notes),
                "is_fallback": False
            }
            
        except Exception as e:
            logger.error(f"Erro ao obter notas recentes: {e}")
            return self._get_fallback_recent_notes()
    
    def get_database_stats(self) -> Dict[str, Any]:
        """Obtém estatísticas gerais do banco de dados."""
        if not self.is_available():
            return self._get_fallback_database_stats()
        
        try:
            from src.core.models import Book, Note, Task, ReadingSession
            
            with self.session as session:
                book_count = session.query(Book).count()
                note_count = session.query(Note).count()
                task_count = session.query(Task).count()
                session_count = session.query(ReadingSession).count()
            
            return {
                "stats": {
                    "books": book_count,
                    "notes": note_count,
                    "tasks": task_count,
                    "reading_sessions": session_count
                },
                "is_fallback": False
            }
            
        except Exception as e:
            logger.error(f"Erro ao obter estatísticas do banco: {e}")
            return self._get_fallback_database_stats()
    
    def execute_query(self, query: str, params: Dict = None) -> Dict[str, Any]:
        """Executa uma consulta SQL personalizada (apenas para leitura)."""
        if not self.is_available():
            return {
                "success": False,
                "results": [],
                "message": "Banco de dados não disponível"
            }
        
        try:
            with self.session as session:
                result = session.execute(query, params or {})
                rows = result.fetchall()
                
                # Converter para lista de dicionários
                columns = result.keys()
                results_list = []
                for row in rows:
                    row_dict = {col: val for col, val in zip(columns, row)}
                    results_list.append(row_dict)
                
                return {
                    "success": True,
                    "results": results_list,
                    "count": len(results_list),
                    "is_fallback": False
                }
                
        except Exception as e:
            logger.error(f"Erro ao executar query: {e}")
            return {
                "success": False,
                "results": [],
                "message": str(e),
                "is_fallback": True
            }
    
    # Métodos auxiliares
    
    def _get_fallback_book_count(self) -> Dict[str, Any]:
        """Dados fallback para contagem de livros."""
        return {
            "counts": {"active": 0, "completed": 0, "paused": 0},
            "total": 0,
            "is_fallback": True,
            "message": "Banco de dados não disponível"
        }
    
    def _get_fallback_recent_notes(self) -> Dict[str, Any]:
        """Dados fallback para notas recentes."""
        return {
            "notes": [],
            "total": 0,
            "is_fallback": True
        }
    
    def _get_fallback_database_stats(self) -> Dict[str, Any]:
        """Estatísticas fallback do banco de dados."""
        return {
            "stats": {
                "books": 0,
                "notes": 0,
                "tasks": 0,
                "reading_sessions": 0
            },
            "is_fallback": True
        }