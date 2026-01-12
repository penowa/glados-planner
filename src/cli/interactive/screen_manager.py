# src/cli/interactive/screen_manager.py
"""
Gerenciador de telas otimizado com Blessed/Curses para navegação entre telas.
"""
import sys
import time
from typing import Optional, Type, Any

from src.cli.interactive.terminal import GLTerminal, Key
from src.cli.theme import theme
from src.cli.icons import Icon, icon_text
from .screens.base_screen import BaseScreen


class ScreenManager:
    """
    Gerencia a navegação entre telas com sistema de pilha e renderização otimizada.
    
    Padrões de uso:
        terminal = GLTerminal()
        manager = ScreenManager(terminal)
        manager.push(DashboardScreen)
        manager.run()
    """
    
    def __init__(self, terminal: GLTerminal):
        self.terminal = terminal
        self.screen_stack = []  # Pilha de telas (instâncias de BaseScreen)
        self.history = []       # Histórico de navegação
        self.running = False
        self.last_input_time = time.time()
        self.input_timeout = 300  # 5 minutos de inatividade
        
        # Cache de telas para reuso
        self.screen_cache = {}
        
        # Configurar atalhos globais
        self.global_shortcuts = self._setup_global_shortcuts()
        
        # Configurações de performance
        self.show_perf_stats = False
        self.frame_count = 0
        self.start_time = time.time()
        
    def push(self, screen_class: Type[BaseScreen], *args, **kwargs) -> BaseScreen:
        """Empilha uma nova tela."""
        # Registrar histórico se houver tela atual
        if self.screen_stack:
            current_screen = self.screen_stack[-1]
            self.history.append({
                'class': current_screen.__class__.__name__,
                'title': getattr(current_screen, 'title', 'Unknown'),
                'timestamp': time.time()
            })
        
        # Criar tela com terminal injetado
        screen_key = f"{screen_class.__name__}:{str(args)}:{str(kwargs)}"
        
        if screen_key in self.screen_cache:
            screen = self.screen_cache[screen_key]
        else:
            screen = screen_class(self.terminal, *args, **kwargs)
            self.screen_cache[screen_key] = screen
        
        self.screen_stack.append(screen)
        return screen
    
    def pop(self) -> Optional[BaseScreen]:
        """Remove a tela atual da pilha e retorna à anterior."""
        if len(self.screen_stack) > 1:
            removed = self.screen_stack.pop()
            return removed
        return None
    
    def replace(self, screen_class: Type[BaseScreen], *args, **kwargs) -> BaseScreen:
        """Substitui a tela atual por uma nova."""
        if self.screen_stack:
            self.screen_stack.pop()
        return self.push(screen_class, *args, **kwargs)
    
    def get_current_screen(self) -> Optional[BaseScreen]:
        """Retorna a tela atual (topo da pilha)."""
        if self.screen_stack:
            return self.screen_stack[-1]
        return None
    
    def run(self):
        """Executa o loop principal otimizado do gerenciador de telas."""
        if not self.screen_stack:
            raise ValueError("Nenhuma tela na pilha. Use push() primeiro.")
        
        self.running = True
        self.start_time = time.time()
        
        try:
            while self.running and self.screen_stack:
                current_screen = self.get_current_screen()
                
                # Verifica timeout de inatividade
                if time.time() - self.last_input_time > self.input_timeout:
                    self._handle_inactivity_timeout()
                    continue
                
                # Executa tela atual
                try:
                    result = current_screen.show()
                    self.frame_count += 1
                    
                    # Atualiza tempo da última interação
                    self.last_input_time = time.time()
                    
                    # Processar resultado da tela
                    self._handle_screen_result(result)
                    
                except KeyboardInterrupt:
                    # Ctrl+C pressionado
                    self._handle_keyboard_interrupt()
                    
                except Exception as e:
                    self._handle_screen_error(current_screen, e)
            
        finally:
            self.cleanup()
    
    def _handle_screen_result(self, result: Any):
        """Processa resultado retornado por uma tela."""
        if result is None:
            return
        
        if isinstance(result, str):
            if result == 'exit':
                self.running = False
            elif result == 'back':
                self.pop()
            elif result.startswith('goto:'):
                screen_key = result[5:]
                self._navigate_to_screen(screen_key)
            elif result.startswith('push:'):
                screen_key = result[6:]
                self._push_screen(screen_key)
        
        # Atualiza tempo da última interação
        self.last_input_time = time.time()
    
    def _navigate_to_screen(self, screen_key: str):
        """Navega para uma tela específica pelo nome."""
        # Mapeamento dinâmico para evitar imports circulares
        try:
            if screen_key == 'dashboard':
                from .screens.dashboard_screen import DashboardScreen
                self.replace(DashboardScreen)
            elif screen_key == 'new_book':
                from .screens.new_book_screen import NewBookScreen
                self.replace(NewBookScreen)
            elif screen_key == 'reading':
                from .screens.reading_session_screen import ReadingSessionScreen
                self.replace(ReadingSessionScreen)
            elif screen_key == 'book_selection':
                from .screens.book_selection_screen import BookSelectionScreen
                self.replace(BookSelectionScreen)
            elif screen_key == 'session':
                from .screens.session_screen import SessionScreen
                self.replace(SessionScreen)
            elif screen_key == 'pomodoro':
                from .screens.pomodoro_session_screen import PomodoroSessionScreen
                self.replace(PomodoroSessionScreen)
            elif screen_key == 'daily_checkin':
                from .screens.daily_checkin_screen import DailyCheckinScreen
                self.replace(DailyCheckinScreen)
            elif screen_key == 'weekly_planning':
                from .screens.weekly_planning_screen import WeeklyPlanningScreen
                self.replace(WeeklyPlanningScreen)
            elif screen_key == 'agenda_config':
                from .screens.agenda_config_screen import AgendaConfigScreen
                self.replace(AgendaConfigScreen)
            elif screen_key == 'task_management':
                from .screens.task_management_screen import TaskManagementScreen
                self.replace(TaskManagementScreen)
            elif screen_key == 'emergency_mode':
                from .screens.emergency_mode_screen import EmergencyModeScreen
                self.replace(EmergencyModeScreen)
            elif screen_key == 'glados_query':
                from .screens.glados_query_screen import GladosQueryScreen
                self.replace(GladosQueryScreen)
            elif screen_key == 'settings':
                from .screens.settings_screen import SettingsScreen
                self.replace(SettingsScreen)
            elif screen_key == 'statistics':
                from .screens.statistics_screen import StatisticsScreen
                self.replace(StatisticsScreen)
            elif screen_key == 'help':
                from .screens.help_screen import HelpScreen
                self.replace(HelpScreen)
            elif screen_key == 'shutdown':
                from .screens.shutdown_screen import ShutdownScreen
                self.replace(ShutdownScreen)
            else:
                self._show_error(f"Tela '{screen_key}' não encontrada.")
                
        except ImportError as e:
            self._show_error(f"Não foi possível carregar a tela {screen_key}: {e}")
    
    def _push_screen(self, screen_key: str):
        """Adiciona uma tela à pilha sem substituir a atual."""
        # Similar a _navigate_to_screen mas com push em vez de replace
        try:
            if screen_key == 'dashboard':
                from .screens.dashboard_screen import DashboardScreen
                self.push(DashboardScreen)
            else:
                self._navigate_to_screen(screen_key)  # Fallback para replace
                
        except ImportError as e:
            self._show_error(f"Não foi possível carregar a tela {screen_key}: {e}")
    
    def _handle_inactivity_timeout(self):
        """Lida com timeout de inatividade."""
        term_width, term_height = self.terminal.get_size()
        
        timeout_msg = "⏰ Tempo de inatividade excedido. Retornando ao dashboard..."
        msg_x = max(0, (term_width - len(timeout_msg)) // 2)
        msg_y = term_height // 2
        
        self.terminal.print_at(msg_x, msg_y, timeout_msg, {"color": "warning", "bold": True})
        self.terminal.flush()
        
        time.sleep(1.5)
        
        # Retorna ao dashboard
        self._navigate_to_screen('dashboard')
    
    def _handle_keyboard_interrupt(self):
        """Lida com interrupção por teclado (Ctrl+C)."""
        if len(self.screen_stack) > 1:
            self.pop()
        else:
            self.running = False
            
            term_width, term_height = self.terminal.get_size()
            msg = "⚠️ Sistema interrompido pelo usuário."
            msg_x = max(0, (term_width - len(msg)) // 2)
            
            self.terminal.print_at(msg_x, term_height // 2, msg, {"color": "warning", "bold": True})
            self.terminal.flush()
            time.sleep(1)
    
    def _handle_screen_error(self, screen: BaseScreen, error: Exception):
        """Lida com erros em telas."""
        term_width, term_height = self.terminal.get_size()
        
        error_title = f"❌ Erro na tela {screen.__class__.__name__}"
        error_msg = f"   {str(error)}"
        
        title_x = max(0, (term_width - len(error_title)) // 2)
        msg_x = max(0, (term_width - len(error_msg)) // 2)
        
        self.terminal.print_at(title_x, term_height // 2 - 1, error_title, 
                              {"color": "error", "bold": True})
        self.terminal.print_at(msg_x, term_height // 2, error_msg, {"color": "error"})
        
        self.terminal.print_at(0, term_height - 1, "Pressione qualquer tecla para continuar...", 
                              {"color": "dim"})
        self.terminal.flush()
        
        self.terminal.get_key()
        
        # Tenta recuperar voltando uma tela
        if len(self.screen_stack) > 1:
            self.pop()
        else:
            self.running = False
    
    def _show_error(self, message: str):
        """Exibe mensagem de erro no terminal."""
        term_width, term_height = self.terminal.get_size()
        
        msg_x = max(0, (term_width - len(message)) // 2)
        self.terminal.print_at(msg_x, term_height // 2, message, {"color": "error", "bold": True})
        self.terminal.flush()
        
        time.sleep(2)
    
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
            Key.D: lambda: self._navigate_to_screen('dashboard'),
            Key.F1: self._toggle_perf_stats
        }
    
    def _show_help(self):
        """Mostra a tela de ajuda."""
        self._navigate_to_screen('help')
    
    def _handle_global_exit(self):
        """Sai do sistema com confirmação."""
        term_width, term_height = self.terminal.get_size()
        
        confirm_msg = "Sair do sistema? (S/N)"
        confirm_x = max(0, (term_width - len(confirm_msg)) // 2)
        
        self.terminal.print_at(confirm_x, term_height // 2, confirm_msg, 
                              {"color": "warning", "bold": True})
        self.terminal.flush()
        
        key = self.terminal.get_key()
        if key == Key.S:
            self.running = False
        else:
            # Limpa mensagem
            self.terminal.clear_line(term_height // 2)
            self.terminal.flush()
    
    def _refresh_current(self):
        """Recarrega a tela atual."""
        current = self.get_current_screen()
        if current:
            if hasattr(current, '_load_data'):
                current._load_data()
            current.mark_dirty()
    
    def _quick_checkin(self):
        """Atalho para check-in rápido."""
        self._navigate_to_screen('daily_checkin')
    
    def _emergency_mode(self):
        """Atalho para modo emergência."""
        self._navigate_to_screen('emergency_mode')
    
    def _toggle_menu(self):
        """Alterna visibilidade do menu."""
        current = self.get_current_screen()
        if hasattr(current, 'toggle_menu'):
            current.toggle_menu()
    
    def _go_back(self):
        """Volta para a tela anterior."""
        if len(self.screen_stack) > 1:
            self.pop()
        else:
            term_width, term_height = self.terminal.get_size()
            msg = "Não há telas anteriores."
            msg_x = max(0, (term_width - len(msg)) // 2)
            
            self.terminal.print_at(msg_x, term_height // 2, msg, {"color": "warning"})
            self.terminal.flush()
            time.sleep(1)
    
    def _toggle_perf_stats(self):
        """Alterna exibição de estatísticas de performance."""
        self.show_perf_stats = not self.show_perf_stats
        
        if self.show_perf_stats:
            self._show_performance_stats()
    
    def _show_performance_stats(self):
        """Exibe estatísticas de performance."""
        term_width, term_height = self.terminal.get_size()
        
        elapsed = time.time() - self.start_time
        fps = self.frame_count / elapsed if elapsed > 0 else 0
        
        stats = [
            f"FPS: {fps:.1f}",
            f"Frames: {self.frame_count}",
            f"Tempo: {elapsed:.1f}s",
            f"Telas na pilha: {len(self.screen_stack)}",
            f"Terminal: {term_width}x{term_height}",
            f"Blessed: {self.terminal.use_blessed}"
        ]
        
        # Mostra estatísticas no canto superior direito
        for i, stat in enumerate(stats):
            x = term_width - len(stat) - 2
            self.terminal.print_at(x, i, stat, {"color": "dim"})
        
        self.terminal.flush()
        time.sleep(2)  # Mostra por 2 segundos
        
        # Limpa estatísticas
        for i in range(len(stats)):
            self.terminal.clear_line(i)
        
        self.terminal.flush()
    
    def cleanup(self):
        """Limpeza ao finalizar."""
        # Limpa cache
        self.screen_cache.clear()
        
        # Limpeza do terminal
        self.terminal.cleanup()
        
        # Mostra cursor
        self.terminal.show_cursor()
        
        # Mensagem de despedida
        if self.terminal.use_blessed:
            print("\n" + "=" * 60)
            theme.print("✨ Sistema GLaDOS Planner finalizado.", style="primary")
            
            # Estatísticas finais
            elapsed = time.time() - self.start_time
            if elapsed > 0:
                fps = self.frame_count / elapsed
                theme.print(f"   FPS médio: {fps:.1f}", style="dim")
                theme.print(f"   Frames renderizados: {self.frame_count}", style="dim")
                theme.print(f"   Tempo de execução: {elapsed:.1f}s", style="dim")
            
            print("=" * 60 + "\n")
    
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
