"""
Cards para interface do GLaDOS Philosophy Planner
"""

from .agenda_card import AgendaCard, CompactEventWidget
from .add_book_card import AddBookCard
from .glados_card import GladosCard
from .stats_card import VaultStatsCard
from .event_creation_card import EventCreationCard

# Alias para compatibilidade
AgendaEventWidget = CompactEventWidget

__all__ = [
    'AgendaCard',
    'CompactEventWidget',
    'AgendaEventWidget',  # Alias
    'AddBookCard',
    'GladosCard',
    'VaultStatsCard'
    'EventCreationCard'
]