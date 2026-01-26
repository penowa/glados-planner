# src/cli/interactive/screen_manager.py (atualização do método _setup_global_shortcuts)
"""
Gerenciador de telas otimizado com Blessed/Curses para navegação entre telas.
"""
import sys
import time
import logging
from typing import Optional, Type, Any

from src.cli.interactive.terminal import GLTerminal, Key
from src.cli.theme import theme
from src.cli.icons import Icon, icon_text
from .screens.base_screen import BaseScreen

logger = logging.getLogger(__name__)

class ScreenManager:
    """
    Gerencia a navegação entre telas com sistema de pilha e renderização otimizada.
    """
    
    def __init__(self, terminal: GLTerminal):
        self.terminal = terminal
        self.screen_stack = []
        self.history = []
        self.running = False
        self.last_input_time = time.time()
        self.input_timeout = 300
        
        # Cache de telas para reuso
        self.screen_cache = {}
        
        # Configurar atalhos globais
        self.global_shortcuts = self._setup_global_shortcuts()
        
        # Configurações de performance
        self.show_perf_stats = False
        self.frame_count = 0
        self.start_time = time.time()
    
    def _force_clean_transition(self):
        """Força uma transição limpa entre telas."""
        self.terminal.clear_screen()
        self.terminal.flush()
        time.sleep(0.05)  # Pequena pausa para garantir limpeza
    
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
            Key.P: self._go_to_dashboard,  # <-- NOVO ATALHO P
            Key.F1: self._toggle_perf_stats
        }
    
    def push(self, screen_class: Type[BaseScreen], *args, **kwargs) -> BaseScreen:
        """Empilha uma nova tela com transição limpa."""
        self._force_clean_transition()
        
        if self.screen_stack:
            current_screen = self.screen_stack[-1]
            self.history.append({
                'class': current_screen.__class__.__name__,
                'title': getattr(current_screen, 'title', 'Unknown'),
                'timestamp': time.time()
            })
        
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
            self._force_clean_transition()
            return removed
        return None
    
    def replace(self, screen_class: Type[BaseScreen], *args, **kwargs) -> BaseScreen:
        """Substitui a tela atual por uma nova com transição limpa."""
        self._force_clean_transition()
        
        if self.screen_stack:
            self.screen_stack.pop()
        return self.push(screen_class, *args, **kwargs)
    
    def get_current_screen(self) -> Optional[BaseScreen]:
        """Retorna a tela atual (topo da pilha)."""
        if self.screen_stack:
            return self.screen_stack[-1]
        return None
    
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
        
        self.last_input_time = time.time()
    
    def _navigate_to_screen(self, screen_key: str):
        """Navega para uma tela específica pelo nome com limpeza garantida."""
        try:
            # Garantir limpeza antes da transição
            self._force_clean_transition()
            
            if screen_key == 'dashboard':
                from .screens.dashboard_screen import DashboardScreen
                self.replace(DashboardScreen)
            elif screen_key == 'agenda':
                from .screens.agenda_screen import AgendaScreen
                self.replace(AgendaScreen)
            elif screen_key == 'daily_checkin':
                from .screens.daily_checkin_screen import DailyCheckinScreen
                self.replace(DailyCheckinScreen)
            elif screen_key == 'emergency_mode':
                from .screens.emergency_screen import EmergencyScreen
                self.replace(EmergencyScreen)
            elif screen_key == 'pomodoro_session':
                from .screens.pomodoro_screen import PomodoroScreen
                self.replace(PomodoroScreen)
            elif screen_key == 'help':
                from .screens.help_screen import HelpScreen
                self.replace(HelpScreen)
            else:
                self._show_error(f"Tela '{screen_key}' não encontrada.")
                
        except ImportError as e:
            self._show_error(f"Não foi possível carregar a tela {screen_key}: {e}")
        except Exception as e:
            logger.error(f"Erro ao navegar para {screen_key}: {e}")
            self._show_error(f"Erro: {str(e)}")
    
    def _push_screen(self, screen_key: str):
        """Adiciona uma tela à pilha sem substituir a atual."""
        try:
            self._force_clean_transition()
            
            if screen_key == 'dashboard':
                from .screens.dashboard_screen import DashboardScreen
                self.push(DashboardScreen)
            elif screen_key == 'agenda':
                from .screens.agenda_screen import AgendaScreen
                self.push(AgendaScreen)
            else:
                # Fallback para navigate se não for push específico
                self._navigate_to_screen(screen_key)
                
        except ImportError as e:
            self._show_error(f"Não foi possível carregar a tela {screen_key}: {e}")
    
    def run(self):
        """Executa o loop principal otimizado do gerenciador de telas."""
        if not self.screen_stack:
            raise ValueError("Nenhuma tela na pilha. Use push() primeiro.")
        
        self.running = True
        self.start_time = time.time()
        
        try:
            while self.running and self.screen_stack:
                current_screen = self.get_current_screen()
                
                if time.time() - self.last_input_time > self.input_timeout:
                    self._handle_inactivity_timeout()
                    continue
                
                try:
                    # Executa tela atual
                    result = current_screen.show()
                    self.frame_count += 1
                    
                    # Verifica se a tecla pressionada é um atalho global
                    if isinstance(result, Key) and result in self.global_shortcuts:
                        self.global_shortcuts[result]()
                        continue
                    
                    self.last_input_time = time.time()
                    self._handle_screen_result(result)
                    
                except KeyboardInterrupt:
                    self._handle_keyboard_interrupt()
                except Exception as e:
                    self._handle_screen_error(current_screen, e)
            
        finally:
            self.cleanup()
    
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
        self._go_to_dashboard()
    
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
    
    def _go_to_dashboard(self):
        """NOVO MÉTODO: Atalho para retornar ao dashboard de qualquer tela."""
        self._navigate_to_screen('dashboard')
    
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
