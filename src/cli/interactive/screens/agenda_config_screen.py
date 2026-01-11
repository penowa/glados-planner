# src/cli/interactive/screens/agenda_config_screen.py
"""
Tela de configuração de agenda (CRUD completo de compromissos).
Integra com AgendaManager.
"""
from .base_screen import BaseScreen
from src.cli.integration.backend_integration import backend
from src.cli.theme import theme
from src.cli.icons import Icon, icon_text
import datetime

class AgendaConfigScreen(BaseScreen):
    """Tela de configuração de agenda."""
    
    def __init__(self):
        super().__init__()
        self.title = "Configuração de Agenda"
    
    def show(self):
        selected_index = 0
        options = [
            ("➕ Adicionar Evento", self.add_event),
            ("✏️  Editar Evento", self.edit_event),
            ("🗑️  Remover Evento", self.remove_event),
            ("📋 Listar Eventos", self.list_events),
            ("🔄 Reorganizar Agenda", self.reorganize_agenda),
            ("⚙️  Configurações da Agenda", self.agenda_settings),
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
    
    def add_event(self):
        """Adiciona um novo evento à agenda."""
        theme.clear()
        theme.rule("[Adicionar Evento]")
        
        theme.print("\nPreencha os detalhes do evento:", style="primary")
        
        # Coletar informações
        title = input("Título do evento: ").strip()
        if not title:
            theme.print("❌ Título é obrigatório.", style="error")
            self.wait_for_exit()
            return
        
        # Data e hora
        event_date = input("Data (DD/MM/AAAA, deixe vazio para hoje): ").strip()
        if not event_date:
            event_date = datetime.datetime.now().strftime("%d/%m/%Y")
        
        start_time = input("Hora de início (HH:MM): ").strip()
        end_time = input("Hora de término (HH:MM): ").strip()
        
        # Tipo de evento
        theme.print("\nTipo de evento:", style="info")
        theme.print("  1) 👨‍🏫 Aula")
        theme.print("  2) 📚 Leitura")
        theme.print("  3) ✍️  Escrita")
        theme.print("  4) 🔁 Revisão")
        theme.print("  5) 🛒 Compromisso")
        theme.print("  6) 🏃 Atividade Física")
        theme.print("  7) 📞 Reunião")
        theme.print("  8) 🍽️  Refeição")
        theme.print("  9) 😴 Descanso")
        theme.print("  10) 🎯 Outro")
        
        event_type = input("\nEscolha (1-10): ").strip()
        type_map = {
            '1': 'class', '2': 'reading', '3': 'writing', '4': 'review',
            '5': 'appointment', '6': 'exercise', '7': 'meeting',
            '8': 'meal', '9': 'rest', '10': 'other'
        }
        
        event_type = type_map.get(event_type, 'other')
        
        # Prioridade
        priority = input("Prioridade (1-baixa, 2-média, 3-alta): ").strip()
        priority_map = {'1': 'low', '2': 'medium', '3': 'high'}
        priority = priority_map.get(priority, 'medium')
        
        # Descrição
        description = input("Descrição (opcional): ").strip()
        
        # Local
        location = input("Local (opcional): ").strip()
        
        # Notificações
        notifications = input("Minutos antes para notificar (0 para desativar): ").strip()
        notifications = int(notifications) if notifications.isdigit() else 0
        
        # Criar objeto de evento
        event_data = {
            'title': title,
            'date': event_date,
            'start_time': start_time,
            'end_time': end_time,
            'type': event_type,
            'priority': priority,
            'description': description,
            'location': location,
            'notifications': notifications,
            'is_flexible': priority != 'high'  # Eventos de baixa/média prioridade são flexíveis
        }
        
        # Confirmar
        theme.print(f"\n{icon_text(Icon.INFO, 'Resumo do evento:')}", style="primary")
        theme.print("=" * 50, style="dim")
        
        for key, value in event_data.items():
            if value:  # Mostrar apenas campos preenchidos
                theme.print(f"  {key.replace('_', ' ').title()}: {value}", style="info")
        
        theme.print(f"\n{icon_text(Icon.QUESTION, 'Adicionar evento à agenda?')}", style="warning")
        confirm = input("(S/n): ").strip().lower()
        
        if confirm in ['s', 'sim', '']:
            try:
                # Usar backend para adicionar evento
                result = backend.add_event(event_data)
                
                if result.get('success', False):
                    theme.print(f"\n✅ {icon_text(Icon.SUCCESS, 'Evento adicionado com sucesso!')}", style="success")
                    
                    # Verificar conflitos
                    conflicts = result.get('conflicts', [])
                    if conflicts:
                        theme.print(f"\n{icon_text(Icon.WARNING, 'Atenção: Conflitos detectados:')}", style="warning")
                        for conflict in conflicts:
                            theme.print(f"  • {conflict}", style="dim")
                    
                else:
                    theme.print(f"\n❌ {icon_text(Icon.ERROR, 'Falha ao adicionar evento:')}", style="error")
                    theme.print(f"  {result.get('error', 'Erro desconhecido')}", style="error")
                    
            except Exception as e:
                theme.print(f"\n❌ {icon_text(Icon.ERROR, 'Erro:')}", style="error")
                theme.print(f"  {str(e)}", style="error")
        
        else:
            theme.print(f"\n{icon_text(Icon.INFO, 'Operação cancelada.')}", style="warning")
        
        self.wait_for_exit()
    
    def edit_event(self):
        """Edita um evento existente."""
        theme.clear()
        theme.rule("[Editar Evento]")
        theme.print("\nEm desenvolvimento...", style="warning")
        self.wait_for_exit()
    
    def remove_event(self):
        """Remove um evento da agenda."""
        theme.clear()
        theme.rule("[Remover Evento]")
        theme.print("\nEm desenvolvimento...", style="warning")
        self.wait_for_exit()
    
    def list_events(self):
        """Lista todos os eventos da agenda."""
        theme.clear()
        theme.rule("[Eventos da Agenda]")
        
        try:
            # Obter eventos do backend
            events = backend.get_today_agenda()
            
            if not events:
                theme.print(f"\n{icon_text(Icon.INFO, 'Nenhum evento agendado para hoje.')}", style="info")
            else:
                theme.print(f"\n📅 Eventos agendados ({len(events)}):", style="primary")
                theme.print("=" * 60, style="dim")
                
                for i, event in enumerate(events, 1):
                    # Determinar ícone baseado no tipo
                    type_icons = {
                        'class': '👨‍🏫', 'reading': '📚', 'writing': '✍️',
                        'review': '🔁', 'appointment': '🛒', 'exercise': '🏃',
                        'meeting': '📞', 'meal': '🍽️', 'rest': '😴', 'other': '🎯'
                    }
                    
                    icon = type_icons.get(event.get('type', 'other'), '🎯')
                    time_str = f"{event.get('start_time', '')} - {event.get('end_time', '')}"
                    
                    theme.print(f"\n{i}. {icon} {event.get('title', 'Sem título')}", style="info")
                    theme.print(f"   ⏰ {time_str}", style="dim")
                    
                    if event.get('location'):
                        theme.print(f"   📍 {event.get('location')}", style="dim")
                    
                    if event.get('description'):
                        theme.print(f"   📝 {event.get('description')[:50]}...", style="dim")
                    
                    # Status
                    if event.get('completed', False):
                        theme.print(f"   ✅ Concluído", style="success")
                    else:
                        theme.print(f"   ⏳ Pendente", style="warning")
        
        except Exception as e:
            theme.print(f"\n❌ {icon_text(Icon.ERROR, 'Erro ao carregar eventos:')}", style="error")
            theme.print(f"  {str(e)}", style="error")
        
        self.wait_for_exit()
    
    def reorganize_agenda(self):
        """Reorganiza a agenda automaticamente."""
        theme.clear()
        theme.rule("[Reorganizar Agenda]")
        theme.print("\nEm desenvolvimento...", style="warning")
        self.wait_for_exit()
    
    def agenda_settings(self):
        """Configurações da agenda."""
        theme.clear()
        theme.rule("[Configurações da Agenda]")
        
        theme.print("\nConfigurações disponíveis:", style="primary")
        theme.print("=" * 50, style="dim")
        
        # TODO: Carregar configurações do backend
        settings = {
            'horario_inicio_dia': '08:00',
            'horario_fim_dia': '22:00',
            'blocos_padrao': '60',  # minutos
            'intervalo_entre_eventos': '15',
            'dias_trabalho': 'Seg-Sex',
            'notificacoes_ativas': True
        }
        
        for key, value in settings.items():
            theme.print(f"  {key.replace('_', ' ').title()}: {value}", style="info")
        
        theme.print(f"\n{icon_text(Icon.QUESTION, 'Editar configurações?')}", style="warning")
        edit = input("(S/n): ").strip().lower()
        
        if edit in ['s', 'sim', '']:
            theme.print("\nEm desenvolvimento...", style="warning")
        
        self.wait_for_exit()
