"""
Módulo de integração completo entre UI interativa e backend GLaDOS.
Conecta todos os módulos existentes com a nova interface.
"""
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
from enum import Enum
from dataclasses import dataclass, asdict, field
from datetime import datetime, date, timedelta
from contextlib import contextmanager
import threading
import time

# Configuração de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Importações do backend existente
try:
    # Core Managers
    from core.modules.agenda_manager import AgendaManager, AgendaEvent, AgendaEventType
    from core.modules.reading_manager import ReadingManager
    from core.modules.book_processor import BookProcessor, ProcessingQuality
    from core.modules.review_system import ReviewSystem
    from core.modules.daily_checkin import DailyCheckinSystem
    from core.modules.pomodoro_timer import PomodoroTimer
    from core.modules.obsidian.vault_manager import ObsidianVaultManager
    
    # LLM e Personalidade
    from core.llm.local_llm import LocalLLM
    from core.llm.glados.personality.glados_voice import GladosVoice
    
    # Database
    from core.database.base import get_db
    from core.repositories.book_repository import BookRepository
    from core.repositories.task_repository import TaskRepository
    from core.repositories.note_repository import NoteRepository
    
    # Configurações
    from core.config.settings import settings
    
    BACKEND_AVAILABLE = True
    logger.info("✅ Backend GLaDOS carregado com sucesso")
    
except ImportError as e:
    logger.warning(f"⚠️ Backend não disponível: {e}")
    BACKEND_AVAILABLE = False
    # Classes mock para desenvolvimento
    class AgendaManager: pass
    class ReadingManager: pass
    class BookProcessor: pass
    class ReviewSystem: pass
    class DailyCheckinSystem: pass
    class PomodoroTimer: pass
    class ObsidianVaultManager: pass
    class LocalLLM:
        def generate(self, query, user_name="Usuário", use_semantic=True):
            return {"text": f"Resposta mock: {query}"}

class AppEvent(Enum):
    """Eventos da aplicação para sistema pub/sub"""
    # Agenda
    AGENDA_UPDATED = "agenda_updated"
    EVENT_ADDED = "event_added"
    EVENT_UPDATED = "event_updated"
    EVENT_DELETED = "event_deleted"
    
    # Leitura
    READING_PROGRESS = "reading_progress"
    BOOK_ADDED = "book_added"
    BOOK_COMPLETED = "book_completed"
    BOOK_STATUS_CHANGED = "book_status_changed"
    
    # Tarefas
    TASK_ADDED = "task_added"
    TASK_COMPLETED = "task_completed"
    TASK_UPDATED = "task_updated"
    
    # Sistema
    CHECKIN_DONE = "checkin_done"
    VAULT_SYNCED = "vault_synced"
    SESSION_STARTED = "session_started"
    SESSION_ENDED = "session_ended"
    MODE_CHANGED = "mode_changed"
    
    # Interface
    UI_REFRESH_NEEDED = "ui_refresh_needed"
    NOTIFICATION_ADDED = "notification_added"

@dataclass
class DashboardData:
    """Dados para o dashboard interativo"""
    # Metas do dia
    daily_goals: List[Dict[str, Any]] = field(default_factory=list)
    
    # Próximos compromissos (agenda)
    upcoming_events: List[Dict[str, Any]] = field(default_factory=list)
    
    # Alertas e notificações
    alerts: List[Dict[str, Any]] = field(default_factory=list)
    
    # Estatísticas do dia
    daily_stats: Dict[str, Any] = field(default_factory=dict)
    
    # Livros ativos
    active_books: List[Dict[str, Any]] = field(default_factory=list)
    
    # Tarefas pendentes
    pending_tasks: List[Dict[str, Any]] = field(default_factory=list)
    
    # Mensagem do dia (GLaDOS)
    daily_message: str = ""
    
    # Estado da aplicação
    app_state: Dict[str, Any] = field(default_factory=dict)

