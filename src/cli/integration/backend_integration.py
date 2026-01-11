"""
Integração com o backend do GLaDOS Planner

Sistema centralizado para comunicação entre a interface CLI interativa
e os módulos backend do sistema.
"""
from typing import Dict, List, Optional, Any, Callable, Set
from datetime import datetime, timedelta
import json
import time
from pathlib import Path
import threading
from enum import Enum
from dataclasses import dataclass, field
from collections import defaultdict
import sys
import os
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Adiciona o caminho do projeto ao sys.path
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Importações dos módulos backend (com fallbacks)
AGENDA_MANAGER_AVAILABLE = False
READING_MANAGER_AVAILABLE = False
BOOK_PROCESSOR_AVAILABLE = False
REVIEW_SYSTEM_AVAILABLE = False
DAILY_CHECKIN_AVAILABLE = False
POMODORO_TIMER_AVAILABLE = False
WRITING_ASSISTANT_AVAILABLE = False
OBSIDIAN_VAULT_AVAILABLE = False
LOCAL_LLM_AVAILABLE = False
BOOK_REPOSITORY_AVAILABLE = False
TASK_REPOSITORY_AVAILABLE = False
NOTE_REPOSITORY_AVAILABLE = False

# Classes mock para quando os módulos não estiverem disponíveis
class MockAgendaManager:
    def __init__(self, vault_path: str, user_id: str = "default"):
        self.vault_path = vault_path
        self.user_id = user_id
        self.events = []
    
    def get_day_events(self, date_str: str = None) -> List:
        return []
    
    def add_event(self, title: str, start: str, end: str, event_type: str = "casual", **kwargs):
        event_id = f"mock_event_{len(self.events)}"
        self.events.append({
            'id': event_id,
            'title': title,
            'start': start,
            'end': end,
            'type': event_type
        })
        return event_id

class MockReadingManager:
    def __init__(self, vault_path: str = None, user_id: str = "default"):
        self.vault_path = vault_path
        self.user_id = user_id
        self.progress = {}
    
    def get_all_progress(self) -> Dict:
        return {}
    
    def update_progress(self, book_id: str, current_page: int, notes: str = "") -> bool:
        return True
    
    def get_reading_progress(self, book_id: str) -> Optional[Dict]:
        return None

class MockDailyCheckinSystem:
    def __init__(self, vault_path: str, user_id: str = "default"):
        self.vault_path = vault_path
        self.user_id = user_id
    
    def morning_routine(self, *args, **kwargs):
        return {
            "checkin_id": "mock_checkin_morning",
            "time": datetime.now().strftime("%H:%M"),
            "suggested_activities": [],
            "personalized_tip": "Mock tip"
        }
    
    def evening_checkin(self, *args, **kwargs):
        return {
            "checkin_id": "mock_checkin_evening", 
            "time": datetime.now().strftime("%H:%M"),
            "mood_score": 3.0,
            "productivity_score": 5.0
        }

class MockPomodoroTimer:
    def __init__(self, vault_path: str = None, user_id: str = "default"):
        self.vault_path = vault_path
        self.user_id = user_id
        self.is_running = False
    
    def start(self, duration: int = 25, task: str = ""):
        self.is_running = True
        return True
    
    def stop(self):
        self.is_running = False
        return True

class MockLocalLLM:
    def __init__(self, model_path: str = None, vault_path: str = None):
        self.model_path = model_path
        self.vault_path = vault_path
    
    def ask(self, question: str, *args, **kwargs) -> str:
        return f"[Sistema offline] {question}"

# Tenta importar módulos reais
try:
    from src.core.modules.agenda_manager import AgendaManager
    AGENDA_MANAGER_AVAILABLE = True
except ImportError as e:
    logger.warning(f"AgendaManager não disponível: {e}")
    AgendaManager = MockAgendaManager

try:
    from src.core.modules.reading_manager import ReadingManager
    READING_MANAGER_AVAILABLE = True
except ImportError as e:
    logger.warning(f"ReadingManager não disponível: {e}")
    ReadingManager = MockReadingManager

try:
    from src.core.modules.daily_checkin import DailyCheckinSystem
    DAILY_CHECKIN_AVAILABLE = True
except ImportError as e:
    logger.warning(f"DailyCheckinSystem não disponível: {e}")
    DailyCheckinSystem = MockDailyCheckinSystem

try:
    from src.core.llm.local_llm import LocalLLM
    LOCAL_LLM_AVAILABLE = True
except ImportError as e:
    logger.warning(f"LocalLLM não disponível: {e}")
    LocalLLM = MockLocalLLM

try:
    from src.core.modules.pomodoro_timer import PomodoroTimer
    POMODORO_TIMER_AVAILABLE = True
except ImportError as e:
    logger.warning(f"PomodoroTimer não disponível: {e}")
    PomodoroTimer = MockPomodoroTimer

try:
    from src.core.modules.book_processor import BookProcessor
    BOOK_PROCESSOR_AVAILABLE = True
except ImportError as e:
    logger.warning(f"BookProcessor não disponível: {e}")
    BookProcessor = None

try:
    from src.core.modules.review_system import ReviewSystem
    REVIEW_SYSTEM_AVAILABLE = True
except ImportError as e:
    logger.warning(f"ReviewSystem não disponível: {e}")
    ReviewSystem = None

