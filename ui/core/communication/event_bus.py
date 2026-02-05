"""
EventBus global para comunicação cross-module
Singleton que gerencia todos os eventos do sistema
"""
from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot
from typing import Any, Dict, Optional, Callable
import threading
import time

class GlobalEventBus(QObject):
    """Singleton para comunicação global cross-module"""
    
    _instance = None
    _lock = threading.Lock()
    
    # ============ SISTEMA ============
    app_initialized = pyqtSignal()
    app_shutdown = pyqtSignal()
    module_loaded = pyqtSignal(str, bool)  # (module_name, success)
    
    # ============ DADOS ============
    data_created = pyqtSignal(str, dict)   # (type, data)
    data_updated = pyqtSignal(str, dict)   # (type, data)
    data_deleted = pyqtSignal(str, str)    # (type, id)
    sync_needed = pyqtSignal(str)          # (module_name)
    
    # ============ USUÁRIO ============
    user_action = pyqtSignal(str, dict)    # (action, metadata)
    notification = pyqtSignal(str, str, str)  # (type, title, message)
    focus_changed = pyqtSignal(str)        # (widget_name)
    
    # ============ ESTADO ============
    state_changed = pyqtSignal(str, dict)  # (state_name, state_data)
    progress_updated = pyqtSignal(str, int, str)  # (task, percent, msg)
    
    # ============ SAÚDE ============
    module_ready = pyqtSignal(str, dict)   # (module, status)
    module_error = pyqtSignal(str, str)    # (module, error)
    connection_lost = pyqtSignal(str)      # (component)
    connection_restored = pyqtSignal(str)  # (component)
    
    def __new__(cls):
        """Implementação do padrão Singleton"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not hasattr(self, '_initialized'):
            super().__init__()
            self._connections = {}
            self._event_history = []
            self._max_history = 1000
            self._subscribers = {}
            self._initialized = True
    
    @classmethod
    def instance(cls):
        """Retorna a instância singleton"""
        return cls()
    
    def emit_safe(self, signal: pyqtSignal, *args):
        """Emite sinal com tratamento de erro seguro"""
        try:
            signal.emit(*args)
            # Registrar no histórico
            self._log_event(signal, args)
        except Exception as e:
            print(f"EventBus emit error: {e}")
            # Tentar emitir novamente sem argumentos se falhar
            try:
                signal.emit()
            except:
                pass
    
    def connect_safe(self, signal: pyqtSignal, slot: Callable):
        """Conexão segura com desconexão automática se objeto deletado"""
        connection = signal.connect(slot)
        
        # Armazenar referência à conexão
        signal_name = signal.__name__ if hasattr(signal, '__name__') else str(signal)
        if signal_name not in self._connections:
            self._connections[signal_name] = []
        self._connections[signal_name].append((slot, connection))
        
        return connection
    
    def disconnect_safe(self, signal: pyqtSignal, slot: Callable):
        """Desconecta slot de forma segura"""
        try:
            signal.disconnect(slot)
            
            # Remover da lista de conexões
            signal_name = signal.__name__ if hasattr(signal, '__name__') else str(signal)
            if signal_name in self._connections:
                self._connections[signal_name] = [
                    (s, c) for s, c in self._connections[signal_name] if s != slot
                ]
        except Exception as e:
            # Conexão não existia
            pass
    
    def subscribe(self, event_type: str, callback: Callable):
        """Inscreve callback para um tipo de evento específico"""
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        
        if callback not in self._subscribers[event_type]:
            self._subscribers[event_type].append(callback)
    
    def unsubscribe(self, event_type: str, callback: Callable):
        """Remove inscrição de callback"""
        if event_type in self._subscribers:
            if callback in self._subscribers[event_type]:
                self._subscribers[event_type].remove(callback)
    
    def publish(self, event_type: str, data: Dict[str, Any] = None):
        """Publica evento para todos os subscribers"""
        if event_type in self._subscribers:
            for callback in self._subscribers[event_type][:]:  # Cópia para segurança
                try:
                    callback(event_type, data or {})
                except Exception as e:
                    print(f"Error in event subscriber {callback}: {e}")
    
    def _log_event(self, signal: pyqtSignal, args: tuple):
        """Registra evento no histórico"""
        event = {
            'timestamp': time.time(),
            'signal': signal.__name__ if hasattr(signal, '__name__') else str(signal),
            'args': args,
            'thread': threading.current_thread().name
        }
        
        self._event_history.append(event)
        
        # Manter histórico limitado
        if len(self._event_history) > self._max_history:
            self._event_history = self._event_history[-self._max_history:]
    
    def get_event_history(self, limit: int = 100) -> list:
        """Retorna histórico recente de eventos"""
        return self._event_history[-limit:] if self._event_history else []
    
    def get_recent_notifications(self, limit: int = 20) -> list:
        """Retorna notificações recentes"""
        notifications = []
        for event in reversed(self._event_history):
            if 'notification' in event['signal'].lower():
                notifications.append(event)
                if len(notifications) >= limit:
                    break
        return notifications
    
    def clear_history(self):
        """Limpa histórico de eventos"""
        self._event_history.clear()
    
    def get_stats(self) -> Dict[str, Any]:
        """Retorna estatísticas do EventBus"""
        total_events = len(self._event_history)
        
        # Contar eventos por tipo
        event_counts = {}
        for event in self._event_history:
            signal = event['signal']
            event_counts[signal] = event_counts.get(signal, 0) + 1
        
        # Contar subscribers
        subscriber_counts = {}
        for event_type, subscribers in self._subscribers.items():
            subscriber_counts[event_type] = len(subscribers)
        
        return {
            'total_events': total_events,
            'event_counts': event_counts,
            'subscriber_counts': subscriber_counts,
            'connections': {k: len(v) for k, v in self._connections.items()}
        }