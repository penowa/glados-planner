# src/cli/interactive/screens/base_screen.py
"""
Classe base para todas as telas interativas com renderização otimizada.
"""
import time
from typing import Optional, Dict, Any, List
from abc import ABC, abstractmethod

from src.cli.interactive.terminal import GLTerminal, Key
from src.cli.theme import theme
from src.cli.icons import Icon, icon_text


class BaseScreen(ABC):
    """Classe base abstrata para todas as telas com renderização otimizada."""
    
    def __init__(self, terminal: GLTerminal):
        self.terminal = terminal
        self.title = "Tela Sem Título"
        self.should_exit = False
        self.needs_redraw = True
        self.last_render_time = 0
        self.min_render_interval = 0.016  # ~60 FPS
        
        # Estado da tela
        self.data = {}
        self.is_initialized = False
        
    @abstractmethod
    def show(self) -> Optional[str]:
        """Exibe a tela e gerencia a interação. Deve retornar um comando de navegação ou None."""
        pass
    
    def initialize(self):
        """Inicializa dados da tela. Chamado uma vez antes do primeiro show."""
        if not self.is_initialized:
            self._load_data()
            self.is_initialized = True
    
    def _load_data(self):
        """Carrega dados específicos da tela. Pode ser sobrescrito por subclasses."""
        pass
    
    def _render(self):
        """Renderiza a tela. Deve ser implementado por subclasses."""
        self.terminal.clear()
        
        # Cabeçalho padrão
        self._render_header()
        
        # Renderiza conteúdo
        self._render_content()
        
        # Rodapé padrão
        self._render_footer()
        
        # Flush das alterações
        self.terminal.flush()
    
    def _render_header(self):
        """Renderiza cabeçalho padrão."""
        # Data e hora
        import datetime
        now = datetime.datetime.now()
        date_str = now.strftime("%d/%m/%Y")
        time_str = now.strftime("%H:%M:%S")
        
        self.terminal.print_at(0, 0, f"📅 {date_str} | 🕐 {time_str} | GLaDOS Planner", 
                              {"color": "dim"})
        
        # Título da tela
        title_width = len(self.title) + 4
        terminal_width, _ = self.terminal.get_size()
        title_x = max(0, (terminal_width - title_width) // 2)
        
        self.terminal.print_at(title_x, 1, f"[ {self.title} ]", {"color": "accent", "bold": True})
    
    def _render_content(self):
        """Renderiza conteúdo específico da tela. Deve ser sobrescrito por subclasses."""
        terminal_width, terminal_height = self.terminal.get_size()
        
        # Mensagem padrão
        message = f"Tela '{self.title}' em desenvolvimento"
        message_x = max(0, (terminal_width - len(message)) // 2)
        message_y = terminal_height // 2
        
        self.terminal.print_at(message_x, message_y, message, {"color": "info"})
    
    def _render_footer(self):
        """Renderiza rodapé padrão."""
        _, terminal_height = self.terminal.get_size()
        
        # Linha de ajuda
        help_text = "ESC: Voltar | Q: Sair | R: Recarregar | H: Ajuda"
        self.terminal.print_at(0, terminal_height - 1, help_text, {"color": "dim"})
    
    def _handle_input(self) -> Optional[str]:
        """Processa input do usuário. Retorna um comando de navegação ou None."""
        key = self.terminal.get_key(timeout=0.1)  # Timeout para não bloquear
        
        if key:
            # Teclas globais
            if key == Key.ESC:
                return 'back'
            elif key == Key.Q:
                return 'exit'
            elif key == Key.R:
                self.needs_redraw = True
                self._load_data()
            elif key == Key.H:
                return 'goto:help'
            
            # Processa teclas específicas da tela
            return self._process_key(key)
        
        return None
    
    def _process_key(self, key: Key) -> Optional[str]:
        """Processa teclas específicas. Deve ser sobrescrito por subclasses."""
        return None
    
    def mark_dirty(self):
        """Marca a tela para redesenho."""
        self.needs_redraw = True
    
    def get_terminal_size(self) -> tuple:
        """Retorna tamanho atual do terminal."""
        return self.terminal.get_size()
    
    def wait_for_exit(self, message="Pressione qualquer tecla para continuar..."):
        """Aguarda confirmação do usuário para sair."""
        self.terminal.print_at(0, self.terminal.height - 2, message, {"color": "dim"})
        self.terminal.flush()
        self.terminal.get_key()
    
    def render_menu(self, items: List[tuple], selected_index: int = 0):
        """Renderiza um menu vertical com seleção."""
        self.terminal.clear()
        
        # Cabeçalho
        self._render_header()
        
        # Itens do menu
        start_y = 3
        for i, (label, _) in enumerate(items):
            prefix = "> " if i == selected_index else "  "
            icon = self._determine_icon(label)
            style = {"color": "primary", "bold": True} if i == selected_index else {"color": "info"}
            self.terminal.print_at(2, start_y + i, f"{prefix}{icon_text(icon, label)}", style)
        
        # Rodapé
        self._render_footer()
        self.terminal.flush()
    
    def _determine_icon(self, label: str) -> Icon:
        """Determina ícone apropriado baseado no texto do label."""
        label_lower = label.lower()
        
        if any(word in label_lower for word in ['livro', 'leitura', 'ler']):
            return Icon.BOOK
        elif any(word in label_lower for word in ['sessão', 'timer', 'pomodoro']):
            return Icon.TIMER
        elif any(word in label_lower for word in ['check-in', 'diário', 'humor']):
            return Icon.CALENDAR
        elif any(word in label_lower for word in ['agenda', 'compromisso', 'evento']):
            return Icon.CALENDAR
        elif any(word in label_lower for word in ['emergência', 'urgente']):
            return Icon.ALERT
        elif any(word in label_lower for word in ['glados', 'consulta', 'pergunta']):
            return Icon.GLADOS
        elif any(word in label_lower for word in ['ajuda', 'sobre']):
            return Icon.INFO
        elif any(word in label_lower for word in ['sair', 'encerrar']):
            return Icon.EXIT
        elif any(word in label_lower for word in ['config', 'configuração', 'definições']):
            return Icon.INFO
        elif any(word in label_lower for word in ['tarefa', 'task']):
            return Icon.TASK
        elif any(word in label_lower for word in ['estatística', 'relatório']):
            return Icon.INFO
        else:
            return Icon.INFO
