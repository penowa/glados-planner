# src/cli/interactive/screens/dashboard_screen.py
"""
Dashboard principal do sistema GLaDOS Planner.
Agrupa todas as telas em categorias organizadas.
"""
import datetime
from typing import Dict, List, Tuple
from .base_screen import BaseScreen
from cli.integration.backend_integration import backend
from cli.theme import theme
from cli.icons import Icon, icon_text

class DashboardScreen(BaseScreen):
    """Dashboard principal com categorias organizadas."""
    
    def __init__(self):
        super().__init__()
        self.title = "Dashboard GLaDOS"
        self.selected_category = 0
        self.selected_item = 0
        self.showing_categories = True
        self.dashboard_data = {}
        self.last_refresh = None
        
        # Categorias organizadas com ícones
        self.categories = [
            {
                "name": "📚 Leitura",
                "icon": Icon.BOOK,
                "color": "primary",
                "screens": [
                    ("➕ Adicionar Livro", "new_book"),
                    ("📖 Sessão de Leitura", "reading"),
                    ("📚 Selecionar Livro", "book_selection"),
                    ("📊 Progresso", "statistics")
                ]
            },
            {
                "name": "⏰ Sessões",
                "icon": Icon.TIMER,
                "color": "accent",
                "screens": [
                    ("🎯 Tipo de Sessão", "session"),
                    ("🍅 Pomodoro", "pomodoro"),
                    ("📖 Leitura Focada", "reading"),
                    ("🔄 Revisão", None)  # TODO: Implementar
                ]
            },
            {
                "name": "📅 Planejamento",
                "icon": Icon.CALENDAR,
                "color": "secondary",
                "screens": [
                    ("✅ Check-in Diário", "daily_checkin"),
                    ("📋 Planejamento Semanal", "weekly_planning"),
                    ("🗓️ Configurar Agenda", "agenda_config"),
                    ("📝 Gerenciar Tarefas", "task_management")
                ]
            },
            {
                "name": "🚨 Sistema",
                "icon": Icon.ALERT,
                "color": "warning",
                "screens": [
                    ("⚠️ Modo Emergência", "emergency_mode"),
                    ("🤖 Consultar GLaDOS", "glados_query"),
                    ("⚙️ Configurações", "settings"),
                    ("📈 Estatísticas", "statistics")
                ]
            },
            {
                "name": "🆘 Ajuda",
                "icon": Icon.INFO,
                "color": "info",
                "screens": [
                    ("❓ Ajuda do Sistema", "help"),
                    ("ℹ️ Sobre", "help"),  # Redireciona para seção Sobre
                    ("🚪 Encerrar", "shutdown"),
                    ("📋 Tutorial", None)  # TODO: Implementar
                ]
            }
        ]
        
        # Atalhos rápidos
        self.quick_actions = [
            ("C", "Check-in rápido"),
            ("E", "Modo emergência"),
            ("P", "Iniciar Pomodoro"),
            ("R", "Recarregar dados"),
            ("S", "Sair do sistema")
        ]
    
    def show(self):
        """Exibe o dashboard e gerencia a navegação."""
        self._load_dashboard_data()
        
        while True:
            if self.showing_categories:
                self._render_categories()
            else:
                self._render_screens()
            
            key = self.keyboard_handler.wait_for_input()
            
            # Navegação global
            if key == Key.H:
                return 'goto:help'
            elif key == Key.S:
                return 'exit'
            elif key == Key.R:
                self._load_dashboard_data()
                continue
            elif key == Key.C:
                return 'goto:daily_checkin'
            elif key == Key.E:
                return 'goto:emergency_mode'
            elif key == Key.ESC:
                if not self.showing_categories:
                    self.showing_categories = True
                    self.selected_item = 0
                else:
                    return 'back'
            
            # Navegação no dashboard
            if self.showing_categories:
                self._handle_category_navigation(key)
            else:
                self._handle_screen_navigation(key)
    
    def _load_dashboard_data(self):
        """Carrega dados para o dashboard."""
        try:
            self.dashboard_data = backend.get_dashboard_data()
            self.last_refresh = datetime.datetime.now()
        except Exception as e:
            theme.print(f"❌ Erro ao carregar dados: {e}", style="error")
            self.dashboard_data = self._get_mock_dashboard_data()
    
    def _get_mock_dashboard_data(self):
        """Retorna dados mock para desenvolvimento."""
        return {
            'daily_goals': [
                {'title': 'Leitura: A República', 'completed': False, 'progress': 45},
                {'title': 'Escrita: Paper sobre Virtude', 'completed': False, 'progress': 60},
                {'title': 'Revisão: Flashcards Ética', 'completed': True, 'progress': 100}
            ],
            'upcoming_events': [
                {'time': '09:00-11:00', 'title': 'A República - Platão', 'type': 'leitura'},
                {'time': '14:00-16:00', 'title': 'Aula: Ética', 'type': 'aula'},
                {'time': '19:00-20:00', 'title': 'Paper: Virtude', 'type': 'escrita'}
            ],
            'alerts': [
                {'type': 'warning', 'message': 'Prova de Lógica em 3 dias'},
                {'type': 'info', 'message': 'Entrega do paper em 7 dias'}
            ],
            'daily_stats': {
                'tasks_completed': 3,
                'sessions_completed': 2,
                'pages_read': 25,
                'streak_days': 5
            },
            'active_books': [
                {'title': 'A República', 'author': 'Platão', 'progress': 45},
                {'title': 'Ética a Nicômaco', 'author': 'Aristóteles', 'progress': 30}
            ],
            'pending_tasks': [
                {'title': 'Revisar capítulo 3', 'priority': 'high'},
                {'title': 'Escrever resumo', 'priority': 'medium'},
                {'title': 'Criar flashcards', 'priority': 'low'}
            ]
        }
    
    def _render_categories(self):
        """Renderiza a tela de categorias."""
        theme.clear()
        
        # Cabeçalho com dados do sistema
        self._render_header()
        
        # Título
        theme.rule(f"[{self.title}]", style="accent")
        
        # Mensagem do dia
        self._render_daily_message()
        
        # Metas do dia
        self._render_daily_goals()
        
        # Categorias principais
        theme.print(f"\n{icon_text(Icon.MENU, 'Menu Principal:')}", style="primary")
        theme.print("=" * 60, style="dim")
        
        for i, category in enumerate(self.categories):
            prefix = "> " if i == self.selected_category else "  "
            icon = category.get('icon', Icon.INFO)
            color = category.get('color', 'primary')
            
            theme.print(f"{prefix}{icon_text(icon, category['name'])}", 
                       style=color if i == self.selected_category else "info")
        
        # Atalhos rápidos
        self._render_quick_actions()
        
        # Rodapé
        theme.print(f"\n{icon_text(Icon.INFO, 'Navegação:')}", style="dim")
        theme.print("  ↑↓: Navegar  Enter: Selecionar  ESC: Voltar/Sair  H: Ajuda", style="dim")
    
    def _render_screens(self):
        """Renderiza as telas dentro da categoria selecionada."""
        theme.clear()
        
        # Cabeçalho
        self._render_header()
        
        # Categoria atual
        category = self.categories[self.selected_category]
        theme.rule(f"[{category['name']}]", style=category['color'])
        
        # Telas disponíveis
        theme.print(f"\n{icon_text(Icon.LIST, 'Opções disponíveis:')}", style="primary")
        theme.print("=" * 60, style="dim")
        
        for i, (screen_name, screen_key) in enumerate(category['screens']):
            prefix = "> " if i == self.selected_item else "  "
            
            # Verificar se a tela está disponível
            if screen_key is None:
                style = "dim"
                suffix = " [Em desenvolvimento]"
            else:
                style = "primary" if i == self.selected_item else "info"
                suffix = ""
            
            theme.print(f"{prefix}{screen_name}{suffix}", style=style)
        
        # Descrição da seleção atual
        self._render_selection_description()
        
        # Rodapé
        theme.print(f"\n{icon_text(Icon.INFO, 'Navegação:')}", style="dim")
        theme.print("  ↑↓: Navegar  Enter: Selecionar  ESC: Voltar  B: Dashboard", style="dim")
    
    def _render_header(self):
        """Renderiza o cabeçalho do dashboard."""
        now = datetime.datetime.now()
        
        # Linha 1: Data e status
        date_str = now.strftime("%d/%m/%Y")
        time_str = now.strftime("%H:%M")
        
        if self.last_refresh:
            refresh_str = self.last_refresh.strftime("%H:%M:%S")
        else:
            refresh_str = "Nunca"
        
        theme.print(f"📅 {date_str} | 🕐 {time_str} | 🔄 {refresh_str}", style="dim")
        
        # Linha 2: Status do backend
        try:
            is_ready = backend.is_ready()
            status_icon = "✅" if is_ready else "⚠️"
            status_text = "Conectado" if is_ready else "Modo Simulação"
            theme.print(f"{status_icon} Backend: {status_text}", 
                       style="success" if is_ready else "warning")
        except:
            theme.print("⚠️ Backend: Indisponível", style="error")
    
    def _render_daily_message(self):
        """Renderiza a mensagem diária da GLaDOS."""
        messages = [
            "Bem-vindo de volta. Espero que tenha usado seu tempo livre de forma produtiva.",
            "Outro dia, outra oportunidade para fracassar de novas maneiras.",
            "O sistema detectou que você está atrasado. Como sempre.",
            "Você está aqui novamente. Vamos tentar não desperdiçar muito tempo hoje.",
            "Análise completa: Você precisa melhorar em tudo. Mas vamos começar devagar."
        ]
        
        import random
        message = random.choice(messages)
        
        theme.print(f"\n{icon_text(Icon.GLADOS, 'GLaDOS diz:')}", style="accent")
        theme.print(f"  \"{message}\"", style="info")
    
    def _render_daily_goals(self):
        """Renderiza as metas do dia."""
        daily_goals = self.dashboard_data.get('daily_goals', [])
        
        if daily_goals:
            completed = sum(1 for goal in daily_goals if goal.get('completed', False))
            total = len(daily_goals)
            
            theme.print(f"\n{icon_text(Icon.TARGET, f'Metas do Dia ({completed}/{total} concluídas):')}", style="primary")
            
            for goal in daily_goals[:3]:  # Mostrar apenas 3
                icon = "✅" if goal.get('completed', False) else "□"
                progress = goal.get('progress', 0)
                
                # Barra de progresso
                bar_length = 20
                filled = int(bar_length * progress / 100)
                bar = '█' * filled + '░' * (bar_length - filled)
                
                theme.print(f"  {icon} {goal.get('title', 'Sem título')}", style="info")
                if progress > 0 and progress < 100:
                    theme.print(f"     [{bar}] {progress}%", style="dim")
    
    def _render_quick_actions(self):
        """Renderiza os atalhos rápidos."""
        theme.print(f"\n{icon_text(Icon.ZAP, 'Atalhos Rápidos (tecla única):')}", style="primary")
        
        for key, description in self.quick_actions:
            theme.print(f"  {key}) {description}", style="dim")
    
    def _render_selection_description(self):
        """Renderiza descrição da seleção atual."""
        category = self.categories[self.selected_category]
        screens = category['screens']
        
        if self.selected_item < len(screens):
            screen_name, screen_key = screens[self.selected_item]
            
            descriptions = {
                'new_book': "Adicionar um novo livro ao sistema (PDF/EPUB/TXT)",
                'reading': "Iniciar uma sessão de leitura focada",
                'book_selection': "Selecionar e gerenciar livros",
                'session': "Escolher tipo de sessão de estudo",
                'pomodoro': "Timer Pomodoro com citações motivacionais",
                'daily_checkin': "Check-in diário com análise de humor",
                'weekly_planning': "Planejamento semanal com relatórios",
                'agenda_config': "Configurar agenda e compromissos",
                'task_management': "Gerenciar tarefas e prioridades",
                'emergency_mode': "Reorganização emergencial da agenda",
                'glados_query': "Consultar a GLaDOS sobre seus dados",
                'settings': "Configurações do sistema",
                'statistics': "Estatísticas detalhadas de produtividade",
                'help': "Ajuda e documentação do sistema",
                'shutdown': "Encerrar o sistema com estatísticas"
            }
            
            if screen_key in descriptions:
                theme.print(f"\n{icon_text(Icon.INFO, 'Descrição:')}", style="primary")
                theme.print(f"  {descriptions[screen_key]}", style="dim")
    
    def _handle_category_navigation(self, key):
        """Lida com navegação na tela de categorias."""
        if key == Key.UP:
            self.selected_category = (self.selected_category - 1) % len(self.categories)
        elif key == Key.DOWN:
            self.selected_category = (self.selected_category + 1) % len(self.categories)
        elif key == Key.ENTER:
            # Verificar se a categoria tem telas
            if self.categories[self.selected_category]['screens']:
                self.showing_categories = False
                self.selected_item = 0
        elif key == Key.P:
            # Atalho direto para Pomodoro
            return 'goto:pomodoro'
    
    def _handle_screen_navigation(self, key):
        """Lida com navegação na tela de telas."""
        category = self.categories[self.selected_category]
        screens = category['screens']
        
        if key == Key.UP:
            self.selected_item = (self.selected_item - 1) % len(screens)
        elif key == Key.DOWN:
            self.selected_item = (self.selected_item + 1) % len(screens)
        elif key == Key.ENTER:
            screen_name, screen_key = screens[self.selected_item]
            
            if screen_key is None:
                theme.print(f"\n⚠️  {screen_name} está em desenvolvimento.", style="warning")
                self.keyboard_handler.wait_for_input()
            else:
                # Navegar para a tela selecionada
                return f'goto:{screen_key}'
    
    def toggle_menu(self):
        """Alterna entre mostrar categorias e telas."""
        self.showing_categories = not self.showing_categories
