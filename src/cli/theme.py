from enum import Enum
from rich.console import Console
from rich.theme import Theme as RichTheme
from rich.style import Style

class PortalColor(Enum):
    """Paleta de cores Portal (GLaDOS)"""
    PRIMARY = "#C0C0C0"   # Prata GLaDOS
    ACCENT = "#FF5500"    # Laranja Portal
    SECONDARY = "#00AAFF" # Azul Portal
    SUCCESS = "#00FFAA"   # Verde
    WARNING = "#FFFF00"   # Amarelo
    ERROR = "#FF00AA"     # Rosa
    INFO = "#AAAAAA"      # Cinza
    BACKGROUND = "#0A0A0A"# Preto

class GladosTheme:
    def __init__(self):
        self.colors = {c.name: c.value for c in PortalColor}
        
        # Tema Rich customizado
        custom_theme = RichTheme({
            "primary": Style(color=self.colors["PRIMARY"]),
            "accent": Style(color=self.colors["ACCENT"], bold=True),
            "secondary": Style(color=self.colors["SECONDARY"]),
            "success": Style(color=self.colors["SUCCESS"]),
            "warning": Style(color=self.colors["WARNING"]),
            "error": Style(color=self.colors["ERROR"], bold=True),
            "info": Style(color=self.colors["INFO"]),
            "title": Style(color=self.colors["ACCENT"], bold=True, underline=True),
            "subtitle": Style(color=self.colors["SECONDARY"], bold=True),
            "highlight": Style(bgcolor=self.colors["ACCENT"], color="black"),
            "panel": Style(bgcolor="#1E1E1E", color=self.colors["PRIMARY"]),
        })
        
        self.console = Console(theme=custom_theme)
        self.console.width = 80  # Largura padrão para CLI
    
    def print(self, *args, **kwargs):
        """Wrapper para print com tema"""
        style = kwargs.pop("style", "primary")
        self.console.print(*args, style=style, **kwargs)
    
    def rule(self, title="", style="accent"):
        """Linha horizontal com título"""
        self.console.rule(title, style=style)
    
    def clear(self):
        """Limpa o terminal"""
        self.console.clear()
    
    def gradient_text(self, text, start_color, end_color):
        """Texto com gradiente (simulado)"""
        # Implementação simplificada - pode ser expandida
        return f"[{start_color}]{text}[/{start_color}]"

# Instância global
theme = GladosTheme()
