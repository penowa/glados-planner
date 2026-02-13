# ui/controllers/vault_controller.py
"""
Controlador para o ObsidianVaultManager.
Atua como ponte entre o backend de gerenciamento do vault e a interface PyQt6.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot, QThread
import logging

from core.modules.obsidian.vault_manager import ObsidianVaultManager
from core.models.book import Book
from core.models.note import Note

logger = logging.getLogger(__name__)


class VaultWorker(QObject):
    """Worker para operações do vault em thread separada"""
    
    sync_completed = pyqtSignal(dict)  # Estatísticas da sincronização
    sync_progress = pyqtSignal(int, str)  # (progresso, mensagem)
    error_occurred = pyqtSignal(str)
    vault_stats_ready = pyqtSignal(dict)
    vault_connected = pyqtSignal(bool)
    
    def __init__(self, vault_manager: ObsidianVaultManager):
        super().__init__()
        self.vault_manager = vault_manager
    
    @pyqtSlot()
    def check_vault_connection(self):
        """Verifica se o vault está conectado"""
        try:
            connected = self.vault_manager.is_connected()
            self.vault_connected.emit(connected)
        except Exception as e:
            self.error_occurred.emit(f"Erro ao verificar conexão: {str(e)}")
    
    @pyqtSlot()
    def get_vault_stats(self):
        """Obtém estatísticas do vault"""
        try:
            stats = self.vault_manager.get_vault_stats()
            self.vault_stats_ready.emit(stats)
        except Exception as e:
            self.error_occurred.emit(f"Erro ao obter estatísticas: {str(e)}")
    
    @pyqtSlot()
    def sync_from_obsidian(self):
        """Sincroniza dados do Obsidian para o banco local"""
        try:
            self.sync_progress.emit(10, "Iniciando sincronização...")
            
            # Escanear vault
            self.vault_manager._scan_vault()
            self.sync_progress.emit(30, "Vault escaneado")
            
            # Sincronizar dados
            stats = self.vault_manager.sync_from_obsidian()
            self.sync_progress.emit(80, "Dados sincronizados")
            
            # Atualizar cache
            self.vault_manager._scan_vault()
            self.sync_progress.emit(100, "Sincronização concluída")
            
            self.sync_completed.emit({
                'type': 'from_obsidian',
                'stats': stats,
                'success': True
            })
            
        except Exception as e:
            logger.error(f"Erro na sincronização: {e}")
            self.error_occurred.emit(f"Erro na sincronização: {str(e)}")
            self.sync_completed.emit({
                'type': 'from_obsidian',
                'stats': {},
                'success': False,
                'error': str(e)
            })
    
    @pyqtSlot(int)
    def sync_book_to_obsidian(self, book_id: int):
        """Sincroniza um livro específico para o Obsidian"""
        try:
            self.sync_progress.emit(10, f"Iniciando sincronização do livro {book_id}")
            
            stats = self.vault_manager.sync_to_obsidian(book_id)
            
            self.sync_completed.emit({
                'type': 'book_to_obsidian',
                'book_id': book_id,
                'stats': stats,
                'success': True
            })
            
        except Exception as e:
            logger.error(f"Erro ao sincronizar livro: {e}")
            self.error_occurred.emit(f"Erro ao sincronizar livro: {str(e)}")
    
    @pyqtSlot()
    def sync_all_to_obsidian(self):
        """Sincroniza todos os dados para o Obsidian"""
        try:
            self.sync_progress.emit(10, "Iniciando sincronização completa...")
            
            stats = self.vault_manager.sync_to_obsidian()
            
            self.sync_completed.emit({
                'type': 'all_to_obsidian',
                'stats': stats,
                'success': True
            })
            
        except Exception as e:
            logger.error(f"Erro na sincronização completa: {e}")
            self.error_occurred.emit(f"Erro na sincronização completa: {str(e)}")


class VaultController(QObject):
    """
    Controlador para o ObsidianVaultManager.
    Adapta a API do backend para sinais Qt e operações assíncronas.
    """
    
    # Sinais de status
    vault_status_changed = pyqtSignal(dict)  # {connected: bool, path: str, stats: dict}
    sync_started = pyqtSignal(str)  # Tipo de sincronização
    sync_progress = pyqtSignal(int, str)  # (percentual, mensagem)
    sync_completed = pyqtSignal(dict)  # Resultado completo
    error_occurred = pyqtSignal(str)
    
    # Sinais de dados
    vault_stats_updated = pyqtSignal(dict)
    note_created = pyqtSignal(dict)  # Dados da nota criada
    note_updated = pyqtSignal(dict)  # Dados da nota atualizada
    note_deleted = pyqtSignal(str)  # Caminho da nota excluída
    
    # Sinais para UI
    notes_list_updated = pyqtSignal(list)  # Lista de notas
    book_notes_updated = pyqtSignal(int, list)  # (book_id, lista de notas)
    
    def __init__(self, vault_path: Optional[str] = None):
        super().__init__()
        
        # Inicializar o gerenciador do vault (singleton)
        self.vault_manager = ObsidianVaultManager.instance(vault_path)
        
        # Thread e worker para operações assíncronas
        self.worker_thread = None
        self.worker = None
        
        # Cache local para dados frequentes
        self.cache = {
            'stats': None,
            'notes': None,
            'last_sync': None
        }
        
        # Verificar conexão inicial
        self.check_vault_connection()
    
    def check_vault_connection(self):
        """Verifica a conexão com o vault"""
        if self.worker_thread and self.worker_thread.isRunning():
            self.worker_thread.quit()
        
        self.worker_thread = QThread()
        self.worker = VaultWorker(self.vault_manager)
        self.worker.moveToThread(self.worker_thread)
        
        # Conectar sinais do worker
        self.worker.vault_connected.connect(self._handle_vault_connected)
        self.worker.error_occurred.connect(self.error_occurred)
        
        # Iniciar thread
        self.worker_thread.started.connect(self.worker.check_vault_connection)
        self.worker_thread.start()
    
    @pyqtSlot(bool)
    def _handle_vault_connected(self, connected: bool):
        """Processa resultado da verificação de conexão"""
        status = {
            'connected': connected,
            'path': str(self.vault_manager.vault_path) if connected else None,
            'stats': None
        }
        
        if connected:
            # Obter estatísticas iniciais
            self.get_vault_stats()
        else:
            self.vault_status_changed.emit(status)
    
    @pyqtSlot()
    def get_vault_stats(self):
        """Obtém estatísticas do vault (assíncrono)"""
        if self.worker_thread and self.worker_thread.isRunning():
            self.worker_thread.quit()
        
        self.worker_thread = QThread()
        self.worker = VaultWorker(self.vault_manager)
        self.worker.moveToThread(self.worker_thread)
        
        # Conectar sinais
        self.worker.vault_stats_ready.connect(self._handle_vault_stats)
        self.worker.error_occurred.connect(self.error_occurred)
        
        # Iniciar
        self.worker_thread.started.connect(self.worker.get_vault_stats)
        self.worker_thread.start()
    
    @pyqtSlot(dict)
    def _handle_vault_stats(self, stats: Dict[str, Any]):
        """Processa estatísticas do vault"""
        self.cache['stats'] = stats
        self.vault_stats_updated.emit(stats)
        
        # Atualizar status completo
        status = {
            'connected': True,
            'path': str(self.vault_manager.vault_path),
            'stats': stats
        }
        self.vault_status_changed.emit(status)
    
    @pyqtSlot()
    def sync_from_obsidian(self):
        """Inicia sincronização do Obsidian para o banco local"""
        self.sync_started.emit('from_obsidian')
        
        if self.worker_thread and self.worker_thread.isRunning():
            self.worker_thread.quit()
        
        self.worker_thread = QThread()
        self.worker = VaultWorker(self.vault_manager)
        self.worker.moveToThread(self.worker_thread)
        
        # Conectar sinais
        self.worker.sync_completed.connect(self._handle_sync_completed)
        self.worker.sync_progress.connect(self.sync_progress)
        self.worker.error_occurred.connect(self.error_occurred)
        
        # Iniciar
        self.worker_thread.started.connect(self.worker.sync_from_obsidian)
        self.worker_thread.start()
    
    @pyqtSlot(int)
    def sync_book_to_obsidian(self, book_id: int):
        """Sincroniza um livro específico para o Obsidian"""
        self.sync_started.emit(f'book_{book_id}_to_obsidian')
        
        if self.worker_thread and self.worker_thread.isRunning():
            self.worker_thread.quit()
        
        self.worker_thread = QThread()
        self.worker = VaultWorker(self.vault_manager)
        self.worker.moveToThread(self.worker_thread)
        
        # Conectar sinais
        self.worker.sync_completed.connect(self._handle_sync_completed)
        self.worker.sync_progress.connect(self.sync_progress)
        self.worker.error_occurred.connect(self.error_occurred)
        
        # Iniciar
        self.worker_thread.started.connect(
            lambda: self.worker.sync_book_to_obsidian(book_id)
        )
        self.worker_thread.start()
    
    @pyqtSlot()
    def sync_all_to_obsidian(self):
        """Sincroniza todos os dados para o Obsidian"""
        self.sync_started.emit('all_to_obsidian')
        
        if self.worker_thread and self.worker_thread.isRunning():
            self.worker_thread.quit()
        
        self.worker_thread = QThread()
        self.worker = VaultWorker(self.vault_manager)
        self.worker.moveToThread(self.worker_thread)
        
        # Conectar sinais
        self.worker.sync_completed.connect(self._handle_sync_completed)
        self.worker.sync_progress.connect(self.sync_progress)
        self.worker.error_occurred.connect(self.error_occurred)
        
        # Iniciar
        self.worker_thread.started.connect(self.worker.sync_all_to_obsidian)
        self.worker_thread.start()
    
    @pyqtSlot(dict)
    def _handle_sync_completed(self, result: Dict[str, Any]):
        """Processa resultado da sincronização"""
        self.sync_completed.emit(result)
        
        # Atualizar cache após sincronização
        if result.get('success'):
            self.get_vault_stats()
            
            # Emitir atualização de dados se necessário
            if result['type'] == 'from_obsidian':
                self._notify_data_updated()
    
    def _notify_data_updated(self):
        """Notifica que os dados foram atualizados"""
        # Este método pode ser chamado por outros controllers
        # para atualizar listas de livros/notas
        pass
    
    # Métodos síncronos para operações rápidas
    def get_all_notes(self) -> List[Dict]:
        """Obtém todas as notas (síncrono, usa cache)"""
        if self.cache['notes'] is not None:
            return self.cache['notes']
        
        try:
            notes = self.vault_manager.get_all_notes()
            ui_notes = [self._note_to_ui_format(note) for note in notes]
            self.cache['notes'] = ui_notes
            return ui_notes
        except Exception as e:
            logger.error(f"Erro ao obter notas: {e}")
            return []
    
    def get_notes_by_book(self, book: Book) -> List[Dict]:
        """Obtém notas relacionadas a um livro"""
        try:
            # Encontrar notas pelo caminho do livro
            book_path = f"01-LEITURAS/{book.author}/{book.title}"
            all_notes = self.vault_manager.get_all_notes()
            
            book_notes = []
            for note in all_notes:
                if str(note.path).startswith(book_path):
                    ui_note = self._note_to_ui_format(note)
                    book_notes.append(ui_note)
            
            return book_notes
        except Exception as e:
            logger.error(f"Erro ao obter notas do livro: {e}")
            return []
    
    def create_note(self, relative_path: str, content: str = "", 
                   frontmatter: Optional[Dict] = None, tags: Optional[List[str]] = None) -> Dict:
        """Cria uma nova nota (síncrono)"""
        try:
            note = self.vault_manager.create_note(
                relative_path, content, frontmatter, tags
            )
            ui_note = self._note_to_ui_format(note)
            self.note_created.emit(ui_note)
            
            # Invalidar cache
            self.cache['notes'] = None
            
            return ui_note
        except Exception as e:
            self.error_occurred.emit(f"Erro ao criar nota: {str(e)}")
            raise
    
    def update_note(self, relative_path: str, **kwargs) -> Dict:
        """Atualiza uma nota existente (síncrono)"""
        try:
            note = self.vault_manager.update_note(relative_path, **kwargs)
            ui_note = self._note_to_ui_format(note)
            self.note_updated.emit(ui_note)
            
            # Invalidar cache
            self.cache['notes'] = None
            
            return ui_note
        except Exception as e:
            self.error_occurred.emit(f"Erro ao atualizar nota: {str(e)}")
            raise
    
    def delete_note(self, relative_path: str):
        """Exclui uma nota (síncrono)"""
        try:
            self.vault_manager.delete_note(relative_path)
            self.note_deleted.emit(relative_path)
            
            # Invalidar cache
            self.cache['notes'] = None
            
        except Exception as e:
            self.error_occurred.emit(f"Erro ao excluir nota: {str(e)}")
            raise
    
    def search_notes(self, query: str, search_in_content: bool = True) -> List[Dict]:
        """Busca notas por texto"""
        try:
            if search_in_content:
                notes = self.vault_manager.find_notes_by_content(query)
            else:
                # Buscar por tag ou título
                notes = [
                    note for note in self.vault_manager.get_all_notes()
                    if query.lower() in ' '.join(note.tags).lower() or
                       query.lower() in note.frontmatter.get('title', '').lower()
                ]
            
            return [self._note_to_ui_format(note) for note in notes]
        except Exception as e:
            logger.error(f"Erro na busca: {e}")
            return []
    
    def _note_to_ui_format(self, note) -> Dict:
        """Converte uma nota do backend para formato da UI"""
        return {
            'path': str(note.path),
            'title': note.frontmatter.get('title', note.path.stem),
            'content_preview': note.content[:200] + '...' if len(note.content) > 200 else note.content,
            'tags': list(note.tags),
            'frontmatter': note.frontmatter,
            'created': note.created.isoformat() if note.created else None,
            'modified': note.modified.isoformat() if note.modified else None,
            'links': note.links,
            'icon': self._get_note_icon(note),
            'color': self._generate_color_from_path(note.path)
        }
    
    def _get_note_icon(self, note) -> str:
        """Determina ícone baseado no tipo da nota"""
        tags = note.tags
        frontmatter = note.frontmatter
        
        if 'book' in tags:
            return '📚'
        elif 'concept' in tags or 'definition' in tags:
            return '🧠'
        elif 'quote' in tags or 'citation' in tags:
            return '💬'
        elif 'class' in tags or 'lecture' in tags:
            return '🎓'
        elif 'idea' in tags:
            return '💡'
        elif 'author' in tags:
            return '👤'
        elif 'task' in tags or 'todo' in tags:
            return '✅'
        else:
            return '📝'
    
    def _generate_color_from_path(self, path: Path) -> str:
        """Gera cor consistente baseada no caminho da nota"""
        import hashlib
        path_str = str(path)
        hash_obj = hashlib.md5(path_str.encode())
        hash_int = int(hash_obj.hexdigest(), 16)
        
        # Gerar HSL color
        hue = hash_int % 360
        saturation = 60 + (hash_int % 20)  # 60-80%
        lightness = 70 + (hash_int % 15)  # 70-85%
        
        return f'hsl({hue}, {saturation}%, {lightness}%)'
    
    def refresh_cache(self):
        """Atualiza o cache manualmente"""
        self.cache['notes'] = None
        self.cache['stats'] = None
        self.get_vault_stats()


# Factory para injeção de dependências
def create_vault_controller(vault_path: Optional[str] = None) -> VaultController:
    """Factory para criação do VaultController"""
    return VaultController(vault_path)
