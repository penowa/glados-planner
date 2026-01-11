# src/cli/interactive/screens/weekly_planning_screen.py
"""
Tela de planejamento semanal com relatórios integrados.
"""
import datetime
from .base_screen import BaseScreen
from src.cli.theme import theme
from src.cli.icons import Icon, icon_text

class WeeklyPlanningScreen(BaseScreen):
    """Tela de planejamento semanal."""
    
    def __init__(self):
        super().__init__()
        self.title = "Planejamento Semanal"
    
    def show(self):
        selected_index = 0
        options = [
            ("📅 Visualizar semana atual", self.view_current_week),
            ("📝 Planejar próxima semana", self.plan_next_week),
            ("🎯 Definir metas semanais", self.set_weekly_goals),
            ("📊 Relatório da semana passada", self.last_week_report),
            ("🔄 Revisar e ajustar", self.review_adjust),
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
    
    def view_current_week(self):
        """Visualiza a semana atual."""
        theme.clear()
        theme.rule("[Semana Atual]")
        
        today = datetime.datetime.now()
        start_of_week = today - datetime.timedelta(days=today.weekday())
        
        theme.print(f"\n📅 Semana de {start_of_week.strftime('%d/%m')} a {(start_of_week + datetime.timedelta(days=6)).strftime('%d/%m/%Y')}", style="primary")
        theme.print("=" * 60, style="dim")
        
        # Dados de exemplo - TODO: Integrar com backend
        week_data = [
            {"day": "Segunda", "tasks": 4, "completed": 3, "focus": "Leitura"},
            {"day": "Terça", "tasks": 5, "completed": 5, "focus": "Escrita"},
            {"day": "Quarta", "tasks": 3, "completed": 2, "focus": "Revisão"},
            {"day": "Quinta", "tasks": 6, "completed": 4, "focus": "Projeto"},
            {"day": "Sexta", "tasks": 4, "completed": 1, "focus": "Leitura"},
            {"day": "Sábado", "tasks": 2, "completed": 0, "focus": "Descanso"},
            {"day": "Domingo", "tasks": 1, "completed": 0, "focus": "Planejamento"}
        ]
        
        for day_data in week_data:
            completion = (day_data['completed'] / day_data['tasks']) * 100 if day_data['tasks'] > 0 else 0
            bar = "█" * int(completion / 10) + "░" * (10 - int(completion / 10))
            
            theme.print(f"\n{day_data['day']}:", style="info")
            theme.print(f"  Tarefas: {day_data['completed']}/{day_data['tasks']} [{bar}] {completion:.0f}%", style="dim")
            theme.print(f"  Foco: {day_data['focus']}", style="dim")
        
        theme.print(f"\n{icon_text(Icon.INFO, 'Total da semana:')}", style="primary")
        total_tasks = sum(d['tasks'] for d in week_data)
        total_completed = sum(d['completed'] for d in week_data)
        total_completion = (total_completed / total_tasks * 100) if total_tasks > 0 else 0
        
        theme.print(f"  Tarefas: {total_completed}/{total_tasks} ({total_completion:.1f}%)", style="info")
        
        self.wait_for_exit()
    
    def plan_next_week(self):
        """Planejamento da próxima semana."""
        theme.clear()
        theme.rule("[Planejamento da Próxima Semana]")
        
        today = datetime.datetime.now()
        next_monday = today + datetime.timedelta(days=(7 - today.weekday()))
        
        theme.print(f"\n📅 Próxima semana: {next_monday.strftime('%d/%m/%Y')}", style="primary")
        theme.print("=" * 50, style="dim")
        
        # Áreas de foco
        theme.print(f"\n{icon_text(Icon.TASK, 'Áreas de foco:')}", style="info")
        focus_areas = []
        
        for i in range(1, 6):
            area = input(f"  Área {i} (deixe vazio para pular): ").strip()
            if not area:
                break
            focus_areas.append(area)
        
        # Metas por área
        weekly_goals = {}
        for area in focus_areas:
            theme.print(f"\n🎯 Metas para '{area}':", style="info")
            goals = []
            
            for j in range(1, 4):
                goal = input(f"  Meta {j}: ").strip()
                if not goal:
                    break
                goals.append(goal)
            
            weekly_goals[area] = goals
        
        # Blocos de tempo disponíveis
        theme.print(f"\n⏰ Blocos de tempo disponíveis:", style="info")
        time_blocks = {}
        
        days = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"]
        for day in days:
            blocks = input(f"  {day} (ex: '9-12,14-17'): ").strip()
            if blocks:
                time_blocks[day] = blocks
        
        # Revisão do planejamento
        theme.print(f"\n{icon_text(Icon.INFO, 'Resumo do planejamento:')}", style="primary")
        theme.print("=" * 50, style="dim")
        
        theme.print(f"\nÁreas de foco ({len(focus_areas)}):", style="info")
        for area in focus_areas:
            theme.print(f"  • {area}", style="dim")
        
        theme.print(f"\nMetas semanais:", style="info")
        for area, goals in weekly_goals.items():
            theme.print(f"  {area}:", style="dim")
            for goal in goals:
                theme.print(f"    • {goal}", style="dim")
        
        # Salvar planejamento
        theme.print(f"\n{icon_text(Icon.QUESTION, 'Salvar planejamento?')}", style="warning")
        confirm = input("(S/n): ").strip().lower()
        
        if confirm in ['s', 'sim', '']:
            # TODO: Salvar no backend
            theme.print(f"\n✅ {icon_text(Icon.SUCCESS, 'Planejamento salvo!')}", style="success")
        else:
            theme.print(f"\n{icon_text(Icon.INFO, 'Planejamento descartado.')}", style="warning")
        
        self.wait_for_exit()
    
    def set_weekly_goals(self):
        """Define metas semanais específicas."""
        theme.clear()
        theme.rule("[Metas Semanais]")
        theme.print("\nEm desenvolvimento...", style="warning")
        self.wait_for_exit()
    
    def last_week_report(self):
        """Gera relatório da semana passada."""
        theme.clear()
        theme.rule("[Relatório da Semana Passada]")
        theme.print("\nEm desenvolvimento...", style="warning")
        self.wait_for_exit()
    
    def review_adjust(self):
        """Revisa e ajusta o planejamento."""
        theme.clear()
        theme.rule("[Revisão e Ajuste]")
        theme.print("\nEm desenvolvimento...", style="warning")
        self.wait_for_exit()
