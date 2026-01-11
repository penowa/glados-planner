from enum import Enum
from typing import Optional

class Icon(Enum):
    """Ícones temáticos GLaDOS/Portal"""
    # Ações
    ADD = "➕"
    EDIT = "✏️"
    DELETE = "🗑️"
    COMPLETE = "✅"
    INCOMPLETE = "⬜"
    
    # Categorias
    BOOK = "📚"
    CALENDAR = "📅"
    TASK = "📝"
    NOTE = "📓"
    FLASHCARD = "🔄"
    TIMER = "⏱️"
    ALERT = "⚠️"
    HELP = "❓"
    SETTINGS = "⚙️"
    
    # Navegação
    ARROW_UP = "↑"
    ARROW_DOWN = "↓"
    BACK = "↩️"
    EXIT = "🚪"
    HOME = "🏠"
    
    # Estados
    SUCCESS = "✓"
    ERROR = "✗"
    WARNING = "!"
    INFO = "i"
    LOADING = "⟳"
    
    # GLaDOS específico
    GLADOS = "🤖"
    PORTAL = "🌀"
    CAKE = "🎂"  # The cake is a lie
    COMPANION_CUBE = "❤️"
    
    @classmethod
    def get(cls, name: str, default: Optional['Icon'] = None) -> 'Icon':
        """Obtém ícone por nome com fallback"""
        try:
            return cls[name.upper()]
        except KeyError:
            return default or cls.INFO

def icon_text(icon: Icon, text: str) -> str:
    """Combina ícone com texto formatado"""
    return f"{icon.value} {text}"
