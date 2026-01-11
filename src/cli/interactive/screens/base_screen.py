# src/cli/interactive/screens/base_screen.py
"""
Classe base para todas as telas interativas.
Fornece interface comum e métodos utilitários.
"""
from abc import ABC, abstractmethod
from src.cli.theme import theme
from src.cli.icons import Icon, icon_text
from src.cli.interactive.input.keyboard_handler import KeyboardHandler, Key

class BaseScreen(ABC):
    """Classe base abstrata para todas as telas."""
    
    def __init__(self):
        self.keyboard_handler = KeyboardHandler()
        self.title = "Tela Sem Título"
        self.should_exit = False
        
    @abstractmethod
    def show(self):
        """Exibe a tela e gerencia a interação."""
        pass
    
    def wait_for_exit(self, message="Pressione qualquer tecla para continuar..."):
        """Aguarda confirmação do usuário para sair."""
        theme.print(f"\n{message}", style="dim")
        self.keyboard_handler.wait_for_input()
    
    def render_menu(self, items, selected_index=0):
        """Renderiza um menu vertical com seleção."""
        theme.clear()
        theme.rule(f"[{self.title}]")
        
        for i, (label, _) in enumerate(items):
            prefix = "> " if i == selected_index else "  "
            # Determinar ícone baseado no conteúdo do label
            icon = self._determine_icon(label)
            theme.print(f"{prefix}{icon_text(icon, label)}", 
                       style="primary" if i == selected_index else "info")
        
        theme.print("\nUse ↑↓ para navegar, Enter para selecionar, ESC para voltar", style="dim")
    
    def _determine_icon(self, label):
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
