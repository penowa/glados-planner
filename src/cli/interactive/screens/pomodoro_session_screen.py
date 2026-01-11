# src/cli/interactive/screens/pomodoro_session_screen.py
"""
Tela de sessão Pomodoro com timer e citações.
Integra com PomodoroTimer.
"""
import time
import threading
from .base_screen import BaseScreen
from cli.integration.backend_integration import backend
from cli.theme import theme
from cli.icons import Icon, icon_text

class PomodoroSessionScreen(BaseScreen):
    """Tela de sessão Pomodoro."""
    
    def __init__(self):
        super().__init__()
        self.title = "Sessão Pomodoro"
        self.duration = 25 * 60  # 25 minutos em segundos
        self.is_running = False
        self.remaining_time = 0
        self.session_type = "work"  # work, break, long_break
        self.session_count = 0
        
    def show(self):
        # Configurar sessão
        self._setup_session()
        
        # Iniciar sessão
        self._start_session()
        
        # Mostrar tela do timer
        self._show_timer()
        
        # Pós-sessão
        self._post_session()
    
    def _setup_session(self):
        """Configura os parâmetros da sessão."""
        theme.clear()
        theme.rule("[Configurar Sessão Pomodoro]")
        
        theme.print(f"\n{icon_text(Icon.TIMER, 'Configuração da sessão:')}", style="primary")
        
        # Duração
        duration_choice = input("Duração (1=25min, 2=50min, 3=custom): ").strip()
        
        if duration_choice == '1':
            self.duration = 25 * 60
        elif duration_choice == '2':
            self.duration = 50 * 60
        elif duration_choice == '3':
            custom_min = input("Minutos personalizados: ").strip()
            if custom_min.isdigit():
                self.duration = int(custom_min) * 60
            else:
                self.duration = 25 * 60
        
        # Tipo de tarefa
        theme.print(f"\n{icon_text(Icon.TASK, 'Tipo de tarefa:')}", style="info")
        task_type = input("Descreva a tarefa: ").strip()
        self.task_description = task_type if task_type else "Tarefa não especificada"
        
        # Metas
        theme.print(f"\n{icon_text(Icon.TARGET, 'Meta para esta sessão:')}", style="info")
        goal = input("(opcional): ").strip()
        self.session_goal = goal
        
        theme.print(f"\n{icon_text(Icon.INFO, 'Pronto para começar!')}", style="success")
        time.sleep(1)
    
    def _start_session(self):
        """Inicia a sessão Pomodoro."""
        self.is_running = True
        self.remaining_time = self.duration
        self.start_time = time.time()
        
        # Iniciar timer em thread separada
        self.timer_thread = threading.Thread(target=self._run_timer)
        self.timer_thread.daemon = True
        self.timer_thread.start()
        
        # Registrar início no backend
        try:
            backend.start_pomodoro_session({
                'duration': self.duration,
                'task': self.task_description,
                'goal': self.session_goal,
                'type': self.session_type
            })
        except:
            pass  # Continuar mesmo se falhar
    
    def _run_timer(self):
        """Executa o timer em background."""
        while self.is_running and self.remaining_time > 0:
            time.sleep(1)
            self.remaining_time -= 1
            
            # Emitir evento a cada minuto
            if self.remaining_time % 60 == 0:
                minutes_left = self.remaining_time // 60
                try:
                    backend._emit_event('POMODORO_TICK', {
                        'minutes_left': minutes_left,
                        'total_minutes': self.duration // 60
                    })
                except:
                    pass
        
        # Sessão completada
        if self.remaining_time <= 0:
            self.is_running = False
            try:
                backend.complete_pomodoro_session({
                    'duration': self.duration,
                    'task': self.task_description,
                    'completed': True
                })
            except:
                pass
    
    def _show_timer(self):
        """Mostra a interface do timer."""
        quotes = [
            "Continue trabalhando. O fracasso não é uma opção. É uma obrigação.",
            "A ciência mostra que pausas são importantes. Mas a ciência também mostra que você é preguiçoso.",
            "Mais 5 minutos. Ou 10. Ou 15. Na verdade, só termine a sessão.",
            "Produtividade é como um bolo: se você olhar muito, ele nunca fica pronto.",
            "Lembre-se: cada minuto que passa é um minuto que você não terá de volta. Aproveite a pressão.",
            "O cérebro humano precisa de descanso. O seu provavelmente precisa de mais que o normal.",
            "Foco é a chave. A menos que a chave esteja errada. Então você precisa de outra chave."
        ]
        
        current_quote = 0
        
        while self.is_running and self.remaining_time > 0:
            theme.clear()
            theme.rule("[Sessão Pomodoro em Andamento]", style="accent")
            
            # Timer
            minutes = self.remaining_time // 60
            seconds = self.remaining_time % 60
            
            theme.print(f"\n{icon_text(Icon.TIMER, 'Tempo restante:')}", style="primary")
            theme.print(f"  ⏰ {minutes:02d}:{seconds:02d}", style="accent")
            
            # Barra de progresso
            progress = 1 - (self.remaining_time / self.duration)
            bar_length = 40
            filled = int(bar_length * progress)
            bar = '█' * filled + '░' * (bar_length - filled)
            
            theme.print(f"\n[{bar}] {progress*100:.1f}%", style="info")
            
            # Tarefa atual
            theme.print(f"\n{icon_text(Icon.TASK, 'Tarefa:')} {self.task_description}", style="info")
            
            if self.session_goal:
                theme.print(f"{icon_text(Icon.TARGET, 'Meta:')} {self.session_goal}", style="dim")
            
            # Citação motivacional
            theme.print(f"\n{icon_text(Icon.GLADOS, 'GLaDOS:')}", style="accent")
            theme.print(f"  \"{quotes[current_quote % len(quotes)]}\"", style="dim")
            
            # Instruções
            theme.print(f"\n{icon_text(Icon.INFO, 'Pressione ESC para pausar/cancelar')}", style="dim")
            
            # Verificar entrada do usuário (não bloqueante)
            key = self.keyboard_handler.get_key()
            if key == Key.ESC:
                self._handle_pause()
                break
            
            # Atualizar a cada segundo
            time.sleep(1)
            
            # Mudar citação a cada 30 segundos
            if self.remaining_time % 30 == 0:
                current_quote += 1
        
        # Sessão completada
        if self.remaining_time <= 0:
            self._show_completion()
    
    def _handle_pause(self):
        """Lida com pausa/cancelamento da sessão."""
        theme.print(f"\n{icon_text(Icon.QUESTION, 'Sessão pausada. Continuar ou cancelar?')}", style="warning")
        theme.print("  C) Continuar", style="info")
        theme.print("  S) Salvar e sair", style="info")
        theme.print("  X) Cancelar sessão", style="error")
        
        while True:
            key = self.keyboard_handler.wait_for_input()
            
            if key in [Key.C, Key.ENTER]:
                self._start_session()  # Reiniciar timer
                break
            elif key == Key.S:
                # Salvar progresso
                self.is_running = False
                try:
                    backend.pause_pomodoro_session({
                        'duration_completed': self.duration - self.remaining_time,
                        'task': self.task_description
                    })
                except:
                    pass
                break
            elif key in [Key.X, Key.ESC]:
                # Cancelar
                self.is_running = False
                try:
                    backend.cancel_pomodoro_session({
                        'duration_completed': self.duration - self.remaining_time,
                        'task': self.task_description
                    })
                except:
                    pass
                break
    
    def _show_completion(self):
        """Mostra tela de conclusão da sessão."""
        theme.clear()
        theme.rule("[Sessão Pomodoro Concluída!]", style="success")
        
        theme.print(f"\n{icon_text(Icon.SUCCESS, 'Sessão completada com sucesso!')}", style="success")
        theme.print("=" * 50, style="dim")
        
        theme.print(f"\n⏰ Duração: {self.duration // 60} minutos", style="info")
        theme.print(f"📋 Tarefa: {self.task_description}", style="info")
        
        if self.session_goal:
            theme.print(f"🎯 Meta: {self.session_goal}", style="info")
        
        # Sugerir pausa
        theme.print(f"\n{icon_text(Icon.INFO, 'Hora de uma pausa! Recomendado:')}", style="primary")
        theme.print("  5 minutos de descanso", style="dim")
        
        # Estatísticas
        try:
            stats = backend.get_pomodoro_stats()
            if stats:
                theme.print(f"\n{icon_text(Icon.CALENDAR, 'Estatísticas Pomodoro:')}", style="primary")
                theme.print(f"  📊 Sessões hoje: {stats.get('sessions_today', 0)}", style="info")
                theme.print(f"  ⏱️  Tempo total: {stats.get('total_minutes', 0)} minutos", style="info")
                theme.print(f"  🔥 Sequência: {stats.get('streak_days', 0)} dias", style="success")
        except:
            pass
        
        self.wait_for_exit("\nPressione qualquer tecla para voltar...")
    
    def _post_session(self):
        """Processamento pós-sessão."""
        self.session_count += 1
        
        # Se foram 4 sessões, sugerir pausa longa
        if self.session_count % 4 == 0:
            theme.print(f"\n{icon_text(Icon.INFO, '4 sessões completadas! Hora de uma pausa longa (15-30min).')}", style="success")
