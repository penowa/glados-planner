# src/cli/interactive/screens/task_management_screen.py
"""
Tela de gerenciamento de tarefas (CRUD completo).
"""
from .base_screen import BaseScreen
from cli.integration.backend_integration import backend
from cli.theme import theme
from cli.icons import Icon, icon_text
import datetime

class TaskManagementScreen(BaseScreen):
    """Tela de gerenciamento de tarefas."""
    
    def __init__(self):
        super().__init__()
        self.title = "Gerenciamento de Tarefas"
        self.tasks = []
    
    def show(self):
        self._load_tasks()
        
        selected_index = 0
        options = [
            ("➕ Adicionar Tarefa", self.add_task),
            ("📋 Listar Tarefas", self.list_tasks),
            ("✅ Concluir Tarefa", self.complete_task),
            ("✏️  Editar Tarefa", self.edit_task),
            ("🗑️  Remover Tarefa", self.remove_task),
            ("📊 Estatísticas", self.task_statistics),
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
                # Recarregar tarefas após ação
                self._load_tasks()
            elif key == Key.ESC:
                break
    
    def _load_tasks(self):
        """Carrega tarefas do backend."""
        try:
            dashboard_data = backend.get_dashboard_data()
            self.tasks = dashboard_data.get('pending_tasks', [])
        except:
            self.tasks = []
    
    def add_task(self):
        """Adiciona uma nova tarefa."""
        theme.clear()
        theme.rule("[Adicionar Tarefa]")
        
        theme.print(f"\n{icon_text(Icon.ADD, 'Nova tarefa:')}", style="primary")
        
        # Coletar informações
        title = input("Título da tarefa: ").strip()
        if not title:
            theme.print("❌ Título é obrigatório.", style="error")
            self.wait_for_exit()
            return "continue"
        
        description = input("Descrição (opcional): ").strip()
        
        # Prioridade
        theme.print(f"\n{icon_text(Icon.WARNING, 'Prioridade:')}", style="info")
        theme.print("  1) 🔴 Alta (urgente e importante)")
        theme.print("  2) 🟡 Média (importante, não urgente)")
        theme.print("  3) 🟢 Baixa (nem urgente, nem importante)")
        
        priority_choice = input("\nEscolha (1-3, padrão=2): ").strip()
        priority_map = {'1': 'high', '2': 'medium', '3': 'low'}
        priority = priority_map.get(priority_choice, 'medium')
        
        # Categoria
        theme.print(f"\n{icon_text(Icon.CATEGORY, 'Categoria:')}", style="info")
        theme.print("  1) 📚 Estudo")
        theme.print("  2) 💼 Trabalho")
        theme.print("  3) 🏠 Pessoal")
        theme.print("  4) 🛒 Compras")
        theme.print("  5) 🏃 Saúde")
        theme.print("  6) 🎯 Outro")
        
        category_choice = input("\nEscolha (1-6): ").strip()
        category_map = {
            '1': 'study', '2': 'work', '3': 'personal',
            '4': 'shopping', '5': 'health', '6': 'other'
        }
        category = category_map.get(category_choice, 'other')
        
        # Data de vencimento
        due_date = input("\nData de vencimento (DD/MM/AAAA, deixe vazio para sem data): ").strip()
        
        # Estimativa de tempo
        time_estimate = input("Estimativa de tempo (minutos, opcional): ").strip()
        
        # Criar objeto de tarefa
        task_data = {
            'title': title,
            'description': description,
            'priority': priority,
            'category': category,
            'due_date': due_date if due_date else None,
            'time_estimate': int(time_estimate) if time_estimate.isdigit() else None,
            'created_at': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'completed': False
        }
        
        # Confirmar
        theme.print(f"\n{icon_text(Icon.INFO, 'Resumo da tarefa:')}", style="primary")
        theme.print("=" * 50, style="dim")
        
        for key, value in task_data.items():
            if value is not None:
                theme.print(f"  {key.replace('_', ' ').title()}: {value}", style="info")
        
        theme.print(f"\n{icon_text(Icon.QUESTION, 'Adicionar tarefa?')}", style="warning")
        confirm = input("(S/n): ").strip().lower()
        
        if confirm in ['s', 'sim', '']:
            try:
                # TODO: Implementar método de adição no backend
                # backend.add_task(task_data)
                theme.print(f"\n✅ {icon_text(Icon.SUCCESS, 'Tarefa adicionada!')}", style="success")
            except Exception as e:
                theme.print(f"\n❌ {icon_text(Icon.ERROR, 'Erro ao adicionar tarefa:')}", style="error")
                theme.print(f"  {str(e)}", style="error")
        else:
            theme.print(f"\n{icon_text(Icon.INFO, 'Operação cancelada.')}", style="warning")
        
        self.wait_for_exit()
        return "continue"
    
    def list_tasks(self):
        """Lista todas as tarefas."""
        theme.clear()
        theme.rule("[Lista de Tarefas]")
        
        if not self.tasks:
            theme.print(f"\n{icon_text(Icon.INFO, 'Nenhuma tarefa pendente.')}", style="info")
        else:
            # Filtrar tarefas não concluídas
            pending_tasks = [t for t in self.tasks if not t.get('completed', False)]
            
            if not pending_tasks:
                theme.print(f"\n{icon_text(Icon.SUCCESS, 'Todas as tarefas concluídas!')}", style="success")
            else:
                theme.print(f"\n{icon_text(Icon.TASK, 'Tarefas pendentes:')} ({len(pending_tasks)})", style="primary")
                theme.print("=" * 70, style="dim")
                
                for i, task in enumerate(pending_tasks, 1):
                    # Ícone de prioridade
                    priority_icons = {'high': '🔴', 'medium': '🟡', 'low': '🟢'}
                    priority_icon = priority_icons.get(task.get('priority', 'medium'), '🟡')
                    
                    # Data de vencimento
                    due_info = ""
                    if task.get('due_date'):
                        due_info = f" | 📅 {task.get('due_date')}"
                    
                    # Estimativa de tempo
                    time_info = ""
                    if task.get('time_estimate'):
                        time_info = f" | ⏰ {task.get('time_estimate')}min"
                    
                    theme.print(f"\n{i}. {priority_icon} {task.get('title', 'Sem título')}", style="info")
                    
                    if task.get('description'):
                        theme.print(f"   📝 {task.get('description')[:60]}...", style="dim")
                    
                    theme.print(f"   🏷️  {task.get('category', 'outro')}{due_info}{time_info}", style="dim")
        
        # Tarefas concluídas
        completed_tasks = [t for t in self.tasks if t.get('completed', False)]
        if completed_tasks:
            theme.print(f"\n{icon_text(Icon.SUCCESS, 'Tarefas concluídas:')} ({len(completed_tasks)})", style="success")
            theme.print("=" * 70, style="dim")
            
            for i, task in enumerate(completed_tasks[-5:], 1):  # Últimas 5
                theme.print(f"{i}. ✅ {task.get('title', 'Sem título')}", style="dim")
        
        self.wait_for_exit()
        return "continue"
    
    def complete_task(self):
        """Marca uma tarefa como concluída."""
        theme.clear()
        theme.rule("[Concluir Tarefa]")
        
        # Filtrar tarefas não concluídas
        pending_tasks = [t for t in self.tasks if not t.get('completed', False)]
        
        if not pending_tasks:
            theme.print(f"\n{icon_text(Icon.INFO, 'Nenhuma tarefa pendente para concluir.')}", style="info")
            self.wait_for_exit()
            return "continue"
        
        theme.print(f"\n{icon_text(Icon.TASK, 'Selecione a tarefa para concluir:')}", style="primary")
        
        for i, task in enumerate(pending_tasks, 1):
            theme.print(f"{i}. {task.get('title', 'Sem título')}", style="info")
        
        choice = input("\nNúmero da tarefa (ou 0 para cancelar): ").strip()
        
        if choice == '0':
            return "continue"
        
        if choice.isdigit() and 1 <= int(choice) <= len(pending_tasks):
            task = pending_tasks[int(choice)-1]
            
            # Marcar como concluída
            task['completed'] = True
            task['completed_at'] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            theme.print(f"\n✅ {icon_text(Icon.SUCCESS, f'Tarefa "{task.get("title")}" concluída!')}", style="success")
            
            # TODO: Salvar no backend
            
            # Perguntar sobre tempo real
            actual_time = input("\nTempo real gasto (minutos, opcional): ").strip()
            if actual_time.isdigit():
                task['actual_time'] = int(actual_time)
                theme.print(f"⏱️  Tempo registrado: {actual_time} minutos", style="info")
            
            # Sugerir próxima ação
            theme.print(f"\n{icon_text(Icon.INFO, 'Próxima tarefa sugerida:')}", style="primary")
            # TODO: Sugerir próxima tarefa baseada em prioridade
            
        else:
            theme.print("❌ Seleção inválida.", style="error")
        
        self.wait_for_exit()
        return "continue"
    
    def edit_task(self):
        """Edita uma tarefa existente."""
        theme.clear()
        theme.rule("[Editar Tarefa]")
        theme.print("\nEm desenvolvimento...", style="warning")
        self.wait_for_exit()
        return "continue"
    
    def remove_task(self):
        """Remove uma tarefa."""
        theme.clear()
        theme.rule("[Remover Tarefa]")
        theme.print("\nEm desenvolvimento...", style="warning")
        self.wait_for_exit()
        return "continue"
    
    def task_statistics(self):
        """Mostra estatísticas de tarefas."""
        theme.clear()
        theme.rule("[Estatísticas de Tarefas]")
        
        if not self.tasks:
            theme.print(f"\n{icon_text(Icon.INFO, 'Nenhuma tarefa registrada.')}", style="info")
            self.wait_for_exit()
            return "continue"
        
        # Calcular estatísticas
        total_tasks = len(self.tasks)
        completed_tasks = sum(1 for t in self.tasks if t.get('completed', False))
        pending_tasks = total_tasks - completed_tasks
        
        completion_rate = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0
        
        # Tempo total estimado vs real
        total_estimated = sum(t.get('time_estimate', 0) for t in self.tasks)
        total_actual = sum(t.get('actual_time', 0) for t in self.tasks)
        
        theme.print(f"\n{icon_text(Icon.CHART, 'Estatísticas gerais:')}", style="primary")
        theme.print("=" * 50, style="dim")
        
        theme.print(f"📋 Total de tarefas: {total_tasks}", style="info")
        theme.print(f"✅ Concluídas: {completed_tasks}", style="success")
        theme.print(f"⏳ Pendentes: {pending_tasks}", style="warning")
        theme.print(f"📊 Taxa de conclusão: {completion_rate:.1f}%", style="info")
        
        if total_estimated > 0:
            theme.print(f"\n{icon_text(Icon.TIMER, 'Tempo:')}", style="primary")
            theme.print(f"⏱️  Estimado total: {total_estimated} minutos", style="info")
            
            if total_actual > 0:
                accuracy = (total_actual / total_estimated * 100) if total_estimated > 0 else 0
                theme.print(f"⏱️  Real total: {total_actual} minutos", style="info")
                theme.print(f"🎯 Precisão: {accuracy:.1f}%", 
                           style="success" if 80 <= accuracy <= 120 else "warning")
        
        # Distribuição por prioridade
        priority_counts = {'high': 0, 'medium': 0, 'low': 0}
        for task in self.tasks:
            priority = task.get('priority', 'medium')
            if priority in priority_counts:
                priority_counts[priority] += 1
        
        theme.print(f"\n{icon_text(Icon.WARNING, 'Distribuição por prioridade:')}", style="primary")
        for priority, count in priority_counts.items():
            if count > 0:
                percentage = (count / total_tasks * 100)
                theme.print(f"  {priority.title()}: {count} ({percentage:.1f}%)", style="info")
        
        # Distribuição por categoria
        category_counts = {}
        for task in self.tasks:
            category = task.get('category', 'other')
            category_counts[category] = category_counts.get(category, 0) + 1
        
        if category_counts:
            theme.print(f"\n{icon_text(Icon.CATEGORY, 'Distribuição por categoria:')}", style="primary")
            for category, count in sorted(category_counts.items(), key=lambda x: x[1], reverse=True)[:5]:
                percentage = (count / total_tasks * 100)
                theme.print(f"  {category.title()}: {count} ({percentage:.1f}%)", style="info")
        
        self.wait_for_exit()
        return "continue"
