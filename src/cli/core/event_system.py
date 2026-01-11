"""
event_system.py - Sistema de eventos pub/sub para atualização dinâmica.
"""
import threading
import time
from typing import Dict, List, Callable, Any
from enum import Enum
from datetime import datetime
from dataclasses import dataclass


class EventType(Enum):
    """Tipos de eventos suportados pelo sistema."""
    AGENDA_UPDATED = "agenda_updated"
    READING_PROGRESS = "reading_progress"
    TASK_COMPLETED = "task_completed"
    TASK_ADDED = "task_added"
    TASK_UPDATED = "task_updated"
    BOOK_ADDED = "book_added"
    BOOK_PROGRESS = "book_progress"
    NOTE_CREATED = "note_created"
    NOTE_UPDATED = "note_updated"
    SESSION_STARTED = "session_started"
    SESSION_ENDED = "session_ended"
    CHECKIN_COMPLETED = "checkin_completed"
    SETTINGS_CHANGED = "settings_changed"
    USER_LOGIN = "user_login"
    USER_LOGOUT = "user_logout"
    SYSTEM_ALERT = "system_alert"
    DATA_CHANGED = "data_changed"
    CACHE_INVALIDATED = "cache_invalidated"
    UI_REFRESH = "ui_refresh"


@dataclass
class Event:
    """Representação de um evento."""
    type: EventType
    data: Dict[str, Any]
    timestamp: datetime = None
    source: str = "system"
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()
    
    def __str__(self) -> str:
        return f"Event({self.type.value}, source={self.source}, data={self.data})"


class EventSystem:
    """Sistema de eventos publish-subscribe."""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialize()
            return cls._instance
    
    def _initialize(self):
        self._subscribers: Dict[EventType, List[Callable[[Event], None]]] = {}
        self._event_history: List[Event] = []
        self._max_history = 1000
        self._is_running = False
        self._event_queue = []
        self._queue_lock = threading.Lock()
        self._worker_thread = None
    
    def subscribe(self, event_type: EventType, callback: Callable[[Event], None]) -> None:
        """Inscreve um callback para um tipo de evento."""
        with self._lock:
            if event_type not in self._subscribers:
                self._subscribers[event_type] = []
            self._subscribers[event_type].append(callback)
    
    def unsubscribe(self, event_type: EventType, callback: Callable[[Event], None]) -> None:
        """Remove a inscrição de um callback."""
        with self._lock:
            if event_type in self._subscribers:
                if callback in self._subscribers[event_type]:
                    self._subscribers[event_type].remove(callback)
    
    def publish(self, event: Event) -> None:
        """Publica um evento de forma síncrona."""
        self._add_to_history(event)
        
        # Notificar subscribers síncronos
        if event.type in self._subscribers:
            for callback in self._subscribers[event.type]:
                try:
                    callback(event)
                except Exception as e:
                    print(f"Erro no callback do evento {event.type}: {e}")
    
    def publish_async(self, event: Event) -> None:
        """Publica um evento de forma assíncrona."""
        with self._queue_lock:
            self._event_queue.append(event)
    
    def start(self) -> None:
        """Inicia o processamento assíncrono de eventos."""
        if self._is_running:
            return
        
        self._is_running = True
        self._worker_thread = threading.Thread(target=self._process_queue, daemon=True)
        self._worker_thread.start()
    
    def stop(self) -> None:
        """Para o processamento assíncrono de eventos."""
        self._is_running = False
        if self._worker_thread:
            self._worker_thread.join(timeout=1.0)
    
    def _process_queue(self) -> None:
        """Processa a fila de eventos assíncronos."""
        while self._is_running:
            events_to_process = []
            
            with self._queue_lock:
                if self._event_queue:
                    events_to_process = self._event_queue.copy()
                    self._event_queue.clear()
            
            for event in events_to_process:
                self.publish(event)
            
            time.sleep(0.1)  # Evitar uso excessivo de CPU
    
    def _add_to_history(self, event: Event) -> None:
        """Adiciona evento ao histórico."""
        self._event_history.append(event)
        
        # Manter histórico limitado
        if len(self._event_history) > self._max_history:
            self._event_history.pop(0)
    
    def get_history(self, limit: int = 50, event_type: EventType = None) -> List[Event]:
        """Obtém histórico de eventos."""
        history = self._event_history.copy()
        
        if event_type:
            history = [e for e in history if e.type == event_type]
        
        return history[-limit:] if limit > 0 else history
    
    def clear_history(self) -> None:
        """Limpa o histórico de eventos."""
        self._event_history.clear()
    
    def get_subscriber_count(self, event_type: EventType = None) -> int:
        """Conta o número de subscribers."""
        if event_type:
            return len(self._subscribers.get(event_type, []))
        return sum(len(subs) for subs in self._subscribers.values())
    
    def trigger_data_changed(self, data_type: str, data_id: Any = None) -> None:
        """Dispara evento de dados alterados."""
        event = Event(
            type=EventType.DATA_CHANGED,
            data={"type": data_type, "id": data_id},
            source="EventSystem"
        )
        self.publish(event)
    
    def trigger_ui_refresh(self, component: str = None) -> None:
        """Dispara evento de atualização de UI."""
        event = Event(
            type=EventType.UI_REFRESH,
            data={"component": component},
            source="EventSystem"
        )
        self.publish_async(event)


# Instância global do sistema de eventos
event_system = EventSystem()
