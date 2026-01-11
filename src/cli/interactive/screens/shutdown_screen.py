# src/cli/interactive/screens/shutdown_screen.py
"""
Tela de encerramento elegante com estatísticas.
"""
import time
import datetime
from .base_screen import BaseScreen
from cli.integration.backend_integration import backend
from cli.theme import theme
from cli.icons import Icon, icon_text

class ShutdownScreen(BaseScreen):
    """Tela de encerramento do sistema."""
    
    def __init__(self):
        super().__init__()
        self.title = "Encerramento"
    
    def show(self):
        theme.clear()
        theme.rule(f"[{self.title}]", style="accent")
        
        # Coletar estatísticas
        stats = self._collect_stats()
        
        # Mostrar mensagem de despedida
        theme.print(f"\n{icon_text(Icon.GLADOS, 'Encerrando o sistema GLaDOS Planner...')}", style="accent")
        theme.print("=" * 60, style="dim")
        
        # Estatísticas do dia
        theme.print(f"\n{icon_text(Icon.INFO, 'Resumo do dia:')}", style="primary")
        
        if stats['sessions_today'] > 0:
            theme.print(f"  🎯 Sessões completadas: {stats['sessions_today']}", style="info")
        
        if stats['pages_read'] > 0:
            theme.print(f"  📖 Páginas lidas: {stats['pages_read']}", style="info")
        
        if stats['tasks_completed'] > 0:
            theme.print(f"  ✅ Tarefas concluídas: {stats['tasks_completed']}", style="success")
        
        if stats['events_today'] > 0:
            completed_events = sum(1 for e in stats['events_today'] if e.get('completed', False))
            theme.print(f"  📅 Eventos: {completed_events}/{len(stats['events_today'])} concluídos", style="info")
        
        # Tempo de uso
        if stats['session_start']:
            session_duration = datetime.datetime.now() - stats['session_start']
            hours, remainder = divmod(session_duration.seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            theme.print(f"  ⏰ Tempo de sessão: {hours:02d}:{minutes:02d}:{seconds:02d}", style="info")
        
        # Produtividade
        theme.print(f"\n{icon_text(Icon.CALENDAR, 'Produtividade:')}", style="primary")
        
        if stats['streak_days'] > 0:
            theme.print(f"  🔥 Sequência: {stats['streak_days']} dias", style="success")
        
        if stats['total_books'] > 0:
            theme.print(f"  📚 Livros ativos: {stats['total_books']}", style="info")
        
        if stats['total_tasks'] > 0:
            completed_percentage = (stats['completed_tasks'] / stats['total_tasks']) * 100
            theme.print(f"  📋 Tarefas: {stats['completed_tasks']}/{stats['total_tasks']} ({completed_percentage:.1f}%)", style="info")
        
        # Mensagem personalizada baseada na produtividade
        theme.print(f"\n{icon_text(Icon.GLADOS, 'GLaDOS diz:')}", style="accent")
        
        if stats['tasks_completed'] >= 5:
            theme.print(f"  'Produtivo para os padrões humanos. Continue assim. Ou não.'", style="success")
        elif stats['tasks_completed'] > 0:
            theme.print(f"  'Algum progresso é melhor que nenhum. Técnicamente.'", style="info")
        else:
            theme.print(f"  'Dia improdutivo. Espero que tenha pelo menos se divertido.'", style="warning")
        
        # Contagem regressiva
        theme.print(f"\n{icon_text(Icon.TIMER, 'Encerrando em:')}", style="warning")
        
        for i in range(3, 0, -1):
            theme.print(f"  {i}...", style="warning")
            time.sleep(1)
        
        theme.print(f"\n{icon_text(Icon.EXIT, 'Sistema encerrado.')}", style="accent")
        
        # Não chamar wait_for_exit pois estamos encerrando
        return 'shutdown'
    
    def _collect_stats(self):
        """Coleta estatísticas para exibir no encerramento."""
        try:
            # Tentar obter dados do backend
            dashboard_data = backend.get_dashboard_data()
            
            stats = {
                'sessions_today': dashboard_data.get('daily_stats', {}).get('sessions_completed', 0),
                'pages_read': dashboard_data.get('daily_stats', {}).get('pages_read', 0),
                'tasks_completed': dashboard_data.get('daily_stats', {}).get('tasks_completed', 0),
                'events_today': dashboard_data.get('upcoming_events', []),
                'streak_days': dashboard_data.get('daily_stats', {}).get('streak_days', 0),
                'total_books': len(dashboard_data.get('active_books', [])),
                'total_tasks': len(dashboard_data.get('pending_tasks', [])),
                'completed_tasks': sum(1 for task in dashboard_data.get('pending_tasks', []) 
                                     if task.get('completed', False)),
                'session_start': datetime.datetime.now()  # TODO: Registrar início real da sessão
            }
            
            return stats
            
        except:
            # Dados padrão em caso de erro
            return {
                'sessions_today': 0,
                'pages_read': 0,
                'tasks_completed': 0,
                'events_today': [],
                'streak_days': 0,
                'total_books': 0,
                'total_tasks': 0,
                'completed_tasks': 0,
                'session_start': None
            }
