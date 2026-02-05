# ui/widgets/cards/__init__.py
"""
Sistema de cards reutilizáveis para o GLaDOS Philosophy Planner
"""

from .base_card import PhilosophyCard
from .book_card import BookCard, BookCoverWidget
from .stats_card import StatsCard, BarChartWidget, PieChartWidget, ProgressChartWidget
from .agenda_card import AgendaCard, AgendaEventWidget  # Adicionado aqui
from .action_card import ActionCard, QuickActionGrid
from .time_card import TimeCard
from .concept_card import ConceptCard
from .goal_card import GoalCard, GoalProgressBar
from .glados_card import GladosCard
from .add_book_card import AddBookCard, AddBookIconWidget
from .next_reading_session_card import NextReadingSessionCard

__all__ = [
    # Classes base
    'PhilosophyCard',
    
    # Cards específicos
    'BookCard',
    'BookCoverWidget',
    'StatsCard',
    'BarChartWidget',
    'PieChartWidget',
    'ProgressChartWidget',
    'AgendaCard',
    'AgendaItemWidget',
    'ActionCard',
    'QuickActionGrid',
    'TimeCard',
    'ConceptCard',
    'GoalCard',
    'GoalProgressBar',
    'GladosCard',
]

# Versão do sistema de cards
__version__ = '1.0.1'  # Atualizado versão