class BackendIntegration:
    """
    Integração completa com backend GLaDOS.
    Gerencia todas as conexões com módulos existentes.
    """
    
    def __init__(self, vault_path: Optional[str] = None):
        self._initialized = False
        self._modules = {}
        self._event_listeners = {}
        self._dashboard_cache = None
        self._cache_timestamp = None
        self._cache_ttl = 60  # 1 minuto de cache
        
        # Frase principal GLaDOS
        self.glados_quote = "Transformando sua confusão filosófica em algo que remotamente se assemelhe a conhecimento. Não me agradeça."
        
        # Tentar inicializar backend
        if BACKEND_AVAILABLE:
            self._initialize_backend(vault_path)
    
    def _initialize_backend(self, vault_path: Optional[str] = None):
        """Inicializa todos os módulos do backend"""
        try:
            logger.info("🚀 Inicializando integração com backend GLaDOS...")
            
            # 1. Gerenciadores core
            self._modules['agenda'] = AgendaManager()
            self._modules['reading'] = ReadingManager()
            self._modules['review'] = ReviewSystem()
            self._modules['checkin'] = DailyCheckinSystem()
            self._modules['pomodoro'] = PomodoroTimer()
            
            # 2. Processamento de livros
            self._modules['book_processor'] = BookProcessor()
            
            # 3. Obsidian Vault
            vault_path = vault_path or settings.obsidian.vault_path
            self._modules['vault'] = ObsidianVaultManager(vault_path)
            
            # 4. LLM com personalidade GLaDOS
            self._modules['llm'] = LocalLLM()
            
            # 5. Personalidade GLaDOS
            self._modules['glados_voice'] = GladosVoice()
            
            # 6. Repositórios de banco de dados
            self._init_database_repositories()
            
            logger.info("✅ Backend inicializado com sucesso")
            self._initialized = True
            
            # Gerar primeira mensagem GLaDOS
            self._generate_daily_message()
            
        except Exception as e:
            logger.error(f"❌ Falha ao inicializar backend: {e}")
            self._initialized = False
    
    def _init_database_repositories(self):
        """Inicializa repositórios de banco de dados"""
        # Usar uma sessão para inicialização
        from core.database.base import SessionLocal
        db = SessionLocal()
        try:
            self._modules['book_repo'] = BookRepository(db)
            self._modules['task_repo'] = TaskRepository(db)
            self._modules['note_repo'] = NoteRepository(db)
        finally:
            db.close()
    
    def is_ready(self) -> bool:
        """Verifica se o backend está pronto para uso"""
        return self._initialized and BACKEND_AVAILABLE
    
    # === MÉTODOS DE AGENDA ===
    
    def get_today_agenda(self) -> List[Dict[str, Any]]:
        """Obtém agenda do dia atual"""
        if not self.is_ready():
            return self._get_mock_agenda()
        
        try:
            agenda_manager = self._modules['agenda']
            events = agenda_manager.get_day_events(date.today())
            
            # Converter para formato da UI
            ui_events = []
            for event in events[:10]:  # Limitar a 10 eventos
                ui_events.append({
                    'id': getattr(event, 'id', 'mock'),
                    'time': self._format_time_range(event.start_time, event.end_time),
                    'title': event.title,
                    'type': getattr(event, 'type', 'event').value if hasattr(event.type, 'value') else str(event.type),
                    'description': getattr(event, 'description', ''),
                    'completed': getattr(event, 'completed', False)
                })
            
            return ui_events
        except Exception as e:
            logger.error(f"Erro ao obter agenda: {e}")
            return self._get_mock_agenda()
    
    def add_event(self, event_data: Dict[str, Any]) -> bool:
        """Adiciona novo evento à agenda"""
        if not self.is_ready():
            return False
        
        try:
            agenda_manager = self._modules['agenda']
            
            # Converter dados da UI para AgendaEvent
            event_type = AgendaEventType(event_data.get('type', 'CASUAL'))
            
            event = AgendaEvent(
                title=event_data['title'],
                event_type=event_type,
                start_time=event_data['start_time'],
                end_time=event_data['end_time'],
                priority=event_data.get('priority', 3),
                metadata={
                    'description': event_data.get('description', ''),
                    'location': event_data.get('location', ''),
                    'discipline': event_data.get('discipline', '')
                }
            )
            
            success = agenda_manager.add_event(event)
            if success:
                self._emit_event(AppEvent.EVENT_ADDED, {'event': event_data})
                self._clear_cache()
            
            return success
        except Exception as e:
            logger.error(f"Erro ao adicionar evento: {e}")
            return False
    
    # === MÉTODOS DE LEITURA ===
    
    def get_active_books(self) -> List[Dict[str, Any]]:
        """Obtém livros ativos com progresso"""
        if not self.is_ready():
            return self._get_mock_books()
        
        try:
            reading_manager = self._modules['reading']
            books = reading_manager.get_active_books()
            
            ui_books = []
            for book in books[:5]:  # Limitar a 5 livros no dashboard
                progress = (book.current_page / book.total_pages * 100) if book.total_pages > 0 else 0
                
                ui_books.append({
                    'id': book.id,
                    'title': book.title,
                    'author': book.author,
                    'current_page': book.current_page,
                    'total_pages': book.total_pages,
                    'progress': round(progress, 1),
                    'deadline': book.deadline.isoformat() if book.deadline else None,
                    'days_remaining': (book.deadline - date.today()).days if book.deadline else None
                })
            
            return ui_books
        except Exception as e:
            logger.error(f"Erro ao obter livros: {e}")
            return self._get_mock_books()
    
    def update_reading_progress(self, book_id: int, current_page: int) -> bool:
        """Atualiza progresso de leitura"""
        if not self.is_ready():
            return False
        
        try:
            reading_manager = self._modules['reading']
            success = reading_manager.update_progress(book_id, current_page)
            
            if success:
                self._emit_event(AppEvent.READING_PROGRESS, {
                    'book_id': book_id,
                    'current_page': current_page
                })
                self._clear_cache()
            
            return success
        except Exception as e:
            logger.error(f"Erro ao atualizar progresso: {e}")
            return False
    
    def add_book_from_file(self, file_path: str, options: Dict[str, Any]) -> Dict[str, Any]:
        """Adiciona novo livro a partir de arquivo"""
        if not self.is_ready():
            return {'success': False, 'message': 'Backend não disponível'}
        
        try:
            book_processor = self._modules['book_processor']
            
            # Configurar qualidade de processamento
            quality_map = {
                'draft': ProcessingQuality.DRAFT,
                'standard': ProcessingQuality.STANDARD,
                'high': ProcessingQuality.HIGH,
                'academic': ProcessingQuality.ACADEMIC
            }
            
            quality = quality_map.get(options.get('quality', 'standard'), ProcessingQuality.STANDARD)
            
            # Processar livro
            result = book_processor.process(
                input_path=file_path,
                quality=quality,
                auto_integrate=options.get('auto_integrate', True)
            )
            
            if result.success:
                self._emit_event(AppEvent.BOOK_ADDED, {'book': result.metadata})
                self._clear_cache()
                
                # Se solicitado, integrar com agenda
                if options.get('schedule_reading', False):
                    self._schedule_book_reading(result.metadata['id'], options.get('deadline_days', 30))
            
            return {
                'success': result.success,
                'message': result.message,
                'book_id': result.metadata.get('id') if result.success else None,
                'metadata': result.metadata
            }
            
        except Exception as e:
            logger.error(f"Erro ao processar livro: {e}")
            return {'success': False, 'message': f'Erro: {str(e)}'}
    
    def _schedule_book_reading(self, book_id: int, deadline_days: int):
        """Agenda leitura do livro"""
        try:
            from core.integration.book_integration import BookIntegrationSystem
            integration = BookIntegrationSystem()
            integration.integrate_book(book_id, deadline_days)
        except Exception as e:
            logger.error(f"Erro ao agendar leitura: {e}")
    
    # === MÉTODOS DE CHECK-IN ===
    
    def perform_daily_checkin(self, responses: Dict[str, Any]) -> Dict[str, Any]:
        """Realiza check-in diário"""
        if not self.is_ready():
            return {'success': False, 'message': 'Backend não disponível'}
        
        try:
            checkin_system = self._modules['checkin']
            result = checkin_system.process_checkin(responses)
            
            if result['success']:
                self._emit_event(AppEvent.CHECKIN_DONE, result)
                self._clear_cache()
                
                # Aplicar ajustes se necessário
                if result.get('adjustments_needed'):
                    self._apply_checkin_adjustments(result['adjustments'])
            
            return result
        except Exception as e:
            logger.error(f"Erro no check-in: {e}")
            return {'success': False, 'message': f'Erro: {str(e)}'}
    
    # === MÉTODOS DE POMODORO ===
    
    def start_pomodoro_session(self, session_type: str, duration: int = 25) -> bool:
        """Inicia sessão Pomodoro"""
        if not self.is_ready():
            return False
        
        try:
            pomodoro = self._modules['pomodoro']
            success = pomodoro.start_session(
                session_type=session_type,
                duration_minutes=duration
            )
            
            if success:
                self._emit_event(AppEvent.SESSION_STARTED, {
                    'type': session_type,
                    'duration': duration
                })
            
            return success
        except Exception as e:
            logger.error(f"Erro ao iniciar Pomodoro: {e}")
            return False
    
    # === MÉTODOS DO LLM (GLaDOS) ===
    
    def ask_glados(self, query: str, use_context: bool = True) -> Dict[str, Any]:
        """Faz uma pergunta ao GLaDOS"""
        if not self.is_ready():
            return {
                'text': f"[Sistema offline] {query}",
                'context_used': False,
                'cache_hit': False
            }
        
        try:
            llm = self._modules['llm']
            
            # Usar nome do settings ou padrão
            user_name = getattr(settings.llm.glados, 'user_name', 'Usuário')
            
            response = llm.generate(
                query=query,
                user_name=user_name,
                use_semantic=use_context
            )
            
            # Adicionar personalidade GLaDOS
            if 'glados_voice' in self._modules:
                glados_voice = self._modules['glados_voice']
                response['text'] = glados_voice.format_response(query, response.get('text', ''))
            
            return response
        except Exception as e:
            logger.error(f"Erro ao consultar GLaDOS: {e}")
            return {
                'text': f"Desculpe, não consegui processar sua pergunta. Erro: {str(e)}",
                'error': str(e),
                'context_used': False,
                'cache_hit': False
            }
    
    # === MÉTODOS DE DASHBOARD ===
    
    def get_dashboard_data(self, force_refresh: bool = False) -> DashboardData:
        """Obtém dados completos para o dashboard"""
        # Verificar cache
        if not force_refresh and self._dashboard_cache and self._cache_timestamp:
            cache_age = time.time() - self._cache_timestamp
            if cache_age < self._cache_ttl:
                return self._dashboard_cache
        
        if not self.is_ready():
            return self._get_mock_dashboard()
        
        try:
            data = DashboardData()
            
            # 1. Metas do dia
            data.daily_goals = self._get_daily_goals()
            
            # 2. Agenda do dia
            data.upcoming_events = self.get_today_agenda()
            
            # 3. Livros ativos
            data.active_books = self.get_active_books()
            
            # 4. Alertas
            data.alerts = self._get_alerts()
            
            # 5. Estatísticas
            data.daily_stats = self._get_daily_stats()
            
            # 6. Tarefas pendentes
            data.pending_tasks = self._get_pending_tasks()
            
            # 7. Mensagem do dia
            data.daily_message = self._get_daily_message()
            
            # 8. Estado da aplicação
            data.app_state = {
                'initialized': self._initialized,
                'backend_available': BACKEND_AVAILABLE,
                'timestamp': datetime.now().isoformat(),
                'glados_quote': self.glados_quote
            }
            
            # Atualizar cache
            self._dashboard_cache = data
            self._cache_timestamp = time.time()
            
            return data
            
        except Exception as e:
            logger.error(f"Erro ao gerar dashboard: {e}")
            return self._get_mock_dashboard()
    
    def _get_daily_goals(self) -> List[Dict[str, Any]]:
        """Obtém metas do dia"""
        # Baseado nos livros ativos e agenda
        goals = []
        
        # Meta de leitura
        active_books = self.get_active_books()
        for book in active_books:
            if book.get('days_remaining') and book['days_remaining'] > 0:
                pages_per_day = (book['total_pages'] - book['current_page']) / book['days_remaining']
                goals.append({
                    'type': 'reading',
                    'title': f"Ler {book['title']}",
                    'target': round(pages_per_day),
                    'current': 0,
                    'unit': 'páginas',
                    'icon': '📚'
                })
        
        # Metas fixas
        goals.extend([
            {
                'type': 'writing',
                'title': 'Produção acadêmica',
                'target': 500,
                'current': 0,
                'unit': 'palavras',
                'icon': '✍️'
            },
            {
                'type': 'review',
                'title': 'Revisão espaçada',
                'target': 15,
                'current': 0,
                'unit': 'flashcards',
                'icon': '🔄'
            }
        ])
        
        return goals
    
    def _get_alerts(self) -> List[Dict[str, Any]]:
        """Obtém alertas do sistema"""
        alerts = []
        
        if not self.is_ready():
            return alerts
        
        try:
            # Verificar prazos próximos
            reading_manager = self._modules['reading']
            urgent_books = reading_manager.get_books_with_approaching_deadline(days=3)
            
            for book in urgent_books:
                alerts.append({
                    'type': 'warning',
                    'title': f"Prazo próximo: {book.title}",
                    'message': f"Termina em {book.days_remaining} dias",
                    'action': f'glados livro progresso --livro {book.id}',
                    'icon': '⚠️'
                })
            
            # Verificar check-in pendente
            checkin_system = self._modules['checkin']
            if not checkin_system.today_checkin_done():
                alerts.append({
                    'type': 'info',
                    'title': "Check-in diário pendente",
                    'message': "Complete seu check-in para ajustar o planejamento",
                    'action': 'checkin diario',
                    'icon': '✅'
                })
            
        except Exception as e:
            logger.error(f"Erro ao obter alertas: {e}")
        
        return alerts
    
    def _get_daily_stats(self) -> Dict[str, Any]:
        """Obtém estatísticas do dia"""
        if not self.is_ready():
            return {
                'productivity_score': 0,
                'focus_time': 0,
                'tasks_completed': 0,
                'pages_read': 0,
                'words_written': 0
            }
        
        try:
            # Obter estatísticas dos vários módulos
            stats = {
                'productivity_score': 75,  # Mock - implementar com métricas reais
                'focus_time': 180,  # minutos
                'tasks_completed': 3,
                'pages_read': 45,
                'words_written': 1200,
                'last_updated': datetime.now().isoformat()
            }
            
            return stats
        except Exception as e:
            logger.error(f"Erro ao obter estatísticas: {e}")
            return {}
    
    def _get_pending_tasks(self) -> List[Dict[str, Any]]:
        """Obtém tarefas pendentes"""
        if not self.is_ready():
            return []
        
        try:
            task_repo = self._modules['task_repo']
            tasks = task_repo.find_today_tasks()
            
            ui_tasks = []
            for task in tasks[:10]:  # Limitar a 10 tarefas
                if not task.completed:
                    ui_tasks.append({
                        'id': task.id,
                        'title': task.title,
                        'type': task.task_type.value if hasattr(task.task_type, 'value') else str(task.task_type),
                        'time': f"{task.start_time.strftime('%H:%M')} - {task.end_time.strftime('%H:%M')}",
                        'priority': task.priority,
                        'completed': task.completed
                    })
            
            return ui_tasks
        except Exception as e:
            logger.error(f"Erro ao obter tarefas: {e}")
            return []
    
    def _generate_daily_message(self):
        """Gera mensagem do dia do GLaDOS"""
        if not self.is_ready():
            self._daily_message = self.glados_quote
            return
        
        try:
            llm = self._modules['llm']
            
            prompt = f"""Como GLaDOS, dê boas-vindas sarcásticas para o dia.
            Hoje é {date.today().strftime('%d/%m/%Y')}.
            Inclua referências à filosofia e ao aprendizado.
            Seja passivo-agressiva mas útil.
            Mantenha em 2-3 frases."""
            
            response = llm.generate(prompt, use_semantic=False)
            self._daily_message = response.get('text', self.glados_quote)
            
        except Exception as e:
            logger.error(f"Erro ao gerar mensagem: {e}")
            self._daily_message = self.glados_quote
    
    def _get_daily_message(self) -> str:
        """Obtém mensagem do dia"""
        if not hasattr(self, '_daily_message'):
            self._generate_daily_message()
        return getattr(self, '_daily_message', self.glados_quote)
    
    # === MÉTODOS DE EVENTOS ===
    
    def _emit_event(self, event_type: AppEvent, data: Dict[str, Any] = None):
        """Emite um evento para listeners"""
        if event_type in self._event_listeners:
            for callback in self._event_listeners[event_type]:
                try:
                    callback(event_type, data or {})
                except Exception as e:
                    logger.error(f"Erro em listener de evento: {e}")
    
    def register_event_listener(self, event_type: AppEvent, callback):
        """Registra listener para eventos"""
        if event_type not in self._event_listeners:
            self._event_listeners[event_type] = []
        self._event_listeners[event_type].append(callback)
    
    def _clear_cache(self):
        """Limpa cache do dashboard"""
        self._dashboard_cache = None
        self._cache_timestamp = None
        self._emit_event(AppEvent.UI_REFRESH_NEEDED)
    
    # === MÉTODOS AUXILIARES ===
    
    def _format_time_range(self, start_time, end_time) -> str:
        """Formata intervalo de tempo"""
        if hasattr(start_time, 'strftime') and hasattr(end_time, 'strftime'):
            return f"{start_time.strftime('%H:%M')}-{end_time.strftime('%H:%M')}"
        return "00:00-00:00"
    
    # === MÉTODOS MOCK (para desenvolvimento) ===
    
    def _get_mock_dashboard(self) -> DashboardData:
        """Dashboard mock para desenvolvimento"""
        return DashboardData(
            daily_goals=[
                {'type': 'reading', 'title': 'Ler A República', 'target': 25, 'current': 10, 'unit': 'páginas', 'icon': '📚'},
                {'type': 'writing', 'title': 'Produção acadêmica', 'target': 500, 'current': 200, 'unit': 'palavras', 'icon': '✍️'},
                {'type': 'review', 'title': 'Revisão espaçada', 'target': 15, 'current': 8, 'unit': 'flashcards', 'icon': '🔄'}
            ],
            upcoming_events=[
                {'time': '09:00-11:00', 'title': 'A República - Platão', 'type': 'leitura', 'description': 'Livro I'},
                {'time': '14:00-16:00', 'title': 'Aula: Ética', 'type': 'aula', 'description': 'Sala 12'},
                {'time': '19:00-20:00', 'title': 'Paper: Virtude', 'type': 'producao', 'description': 'Rascunho inicial'}
            ],
            alerts=[
                {'type': 'warning', 'title': 'Prova de Lógica em 3 dias', 'message': 'Prepare-se para o fracasso inevitável.', 'icon': '⚠️'},
                {'type': 'info', 'title': 'Check-in diário pendente', 'message': 'Complete para ajustar o planejamento', 'icon': '✅'}
            ],
            daily_stats={
                'productivity_score': 78,
                'focus_time': 180,
                'tasks_completed': 3,
                'pages_read': 45,
                'words_written': 1200
            },
            active_books=[
                {'title': 'A República', 'author': 'Platão', 'progress': 45.0, 'current_page': 225, 'total_pages': 500},
                {'title': 'Crítica da Razão Pura', 'author': 'Kant', 'progress': 28.5, 'current_page': 142, 'total_pages': 500}
            ],
            pending_tasks=[
                {'title': 'Revisar flashcards', 'type': 'review', 'time': '09:00-09:30', 'priority': 2},
                {'title': 'Buscar referências', 'type': 'research', 'time': '16:00-17:00', 'priority': 1}
            ],
            daily_message=self.glados_quote,
            app_state={
                'initialized': False,
                'backend_available': False,
                'timestamp': datetime.now().isoformat(),
                'glados_quote': self.glados_quote
            }
        )
    
    def _get_mock_agenda(self):
        """Agenda mock"""
        return [
            {'time': '09:00-11:00', 'title': 'A República - Platão', 'type': 'leitura', 'description': 'Livro I'},
            {'time': '14:00-16:00', 'title': 'Aula: Ética', 'type': 'aula', 'description': 'Sala 12'},
            {'time': '19:00-20:00', 'title': 'Paper: Virtude', 'type': 'producao', 'description': 'Rascunho inicial'}
        ]
    
    def _get_mock_books(self):
        """Livros mock"""
        return [
            {'title': 'A República', 'author': 'Platão', 'progress': 45.0, 'current_page': 225, 'total_pages': 500},
            {'title': 'Crítica da Razão Pura', 'author': 'Kant', 'progress': 28.5, 'current_page': 142, 'total_pages': 500}
        ]

# Instância global
backend = BackendIntegration()
