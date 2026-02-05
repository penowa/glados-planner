"""
Card para exibição de agenda/tarefas - VERSÃO REFATORADA COM INTEGRAÇÃO COMPLETA
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QFrame, QCheckBox, QScrollArea,
    QProgressBar, QMenu, QToolButton
)
from PyQt6.QtCore import Qt, pyqtSignal, pyqtSlot, QTimer, QTime
from PyQt6.QtGui import QFont, QColor, QPainter, QPen, QAction, QCursor
import logging

from .base_card import PhilosophyCard

logger = logging.getLogger('GLaDOS.UI.AgendaCard')


class AgendaCard(PhilosophyCard):
    """Card completo para exibição de agenda com controller"""
    
    item_clicked = pyqtSignal(dict)
    item_completed = pyqtSignal(str, bool)
    navigate_to_agenda = pyqtSignal()
    quick_action = pyqtSignal(str, dict)  # action_name, data
    
    def __init__(self, agenda_controller=None, parent=None):
        """
        Args:
            agenda_controller: Controller da agenda
            parent: Parent widget
        """
        super().__init__(parent)
        
        self.controller = agenda_controller
        self.agenda_data = {}
        self.items = []
        self.completed_count = 0
        self.current_date = None
        
        self.setup_ui()
        self.setup_connections()
        self.setup_animations()
        
        # Timer para atualizações em tempo real
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_time_displays)
        self.update_timer.start(60000)  # 1 minuto
        
        logger.info("AgendaCard inicializado")
    
    def setup_ui(self):
        """Configura interface do card"""
        self.set_title('📅 Agenda do Dia')
        self.set_minimizable(True)
        self.set_draggable(True)
        
        # Cabeçalho com estatísticas
        header_widget = QWidget()
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(0, 0, 0, 10)
        
        # Estatísticas
        self.stats_widget = QWidget()
        stats_layout = QHBoxLayout(self.stats_widget)
        stats_layout.setSpacing(15)
        
        # Contadores
        self.total_label = QLabel("0")
        self.total_label.setObjectName("stat_number")
        self.total_desc = QLabel("Total")
        self.total_desc.setObjectName("stat_desc")
        
        self.completed_label = QLabel("0")
        self.completed_label.setObjectName("stat_number")
        self.completed_desc = QLabel("Concluídos")
        self.completed_desc.setObjectName("stat_desc")
        
        self.upcoming_label = QLabel("0")
        self.upcoming_label.setObjectName("stat_number")
        self.upcoming_desc = QLabel("Próximos")
        self.upcoming_desc.setObjectName("stat_desc")
        
        # Layout para cada estatística
        def create_stat_widget(number_label, desc_label):
            widget = QWidget()
            layout = QVBoxLayout(widget)
            layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(number_label)
            layout.addWidget(desc_label)
            return widget
        
        stats_layout.addWidget(create_stat_widget(self.total_label, self.total_desc))
        stats_layout.addWidget(create_stat_widget(self.completed_label, self.completed_desc))
        stats_layout.addWidget(create_stat_widget(self.upcoming_label, self.upcoming_desc))
        
        # Barra de progresso
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setObjectName("agenda_progress")
        
        # Hora atual e próximo evento
        self.time_widget = QWidget()
        time_layout = QVBoxLayout(self.time_widget)
        time_layout.setSpacing(5)
        
        self.current_time_label = QLabel()
        self.current_time_label.setObjectName("current_time")
        self.current_time_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        
        self.next_event_label = QLabel("Próximo: Nenhum")
        self.next_event_label.setObjectName("next_event")
        self.next_event_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        
        time_layout.addWidget(self.current_time_label)
        time_layout.addWidget(self.next_event_label)
        
        header_layout.addWidget(self.stats_widget)
        header_layout.addWidget(self.progress_bar, 1)
        header_layout.addWidget(self.time_widget)
        
        # Área de conteúdo
        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setSpacing(8)
        
        # Lista de itens com scroll
        self.items_container = QWidget()
        self.items_layout = QVBoxLayout(self.items_container)
        self.items_layout.setSpacing(6)
        self.items_layout.setContentsMargins(2, 2, 2, 2)
        
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_area.setWidget(self.items_container)
        self.scroll_area.setMinimumHeight(200)
        
        # Botões de ação
        self.actions_widget = QWidget()
        actions_layout = QHBoxLayout(self.actions_widget)
        actions_layout.setContentsMargins(0, 10, 0, 0)
        
        self.add_button = QToolButton()
        self.add_button.setText("➕ Adicionar")
        self.add_button.setObjectName("card_action_button")
        self.add_button.clicked.connect(self.on_add_event)
        
        self.view_all_button = QToolButton()
        self.view_all_button.setText("📋 Ver Todos")
        self.view_all_button.setObjectName("card_action_button")
        self.view_all_button.clicked.connect(self.on_view_all)
        
        self.menu_button = QToolButton()
        self.menu_button.setText("⋯")
        self.menu_button.setObjectName("card_menu_button")
        self.menu_button.clicked.connect(self.show_context_menu)
        
        actions_layout.addWidget(self.add_button)
        actions_layout.addWidget(self.view_all_button)
        actions_layout.addStretch()
        actions_layout.addWidget(self.menu_button)
        
        # Layout principal do conteúdo
        self.content_layout.addWidget(header_widget)
        self.content_layout.addWidget(self.scroll_area, 1)
        self.content_layout.addWidget(self.actions_widget)
        
        self.set_content(self.content_widget)
        
        # Estado inicial
        self.show_loading_state()
    
    def setup_connections(self):
        """Configura conexões com o controller"""
        if self.controller:
            self.controller.agenda_loaded.connect(self.on_agenda_loaded)
            self.controller.event_added.connect(self.on_event_added)
            self.controller.event_updated.connect(self.on_event_updated)
            self.controller.event_completed.connect(self.on_event_completed)
            
            # Solicita dados iniciais
            self.load_initial_data()
    
    def load_initial_data(self):
        """Carrega dados iniciais da agenda"""
        from datetime import datetime
        self.current_date = datetime.now().strftime("%Y-%m-%d")
        
        if self.controller:
            try:
                # Usar método síncrono para carregamento inicial
                events = self.controller.load_agenda(self.current_date)
                self.on_agenda_loaded(events)
            except Exception as e:
                logger.error(f"Erro ao carregar dados iniciais: {e}")
                self.show_error_state("Erro ao carregar agenda")
    
    def show_loading_state(self):
        """Mostra estado de carregamento"""
        self.clear_items()
        
        loading_widget = QWidget()
        loading_layout = QVBoxLayout(loading_widget)
        loading_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        loading_label = QLabel("Carregando agenda...")
        loading_label.setObjectName("loading_label")
        
        loading_layout.addWidget(loading_label)
        self.items_layout.addWidget(loading_widget)
        
        # Atualiza estatísticas
        self.total_label.setText("--")
        self.completed_label.setText("--")
        self.upcoming_label.setText("--")
        self.progress_bar.setValue(0)
    
    def show_empty_state(self):
        """Mostra estado vazio"""
        self.clear_items()
        
        empty_widget = QWidget()
        empty_layout = QVBoxLayout(empty_widget)
        empty_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        empty_icon = QLabel("📅")
        empty_icon.setObjectName("empty_icon")
        empty_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        empty_label = QLabel("Nenhum evento hoje")
        empty_label.setObjectName("empty_label")
        
        empty_sublabel = QLabel("Adicione eventos para começar")
        empty_sublabel.setObjectName("empty_sublabel")
        
        empty_layout.addWidget(empty_icon)
        empty_layout.addWidget(empty_label)
        empty_layout.addWidget(empty_sublabel)
        
        self.items_layout.addWidget(empty_widget)
        
        # Atualiza estatísticas
        self.total_label.setText("0")
        self.completed_label.setText("0")
        self.upcoming_label.setText("0")
        self.progress_bar.setValue(0)
    
    def show_error_state(self, message):
        """Mostra estado de erro"""
        self.clear_items()
        
        error_widget = QWidget()
        error_layout = QVBoxLayout(error_widget)
        error_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        error_icon = QLabel("⚠️")
        error_icon.setObjectName("error_icon")
        error_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        error_label = QLabel(message)
        error_label.setObjectName("error_label")
        
        retry_button = QPushButton("Tentar novamente")
        retry_button.setObjectName("retry_button")
        retry_button.clicked.connect(self.refresh)
        
        error_layout.addWidget(error_icon)
        error_layout.addWidget(error_label)
        error_layout.addWidget(retry_button)
        
        self.items_layout.addWidget(error_widget)
    
    def clear_items(self):
        """Remove todos os itens da lista"""
        while self.items_layout.count():
            child = self.items_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
    
    @pyqtSlot(list)
    def on_agenda_loaded(self, events):
        """Atualiza o card com os eventos do dia"""
        self.items = events
        
        if not events:
            self.show_empty_state()
            return
        
        self.clear_items()
        
        # Ordena eventos por horário
        events.sort(key=lambda e: e.get('start', ''))
        
        # Filtra eventos concluídos e próximos
        completed_events = [e for e in events if e.get('completed', False)]
        upcoming_events = [e for e in events if not e.get('completed', False)]
        
        # Atualiza estatísticas
        total_count = len(events)
        completed_count = len(completed_events)
        upcoming_count = len(upcoming_events)
        
        self.total_label.setText(str(total_count))
        self.completed_label.setText(str(completed_count))
        self.upcoming_label.setText(str(upcoming_count))
        
        # Atualiza barra de progresso
        progress = int((completed_count / total_count * 100)) if total_count > 0 else 0
        self.progress_bar.setValue(progress)
        
        # Mostra apenas os próximos 5 eventos
        display_events = upcoming_events[:5]
        
        for event in display_events:
            item_widget = self.create_event_widget(event)
            self.items_layout.addWidget(item_widget)
        
        # Se houver mais eventos, mostra contador
        if len(upcoming_events) > 5:
            more_label = QLabel(f"... e mais {len(upcoming_events) - 5} eventos")
            more_label.setObjectName("more_events")
            more_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.items_layout.addWidget(more_label)
        
        # Atualiza próximo evento
        self.update_next_event(upcoming_events)
        
        logger.debug(f"Agenda atualizada: {total_count} eventos")
    
    @pyqtSlot(dict)
    def on_event_added(self, event_data):
        """Quando novo evento é adicionado"""
        logger.info(f"Evento adicionado: {event_data.get('title')}")
        
        # Recarrega agenda para refletir mudança
        self.refresh()
    
    @pyqtSlot(str, dict)
    def on_event_updated(self, event_id, update_data):
        """Quando evento é atualizado"""
        logger.debug(f"Evento atualizado: {event_id}, {update_data}")
        
        # Atualiza evento na lista local
        for event in self.items:
            if event['id'] == event_id:
                event.update(update_data)
                break
        
        # Atualiza interface sem recarregar tudo
        self.update_event_display(event_id, update_data)
    
    @pyqtSlot(str, bool)
    def on_event_completed(self, event_id, completed):
        """Quando evento é marcado como concluído"""
        logger.debug(f"Evento {event_id} concluído: {completed}")
        
        # Atualiza evento na lista local
        for event in self.items:
            if event['id'] == event_id:
                event['completed'] = completed
                break
        
        # Atualiza visual do item específico
        for i in range(self.items_layout.count()):
            item_widget = self.items_layout.itemAt(i).widget()
            if item_widget and hasattr(item_widget, 'event_id'):
                if item_widget.event_id == event_id:
                    item_widget.set_completed(completed)
                    break
        
        # Atualiza estatísticas
        self.update_stats()
    
    def create_event_widget(self, event_data):
        """Cria widget para um evento"""
        widget = AgendaEventWidget(event_data)
        widget.clicked.connect(lambda: self.item_clicked.emit(event_data))
        widget.completed_changed.connect(
            lambda event_id, completed: self.on_item_completed(event_id, completed)
        )
        
        return widget
    
    def update_event_display(self, event_id, updates):
        """Atualiza display de um evento específico"""
        for i in range(self.items_layout.count()):
            item_widget = self.items_layout.itemAt(i).widget()
            if item_widget and hasattr(item_widget, 'event_id'):
                if item_widget.event_id == event_id:
                    # Atualiza propriedades do widget se necessário
                    if 'completed' in updates:
                        item_widget.set_completed(updates['completed'])
                    break
        
        # Atualiza estatísticas
        self.update_stats()
    
    def update_stats(self):
        """Atualiza estatísticas do card"""
        if not self.items:
            return
        
        completed_events = [e for e in self.items if e.get('completed', False)]
        upcoming_events = [e for e in self.items if not e.get('completed', False)]
        
        total_count = len(self.items)
        completed_count = len(completed_events)
        upcoming_count = len(upcoming_events)
        
        self.total_label.setText(str(total_count))
        self.completed_label.setText(str(completed_count))
        self.upcoming_label.setText(str(upcoming_count))
        
        progress = int((completed_count / total_count * 100)) if total_count > 0 else 0
        self.progress_bar.setValue(progress)
        
        # Atualiza próximo evento
        self.update_next_event(upcoming_events)
    
    def update_next_event(self, upcoming_events):
        """Atualiza informação do próximo evento"""
        if not upcoming_events:
            self.next_event_label.setText("Próximo: Nenhum")
            return
        
        next_event = upcoming_events[0]
        event_time = next_event.get('start_time', '')
        event_title = next_event.get('title', '')
        
        self.next_event_label.setText(f"Próximo: {event_time} - {event_title[:20]}")
    
    def update_time_displays(self):
        """Atualiza displays de tempo"""
        current_time = QTime.currentTime().toString("HH:mm")
        self.current_time_label.setText(current_time)
        
        # Atualiza próximo evento a cada hora
        if QTime.currentTime().minute() == 0:
            self.update_stats()
    
    def on_add_event(self):
        """Adiciona novo evento"""
        self.quick_action.emit("add_event", {})
    
    def on_view_all(self):
        """Navega para view completa da agenda"""
        self.navigate_to_agenda.emit()
    
    def show_context_menu(self):
        """Mostra menu de contexto"""
        menu = QMenu(self)
        
        refresh_action = QAction("🔄 Atualizar", self)
        refresh_action.triggered.connect(self.refresh)
        
        today_action = QAction("📅 Hoje", self)
        today_action.triggered.connect(self.show_today)
        
        tomorrow_action = QAction("⏭️ Amanhã", self)
        tomorrow_action.triggered.connect(self.show_tomorrow)
        
        mark_all_completed = QAction("✅ Concluir Todos", self)
        mark_all_completed.triggered.connect(self.mark_all_completed)
        
        emergency_mode = QAction("🚨 Modo Emergência", self)
        emergency_mode.triggered.connect(self.activate_emergency_mode)
        
        menu.addAction(refresh_action)
        menu.addSeparator()
        menu.addAction(today_action)
        menu.addAction(tomorrow_action)
        menu.addSeparator()
        menu.addAction(mark_all_completed)
        menu.addAction(emergency_mode)
        
        menu.exec(QCursor.pos())
    
    def refresh(self):
        """Recarrega agenda"""
        if self.controller:
            try:
                events = self.controller.load_agenda(self.current_date)
                self.on_agenda_loaded(events)
            except Exception as e:
                logger.error(f"Erro ao recarregar agenda: {e}")
                self.show_error_state("Erro ao recarregar")
    
    def show_today(self):
        """Mostra agenda de hoje"""
        from datetime import datetime
        self.current_date = datetime.now().strftime("%Y-%m-%d")
        self.refresh()
    
    def show_tomorrow(self):
        """Mostra agenda de amanhã"""
        from datetime import datetime, timedelta
        self.current_date = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        self.refresh()
    
    def mark_all_completed(self):
        """Marca todos os eventos como concluídos"""
        if not self.controller or not self.items:
            return
        
        for event in self.items:
            if not event.get('completed', False):
                # Usa método síncrono do controller
                success = self.controller.toggle_event_completion(event['id'], True)
                if not success:
                    logger.error(f"Falha ao concluir evento {event['id']}")
    
    def activate_emergency_mode(self):
        """Ativa modo emergência"""
        self.quick_action.emit("emergency_mode", {})
    
    def on_item_completed(self, event_id, completed):
        """Quando item é marcado como concluído"""
        if self.controller:
            # Usa método síncrono do controller
            success = self.controller.toggle_event_completion(event_id, completed)
            
            if not success:
                logger.error(f"Falha ao atualizar evento {event_id}")
                # Reverte visualmente se falhar
                for i in range(self.items_layout.count()):
                    item_widget = self.items_layout.itemAt(i).widget()
                    if item_widget and hasattr(item_widget, 'event_id'):
                        if item_widget.event_id == event_id:
                            item_widget.checkbox.blockSignals(True)
                            item_widget.checkbox.setChecked(not completed)
                            item_widget.checkbox.blockSignals(False)
                            break


class AgendaEventWidget(QWidget):
    """Widget individual para evento da agenda"""
    
    clicked = pyqtSignal(dict)
    completed_changed = pyqtSignal(str, bool)  # event_id, completed
    
    def __init__(self, event_data, parent=None):
        super().__init__(parent)
        self.event_data = event_data
        self.event_id = event_data.get('id', '')
        
        self.setup_ui()
        self.setup_connections()
        
        # Tooltip com detalhes
        self.setToolTip(self.create_tooltip())
    
    def setup_ui(self):
        """Configura interface do widget"""
        self.setObjectName("agenda_event_widget")
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(12)
        
        # Checkbox de conclusão
        self.checkbox = QCheckBox()
        self.checkbox.setChecked(self.event_data.get('completed', False))
        self.checkbox.setFixedSize(20, 20)
        self.checkbox.setToolTip("Marcar como concluído")
        
        # Indicador de tipo/cor
        self.color_indicator = QLabel()
        self.color_indicator.setFixedSize(8, 30)
        self.color_indicator.setStyleSheet(f"""
            background-color: {self.event_data.get('color', '#9B9B9B')};
            border-radius: 4px;
        """)
        
        # Informações do evento
        info_widget = QWidget()
        info_layout = QVBoxLayout(info_widget)
        info_layout.setContentsMargins(0, 0, 0, 0)
        info_layout.setSpacing(4)
        
        # Linha superior: tempo e título
        top_layout = QHBoxLayout()
        
        self.time_label = QLabel(self.event_data.get('start_time', ''))
        self.time_label.setObjectName("event_time")
        self.time_label.setFixedWidth(50)
        
        self.title_label = QLabel(self.event_data.get('title', 'Sem título'))
        self.title_label.setObjectName("event_title")
        
        top_layout.addWidget(self.time_label)
        top_layout.addWidget(self.title_label, 1)  # stretch
        
        # Linha inferior: tipo e duração
        bottom_layout = QHBoxLayout()
        
        self.type_label = QLabel(self.event_data.get('type', 'casual').title())
        self.type_label.setObjectName("event_type")
        
        duration = self.event_data.get('duration_minutes', 60)
        self.duration_label = QLabel(f"{duration} min")
        self.duration_label.setObjectName("event_duration")
        
        bottom_layout.addWidget(self.type_label)
        bottom_layout.addStretch()
        bottom_layout.addWidget(self.duration_label)
        
        info_layout.addLayout(top_layout)
        info_layout.addLayout(bottom_layout)
        
        # Prioridade
        priority = self.event_data.get('priority', 2)
        if priority >= 4:
            priority_icon = QLabel("⚠️")
            priority_icon.setToolTip("Alta prioridade")
            priority_icon.setFixedWidth(20)
        else:
            priority_icon = QLabel()
            priority_icon.setFixedWidth(20)
        
        layout.addWidget(self.checkbox)
        layout.addWidget(self.color_indicator)
        layout.addWidget(info_widget, 1)  # stretch
        layout.addWidget(priority_icon)
        
        # Aplica estilo de concluído se necessário
        if self.event_data.get('completed', False):
            self.set_completed(True)
    
    def setup_connections(self):
        """Configura conexões"""
        self.checkbox.stateChanged.connect(self.on_checkbox_changed)
    
    def on_checkbox_changed(self, state):
        """Quando checkbox é alterado"""
        completed = (state == Qt.CheckState.Checked.value)
        self.completed_changed.emit(self.event_id, completed)
        self.set_completed(completed)
    
    def set_completed(self, completed):
        """Marca item como completo/incompleto"""
        if completed:
            self.title_label.setStyleSheet("text-decoration: line-through; color: #888;")
            self.time_label.setStyleSheet("text-decoration: line-through; color: #888;")
            self.type_label.setStyleSheet("color: #888;")
            self.duration_label.setStyleSheet("color: #888;")
            self.checkbox.setToolTip("Marcar como não concluído")
        else:
            self.title_label.setStyleSheet("")
            self.time_label.setStyleSheet("")
            self.type_label.setStyleSheet("")
            self.duration_label.setStyleSheet("")
            self.checkbox.setToolTip("Marcar como concluído")
    
    def create_tooltip(self):
        """Cria tooltip com detalhes do evento"""
        lines = [
            f"<b>{self.event_data.get('title', 'Sem título')}</b>",
            f"Horário: {self.event_data.get('start_time', '')} - {self.event_data.get('end_time', '')}",
            f"Duração: {self.event_data.get('duration_minutes', 60)} minutos",
            f"Tipo: {self.event_data.get('type', 'casual')}",
            f"Prioridade: {self.event_data.get('priority', 2)}",
        ]
        
        if self.event_data.get('description'):
            lines.append(f"Descrição: {self.event_data.get('description')}")
        
        if self.event_data.get('discipline'):
            lines.append(f"Disciplina: {self.event_data.get('discipline')}")
        
        return "<br>".join(lines)
    
    def mousePressEvent(self, event):
        """Quando widget é clicado"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.event_data)
        super().mousePressEvent(event)