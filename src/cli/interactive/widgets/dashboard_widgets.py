# src/cli/interactive/widgets/dashboard_widgets.py
"""
Widgets especializados para o dashboard do GLaDOS Planner.
"""
from typing import Dict, List, Optional
from src.cli.interactive.terminal import GLTerminal
from src.cli.theme import theme
from src.cli.icons import Icon


class DashboardWidget:
    """Classe base para widgets do dashboard."""
    
    def __init__(self, terminal: GLTerminal):
        self.terminal = terminal
        self.data = None
        self.width = 0
        self.height = 0
    
    def update_data(self, data: Dict):
        """Atualiza dados do widget."""
        self.data = data
    
    def calculate_size(self, available_width: int, available_height: int):
        """Calcula tamanho necessário para o widget."""
        pass
    
    def render(self, x: int, y: int, width: int, height: int):
        """Renderiza o widget na posição especificada."""
        pass


class GoalWidget(DashboardWidget):
    """Widget para exibir metas do dia."""
    
    def __init__(self, terminal: GLTerminal):
        super().__init__(terminal)
        self.title = "🎯 Metas do Dia"
        self.max_goals = 3
    
    def calculate_size(self, available_width: int, available_height: int):
        goals = self.data.get('daily_goals', [])[:self.max_goals]
        self.height = 2 + len(goals)  # Título + separador + cada meta
        self.width = available_width
    
    def render(self, x: int, y: int, width: int, height: int):
        goals = self.data.get('daily_goals', [])[:self.max_goals]
        
        # Título
        self.terminal.print_at(x, y, self.title, {"color": "primary", "bold": True})
        
        if not goals:
            self.terminal.print_at(x, y + 1, "  Nenhuma meta para hoje", {"color": "dim"})
            return
        
        # Metas
        for i, goal in enumerate(goals):
            goal_y = y + 1 + i
            
            status = "✅" if goal.get('completed', False) else "□"
            title = goal.get('title', 'Meta sem nome')
            progress = goal.get('progress', 0)
            
            # Barra de progresso
            bar_width = 20
            filled = int(progress * bar_width / 100)
            bar = "█" * filled + "░" * (bar_width - filled)
            
            goal_text = f"  {status} {title} [{bar}] {progress}%"
            if len(goal_text) > width:
                goal_text = goal_text[:width-3] + "..."
            
            color = "success" if goal.get('completed', False) else "info"
            self.terminal.print_at(x, goal_y, goal_text, {"color": color})


class EventWidget(DashboardWidget):
    """Widget para exibir eventos do dia."""
    
    def __init__(self, terminal: GLTerminal):
        super().__init__(terminal)
        self.title = "📅 Agenda do Dia"
        self.max_events = 3
    
    def calculate_size(self, available_width: int, available_height: int):
        events = self.data.get('upcoming_events', [])[:self.max_events]
        self.height = 2 + len(events)
        self.width = available_width
    
    def render(self, x: int, y: int, width: int, height: int):
        events = self.data.get('upcoming_events', [])[:self.max_events]
        
        # Título
        self.terminal.print_at(x, y, self.title, {"color": "primary", "bold": True})
        
        if not events:
            self.terminal.print_at(x, y + 1, "  Nenhum compromisso para hoje", {"color": "dim"})
            return
        
        # Eventos
        for i, event in enumerate(events):
            event_y = y + 1 + i
            
            time_str = event.get('time', '')
            title = event.get('title', 'Evento sem nome')
            
            # Ícone baseado no tipo
            event_type = event.get('type', 'default')
            icons = {
                'leitura': '📚',
                'aula': '🎓',
                'escrita': '✍️',
                'default': '📝'
            }
            icon = icons.get(event_type, icons['default'])
            
            event_text = f"  {icon} {time_str} {title}"
            if len(event_text) > width:
                event_text = event_text[:width-3] + "..."
            
            self.terminal.print_at(x, event_y, event_text, {"color": "info"})


class AlertWidget(DashboardWidget):
    """Widget para exibir alertas do sistema."""
    
    def __init__(self, terminal: GLTerminal):
        super().__init__(terminal)
        self.title = "⚠️ Alertas"
        self.max_alerts = 2
    
    def calculate_size(self, available_width: int, available_height: int):
        alerts = self.data.get('alerts', [])[:self.max_alerts]
        self.height = 2 + len(alerts)
        self.width = available_width
    
    def render(self, x: int, y: int, width: int, height: int):
        alerts = self.data.get('alerts', [])[:self.max_alerts]
        
        # Título
        self.terminal.print_at(x, y, self.title, {"color": "warning", "bold": True})
        
        if not alerts:
            self.terminal.print_at(x, y + 1, "  Nenhum alerta no momento", {"color": "dim"})
            return
        
        # Alertas
        for i, alert in enumerate(alerts):
            alert_y = y + 1 + i
            
            alert_type = alert.get('type', 'info')
            message = alert.get('message', 'Alerta sem mensagem')
            
            # Cor baseada no tipo
            colors = {
                'warning': 'warning',
                'error': 'error',
                'info': 'info',
                'success': 'success'
            }
            color = colors.get(alert_type, 'info')
            
            alert_text = f"  • {message}"
            if len(alert_text) > width:
                alert_text = alert_text[:width-3] + "..."
            
            self.terminal.print_at(x, alert_y, alert_text, {"color": color})


class BookWidget(DashboardWidget):
    """Widget para exibir livros ativos."""
    
    def __init__(self, terminal: GLTerminal):
        super().__init__(terminal)
        self.title = "📚 Livros Ativos"
        self.max_books = 2
    
    def calculate_size(self, available_width: int, available_height: int):
        books = self.data.get('active_books', [])[:self.max_books]
        self.height = 2 + len(books)
        self.width = available_width
    
    def render(self, x: int, y: int, width: int, height: int):
        books = self.data.get('active_books', [])[:self.max_books]
        
        # Título
        self.terminal.print_at(x, y, self.title, {"color": "primary", "bold": True})
        
        if not books:
            self.terminal.print_at(x, y + 1, "  Nenhum livro ativo", {"color": "dim"})
            return
        
        # Livros
        for i, book in enumerate(books):
            book_y = y + 1 + i
            
            title = book.get('title', 'Livro sem nome')
            author = book.get('author', 'Autor desconhecido')
            progress = book.get('progress', 0)
            
            book_text = f"  {title} ({author}) - {progress}%"
            if len(book_text) > width:
                book_text = book_text[:width-3] + "..."
            
            self.terminal.print_at(x, book_y, book_text, {"color": "info"})
