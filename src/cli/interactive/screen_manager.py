# src/cli/interactive/screen_manager.py
"""
Gerenciador de telas para navegação entre as telas do sistema.
Implementa pilha de telas, histórico e transições.
"""
import sys
from typing import Optional, Any, Callable
from src.cli.theme import theme
from src.cli.icons import Icon, icon_text
from src.cli.interactive.input.keyboard_handler import KeyboardHandler, Key

class ScreenManager:
    """
    Gerencia a navegação entre telas com sistema de pilha.
    
    Padrões de uso:
        manager = ScreenManager()
        manager.push(DashboardScreen())
        manager.run()
    """
    
    def __init__(self):
        self.screen_stack = []  # Pilha de telas
        self.history = []       # Histórico de navegação (para possível "voltar" global)
        self.keyboard_handler = KeyboardHandler()
        self.running = False
        self.global_shortcuts = self._setup_global_shortcuts()
        
    def push(self, screen):
        """Empilha uma nova tela."""
        if self.screen_stack:
            current_screen = self.screen_stack[-1]
            self.history.append((current_screen.__class__.__name__, current_screen.title))
        
        self.screen_stack.append(screen)
        return screen
    
    def pop(self):
        """Remove a tela atual da pilha e retorna à anterior."""
        if len(self.screen_stack) > 1:
            removed = self.screen_stack.pop()
            return removed
        return None
    
    def replace(self, screen):
        """Substitui a tela atual por uma nova."""
        if self.screen_stack:
            self.screen_stack.pop()
        return self.push(screen)
    
    def clear_stack(self):
        """Limpa toda a pilha de telas."""
        self.screen_stack.clear()
    
    def get_current_screen(self):
        """Retorna a tela atual (topo da pilha)."""
        if self.screen_stack:
            return self.screen_stack[-1]
        return None
    
    def run(self):
        """Executa o loop principal do gerenciador de telas."""
        if not self.screen_stack:
            raise ValueError("Nenhuma tela na pilha. Use push() primeiro.")
        
        self.running = True
        
        while self.running and self.screen_stack:
            current_screen = self.screen_stack[-1]
            
            try:
                # Exibir a tela atual
                result = current_screen.show()
                
                # Processar resultado da tela
                if result == 'back':
                    self.pop()
                elif result == 'exit':
                    self.running = False
                elif result == 'shutdown':
                    self._handle_shutdown()
                    self.running = False
                elif isinstance(result, str) and result.startswith('goto:'):
                    screen_name = result[5:]
                    self._navigate_to_screen(screen_name)
                elif result is not None:
                    theme.print(f"Resultado não tratado: {result}", style="warning")
                    
            except KeyboardInterrupt:
                # Ctrl+C pressionado - voltar ou sair
                if len(self.screen_stack) > 1:
                    self.pop()
                else:
                    self.running = False
                    theme.print("\n\nInterrompido pelo usuário.", style="warning")
                    
            except Exception as e:
                theme.print(f"\n❌ Erro na tela {current_screen.__class__.__name__}: {e}", style="error")
                import traceback
                theme.print(traceback.format_exc(), style="error")
                
                # Tentar recuperar voltando uma tela
                if len(self.screen_stack) > 1:
                    theme.print("Voltando para tela anterior...", style="warning")
                    self.pop()
                else:
                    theme.print("Erro fatal. Encerrando...", style="error")
                    self.running = False
        
        # Mensagem de encerramento
        if not self.running:
            theme.print(f"\n{icon_text(Icon.EXIT, 'Sistema encerrado.')}", style="accent")
    
    def _navigate_to_screen(self, screen_name: str):
        """Navega para uma tela específica pelo nome."""
        # Mapeamento de nomes para classes de tela
        screen_map = {
            'dashboard': 'DashboardScreen',
            'new_book': 'NewBookScreen',
            'session': 'SessionScreen',
            'daily_checkin': 'DailyCheckinScreen',
            'weekly_planning': 'WeeklyPlanningScreen',
            'agenda_config': 'AgendaConfigScreen',
            'emergency_mode': 'EmergencyModeScreen',
            'glados_query': 'GladosQueryScreen',
            'help': 'HelpScreen',
            'shutdown': 'ShutdownScreen',
            'pomodoro': 'PomodoroSessionScreen',
            'reading': 'ReadingSessionScreen',
            'book_selection': 'BookSelectionScreen',
            'task_management': 'TaskManagementScreen',
            'statistics': 'StatisticsScreen',
            'settings': 'SettingsScreen'
        }
        
        if screen_name in screen_map:
            try:
                # Importar dinamicamente a classe da tela
                module_name = f"cli.interactive.screens.{screen_name}_screen"
                if screen_name == 'dashboard':
                    module_name = "cli.interactive.screens.dashboard_screen"
                
                module = __import__(module_name, fromlist=[screen_map[screen_name]])
                screen_class = getattr(module, screen_map[screen_name])
                
                # Criar e empilhar nova tela
                new_screen = screen_class()
                self.push(new_screen)
                
            except ImportError as e:
                theme.print(f"❌ Não foi possível carregar a tela {screen_name}: {e}", style="error")
        else:
            theme.print(f"❌ Tela desconhecida: {screen_name}", style="error")
    
    def _handle_shutdown(self):
        """Processa o encerramento do sistema."""
        from cli.interactive.screens.shutdown_screen import ShutdownScreen
        shutdown_screen = ShutdownScreen()
        shutdown_screen.show()
    
    def _setup_global_shortcuts(self):
        """Configura atalhos globais que funcionam em qualquer tela."""
        return {
            Key.H: self._show_help,
            Key.S: self._handle_global_exit,
            Key.R: self._refresh_current,
            Key.C: self._quick_checkin,
            Key.E: self._emergency_mode,
            Key.M: self._toggle_menu,
            Key.B: self._go_back,
            Key.D: lambda: self._navigate_to_screen('dashboard')
        }
    
    def _show_help(self):
        """Mostra a tela de ajuda."""
        self._navigate_to_screen('help')
    
    def _handle_global_exit(self):
        """Sai do sistema com confirmação."""
        theme.print(f"\n{icon_text(Icon.QUESTION, 'Sair do sistema?')}", style="warning")
        theme.print("  S) Sim, sair", style="info")
        theme.print("  N) Não, continuar", style="info")
        
        key = self.keyboard_handler.wait_for_input()
        if key == Key.S:
            self.running = False
    
    def _refresh_current(self):
        """Recarrega a tela atual."""
        current = self.get_current_screen()
        if current:
            theme.print(f"{icon_text(Icon.REFRESH, 'Recarregando...')}", style="info")
            # A próxima iteração do loop irá mostrar a tela novamente
    
    def _quick_checkin(self):
        """Atalho para check-in rápido."""
        self._navigate_to_screen('daily_checkin')
    
    def _emergency_mode(self):
        """Atalho para modo emergência."""
        self._navigate_to_screen('emergency_mode')
    
    def _toggle_menu(self):
        """Alterna visibilidade do menu (implementação específica por tela)."""
        current = self.get_current_screen()
        if hasattr(current, 'toggle_menu'):
            current.toggle_menu()
    
    def _go_back(self):
        """Volta para a tela anterior."""
        if len(self.screen_stack) > 1:
            self.pop()
        else:
            theme.print("Não há telas anteriores.", style="warning")
    
    def get_navigation_breadcrumb(self):
        """Retorna o breadcrumb de navegação atual."""
        breadcrumbs = []
        for screen in self.screen_stack:
            if hasattr(screen, 'title'):
                breadcrumbs.append(screen.title)
            else:
                breadcrumbs.append(screen.__class__.__name__)
        
        return " → ".join(breadcrumbs)
    
    def get_screen_history(self, limit: int = 10):
        """Retorna o histórico de navegação."""
        return self.history[-limit:] if self.history else []