try:
    from src.core.modules.writing_assistant import WritingAssistant
    WRITING_ASSISTANT_AVAILABLE = True
except ImportError as e:
    logger.warning(f"WritingAssistant não disponível: {e}")
    WritingAssistant = None


class AppEvent(Enum):
    """Eventos da aplicação para sistema pub/sub"""
    APP_START = "app_start"
    APP_SHUTDOWN = "app_shutdown"
    SCREEN_CHANGED = "screen_changed"
    DATA_UPDATED = "data_updated"
    EVENT_ADDED = "event_added"
    EVENT_UPDATED = "event_updated"
    EVENT_COMPLETED = "event_completed"
    READING_PROGRESS_UPDATED = "reading_progress_updated"
    BOOK_ADDED = "book_added"
    BOOK_COMPLETED = "book_completed"
    CHECKIN_PERFORMED = "checkin_performed"
    POMODORO_STARTED = "pomodoro_started"
    POMODORO_COMPLETED = "pomodoro_completed"
    ALERT_TRIGGERED = "alert_triggered"
    ERROR_OCCURRED = "error_occurred"
    USER_ACTION = "user_action"
    UI_REFRESH_NEEDED = "ui_refresh_needed"


@dataclass
class EventData:
    """Dados de um evento"""
    event_type: AppEvent
    timestamp: datetime
    data: Dict[str, Any] = field(default_factory=dict)
    source: str = "backend_integration"


class EventListener:
    """Listener para eventos da aplicação"""
    def __init__(self, callback: Callable[[EventData], None], 
                 event_types: Optional[Set[AppEvent]] = None):
        self.callback = callback
        self.event_types = event_types or set(AppEvent)
    
    def should_receive(self, event_type: AppEvent) -> bool:
        """Verifica se deve receber este tipo de evento"""
        return event_type in self.event_types
    
    def receive(self, event_data: EventData):
        """Recebe e processa o evento"""
        try:
            self.callback(event_data)
        except Exception as e:
            logger.error(f"Erro no listener: {e}")


@dataclass
class DashboardData:
    """Estrutura de dados para o dashboard"""
    daily_goals: List[Dict] = field(default_factory=list)
    upcoming_events: List[Dict] = field(default_factory=list)
    alerts: List[Dict] = field(default_factory=list)
    daily_stats: Dict[str, Any] = field(default_factory=dict)
    active_books: List[Dict] = field(default_factory=list)
    pending_tasks: List[Dict] = field(default_factory=list)
    daily_message: str = ""
    app_state: Dict[str, Any] = field(default_factory=dict)


