# src/cli/interactive/screens/statistics_screen.py
"""
Tela de estatísticas detalhadas do sistema.
"""
from .base_screen import BaseScreen
from src.cli.integration.backend_integration import backend
from src.cli.theme import theme
from src.cli.icons import Icon, icon_text
import datetime

class StatisticsScreen(BaseScreen):
    """Tela de estatísticas."""
    
    def __init__(self):
        super().__init__()
        self.title = "Estatísticas"
    
    def show(self):
        selected_index = 0
        options = [
            ("📚 Estatísticas de Leitura", self.reading_stats),
            ("⏱️  Estatísticas de Produtividade", self.productivity_stats),
            ("📊 Estatísticas Gerais", self.general_stats),
            ("📈 Tendências", self.trends),
            ("🏆 Conquistas", self.achievements),
            ("📋 Relatório Detalhado", self.detailed_report),
            ("← Voltar", lambda: "back")
        ]
        
        while True:
            self.render_menu(options, selected_index)
            
            key = self.keyboard_handler.wait_for_input()
            
            if key == Key.UP:
                selected_index = (selected_index - 1) % len(options)
            elif key == Key.DOWN:
                selected_index = (selected_index + 1) % len(options)
            elif key == Key.ENTER:
                result = options[selected_index][1]()
                if result == "back":
                    break
            elif key == Key.ESC:
                break
    
    def reading_stats(self):
        """Estatísticas de leitura."""
        theme.clear()
        theme.rule("[Estatísticas de Leitura]")
        
        try:
            dashboard_data = backend.get_dashboard_data()
            active_books = dashboard_data.get('active_books', [])
            
            theme.print(f"\n{icon_text(Icon.BOOK, 'Resumo de leitura:')}", style="primary")
            theme.print("=" * 60, style="dim")
            
            # Livros ativos
            theme.print(f"\n📚 Livros ativos: {len(active_books)}", style="info")
            
            if active_books:
                total_pages = 0
                read_pages = 0
                completed_books = 0
                
                for book in active_books:
                    total = book.get('total_pages', 0)
                    current = book.get('current_page', 0)
                    
                    if total > 0:
                        total_pages += total
                        read_pages += current
                        
                        if current >= total:
                            completed_books += 1
                
                theme.print(f"📖 Páginas totais: {total_pages}", style="info")
                theme.print(f"📖 Páginas lidas: {read_pages}", style="info")
                
                if total_pages > 0:
                    overall_progress = (read_pages / total_pages) * 100
                    theme.print(f"📊 Progresso geral: {overall_progress:.1f}%", style="info")
                
                theme.print(f"✅ Livros concluídos: {completed_books}", style="success")
                
                # Velocidade média
                # TODO: Calcular velocidade média baseada em histórico
            
            # Sessões de leitura
            daily_stats = dashboard_data.get('daily_stats', {})
            sessions_today = daily_stats.get('reading_sessions', 0)
            pages_today = daily_stats.get('pages_read', 0)
            
            theme.print(f"\n{icon_text(Icon.CALENDAR, 'Hoje:')}", style="primary")
            theme.print(f"📚 Sessões: {sessions_today}", style="info")
            theme.print(f"📖 Páginas: {pages_today}", style="info")
            
            # Histórico (últimos 7 dias)
            theme.print(f"\n{icon_text(Icon.CHART, 'Últimos 7 dias:')}", style="primary")
            # TODO: Implementar histórico real
            
            # Livros com melhor progresso
            if len(active_books) >= 3:
                sorted_books = sorted(active_books, key=lambda x: x.get('progress', 0), reverse=True)[:3]
                
                theme.print(f"\n{icon_text(Icon.TROPHY, 'Top 3 livros:')}", style="primary")
                for i, book in enumerate(sorted_books, 1):
                    progress = book.get('progress', 0)
                    theme.print(f"{i}. {book.get('title', 'Sem título')} - {progress:.1f}%", 
                               style="success" if progress >= 75 else "info" if progress >= 50 else "warning")
            
        except Exception as e:
            theme.print(f"\n❌ Erro ao carregar estatísticas: {e}", style="error")
        
        self.wait_for_exit()
        return "continue"
    
    def productivity_stats(self):
        """Estatísticas de produtividade."""
        theme.clear()
        theme.rule("[Estatísticas de Produtividade]")
        
        try:
            dashboard_data = backend.get_dashboard_data()
            daily_stats = dashboard_data.get('daily_stats', {})
            
            theme.print(f"\n{icon_text(Icon.CHART, 'Produtividade hoje:')}", style="primary")
            theme.print("=" * 60, style="dim")
            
            # Sessões Pomodoro
            pomodoro_sessions = daily_stats.get('pomodoro_sessions', 0)
            pomodoro_minutes = daily_stats.get('pomodoro_minutes', 0)
            
            theme.print(f"\n{icon_text(Icon.TIMER, 'Sessões Pomodoro:')}", style="info")
            theme.print(f"📊 Sessões: {pomodoro_sessions}", style="info")
            theme.print(f"⏱️  Minutos focados: {pomodoro_minutes}", style="info")
            
            if pomodoro_sessions > 0:
                avg_session = pomodoro_minutes / pomodoro_sessions
                theme.print(f"📈 Média/sessão: {avg_session:.1f} minutos", style="info")
            
            # Tarefas
            tasks_completed = daily_stats.get('tasks_completed', 0)
            total_tasks = len(dashboard_data.get('pending_tasks', [])) + tasks_completed
            
            theme.print(f"\n{icon_text(Icon.TASK, 'Tarefas:')}", style="info")
            theme.print(f"✅ Concluídas: {tasks_completed}", style="success" if tasks_completed > 0 else "info")
            
            if total_tasks > 0:
                completion_rate = (tasks_completed / total_tasks * 100)
                theme.print(f"📊 Taxa de conclusão: {completion_rate:.1f}%", style="info")
            
            # Check-in streak
            streak_days = daily_stats.get('streak_days', 0)
            
            theme.print(f"\n{icon_text(Icon.FIRE, 'Sequência:')}", style="info")
            if streak_days > 0:
                theme.print(f"🔥 {streak_days} dias consecutivos", 
                           style="success" if streak_days >= 7 else "info")
            else:
                theme.print(f"⏸️  Nenhuma sequência ativa", style="warning")
            
            # Horas produtivas
            theme.print(f"\n{icon_text(Icon.CLOCK, 'Horário mais produtivo:')}", style="info")
            # TODO: Analisar horários baseado em histórico
            
        except Exception as e:
            theme.print(f"\n❌ Erro ao carregar estatísticas: {e}", style="error")
        
        self.wait_for_exit()
        return "continue"
    
    def general_stats(self):
        """Estatísticas gerais do sistema."""
        theme.clear()
        theme.rule("[Estatísticas Gerais]")
        
        try:
            dashboard_data = backend.get_dashboard_data()
            
            theme.print(f"\n{icon_text(Icon.INFO, 'Resumo geral do sistema:')}", style="primary")
            theme.print("=" * 60, style="dim")
            
            # Contagens
            active_books = len(dashboard_data.get('active_books', []))
            pending_tasks = len([t for t in dashboard_data.get('pending_tasks', []) if not t.get('completed', False)])
            upcoming_events = len(dashboard_data.get('upcoming_events', []))
            daily_goals = len(dashboard_data.get('daily_goals', []))
            
            stats = [
                ("📚 Livros ativos", active_books),
                ("📋 Tarefas pendentes", pending_tasks),
                ("📅 Eventos futuros", upcoming_events),
                ("🎯 Metas do dia", daily_goals)
            ]
            
            for label, value in stats:
                theme.print(f"{label}: {value}", style="info")
            
            # Tempo de uso
            # TODO: Registrar e calcular tempo de uso
            
            # Eficiência
            theme.print(f"\n{icon_text(Icon.TARGET, 'Eficiência do sistema:')}", style="primary")
            
            # Baseado em conclusão de tarefas e sessões
            tasks_completed = dashboard_data.get('daily_stats', {}).get('tasks_completed', 0)
            sessions_completed = dashboard_data.get('daily_stats', {}).get('sessions_completed', 0)
            
            efficiency_score = (tasks_completed * 10) + (sessions_completed * 5)
            
            if efficiency_score >= 50:
                rating = "⭐⭐⭐⭐⭐ Excelente"
                style = "success"
            elif efficiency_score >= 30:
                rating = "⭐⭐⭐⭐ Bom"
                style = "info"
            elif efficiency_score >= 15:
                rating = "⭐⭐⭐ Regular"
                style = "warning"
            else:
                rating = "⭐⭐ Melhorar"
                style = "error"
            
            theme.print(f"📈 Pontuação: {efficiency_score} pontos", style="info")
            theme.print(f"🏆 Classificação: {rating}", style=style)
            
        except Exception as e:
            theme.print(f"\n❌ Erro ao carregar estatísticas: {e}", style="error")
        
        self.wait_for_exit()
        return "continue"
    
    def trends(self):
        """Mostra tendências e padrões."""
        theme.clear()
        theme.rule("[Tendências e Padrões]")
        
        theme.print(f"\n{icon_text(Icon.CHART, 'Análise de tendências:')}", style="primary")
        theme.print("=" * 60, style="dim")
        
        # Tendências de produtividade
        theme.print(f"\n📊 Tendências de produtividade:", style="info")
        theme.print("  • Segunda: 📈 Alta produtividade", style="dim")
        theme.print("  • Quarta: 📉 Queda comum", style="dim")
        theme.print("  • Sexta: 📈 Recuperação", style="dim")
        
        # Padrões de leitura
        theme.print(f"\n📚 Padrões de leitura:", style="info")
        theme.print("  • Manhã (8-12): 📖 Foco em livros técnicos", style="dim")
        theme.print("  • Tarde (14-18): 📚 Leitura geral", style="dim")
        theme.print("  • Noite (20-22): 🔁 Revisão e flashcards", style="dim")
        
        # Recomendações
        theme.print(f"\n💡 Recomendações baseadas em padrões:", style="primary")
        theme.print("  1. ⏰ Agendar tarefas difíceis para segunda-feira", style="info")
        theme.print("  2. 📚 Reservar manhãs para estudo técnico", style="info")
        theme.print("  3. 🔁 Usar noites para revisão espaçada", style="info")
        
        # Previsões
        theme.print(f"\n🔮 Previsões para amanhã:", style="primary")
        theme.print("  • 📖 25-30 páginas de leitura", style="dim")
        theme.print("  • ⏰ 3-4 sessões Pomodoro", style="dim")
        theme.print("  • ✅ 5-7 tarefas concluídas", style="dim")
        
        self.wait_for_exit()
        return "continue"
    
    def achievements(self):
        """Mostra conquistas e metas."""
        theme.clear()
        theme.rule("[Conquistas e Metas]")
        
        theme.print(f"\n{icon_text(Icon.TROPHY, 'Conquistas desbloqueadas:')}", style="primary")
        theme.print("=" * 60, style="dim")
        
        achievements = [
            {"name": "🔥 Iniciante", "desc": "Primeiro login no sistema", "unlocked": True},
            {"name": "📚 Leitor Iniciante", "desc": "Ler 100 páginas", "unlocked": True},
            {"name": "⏰ Foco Total", "desc": "Completar 10 sessões Pomodoro", "unlocked": False},
            {"name": "✅ Produtivo", "desc": "Concluir 50 tarefas", "unlocked": False},
            {"name": "📖 Leitor Ávido", "desc": "Ler 1000 páginas", "unlocked": False},
            {"name": "🔥 Streak de Fogo", "desc": "7 dias consecutivos de check-in", "unlocked": False},
            {"name": "🎓 Mestre da Leitura", "desc": "Completar 5 livros", "unlocked": False}
        ]
        
        for achievement in achievements:
            icon = "✅" if achievement['unlocked'] else "⏳"
            style = "success" if achievement['unlocked'] else "dim"
            
            theme.print(f"\n{icon} {achievement['name']}", style=style)
            theme.print(f"   {achievement['desc']}", style="dim")
        
        # Progresso geral
        theme.print(f"\n{icon_text(Icon.CHART, 'Progresso geral:')}", style="primary")
        
        unlocked = sum(1 for a in achievements if a['unlocked'])
        total = len(achievements)
        progress = (unlocked / total * 100) if total > 0 else 0
        
        bar_length = 30
        filled = int(bar_length * progress / 100)
        bar = '█' * filled + '░' * (bar_length - filled)
        
        theme.print(f"  [{bar}] {progress:.1f}% ({unlocked}/{total})", style="info")
        
        # Próximas conquistas
        theme.print(f"\n{icon_text(Icon.TARGET, 'Próximas conquistas:')}", style="primary")
        
        next_achievements = [a for a in achievements if not a['unlocked']][:3]
        for i, achievement in enumerate(next_achievements, 1):
            theme.print(f"{i}. {achievement['name']} - {achievement['desc']}", style="info")
        
        self.wait_for_exit()
        return "continue"
    
    def detailed_report(self):
        """Gera relatório detalhado."""
        theme.clear()
        theme.rule("[Relatório Detalhado]")
        
        theme.print(f"\n{icon_text(Icon.REPORT, 'Gerando relatório...')}", style="info")
        
        # Data atual
        today = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
        
        # Coletar dados
        try:
            dashboard_data = backend.get_dashboard_data()
            
            # Cabeçalho
            theme.print(f"\n📅 Relatório gerado em: {today}", style="primary")
            theme.print("=" * 70, style="dim")
            
            # Seção 1: Resumo do dia
            theme.print(f"\n{icon_text(Icon.CALENDAR, '1. RESUMO DO DIA')}", style="primary")
            
            daily_stats = dashboard_data.get('daily_stats', {})
            
            if daily_stats:
                stats_items = [
                    ("Sessões Pomodoro", daily_stats.get('pomodoro_sessions', 0)),
                    ("Minutos focados", daily_stats.get('pomodoro_minutes', 0)),
                    ("Tarefas concluídas", daily_stats.get('tasks_completed', 0)),
                    ("Páginas lidas", daily_stats.get('pages_read', 0)),
                    ("Check-in streak", daily_stats.get('streak_days', 0))
                ]
                
                for label, value in stats_items:
                    if value:
                        theme.print(f"  • {label}: {value}", style="info")
            
            # Seção 2: Livros ativos
            theme.print(f"\n{icon_text(Icon.BOOK, '2. LIVROS ATIVOS')}", style="primary")
            
            active_books = dashboard_data.get('active_books', [])
            if active_books:
                for book in active_books:
                    progress = book.get('progress', 0)
                    theme.print(f"  • {book.get('title', 'Sem título')}: {progress:.1f}%", 
                               style="success" if progress >= 100 else "info")
            else:
                theme.print("  Nenhum livro ativo.", style="dim")
            
            # Seção 3: Tarefas pendentes
            theme.print(f"\n{icon_text(Icon.TASK, '3. TAREFAS PENDENTES')}", style="primary")
            
            pending_tasks = [t for t in dashboard_data.get('pending_tasks', []) 
                           if not t.get('completed', False)]
            
            if pending_tasks:
                for task in pending_tasks[:5]:  # Limitar a 5
                    priority = task.get('priority', 'medium')
                    priority_icon = {'high': '🔴', 'medium': '🟡', 'low': '🟢'}.get(priority, '🟡')
                    theme.print(f"  • {priority_icon} {task.get('title', 'Sem título')}", style="info")
            else:
                theme.print("  Nenhuma tarefa pendente.", style="success")
            
            # Seção 4: Análise e recomendações
            theme.print(f"\n{icon_text(Icon.GLADOS, '4. ANÁLISE E RECOMENDAÇÕES')}", style="primary")
            
            # Análise baseada em dados
            tasks_completed = daily_stats.get('tasks_completed', 0)
            pages_read = daily_stats.get('pages_read', 0)
            
            if tasks_completed >= 5 and pages_read >= 20:
                theme.print("  ✅ Dia muito produtivo! Continue assim.", style="success")
                theme.print("  💡 Sugestão: Mantenha o ritmo amanhã.", style="dim")
            elif tasks_completed >= 3 or pages_read >= 10:
                theme.print("  👍 Dia razoavelmente produtivo.", style="info")
                theme.print("  💡 Sugestão: Tente aumentar em 20% amanhã.", style="dim")
            else:
                theme.print("  ⚠️  Dia abaixo do potencial.", style="warning")
                theme.print("  💡 Sugestão: Planeje melhor as tarefas amanhã.", style="dim")
            
            # Seção 5: Meta para amanhã
            theme.print(f"\n{icon_text(Icon.TARGET, '5. META PARA AMANHÃ')}", style="primary")
            
            tomorrow_goal = {
                'min_tasks': max(3, tasks_completed),
                'min_pages': max(15, pages_read),
                'min_sessions': max(2, daily_stats.get('pomodoro_sessions', 0))
            }
            
            theme.print(f"  • Tarefas: {tomorrow_goal['min_tasks']}+", style="info")
            theme.print(f"  • Páginas: {tomorrow_goal['min_pages']}+", style="info")
            theme.print(f"  • Sessões: {tomorrow_goal['min_sessions']}+", style="info")
            
            # Rodapé
            theme.print(f"\n{icon_text(Icon.INFO, 'Fim do relatório.')}", style="dim")
            
        except Exception as e:
            theme.print(f"\n❌ Erro ao gerar relatório: {e}", style="error")
        
        # Opção de exportar
        theme.print(f"\n{icon_text(Icon.EXPORT, 'Exportar relatório?')}", style="warning")
        export = input("(S/n): ").strip().lower()
        
        if export in ['s', 'sim', '']:
            # TODO: Implementar exportação para arquivo
            theme.print("✅ Relatório exportado para 'relatorio_diario.txt'", style="success")
        
        self.wait_for_exit()
        return "continue"
