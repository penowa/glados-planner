"""
EventBus global para comunicação cross-module - Versão Simplificada
"""
from datetime import datetime

from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot
from typing import Any, Dict, Callable
import time

class GlobalEventBus(QObject):
    """Singleton simplificado para comunicação global"""
    
    # ============ SISTEMA ============
    app_initialized = pyqtSignal()
    app_shutdown = pyqtSignal()
    module_loaded = pyqtSignal(str, bool)
    
    # ============ DADOS ============
    data_created = pyqtSignal(str, dict)
    data_updated = pyqtSignal(str, dict)
    data_deleted = pyqtSignal(str, str)
    sync_needed = pyqtSignal(str)
    
    # ============ USUÁRIO ============
    user_action = pyqtSignal(str, dict)
    notification = pyqtSignal(str, str, str)
    focus_changed = pyqtSignal(str)
    
    # ============ ESTADO ============
    state_changed = pyqtSignal(str, dict)
    progress_updated = pyqtSignal(str, int, str)
    
    # ============ SAÚDE ============
    module_ready = pyqtSignal(str, dict)
    module_error = pyqtSignal(str, str)
    connection_lost = pyqtSignal(str)
    connection_restored = pyqtSignal(str)
    
    # Instância singleton
    _instance = None
    
    def __init__(self):
        """Construtor - deve ser chamado apenas uma vez"""
        super().__init__()
        self._connections = {}
        self._event_history = []
        self._max_history = 1000
        self._notification_history = []
        self._max_notification_history = 200
        self._subscribers = {}
        self.notification.connect(self._record_notification)
        print("✅ GlobalEventBus.__init__() chamado")
    
    @classmethod
    def instance(cls):
        """Retorna a instância singleton"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def emit_safe(self, signal: pyqtSignal, *args):
        """Emite sinal com tratamento de erro seguro"""
        try:
            signal.emit(*args)
            self._log_event(signal, args)
        except Exception as e:
            print(f"EventBus emit error: {e}")
    
    def connect_safe(self, signal: pyqtSignal, slot: Callable):
        """Conexão segura"""
        connection = signal.connect(slot)
        
        signal_name = signal.__name__ if hasattr(signal, '__name__') else str(signal)
        if signal_name not in self._connections:
            self._connections[signal_name] = []
        self._connections[signal_name].append((slot, connection))
        
        return connection
    
    def subscribe(self, event_type: str, callback: Callable):
        """Inscreve callback para um tipo de evento específico"""
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        
        if callback not in self._subscribers[event_type]:
            self._subscribers[event_type].append(callback)
    
    def publish(self, event_type: str, data: Dict[str, Any] = None):
        """Publica evento para todos os subscribers"""
        if event_type in self._subscribers:
            for callback in self._subscribers[event_type][:]:
                try:
                    callback(event_type, data or {})
                except Exception as e:
                    print(f"Error in event subscriber: {e}")
    
    def _log_event(self, signal: pyqtSignal, args: tuple):
        """Registra evento no histórico"""
        event = {
            'timestamp': time.time(),
            'signal': signal.__name__ if hasattr(signal, '__name__') else str(signal),
            'args': args
        }
        
        self._event_history.append(event)
        
        if len(self._event_history) > self._max_history:
            self._event_history = self._event_history[-self._max_history:]
    
    def get_event_history(self, limit: int = 100) -> list:
        """Retorna histórico recente de eventos"""
        return self._event_history[-limit:] if self._event_history else []

    @pyqtSlot(str, str, str)
    def _record_notification(self, notif_type: str, title: str, message: str):
        """Mantém um histórico normalizado das notificações emitidas."""
        timestamp = datetime.now()
        entry = {
            'type': str(notif_type or 'info').strip().lower() or 'info',
            'title': str(title or 'Notificação').strip() or 'Notificação',
            'message': str(message or '').strip(),
            'timestamp': timestamp.strftime('%d/%m %H:%M'),
            'epoch': timestamp.timestamp(),
        }

        self._notification_history.append(entry)
        if len(self._notification_history) > self._max_notification_history:
            self._notification_history = self._notification_history[-self._max_notification_history:]

    def get_recent_notifications(self, limit: int = 20) -> list:
        """Retorna notificações recentes em formato pronto para UI."""
        if not self._notification_history:
            return []
        recent = self._notification_history[-limit:]
        return list(reversed(recent))

    def clear_notifications(self) -> None:
        """Limpa apenas o histórico normalizado de notificações."""
        self._notification_history.clear()

    def clear_history(self):
        """Limpa histórico de eventos e notificações."""
        self._event_history.clear()
        self.clear_notifications()
