"""
Controller para módulo de Leitura - Integração completa com ReadingManager
"""
from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot, QThread, pyqtBoundSignal
from core.communication.base_controller import BackendController
import logging
from typing import Dict, List, Optional, Any, Callable
import traceback

logger = logging.getLogger('GLaDOS.UI.ReadingController')


class ReadingController(BackendController):
    """Controller para atividades de leitura - Integração completa com ReadingManager"""
    
    # Sinais principais
    reading_progress_updated = pyqtSignal(dict)          # Atualização de progresso
    reading_session_completed = pyqtSignal(dict)         # Sessão completada
    reading_stats_updated = pyqtSignal(dict)             # Estatísticas atualizadas
    books_list_loaded = pyqtSignal(list)                 # Lista de livros carregada
    reading_schedule_generated = pyqtSignal(dict)        # Cronograma gerado
    reading_time_recommendation = pyqtSignal(dict)       # Recomendações de tempo
    book_added_success = pyqtSignal(str, dict)           # Livro adicionado (book_id, book_data)
    error_occurred = pyqtSignal(str)                     # Erro ocorrido
    operation_started = pyqtSignal(str)                  # Operação iniciada
    operation_completed = pyqtSignal(str, dict)          # Operação completada (op_name, result)
    
    def __init__(self, reading_manager):
        super().__init__(reading_manager, "ReadingController")
        self.reading_manager = reading_manager  # Referência direta ao manager
        self.current_session = None
        self._data_cache = {}  # Cache para dados frequentes
        self._pending_operations = {}  # Operações pendentes
        
        logger.info(f"ReadingController inicializado com manager: {reading_manager}")
    
    # ============================================================================
    # MÉTODOS ASSÍNCRONOS PRINCIPAIS (Chamados pela UI)
    # ============================================================================
    
    @pyqtSlot(str, int, str)
    def update_reading_progress(self, book_id: str, pages_read: int, notes: str = ""):
        """
        Atualiza progresso de leitura de forma assíncrona
        
        Args:
            book_id: ID do livro
            pages_read: Páginas lidas (incremento)
            notes: Notas sobre a leitura
        """
        logger.info(f"Atualizando progresso: livro={book_id}, páginas={pages_read}")
        
        def operation():
            # Calcula a página atual baseada no incremento
            current_progress = self.reading_manager.get_reading_progress(book_id)
            current_page = 0
            
            if current_progress and 'current_page' in current_progress:
                current_page = current_progress['current_page']
            elif current_progress and 'progress' in current_progress:
                # Tenta extrair da string "X/Y"
                try:
                    current_page = int(current_progress['progress'].split('/')[0])
                except:
                    current_page = 0
            
            new_page = current_page + pages_read
            
            # Atualiza no manager
            success = self.reading_manager.update_progress(
                book_id=book_id,
                current_page=new_page,
                notes=notes
            )
            
            return {
                'success': success,
                'book_id': book_id,
                'current_page': new_page,
                'pages_read': pages_read,
                'notes_added': bool(notes)
            }
        
        self.execute_async(
            operation,
            callback=self._on_progress_updated
        )
    
    @pyqtSlot()
    def load_reading_stats(self):
        """Carrega estatísticas de leitura de forma assíncrona"""
        logger.info("Carregando estatísticas de leitura")
        
        def operation():
            return self.reading_manager.stats()
        
        self.execute_async(
            operation,
            callback=self._on_stats_loaded
        )
    
    @pyqtSlot(bool)
    def load_all_books(self, include_progress: bool = True):
        """
        Carrega todos os livros de forma assíncrona
        
        Args:
            include_progress: Incluir informações de progresso
        """
        logger.info(f"Carregando todos os livros (progresso={include_progress})")
        
        def operation():
            return self.reading_manager.list_books(include_progress=include_progress)
        
        self.execute_async(
            operation,
            callback=self._on_books_loaded
        )
    
    @pyqtSlot(str, str)
    def generate_reading_schedule(self, book_id: str, target_date: str = None):
        """
        Gera cronograma de leitura para um livro
        
        Args:
            book_id: ID do livro
            target_date: Data alvo para conclusão (YYYY-MM-DD)
        """
        logger.info(f"Gerando cronograma para livro {book_id}, data={target_date}")
        
        def operation():
            return self.reading_manager.generate_schedule(book_id, target_date)
        
        self.execute_async(
            operation,
            callback=self._on_schedule_generated
        )
    
    @pyqtSlot(str, str, int, str)
    def add_new_book(self, title: str, author: str, total_pages: int, book_id: str = None):
        """
        Adiciona um novo livro ao sistema
        
        Args:
            title: Título do livro
            author: Autor
            total_pages: Total de páginas
            book_id: ID opcional
        """
        logger.info(f"Adicionando novo livro: {title} por {author}")
        
        def operation():
            new_book_id = self.reading_manager.add_book(
                title=title,
                author=author,
                total_pages=total_pages,
                book_id=book_id
            )
            
            # Retorna informações do livro adicionado
            return {
                'book_id': new_book_id,
                'title': title,
                'author': author,
                'total_pages': total_pages,
                'success': True
            }
        
        self.execute_async(
            operation,
            callback=self._on_book_added
        )
    
    @pyqtSlot(str)
    def get_book_progress(self, book_id: str):
        """
        Obtém progresso específico de um livro
        
        Args:
            book_id: ID do livro
        """
        logger.info(f"Obtendo progresso do livro {book_id}")
        
        def operation():
            return self.reading_manager.get_reading_progress(book_id)
        
        self.execute_async(
            operation,
            callback=self._on_book_progress_loaded
        )
    
    @pyqtSlot()
    def get_recommended_reading_times(self):
        """Obtém recomendações de tempo de leitura"""
        logger.info("Obtendo recomendações de tempo de leitura")
        
        def operation():
            return self.reading_manager.get_recommended_reading_time()
        
        self.execute_async(
            operation,
            callback=self._on_recommendations_loaded
        )
    
    # ============================================================================
    # MÉTODOS DE SESSÃO DE LEITURA
    # ============================================================================
    
    @pyqtSlot(str, int)
    def start_reading_session(self, book_id: str, target_pages: int = 10):
        """
        Inicia sessão de leitura (síncrono - apenas no controller)
        
        Args:
            book_id: ID do livro
            target_pages: Meta de páginas para a sessão
        """
        session_data = {
            'book_id': book_id,
            'target_pages': target_pages,
            'start_time': self.get_timestamp(),
            'pages_read': 0,
            'status': 'active'
        }
        
        self.current_session = session_data
        logger.info(f"Sessão de leitura iniciada: livro={book_id}, meta={target_pages}")
        
        # Emite sinal de sessão iniciada
        self.operation_completed.emit('session_started', session_data)
    
    @pyqtSlot(int, str)
    def end_reading_session(self, pages_read: int, notes: str = ""):
        """
        Finaliza sessão de leitura e atualiza progresso
        
        Args:
            pages_read: Páginas lidas na sessão
            notes: Notas sobre a sessão
        """
        if not self.current_session:
            self.error_occurred.emit("Nenhuma sessão ativa para finalizar")
            return
        
        book_id = self.current_session['book_id']
        
        # Atualiza dados da sessão
        self.current_session.update({
            'pages_read': pages_read,
            'end_time': self.get_timestamp(),
            'completed': pages_read >= self.current_session['target_pages'],
            'notes': notes
        })
        
        logger.info(f"Finalizando sessão: livro={book_id}, páginas={pages_read}")
        
        # Se leu páginas, atualiza progresso
        if pages_read > 0:
            self.update_reading_progress(book_id, pages_read, notes)
        
        # Emite sinal de sessão completada
        session_complete_data = self.current_session.copy()
        self.reading_session_completed.emit(session_complete_data)
        
        # Limpa sessão atual
        self.current_session = None
    
    @pyqtSlot(result=dict)
    def get_current_session(self) -> dict:
        """Retorna informações da sessão atual"""
        return self.current_session or {}
    
    # ============================================================================
    # CALLBACKS DE OPERAÇÕES ASSÍNCRONAS
    # ============================================================================
    
    def _on_progress_updated(self, result: Dict[str, Any]):
        """Processa resultado da atualização de progresso"""
        try:
            if result.get('success', False):
                book_id = result['book_id']
                
                # Atualiza cache
                cache_key = f"progress_{book_id}"
                self._data_cache[cache_key] = {
                    'timestamp': self.get_timestamp(),
                    'data': result
                }
                
                # Emite sinal de progresso atualizado
                self.reading_progress_updated.emit(result)
                
                # Atualiza estatísticas
                self.load_reading_stats()
                
                logger.info(f"Progresso atualizado com sucesso: {book_id}")
            else:
                error_msg = f"Falha ao atualizar progresso: {result.get('error', 'Erro desconhecido')}"
                self.error_occurred.emit(error_msg)
                
        except Exception as e:
            error_msg = f"Erro em _on_progress_updated: {str(e)}"
            logger.error(error_msg)
            logger.error(traceback.format_exc())
            self.error_occurred.emit(error_msg)
    
    def _on_stats_loaded(self, stats: Dict[str, Any]):
        """Processa estatísticas carregadas"""
        try:
            # Formata estatísticas para UI
            ui_stats = {
                'total_books': stats.get('total_books', 0),
                'completed_books': stats.get('completed_books', 0),
                'books_in_progress': stats.get('books_in_progress', 0),
                'pages_total': stats.get('total_pages_read', 0),
                'completion_percentage': stats.get('completion_percentage', 0),
                'average_reading_speed': stats.get('average_reading_speed', 0),
                'pages_last_week': stats.get('pages_last_week', 0),
                'estimated_time_to_complete': stats.get('estimated_time_to_complete', 'N/A'),
                
                # Campos adicionais para UI (pode ser calculado ou mock)
                'pages_today': stats.get('pages_today', 0),
                'reading_streak': stats.get('reading_streak', 0),
                'favorite_author': stats.get('favorite_author', 'Nenhum')
            }
            
            # Atualiza cache
            self._data_cache['stats'] = {
                'timestamp': self.get_timestamp(),
                'data': ui_stats
            }
            
            # Emite sinal
            self.reading_stats_updated.emit(ui_stats)
            logger.info(f"Estatísticas carregadas: {stats.get('total_books', 0)} livros")
            
        except Exception as e:
            error_msg = f"Erro em _on_stats_loaded: {str(e)}"
            logger.error(error_msg)
            logger.error(traceback.format_exc())
            self.error_occurred.emit(error_msg)
    
    def _on_books_loaded(self, books: List[Dict[str, Any]]):
        """Processa lista de livros carregada"""
        try:
            # Formata livros para UI
            ui_books = []
            for book in books:
                ui_book = {
                    'id': book.get('id', ''),
                    'title': book.get('title', 'Sem título'),
                    'author': book.get('author', 'Autor desconhecido'),
                    'total_pages': book.get('total_pages', 0),
                    'current_page': book.get('current_page', 0),
                    'percentage': book.get('percentage', 0),
                    'reading_speed': book.get('reading_speed', 0),
                    'last_read': book.get('last_read', ''),
                    'status': 'completed' if book.get('percentage', 0) >= 100 else 'in_progress'
                }
                ui_books.append(ui_book)
            
            # Atualiza cache
            self._data_cache['books'] = {
                'timestamp': self.get_timestamp(),
                'data': ui_books
            }
            
            # Emite sinal
            self.books_list_loaded.emit(ui_books)
            logger.info(f"Lista de livros carregada: {len(ui_books)} livros")
            
        except Exception as e:
            error_msg = f"Erro em _on_books_loaded: {str(e)}"
            logger.error(error_msg)
            logger.error(traceback.format_exc())
            self.error_occurred.emit(error_msg)
    
    def _on_schedule_generated(self, schedule: Dict[str, Any]):
        """Processa cronograma gerado"""
        try:
            if 'error' in schedule:
                self.error_occurred.emit(f"Erro ao gerar cronograma: {schedule['error']}")
                return
            
            # Formata para UI
            ui_schedule = {
                'book': schedule.get('book', ''),
                'author': schedule.get('author', ''),
                'current_progress': schedule.get('current_progress', '0/0'),
                'pages_remaining': schedule.get('pages_remaining', 0),
                'days_remaining': schedule.get('days_remaining', 0),
                'pages_per_day': schedule.get('pages_per_day', 0),
                'target_completion': schedule.get('target_completion', ''),
                'daily_schedule': schedule.get('daily_schedule', [])
            }
            
            # Emite sinal
            self.reading_schedule_generated.emit(ui_schedule)
            logger.info(f"Cronograma gerado: {schedule.get('book', 'Livro desconhecido')}")
            
        except Exception as e:
            error_msg = f"Erro em _on_schedule_generated: {str(e)}"
            logger.error(error_msg)
            logger.error(traceback.format_exc())
            self.error_occurred.emit(error_msg)
    
    def _on_book_added(self, result: Dict[str, Any]):
        """Processa livro adicionado"""
        try:
            if result.get('success', False):
                book_id = result['book_id']
                
                # Atualiza cache
                self._data_cache[f"book_{book_id}"] = {
                    'timestamp': self.get_timestamp(),
                    'data': result
                }
                
                # Emite sinal
                self.book_added_success.emit(book_id, result)
                
                # Recarrega lista de livros
                self.load_all_books()
                
                logger.info(f"Livro adicionado com sucesso: {result.get('title', 'Sem título')}")
            else:
                error_msg = f"Falha ao adicionar livro: {result.get('error', 'Erro desconhecido')}"
                self.error_occurred.emit(error_msg)
                
        except Exception as e:
            error_msg = f"Erro em _on_book_added: {str(e)}"
            logger.error(error_msg)
            logger.error(traceback.format_exc())
            self.error_occurred.emit(error_msg)
    
    def _on_book_progress_loaded(self, progress: Dict[str, Any]):
        """Processa progresso de livro carregado"""
        try:
            if progress:
                # Emite sinal de progresso atualizado
                self.reading_progress_updated.emit(progress)
                logger.info(f"Progresso carregado para livro: {progress.get('title', 'Desconhecido')}")
            else:
                self.error_occurred.emit(f"Livro não encontrado ou sem progresso")
                
        except Exception as e:
            error_msg = f"Erro em _on_book_progress_loaded: {str(e)}"
            logger.error(error_msg)
            logger.error(traceback.format_exc())
            self.error_occurred.emit(error_msg)
    
    def _on_recommendations_loaded(self, recommendations: Dict[str, Any]):
        """Processa recomendações de tempo carregadas"""
        try:
            if recommendations:
                # Formata para UI
                ui_recommendations = {
                    'timestamp': self.get_timestamp(),
                    'recommendations': recommendations
                }
                
                # Emite sinal
                self.reading_time_recommendation.emit(ui_recommendations)
                logger.info(f"Recomendações carregadas: {len(recommendations)} livros")
            else:
                logger.warning("Nenhuma recomendação disponível")
                
        except Exception as e:
            error_msg = f"Erro em _on_recommendations_loaded: {str(e)}"
            logger.error(error_msg)
            logger.error(traceback.format_exc())
            self.error_occurred.emit(error_msg)
    
    # ============================================================================
    # MÉTODOS AUXILIARES E UTILITÁRIOS
    # ============================================================================
    
    def get_timestamp(self) -> str:
        """Retorna timestamp atual formatado"""
        from datetime import datetime
        return datetime.now().isoformat()
    
    @pyqtSlot(str, result=object)
    def get_cached_data(self, cache_key: str) -> Optional[Dict]:
        """
        Obtém dados do cache
        
        Args:
            cache_key: Chave do cache
            
        Returns:
            Dados em cache ou None
        """
        cached = self._data_cache.get(cache_key)
        if cached:
            # Verifica se não está muito antigo (mais de 5 minutos)
            from datetime import datetime, timedelta
            cache_time = datetime.fromisoformat(cached['timestamp'])
            if datetime.now() - cache_time < timedelta(minutes=5):
                return cached['data']
        
        return None
    
    @pyqtSlot()
    def clear_cache(self):
        """Limpa o cache de dados"""
        self._data_cache.clear()
        logger.info("Cache limpo")
    
    @pyqtSlot(str, result=bool)
    def has_cached_data(self, cache_key: str) -> bool:
        """Verifica se há dados em cache para a chave"""
        return cache_key in self._data_cache
    
    @pyqtSlot(result=list)
    def get_cache_keys(self) -> List[str]:
        """Retorna lista de chaves de cache disponíveis"""
        return list(self._data_cache.keys())
    
    # ============================================================================
    # MÉTODOS DE DIAGNÓSTICO E DEBUG
    # ============================================================================
    
    @pyqtSlot(result=dict)
    def get_controller_status(self) -> Dict[str, Any]:
        """Retorna status do controller para diagnóstico"""
        return {
            'controller_name': 'ReadingController',
            'manager_connected': self.reading_manager is not None,
            'current_session': bool(self.current_session),
            'cache_size': len(self._data_cache),
            'cache_keys': list(self._data_cache.keys()),
            'backend_type': type(self.reading_manager).__name__ if self.reading_manager else 'None'
        }
    
    @pyqtSlot()
    def force_refresh_all(self):
        """Força atualização de todos os dados"""
        logger.info("Forçando atualização de todos os dados")
        
        # Limpa cache
        self.clear_cache()
        
        # Carrega todos os dados
        self.load_reading_stats()
        self.load_all_books(include_progress=True)
        
        # Se houver sessão ativa, atualiza progresso
        if self.current_session:
            self.get_book_progress(self.current_session['book_id'])