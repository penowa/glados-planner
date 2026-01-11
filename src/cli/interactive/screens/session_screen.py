# src/cli/interactive/screens/session_screen.py
"""
Tela para iniciar diferentes tipos de sessões de estudo.
"""
from .base_screen import BaseScreen
from cli.theme import theme
from cli.icons import Icon, icon_text

class SessionScreen(BaseScreen):
    """Tela para seleção de tipo de sessão."""
    
    def __init__(self):
        super().__init__()
        self.title = "Tipo de Sessão"
        self.session_types = [
            ("Sessão Pomodoro (25min)", "pomodoro"),
            ("Sessão de Leitura", "reading"),
            ("Sessão de Revisão", "review"),
            ("Sessão de Escrita", "writing"),
            ("Sessão de Flashcards", "flashcards"),
            ("Sessão Personalizada", "custom")
        ]
    
    def show(self):
        selected_index = 0
        
        while True:
            self.render_menu(self.session_types, selected_index)
            
            key = self.keyboard_handler.wait_for_input()
            
            if key == Key.UP:
                selected_index = (selected_index - 1) % len(self.session_types)
            elif key == Key.DOWN:
                selected_index = (selected_index + 1) % len(self.session_types)
            elif key == Key.ENTER:
                session_name, session_type = self.session_types[selected_index]
                self.start_session(session_type, session_name)
                break
            elif key == Key.ESC:
                break
    
    def start_session(self, session_type, session_name):
        """Inicia a sessão selecionada."""
        
        if session_type == "pomodoro":
            from .pomodoro_session_screen import PomodoroSessionScreen
            screen = PomodoroSessionScreen()
            screen.show()
            
        elif session_type == "reading":
            from .reading_session_screen import ReadingSessionScreen
            screen = ReadingSessionScreen()
            screen.show()
            
        elif session_type == "review":
            theme.print(f"\n🎯 {icon_text(Icon.FLASHCARD, 'Iniciando sessão de revisão...')}", style="info")
            # TODO: Integrar com ReviewSystem
            theme.print("Sistema de revisão em desenvolvimento...", style="warning")
            self.wait_for_exit()
            
        elif session_type == "writing":
            theme.print(f"\n✍️  {icon_text(Icon.NOTE, 'Iniciando sessão de escrita...')}", style="info")
            # TODO: Integrar com WritingAssistant
            theme.print("Sistema de escrita em desenvolvimento...", style="warning")
            self.wait_for_exit()
            
        elif session_type == "flashcards":
            theme.print(f"\n🃏 {icon_text(Icon.FLASHCARD, 'Iniciando sessão de flashcards...')}", style="info")
            # TODO: Integrar com ReviewSystem
            theme.print("Sistema de flashcards em desenvolvimento...", style="warning")
            self.wait_for_exit()
            
        elif session_type == "custom":
            self.custom_session()
    
    def custom_session(self):
        """Configuração de sessão personalizada."""
        theme.clear()
        theme.rule("[Sessão Personalizada]")
        
        theme.print("\nConfigurar sessão personalizada:", style="primary")
        
        duration = input("Duração (minutos): ").strip()
        session_type = input("Tipo (leitura/revisão/escrita): ").strip()
        goal = input("Objetivo (opcional): ").strip()
        
        if duration.isdigit():
            theme.print(f"\n{icon_text(Icon.TIMER, f'Iniciando sessão de {duration} minutos...')}", style="success")
            # TODO: Implementar timer personalizado
            self.wait_for_exit()
        else:
            theme.print("❌ Duração inválida.", style="error")
            self.wait_for_exit()
