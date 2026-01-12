"""
Dashboard mínimo e funcional - versão 3.0
"""
import datetime
import time
from typing import Optional
from .base_screen import BaseScreen
from src.cli.interactive.terminal import Key


class DashboardScreen(BaseScreen):
    """Dashboard com navegação por setas e atualização de relógio."""
    
    def __init__(self, terminal):
        super().__init__(terminal)
        self.title = "Dashboard"
        
        # Menu simples
        self.menu_items = [
            ("📚 Adicionar Livro", "new_book"),
            ("📖 Sessão de Leitura", "reading_session"),
            ("🍅 Pomodoro", "pomodoro_session"),
            ("✅ Check-in Diário", "daily_checkin"),
            ("📅 Configurar Agenda", "agenda_config"),
            ("⚠️ Modo Emergência", "emergency_mode"),
            ("🤖 Consultar GLaDOS", "glados_query"),
            ("❓ Ajuda", "help"),
            ("⚙️ Configurações", "settings"),
            ("🚪 Sair", "exit")
        ]
        self.selected = 0
        self.menu_visible = True
        self.last_clock_update = 0
        self.clock_interval = 1.0  # Atualizar relógio a cada segundo
        self.input_timeout = 0.1   # Timeout curto para verificar input
    
    def show(self) -> Optional[str]:
        """Loop principal com timeout para atualizar relógio."""
        self.initialize()
        
        while True:
            # Atualiza tela
            self._draw()
            
            # Obtém input com timeout curto
            key = self.terminal.get_key(self.input_timeout)
            
            # Processa input se houver
            if key:
                return self._handle_input(key)
            
            # Atualiza relógio se necessário
            self._update_clock_if_needed()
    
    def initialize(self):
        """Inicialização básica."""
        if not self.is_initialized:
            # Verifica backend uma vez
            self.backend_status = self._check_backend()
            self.last_clock_update = time.time()
            self.is_initialized = True
    
    def _check_backend(self):
        """Verifica backend de forma simples."""
        try:
            from src.cli.integration.backend_integration import backend
            if backend and hasattr(backend, 'is_ready'):
                return backend.is_ready()
        except:
            pass
        return False
    
    def _update_clock_if_needed(self):
        """Verifica se precisa atualizar o relógio."""
        current_time = time.time()
        if current_time - self.last_clock_update >= self.clock_interval:
            self.last_clock_update = current_time
            # Redesenha apenas a linha do relógio
            self._draw_clock_line()
            self.terminal.flush()
    
    def _draw_clock_line(self):
        """Desenha apenas a linha do relógio (otimizado)."""
        width, _ = self.terminal.get_size()
        
        # Linha 1: Data/hora
        now = datetime.datetime.now()
        time_str = now.strftime("%H:%M:%S")
        date_str = now.strftime("%d/%m/%Y")
        clock_text = f"🕐 {time_str} | 📅 {date_str}"
        
        self.terminal.print_at(0, 0, clock_text, {"color": "primary"})
    
    def _draw(self):
        """Desenha a tela inteira de uma vez."""
        self.terminal.clear()
        
        width, height = self.terminal.get_size()
        
        # Linha 1: Data/hora (será atualizada separadamente)
        self._draw_clock_line()
        
        # Linha 2: Título
        title = "GLaDOS Planner"
        x = max(0, (width - len(title)) // 2)
        self.terminal.print_at(x, 1, title, {"color": "accent", "bold": True})
        
        # Linha 3: Status do backend
        status = "✅ Conectado" if self.backend_status else "⚠️ Modo offline"
        color = "success" if self.backend_status else "warning"
        self.terminal.print_at(0, 2, status, {"color": color})
        
        # Separador
        separator = "─" * width
        self.terminal.print_at(0, 3, separator, {"color": "dim"})
        
        # Menu (começa na linha 5)
        start_y = 5
        self.terminal.print_at(0, 4, "📋 Menu Principal:", {"color": "primary", "bold": True})
        
        # Itens do menu
        max_items = min(len(self.menu_items), height - start_y - 3)
        for i in range(max_items):
            y = start_y + i
            name, _ = self.menu_items[i]
            
            if i == self.selected:
                prefix = "▶ "
                style = {"color": "accent", "bold": True, "reverse": True}
            else:
                prefix = "  "
                style = {"color": "info"}
            
            text = f"{prefix}{name}"
            if len(text) > width:
                text = text[:width-3] + "..."
            
            self.terminal.print_at(0, y, text, style)
        
        # Rodapé (2 linhas do final)
        footer_y = height - 2
        shortcuts = "↑↓: Navegar | Enter: Selecionar | S: Sair | ESC: Voltar"
        if len(shortcuts) > width:
            shortcuts = shortcuts[:width-3] + "..."
        self.terminal.print_at(0, footer_y, shortcuts, {"color": "dim"})
        
        footer_y2 = height - 1
        shortcuts2 = "C: Check-in | E: Emergência | P: Pomodoro | H: Ajuda"
        if len(shortcuts2) > width:
            shortcuts2 = shortcuts2[:width-3] + "..."
        self.terminal.print_at(0, footer_y2, shortcuts2, {"color": "dim"})
        
        self.terminal.flush()
    
    def _handle_input(self, key: Key) -> Optional[str]:
        """Processa input do usuário."""
        # Debug: mostrar tecla pressionada
        # print(f"\rDEBUG: Key pressed: {key}", end="", flush=True)
        
        # Navegação do menu
        if key == Key.UP:
            self.selected = (self.selected - 1) % len(self.menu_items)
            return None  # Não sair, apenas atualizar
        elif key == Key.DOWN:
            self.selected = (self.selected + 1) % len(self.menu_items)
            return None  # Não sair, apenas atualizar
        elif key == Key.ENTER:
            action = self.menu_items[self.selected][1]
            # print(f"\rDEBUG: Executing: {action}", end="", flush=True)
            return action
        elif key == Key.ESC:
            return 'back'
        elif key == Key.SPACE:
            return 'exit'
        
        # Atalhos de teclado
        elif key == Key.S:
            return 'exit'
        elif key == Key.C:
            return 'goto:daily_checkin'
        elif key == Key.E:
            return 'goto:emergency_mode'
        elif key == Key.P:
            return 'goto:pomodoro_session'
        elif key == Key.H:
            return 'goto:help'
        elif key == Key.D:
            return 'goto:dashboard'  # Recarregar
        
        return None  # Nenhuma ação