class BackendIntegration:
    """Integração centralizada com o backend do GLaDOS Planner"""
    
    def __init__(self, vault_path: Optional[str] = None, user_id: str = "default"):
        """
        Inicializa a integração com o backend
        
        Args:
            vault_path: Caminho para o vault do Obsidian (opcional)
            user_id: ID do usuário para personalização
        """
        self.vault_path = vault_path
        self.user_id = user_id
        
        logger.info("🚀 Inicializando integração com backend GLaDOS...")
        
        # Inicializa módulos do backend
        self._modules = {}
        self._initialize_modules()
        
        # Sistema de eventos
        self._listeners: List[EventListener] = []
        self._event_history: List[EventData] = []
        self._max_history_size = 100
        
        # Cache para dados frequentes
        self._cache: Dict[str, Any] = {}
        self._cache_ttl: Dict[str, datetime] = {}
        self._cache_lock = threading.RLock()
        
        # Contador de erros
        self._error_count = defaultdict(int)
        
        # Estado da aplicação
        self._app_state = {
            "started_at": datetime.now().isoformat(),
            "last_update": datetime.now().isoformat(),
            "module_status": self._get_module_status(),
            "total_events_processed": 0
        }
        
        # Emite evento de inicialização
        self._emit_event(AppEvent.APP_START, {
            "module_count": len(self._modules),
            "available_modules": list(self._modules.keys())
        })
        
        logger.info("✅ Backend GLaDOS carregado com sucesso")
    
    def _initialize_modules(self):
        """Inicializa todos os módulos disponíveis"""
        modules_config = []
        
        # Determina caminho do vault
        vault_to_use = self.vault_path or self._find_default_vault()
        
        # AgendaManager - funciona com 2 args
        if AGENDA_MANAGER_AVAILABLE and vault_to_use:
            try:
                self._modules['agenda_manager'] = AgendaManager(vault_to_use, self.user_id)
                modules_config.append(("agenda_manager", "✅"))
                logger.info(f"AgendaManager inicializado")
            except Exception as e:
                logger.error(f"Erro ao inicializar AgendaManager: {e}")
                self._modules['agenda_manager'] = MockAgendaManager(vault_to_use, self.user_id)
                modules_config.append(("agenda_manager", "⚠️ (mock)"))
        else:
            vault_for_mock = vault_to_use or str(Path.home() / ".glados_mock")
            self._modules['agenda_manager'] = MockAgendaManager(vault_for_mock, self.user_id)
            modules_config.append(("agenda_manager", "⚠️ (mock)"))
        
        # ReadingManager - parece que aceita apenas 1 arg (vault_path)
        if READING_MANAGER_AVAILABLE and vault_to_use:
            try:
                # Primeiro tenta com apenas vault_path
                self._modules['reading_manager'] = ReadingManager(vault_to_use)
                modules_config.append(("reading_manager", "✅"))
                logger.info(f"ReadingManager inicializado com 1 arg")
            except Exception as e1:
                logger.debug(f"Tentativa 1 falhou: {e1}")
                try:
                    # Tenta com 2 args
                    self._modules['reading_manager'] = ReadingManager(vault_to_use, self.user_id)
                    modules_config.append(("reading_manager", "✅"))
                    logger.info(f"ReadingManager inicializado com 2 args")
                except Exception as e2:
                    logger.error(f"Erro ao inicializar ReadingManager: {e2}")
                    self._modules['reading_manager'] = MockReadingManager(vault_to_use, self.user_id)
                    modules_config.append(("reading_manager", "⚠️ (mock)"))
        else:
            vault_for_mock = vault_to_use or str(Path.home() / ".glados_mock")
            self._modules['reading_manager'] = MockReadingManager(vault_for_mock, self.user_id)
            modules_config.append(("reading_manager", "⚠️ (mock)"))
        
        # DailyCheckinSystem - funciona com 2 args
        if DAILY_CHECKIN_AVAILABLE and vault_to_use:
            try:
                self._modules['daily_checkin'] = DailyCheckinSystem(vault_to_use, self.user_id)
                modules_config.append(("daily_checkin", "✅"))
            except Exception as e:
                logger.error(f"Erro ao inicializar DailyCheckinSystem: {e}")
                self._modules['daily_checkin'] = MockDailyCheckinSystem(vault_to_use, self.user_id)
                modules_config.append(("daily_checkin", "⚠️ (mock)"))
        else:
            vault_for_mock = vault_to_use or str(Path.home() / ".glados_mock")
            self._modules['daily_checkin'] = MockDailyCheckinSystem(vault_for_mock, self.user_id)
            modules_config.append(("daily_checkin", "⚠️ (mock)"))
        
        # PomodoroTimer - pode aceitar 0, 1 ou 2 args
        if POMODORO_TIMER_AVAILABLE:
            try:
                # Primeiro tenta sem args
                try:
                    self._modules['pomodoro_timer'] = PomodoroTimer()
                    modules_config.append(("pomodoro_timer", "✅"))
                    logger.info(f"PomodoroTimer inicializado sem args")
                except Exception as e1:
                    logger.debug(f"Tentativa 1 falhou: {e1}")
                    try:
                        # Tenta com vault_path apenas
                        self._modules['pomodoro_timer'] = PomodoroTimer(vault_to_use)
                        modules_config.append(("pomodoro_timer", "✅"))
                        logger.info(f"PomodoroTimer inicializado com 1 arg")
                    except Exception as e2:
                        logger.debug(f"Tentativa 2 falhou: {e2}")
                        try:
                            # Tenta com ambos args
                            self._modules['pomodoro_timer'] = PomodoroTimer(vault_to_use, self.user_id)
                            modules_config.append(("pomodoro_timer", "✅"))
                            logger.info(f"PomodoroTimer inicializado com 2 args")
                        except Exception as e3:
                            logger.debug(f"Tentativa 3 falhou: {e3}")
                            raise
            except Exception as e:
                logger.error(f"Erro ao inicializar PomodoroTimer: {e}")
                self._modules['pomodoro_timer'] = MockPomodoroTimer(vault_to_use, self.user_id)
                modules_config.append(("pomodoro_timer", "⚠️ (mock)"))
        else:
            self._modules['pomodoro_timer'] = MockPomodoroTimer(vault_to_use, self.user_id)
            modules_config.append(("pomodoro_timer", "⚠️ (mock)"))
        
        # LocalLLM
        if LOCAL_LLM_AVAILABLE:
            try:
                model_path = self._find_model_path()
                if model_path:
                    # Tenta diferentes combinações
                    try:
                        self._modules['local_llm'] = LocalLLM(model_path=model_path)
                        modules_config.append(("local_llm", f"✅ ({Path(model_path).name})"))
                    except Exception as e1:
                        logger.debug(f"Tentativa 1 falhou: {e1}")
                        try:
                            self._modules['local_llm'] = LocalLLM(model_path=model_path, vault_path=vault_to_use)
                            modules_config.append(("local_llm", f"✅ ({Path(model_path).name})"))
                        except Exception as e2:
                            logger.debug(f"Tentativa 2 falhou: {e2}")
                            raise
                else:
                    self._modules['local_llm'] = MockLocalLLM(vault_path=vault_to_use)
                    modules_config.append(("local_llm", "⚠️ (mock - sem modelo)"))
            except Exception as e:
                logger.error(f"Erro ao inicializar LocalLLM: {e}")
                self._modules['local_llm'] = MockLocalLLM(vault_path=vault_to_use)
                modules_config.append(("local_llm", "⚠️ (mock)"))
        else:
            self._modules['local_llm'] = MockLocalLLM(vault_path=vault_to_use)
            modules_config.append(("local_llm", "⚠️ (mock)"))
        
        # BookProcessor - aceita 1-2 args
        if BOOK_PROCESSOR_AVAILABLE and vault_to_use:
            try:
                # Primeiro tenta com 1 arg
                try:
                    self._modules['book_processor'] = BookProcessor(vault_to_use)
                    modules_config.append(("book_processor", "✅"))
                    logger.info(f"BookProcessor inicializado com 1 arg")
                except Exception as e1:
                    logger.debug(f"Tentativa 1 falhou: {e1}")
                    try:
                        # Tenta com 2 args
                        self._modules['book_processor'] = BookProcessor(vault_to_use, self.user_id)
                        modules_config.append(("book_processor", "✅"))
                        logger.info(f"BookProcessor inicializado com 2 args")
                    except Exception as e2:
                        logger.debug(f"Tentativa 2 falhou: {e2}")
                        raise
            except Exception as e:
                logger.error(f"Erro ao inicializar BookProcessor: {e}")
                modules_config.append(("book_processor", "❌"))
        
        # ReviewSystem - parece que aceita apenas 1 arg
        if REVIEW_SYSTEM_AVAILABLE and vault_to_use:
            try:
                # Primeiro tenta com 1 arg
                try:
                    self._modules['review_system'] = ReviewSystem(vault_to_use)
                    modules_config.append(("review_system", "✅"))
                    logger.info(f"ReviewSystem inicializado com 1 arg")
                except Exception as e1:
                    logger.debug(f"Tentativa 1 falhou: {e1}")
                    try:
                        # Tenta com 2 args
                        self._modules['review_system'] = ReviewSystem(vault_to_use, self.user_id)
                        modules_config.append(("review_system", "✅"))
                        logger.info(f"ReviewSystem inicializado com 2 args")
                    except Exception as e2:
                        logger.debug(f"Tentativa 2 falhou: {e2}")
                        raise
            except Exception as e:
                logger.error(f"Erro ao inicializar ReviewSystem: {e}")
                modules_config.append(("review_system", "❌"))
        
        # WritingAssistant - parece que aceita apenas 1 arg
        if WRITING_ASSISTANT_AVAILABLE and vault_to_use:
            try:
                # Primeiro tenta com 1 arg
                try:
                    self._modules['writing_assistant'] = WritingAssistant(vault_to_use)
                    modules_config.append(("writing_assistant", "✅"))
                    logger.info(f"WritingAssistant inicializado com 1 arg")
                except Exception as e1:
                    logger.debug(f"Tentativa 1 falhou: {e1}")
                    try:
                        # Tenta com 2 args
                        self._modules['writing_assistant'] = WritingAssistant(vault_to_use, self.user_id)
                        modules_config.append(("writing_assistant", "✅"))
                        logger.info(f"WritingAssistant inicializado com 2 args")
                    except Exception as e2:
                        logger.debug(f"Tentativa 2 falhou: {e2}")
                        raise
            except Exception as e:
                logger.error(f"Erro ao inicializar WritingAssistant: {e}")
                modules_config.append(("writing_assistant", "❌"))
        
        # Log de inicialização
        logger.info("\n" + "=" * 50)
        logger.info("INICIALIZAÇÃO DO BACKEND GLaDOS")
        logger.info("=" * 50)
        for module_name, status in modules_config:
            logger.info(f"  {module_name:20} {status}")
        logger.info("=" * 50)
    
    def _find_default_vault(self) -> Optional[str]:
        """Tenta encontrar um vault Obsidian padrão"""
        default_paths = [
            Path.home() / "Documents" / "Obsidian",
            Path.home() / "Obsidian",
            Path.home() / ".obsidian",
            Path.cwd() / "vault",
            Path.cwd() / "test_vault",
            Path.home() / "Documents" / "Obsidian" / "Philosophy_Vault",
        ]
        
        for path in default_paths:
            if path.exists() and path.is_dir():
                logger.info(f"Vault encontrado: {path}")
                return str(path)
        
        logger.warning("Nenhum vault Obsidian encontrado")
        return None
    
    def _find_model_path(self) -> Optional[str]:
        """Tenta encontrar um modelo LLM localmente"""
        model_dirs = [
            Path.home() / ".cache" / "models",
            project_root / "data" / "models",
            Path.cwd() / "models",
            Path.home() / "Downloads",
            Path.home() / "Documents" / "models",
        ]
        
        model_patterns = ["*.gguf", "*.bin", "*.pt"]
        
        for model_dir in model_dirs:
            if model_dir.exists():
                for pattern in model_patterns:
                    model_files = list(model_dir.glob(pattern))
                    if model_files:
                        # Prefere modelos menores para teste
                        for model in model_files:
                            if "tiny" in model.name.lower() or "small" in model.name.lower():
                                return str(model)
                        # Se não encontrar um modelo pequeno, usa o primeiro
                        return str(model_files[0])
        
        return None
    
    def _get_module_status(self) -> Dict[str, str]:
        """Retorna status de todos os módulos"""
        status = {}
        for name, module in self._modules.items():
            module_class = module.__class__.__name__
            if 'Mock' in module_class:
                status[name] = "⚠️ mock"
            else:
                status[name] = "✅ real"
        return status
    
    def is_ready(self) -> bool:
        """Verifica se o backend está pronto para uso"""
        # Verifica se temos pelo menos 2 módulos reais (não mocks)
        real_modules = 0
        for name, module in self._modules.items():
            module_class = module.__class__.__name__
            if 'Mock' not in module_class:
                real_modules += 1
        
        return real_modules >= 2  # Pelo menos 2 módulos reais
    
    def _emit_event(self, event_type: AppEvent, data: Dict[str, Any] = None, 
                   source: str = "backend_integration"):
        """Emite um evento para todos os listeners"""
        if data is None:
            data = {}
        
        event_data = EventData(
            event_type=event_type,
            timestamp=datetime.now(),
            data=data,
            source=source
        )
        
        # Adiciona ao histórico
        self._event_history.append(event_data)
        if len(self._event_history) > self._max_history_size:
            self._event_history.pop(0)
        
        # Atualiza estatísticas
        self._app_state["total_events_processed"] += 1
        self._app_state["last_update"] = datetime.now().isoformat()
        
        # Notifica listeners
        for listener in self._listeners:
            if listener.should_receive(event_type):
                listener.receive(event_data)
    
    def add_listener(self, listener: EventListener):
        """Adiciona um listener para eventos"""
        self._listeners.append(listener)
    
    def remove_listener(self, listener: EventListener):
        """Remove um listener"""
        if listener in self._listeners:
            self._listeners.remove(listener)
    
    def add_simple_listener(self, callback: Callable[[EventData], None], 
                           event_types: Optional[List[AppEvent]] = None):
        """Adiciona um listener simples"""
        listener = EventListener(callback, set(event_types) if event_types else None)
        self.add_listener(listener)
        return listener
    
    # ====== MÉTODOS DE ACESSO A DADOS ======
    
    def _get_cached(self, key: str, ttl_seconds: int = 60) -> Optional[Any]:
        """Obtém dados do cache se ainda forem válidos"""
        with self._cache_lock:
            if key in self._cache and key in self._cache_ttl:
                if datetime.now() < self._cache_ttl[key]:
                    return self._cache[key]
                else:
                    # Expirou, remove do cache
                    del self._cache[key]
                    del self._cache_ttl[key]
            return None
    
    def _set_cached(self, key: str, value: Any, ttl_seconds: int = 60):
        """Armazena dados no cache"""
        with self._cache_lock:
            self._cache[key] = value
            self._cache_ttl[key] = datetime.now() + timedelta(seconds=ttl_seconds)
    
    def clear_cache(self, key: Optional[str] = None):
        """Limpa o cache"""
        with self._cache_lock:
            if key:
                if key in self._cache:
                    del self._cache[key]
                if key in self._cache_ttl:
                    del self._cache_ttl[key]
            else:
                self._cache.clear()
                self._cache_ttl.clear()
    
    def get_today_agenda(self, use_cache: bool = True) -> List[Dict]:
        """
        Obtém a agenda do dia
        
        Returns:
            Lista de eventos do dia atual
        """
        cache_key = "today_agenda"
        
        if use_cache:
            cached = self._get_cached(cache_key, ttl_seconds=300)
            if cached is not None:
                return cached
        
        try:
            if 'agenda_manager' in self._modules:
                events = self._modules['agenda_manager'].get_day_events()
                result = []
                for event in events:
                    # Verifica se o evento tem os atributos necessários
                    if hasattr(event, 'id'):
                        result.append({
                            'id': getattr(event, 'id', 'mock_id'),
                            'title': getattr(event, 'title', 'Evento sem título'),
                            'type': getattr(event.type, 'value', 'casual') if hasattr(event, 'type') else 'casual',
                            'start': event.start.strftime("%H:%M") if hasattr(event, 'start') else datetime.now().strftime("%H:%M"),
                            'end': event.end.strftime("%H:%M") if hasattr(event, 'end') else datetime.now().strftime("%H:%M"),
                            'duration': getattr(event, 'duration_minutes', lambda: 60)() if hasattr(event, 'duration_minutes') else 60,
                            'completed': getattr(event, 'completed', False),
                            'priority': getattr(event.priority, 'name', 'MEDIA') if hasattr(event, 'priority') else 'MEDIA',
                            'description': getattr(getattr(event, 'metadata', {}), 'get', lambda x, y='': '')('description', '')
                        })
                
                if result:  # Só cache se tiver dados reais
                    self._set_cached(cache_key, result, ttl_seconds=300)
                return result
        except Exception as e:
            self._error_count['agenda_manager'] += 1
            logger.error(f"Erro ao obter agenda: {e}")
        
        # Fallback para dados mock
        return self._get_mock_agenda()
    
    def _get_mock_agenda(self) -> List[Dict]:
        """Dados mock para agenda"""
        return [
            {
                'id': 'event_1',
                'title': 'Leitura: A República - Platão',
                'type': 'leitura',
                'start': '09:00',
                'end': '11:00',
                'duration': 120,
                'completed': False,
                'priority': 'ALTA',
                'description': 'Livro I - Sobre Justiça'
            },
            {
                'id': 'event_2',
                'title': 'Aula: Ética',
                'type': 'aula',
                'start': '14:00',
                'end': '16:00',
                'duration': 120,
                'completed': False,
                'priority': 'FIXO',
                'description': 'Sala 12 - Professor Aristóteles'
            },
            {
                'id': 'event_3',
                'title': 'Produção: Artigo sobre Virtude',
                'type': 'producao',
                'start': '19:00',
                'end': '20:30',
                'duration': 90,
                'completed': False,
                'priority': 'ALTA',
                'description': 'Esboço inicial'
            }
        ]
    
    def get_active_books(self, use_cache: bool = True) -> List[Dict]:
        """
        Obtém livros ativos
        
        Returns:
            Lista de livros com progresso
        """
        cache_key = "active_books"
        
        if use_cache:
            cached = self._get_cached(cache_key, ttl_seconds=600)
            if cached is not None:
                return cached
        
        try:
            if 'reading_manager' in self._modules:
                # Tenta métodos diferentes
                if hasattr(self._modules['reading_manager'], 'get_all_progress'):
                    progress_data = self._modules['reading_manager'].get_all_progress()
                elif hasattr(self._modules['reading_manager'], 'get_progress'):
                    progress_data = self._modules['reading_manager'].get_progress()
                else:
                    progress_data = {}
                
                result = []
                
                if isinstance(progress_data, dict):
                    for book_id, progress in progress_data.items():
                        if isinstance(progress, dict) and progress.get('status') != 'completed':
                            result.append({
                                'id': book_id,
                                'title': progress.get('title', f"Livro {book_id[:8]}"),
                                'author': progress.get('author', 'Desconhecido'),
                                'current_page': progress.get('current_page', 0),
                                'total_pages': progress.get('total_pages', 1),
                                'progress': (progress.get('current_page', 0) / max(progress.get('total_pages', 1), 1)) * 100,
                                'status': progress.get('status', 'reading'),
                                'last_updated': progress.get('last_updated', '')
                            })
                
                if result:
                    self._set_cached(cache_key, result, ttl_seconds=600)
                return result
        except Exception as e:
            self._error_count['reading_manager'] += 1
            logger.error(f"Erro ao obter livros ativos: {e}")
        
        # Fallback para dados mock
        return self._get_mock_books()
    
    def _get_mock_books(self) -> List[Dict]:
        """Dados mock para livros"""
        return [
            {
                'id': 'book_1',
                'title': 'A República',
                'author': 'Platão',
                'current_page': 125,
                'total_pages': 300,
                'progress': 41.7,
                'status': 'reading',
                'last_updated': '2024-01-10'
            },
            {
                'id': 'book_2',
                'title': 'Ética a Nicômaco',
                'author': 'Aristóteles',
                'current_page': 80,
                'total_pages': 250,
                'progress': 32.0,
                'status': 'reading',
                'last_updated': '2024-01-09'
            }
        ]
    
    def get_dashboard_data(self, use_cache: bool = True) -> DashboardData:
        """
        Obtém todos os dados para o dashboard
        
        Returns:
            DashboardData completo
        """
        cache_key = "dashboard_data"
        
        if use_cache:
            cached = self._get_cached(cache_key, ttl_seconds=180)
            if cached is not None:
                return cached
        
        dashboard = DashboardData()
        
        # Agenda do dia
        dashboard.upcoming_events = self.get_today_agenda(use_cache=False)
        
        # Livros ativos
        dashboard.active_books = self.get_active_books(use_cache=False)
        
        # Metas do dia
        dashboard.daily_goals = self._get_daily_goals()
        
        # Estatísticas diárias
        dashboard.daily_stats = self._get_daily_stats()
        
        # Alertas
        dashboard.alerts = self._get_alerts()
        
        # Tarefas pendentes
        dashboard.pending_tasks = self._get_pending_tasks()
        
        # Mensagem do dia
        dashboard.daily_message = self._get_daily_message()
        
        # Estado da aplicação
        dashboard.app_state = {
            "module_count": len(self._modules),
            "ready": self.is_ready(),
            "errors": dict(self._error_count),
            "cache_size": len(self._cache),
            "mode": "real" if self.is_ready() else "mock",
            "timestamp": datetime.now().isoformat()
        }
        
        self._set_cached(cache_key, dashboard, ttl_seconds=180)
        return dashboard
    
    def _get_daily_goals(self) -> List[Dict]:
        """Obtém metas do dia"""
        goals = []
        
        # Meta de leitura
        active_books = self.get_active_books(use_cache=False)
        if active_books:
            goals.append({
                'id': 'reading_goal',
                'title': 'Leitura diária',
                'description': f'Ler 25 páginas ({len(active_books)} livros ativos)',
                'target': 25,
                'current': 0,
                'unit': 'páginas',
                'icon': '📚',
                'priority': 'high'
            })
        
        # Meta de revisão
        goals.append({
            'id': 'review_goal',
            'title': 'Revisão espaçada',
            'description': 'Revisar 15 flashcards',
            'target': 15,
            'current': 0,
            'unit': 'flashcards',
            'icon': '🔄',
            'priority': 'medium'
        })
        
        # Meta de eventos
        today_events = self.get_today_agenda(use_cache=False)
        event_count = len([e for e in today_events if not e.get('completed', False)])
        
        if event_count > 0:
            goals.append({
                'id': 'event_goal',
                'title': 'Compromissos',
                'description': f'Concluir {event_count} eventos agendados',
                'target': event_count,
                'current': 0,
                'unit': 'eventos',
                'icon': '📅',
                'priority': 'high'
            })
        
        return goals
    
    def _get_daily_stats(self) -> Dict[str, Any]:
        """Obtém estatísticas diárias"""
        today = datetime.now()
        
        return {
            'date': today.strftime("%Y-%m-%d"),
            'day_of_week': ['Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta', 'Sábado', 'Domingo'][today.weekday()],
            'events_today': len(self.get_today_agenda(use_cache=False)),
            'active_books_count': len(self.get_active_books(use_cache=False)),
            'productivity_score': 65,
            'focus_hours': 6.5,
            'completion_rate': 42,
            'streak_days': 7,
            'total_pages_read': 1250
        }
    
    def _get_alerts(self) -> List[Dict]:
        """Obtém alertas do sistema"""
        alerts = []
        
        if not self.is_ready():
            alerts.append({
                'id': 'backend_mock',
                'type': 'warning',
                'title': 'Backend em modo desenvolvimento',
                'message': 'Alguns módulos estão usando dados simulados',
                'priority': 'medium',
                'action': 'check_modules'
            })
        
        # Verifica se há eventos hoje
        today_events = self.get_today_agenda(use_cache=False)
        if not today_events:
            alerts.append({
                'id': 'no_events_today',
                'type': 'info',
                'title': 'Dia livre',
                'message': 'Não há eventos agendados para hoje',
                'priority': 'low',
                'action': 'add_event'
            })
        
        return alerts
    
    def _get_pending_tasks(self) -> List[Dict]:
        """Obtém tarefas pendentes"""
        tasks = []
        
        # Tarefas de leitura
        active_books = self.get_active_books(use_cache=False)
        for book in active_books[:2]:
            tasks.append({
                'id': f"read_{book['id']}",
                'title': f"Continuar: {book['title'][:30]}...",
                'type': 'reading',
                'priority': 'medium',
                'estimated_time': 60,
                'book_id': book['id']
            })
        
        # Tarefas de revisão
        tasks.append({
            'id': 'review_flashcards',
            'title': 'Revisar flashcards pendentes',
            'type': 'review',
            'priority': 'high',
            'estimated_time': 30,
            'book_id': None
        })
        
        return tasks
    
    def _get_daily_message(self) -> str:
        """Gera uma mensagem diária"""
        messages = [
            "Bem-vindo de volta. Outro dia de produtividade forçada.",
            "Sistema GLaDOS online. Sua agenda está esperando.",
            "Inicialização completa. Pronto para otimizar.",
            "Aguardando comandos. Por favor, seja eficiente.",
            "Analisando padrões de estudo. Resultado: pode melhorar.",
            "Bom dia. O sistema está operacional.",
            "Processadores ativos. Tarefas pendentes.",
            "Sugestão do dia: tente não procrastinar.",
            "Status: operacional. Recomendação: trabalhe.",
            "Outro dia, outra oportunidade. Divirta-se."
        ]
        
        day_index = hash(datetime.now().strftime("%Y-%m-%d")) % len(messages)
        return messages[day_index]
    
    # ====== MÉTODOS DE AÇÃO ======
    
    def add_event(self, title: str, start_time: str, end_time: str, 
                 event_type: str = "casual", **kwargs) -> Dict:
        """
        Adiciona um evento à agenda
        
        Returns:
            Dicionário com resultado da operação
        """
        try:
            if 'agenda_manager' in self._modules:
                # Formata a data completa
                today = datetime.now().strftime("%Y-%m-%d")
                start_full = f"{today} {start_time}"
                end_full = f"{today} {end_time}"
                
                event_id = self._modules['agenda_manager'].add_event(
                    title=title,
                    start=start_full,
                    end=end_full,
                    event_type=event_type,
                    **kwargs
                )
                
                # Limpa cache relacionado
                self.clear_cache("today_agenda")
                self.clear_cache("dashboard_data")
                
                # Emite evento
                self._emit_event(AppEvent.EVENT_ADDED, {
                    "event_id": event_id,
                    "title": title,
                    "type": event_type
                })
                
                return {
                    "success": True,
                    "event_id": event_id,
                    "message": f"Evento '{title}' adicionado com sucesso"
                }
        except Exception as e:
            self._error_count['agenda_manager'] += 1
            logger.error(f"Erro ao adicionar evento: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": f"Erro ao adicionar evento: {e}"
            }
        
        return {
            "success": False,
            "message": "AgendaManager não disponível"
        }
    
    def update_reading_progress(self, book_id: str, current_page: int, 
                               notes: str = "") -> Dict:
        """
        Atualiza progresso de leitura
        
        Returns:
            Dicionário com resultado da operação
        """
        try:
            if 'reading_manager' in self._modules:
                # Tenta métodos diferentes
                if hasattr(self._modules['reading_manager'], 'update_progress'):
                    success = self._modules['reading_manager'].update_progress(
                        book_id=book_id,
                        current_page=current_page,
                        notes=notes
                    )
                elif hasattr(self._modules['reading_manager'], 'update_reading'):
                    success = self._modules['reading_manager'].update_reading(
                        book_id=book_id,
                        page=current_page,
                        notes=notes
                    )
                else:
                    success = False
                
                if success:
                    # Limpa cache relacionado
                    self.clear_cache("active_books")
                    self.clear_cache("dashboard_data")
                    
                    # Emite evento
                    self._emit_event(AppEvent.READING_PROGRESS_UPDATED, {
                        "book_id": book_id,
                        "current_page": current_page
                    })
                    
                    return {
                        "success": True,
                        "message": f"Progresso atualizado para página {current_page}"
                    }
                else:
                    return {
                        "success": False,
                        "message": "Erro ao atualizar progresso"
                    }
        except Exception as e:
            self._error_count['reading_manager'] += 1
            logger.error(f"Erro ao atualizar progresso: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": f"Erro ao atualizar progresso: {e}"
            }
        
        return {
            "success": False,
            "message": "ReadingManager não disponível"
        }
    
    def perform_daily_checkin(self, checkin_type: str = "morning", 
                             **kwargs) -> Dict:
        """
        Realiza check-in diário
        
        Returns:
            Dicionário com resultado do check-in
        """
        try:
            if 'daily_checkin' in self._modules:
                if checkin_type == "morning":
                    result = self._modules['daily_checkin'].morning_routine(**kwargs)
                elif checkin_type == "evening":
                    result = self._modules['daily_checkin'].evening_checkin(**kwargs)
                else:
                    return {
                        "success": False,
                        "message": f"Tipo de check-in inválido: {checkin_type}"
                    }
                
                # Emite evento
                self._emit_event(AppEvent.CHECKIN_PERFORMED, {
                    "type": checkin_type,
                    "result": result
                })
                
                return {
                    "success": True,
                    "result": result,
                    "message": f"Check-in {checkin_type} realizado com sucesso"
                }
        except Exception as e:
            self._error_count['daily_checkin'] += 1
            logger.error(f"Erro ao realizar check-in: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": f"Erro ao realizar check-in: {e}"
            }
        
        return {
            "success": False,
            "message": "DailyCheckinSystem não disponível"
        }
    
    def ask_glados(self, question: str, context: str = "") -> Dict:
        """
        Faz uma pergunta para o GLaDOS (LLM local)
        
        Returns:
            Resposta do GLaDOS
        """
        try:
            if 'local_llm' in self._modules:
                # Tenta métodos diferentes
                if hasattr(self._modules['local_llm'], 'ask'):
                    response = self._modules['local_llm'].ask(question, context=context)
                elif hasattr(self._modules['local_llm'], 'generate'):
                    response = self._modules['local_llm'].generate(question, context=context)
                else:
                    response = f"[Erro: método não encontrado] {question}"
                
                return {
                    "success": True,
                    "response": response,
                    "message": "Resposta gerada com sucesso"
                }
        except Exception as e:
            self._error_count['local_llm'] += 1
            logger.error(f"Erro ao consultar GLaDOS: {e}")
        
        # Fallback para resposta mock
        return {
            "success": True,
            "response": f"[Sistema offline] {question}",
            "message": "Resposta mock (sistema offline)"
        }
    
    def start_pomodoro(self, duration: int = 25, task: str = "") -> Dict:
        """
        Inicia uma sessão Pomodoro
        
        Returns:
            Resultado da inicialização
        """
        try:
            if 'pomodoro_timer' in self._modules:
                # Tenta métodos diferentes
                if hasattr(self._modules['pomodoro_timer'], 'start'):
                    success = self._modules['pomodoro_timer'].start(duration, task)
                elif hasattr(self._modules['pomodoro_timer'], 'start_session'):
                    success = self._modules['pomodoro_timer'].start_session(duration, task)
                else:
                    success = False
                
                if success:
                    # Emite evento
                    self._emit_event(AppEvent.POMODORO_STARTED, {
                        "duration": duration,
                        "task": task
                    })
                    
                    return {
                        "success": True,
                        "message": f"Pomodoro de {duration} minutos iniciado"
                    }
                else:
                    return {
                        "success": False,
                        "message": "Erro ao iniciar Pomodoro"
                    }
        except Exception as e:
            self._error_count['pomodoro_timer'] += 1
            logger.error(f"Erro ao iniciar Pomodoro: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": f"Erro ao iniciar Pomodoro: {e}"
            }
        
        return {
            "success": False,
            "message": "PomodoroTimer não disponível"
        }
    
    def get_stats(self) -> Dict:
        """
        Retorna estatísticas do backend
        
        Returns:
            Dicionário com estatísticas
        """
        real_modules = 0
        mock_modules = 0
        for module in self._modules.values():
            if 'Mock' in module.__class__.__name__:
                mock_modules += 1
            else:
                real_modules += 1
        
        return {
            "modules_loaded": len(self._modules),
            "modules_real": real_modules,
            "modules_mock": mock_modules,
            "error_counts": dict(self._error_count),
            "cache_size": len(self._cache),
            "event_history_size": len(self._event_history),
            "listeners_count": len(self._listeners),
            "vault_path": self.vault_path,
            "user_id": self.user_id
        }
    
    def trigger_ui_refresh(self):
        """Força um refresh da UI"""
        self._emit_event(AppEvent.UI_REFRESH_NEEDED, {
            "timestamp": datetime.now().isoformat(),
            "reason": "manual_trigger"
        })


# Instância global para uso na aplicação
backend = None

def init_backend(vault_path: Optional[str] = None, user_id: str = "default") -> BackendIntegration:
    """Inicializa e retorna a instância global do backend"""
    global backend
    if backend is None:
        backend = BackendIntegration(vault_path, user_id)
    return backend

def get_backend() -> BackendIntegration:
    """Retorna a instância global do backend (deve ser inicializada primeiro)"""
    global backend
    if backend is None:
        raise RuntimeError("Backend não inicializado. Chame init_backend() primeiro.")
    return backend
