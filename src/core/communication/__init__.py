"""
Módulo de comunicação assíncrona para GLaDOS Philosophy Planner
Sistema de eventos, workers e controllers para integração backend-frontend
"""

from .event_bus import GlobalEventBus
from .base_controller import BackendController
from .worker import BackendWorker
from .debouncer import Debouncer, Throttler, AdaptiveThrottler
from .message_queue import MessageQueue, Message

__all__ = [
    'GlobalEventBus',
    'BackendController',
    'BackendWorker',
    'Debouncer',
    'Throttler',
    'AdaptiveThrottler',
    'MessageQueue',
    'Message'
]