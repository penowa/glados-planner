"""
Ponte para o ObsidianVaultManager.
"""
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

class ObsidianBridge:
    def __init__(self, backend_integration):
        self.backend = backend_integration
        self._vault_manager = None
        
    @property
    def vault_manager(self):
        if self._vault_manager is None:
            try:
                from src.core.modules.obsidian.vault_manager import ObsidianVaultManager
                self._vault_manager = ObsidianVaultManager()
            except ImportError as e:
                logger.error(f"ObsidianVaultManager não disponível: {e}")
                self._vault_manager = None
        return self._vault_manager
    
    def is_available(self) -> bool:
        """Verifica se o módulo está disponível."""
        return self.vault_manager is not None
    
    # API pública para a interface CLI
    
    def create_note(self, relative_path: str, content: str, 
                   frontmatter: Dict = None) -> Dict[str, Any]:
        """Cria uma nova nota no vault."""
        if not self.is_available():
            return {
                "success": False,
                "error": "ObsidianVaultManager não disponível",
                "path": None
            }
        
        try:
            # Chamada real para o backend
            note = self.vault_manager.create_note(
                relative_path=relative_path,
                content=content,
                frontmatter=frontmatter
            )
            
            return {
                "success": True,
                "path": str(note.path) if hasattr(note, 'path') else relative_path,
                "note": note
            }
            
        except Exception as e:
            logger.error(f"Erro ao criar nota: {e}")
            return {
                "success": False,
                "error": str(e),
                "path": None
            }
    
    def find_notes_by_tag(self, tag: str) -> Dict[str, Any]:
        """Encontra notas por tag."""
        if not self.is_available():
            return self._get_fallback_notes()
        
        try:
            notes = self.vault_manager.find_notes_by_tag(tag)
            return self._format_notes(notes)
            
        except Exception as e:
            logger.error(f"Erro ao buscar notas por tag: {e}")
            return self._get_fallback_notes()
    
    def get_vault_stats(self) -> Dict[str, Any]:
        """Obtém estatísticas do vault."""
        if not self.is_available():
            return self._get_fallback_stats()
        
        try:
            stats = self.vault_manager.get_vault_stats()
            return {
                "stats": stats,
                "is_fallback": False
            }
        except Exception as e:
            logger.error(f"Erro ao obter estatísticas: {e}")
            return self._get_fallback_stats()
    
    def sync_from_obsidian(self) -> Dict[str, Any]:
        """Sincroniza do Obsidian para o banco de dados."""
        if not self.is_available():
            return {
                "success": False,
                "message": "ObsidianVaultManager não disponível",
                "stats": {}
            }
        
        try:
            stats = self.vault_manager.sync_from_obsidian()
            return {
                "success": True,
                "message": f"Sincronização concluída. "
                          f"Encontrados {stats.get('books_found', 0)} livros, "
                          f"criados {stats.get('books_created', 0)} novos.",
                "stats": stats
            }
        except Exception as e:
            logger.error(f"Erro na sincronização: {e}")
            return {
                "success": False,
                "message": f"Erro na sincronização: {str(e)}",
                "stats": {}
            }
    
    def sync_to_obsidian(self, book_id: Optional[int] = None) -> Dict[str, Any]:
        """Sincroniza do banco de dados para o Obsidian."""
        if not self.is_available():
            return {
                "success": False,
                "message": "ObsidianVaultManager não disponível",
                "stats": {}
            }
        
        try:
            stats = self.vault_manager.sync_to_obsidian(book_id=book_id)
            return {
                "success": True,
                "message": f"Sincronização concluída. "
                          f"Atualizados {stats.get('books_updated', 0)} livros.",
                "stats": stats
            }
        except Exception as e:
            logger.error(f"Erro na sincronização: {e}")
            return {
                "success": False,
                "message": f"Erro na sincronização: {str(e)}",
                "stats": {}
            }
    
    def search_notes(self, query: str, limit: int = 10) -> Dict[str, Any]:
        """Busca notas por texto."""
        if not self.is_available():
            return self._get_fallback_notes()
        
        try:
            notes = self.vault_manager.search_notes(query, limit=limit)
            return self._format_notes(notes)
            
        except Exception as e:
            logger.error(f"Erro ao buscar notas: {e}")
            return self._get_fallback_notes()
    
    # Métodos auxiliares
    
    def _get_fallback_notes(self) -> Dict[str, Any]:
        """Dados fallback para notas."""
        return {
            "notes": [],
            "total": 0,
            "is_fallback": True,
            "message": "ObsidianVaultManager não disponível"
        }
    
    def _get_fallback_stats(self) -> Dict[str, Any]:
        """Estatísticas fallback."""
        return {
            "stats": {
                "total_notes": 0,
                "type_counts": {},
                "tag_counts": {},
                "total_links": 0,
                "vault_size_mb": 0
            },
            "is_fallback": True
        }
    
    def _format_notes(self, notes: List) -> Dict[str, Any]:
        """Formata lista de notas para o padrão da CLI."""
        formatted_notes = []
        
        for note in notes:
            formatted_notes.append({
                "path": getattr(note, 'path', ''),
                "title": getattr(note, 'title', 'Sem título'),
                "type": getattr(note, 'type', 'note'),
                "tags": getattr(note, 'tags', []),
                "created": getattr(note, 'created', datetime.now()),
                "modified": getattr(note, 'modified', datetime.now()),
                "content_preview": getattr(note, 'content', '')[:100] + '...' if getattr(note, 'content', '') else ''
            })
        
        return {
            "notes": formatted_notes,
            "total": len(formatted_notes),
            "is_fallback": False
        }