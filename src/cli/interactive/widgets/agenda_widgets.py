# src/cli/interactive/widgets/agenda_widget.py
"""
Widgets reutilizáveis para a Agenda Inteligente
"""
from datetime import datetime
from typing import List, Dict

from cli.theme import theme
from cli.icons import Icon, icon_text

class AgendaWidget:
    """Widget de agenda que segue o padrão GLaDOS"""
    
    @staticmethod
    def render_day_summary(date: datetime, events: List[Dict], width: int = 40):
        """Renderiza resumo do dia em formato de painel"""
        # Cabeçalho do painel
        day_name = date.strftime('%A')
        theme.rule(f" {day_name} ", style="subtitle")
        
        # Data
        date_str = date.strftime('%d/%m/%Y')
        theme.print(f"📅 {date_str}", style="dim")
        
        # Conteúdo
        if not events:
            theme.print(icon_text(Icon.ALERT, "Dia livre"), style="info")
        else:
            for i, event in enumerate(events[:5]):  # Limita a 5 eventos
                AgendaWidget._render_event_line(event, width)
            
            if len(events) > 5:
                theme.print(f"... +{len(events)-5} eventos", style="dim")
        
        theme.rule(style="secondary")
    
    @staticmethod
    def _render_event_line(event: Dict, width: int):
        """Renderiza linha de evento compacta"""
        # Ícone baseado no tipo
        icon_map = {
            'aula': '📚',
            'leitura': '📖',
            'producao': '✍️',
            'revisao': '🔄',
            'prova': '📝',
            'seminario': '🎤'
        }
        
        icon = icon_map.get(event.get('type', ''), '•')
        time = event.get('time', '')[:5]
        title = event.get('title', '')[:width - 10]
        
        # Determina estilo baseado em prioridade e status
        if event.get('completed', False):
            style = "success"
        elif event.get('priority') == 'high':
            style = "warning"
        else:
            style = "primary"
        
        line = f"{icon} {time} {title}"
        theme.print(line, style=style)
    
    @staticmethod
    def render_upcoming_events(events: List[Dict], limit: int = 5, width: int = 50):
        """Renderiza lista de eventos próximos"""
        theme.rule(" 🕐 PRÓXIMOS EVENTOS ", style="subtitle")
        
        if not events:
            theme.print("Nenhum evento próximo", style="info")
        else:
            for event in events[:limit]:
                AgendaWidget._render_upcoming_event(event, width)
        
        theme.rule(style="secondary")
    
    @staticmethod
    def _render_upcoming_event(event: Dict, width: int):
        """Renderiza um evento próximo"""
        date_str = event.get('date', '')
        time_str = event.get('time', '')
        title = event.get('title', '')[:width - 20]
        
        # Formata data/hora
        try:
            dt = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
            display_time = dt.strftime("%d/%m %H:%M")
        except:
            display_time = f"{date_str} {time_str}"
        
        # Prioridade
        priority = event.get('priority', 'medium')
        priority_icon = "⚠️" if priority == 'high' else "ℹ️"
        
        line = f"{priority_icon} {display_time:12s} {title}"
        
        # Estilo
        if priority == 'high':
            theme.print(line, style="warning")
        else:
            theme.print(line, style="primary")
    
    @staticmethod
    def render_productivity_stats(stats: Dict):
        """Renderiza estatísticas de produtividade"""
        theme.rule(" 📈 ESTATÍSTICAS ", style="subtitle")
        
        # Métricas básicas
        metrics = [
            (f"Eventos concluídos: {stats.get('completed', 0)}/{stats.get('total', 0)}", 
             "primary"),
            (f"Horas produtivas: {stats.get('productive_hours', 0):.1f}h", "info"),
            (f"Taxa de conclusão: {stats.get('completion_rate', 0):.1f}%", 
             "success" if stats.get('completion_rate', 0) > 70 else "warning"),
            (f"Score de foco: {stats.get('focus_score', 0)}/100", 
             "success" if stats.get('focus_score', 0) > 70 else "warning")
        ]
        
        for text, style in metrics:
            theme.print(text, style=style)
        
        theme.rule(style="secondary")
