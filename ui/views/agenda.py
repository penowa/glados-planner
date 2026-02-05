"""
View da agenda inteligente com navegação - VERSÃO COMPLETA
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame, QGridLayout,
    QTableWidget, QTableWidgetItem, QHeaderView, QListWidget, QListWidgetItem,
    QDialog, QFormLayout, QLineEdit, QDateTimeEdit, QComboBox, QTextEdit,
    QMessageBox, QSplitter, QTabWidget, QCalendarWidget, QSpinBox,
    QGroupBox, QRadioButton, QButtonGroup, QProgressBar, QToolBar
)
from PyQt6.QtCore import Qt, pyqtSignal, pyqtSlot, QDateTime, QDate, QTimer
from PyQt6.QtGui import QFont, QColor, QBrush, QIcon, QPalette, QAction
import logging
from datetime import datetime, timedelta

logger = logging.getLogger('GLaDOS.UI.AgendaView')


class AgendaView(QWidget):
    """View completa da agenda inteligente"""
    
    # Sinais
    navigate_to = pyqtSignal(str)
    
    def __init__(self, agenda_controller=None):
        super().__init__()
        self.controller = agenda_controller
        self.current_date = QDate.currentDate()
        self.selected_event = None
        
        self.setup_ui()
        self.setup_connections()
        self.setup_toolbar()
        
        # Carrega dados iniciais
        self.load_initial_data()
        
        logger.info("AgendaView inicializada")
    
    def setup_ui(self):
        """Configura interface da agenda"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Toolbar
        self.toolbar = QToolBar()
        self.toolbar.setObjectName("agenda_toolbar")
        main_layout.addWidget(self.toolbar)
        
        # Splitter principal
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Painel esquerdo: Calendário e controles
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(16, 16, 16, 16)
        left_layout.setSpacing(20)
        
        # Controles de data
        date_controls = QWidget()
        date_layout = QHBoxLayout(date_controls)
        
        self.prev_day_btn = QPushButton("◀")
        self.prev_day_btn.setObjectName("nav_button")
        self.prev_day_btn.setFixedWidth(40)
        
        self.date_label = QLabel(self.current_date.toString("dddd, d 'de' MMMM"))
        self.date_label.setObjectName("current_date")
        self.date_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.next_day_btn = QPushButton("▶")
        self.next_day_btn.setObjectName("nav_button")
        self.next_day_btn.setFixedWidth(40)
        
        self.today_btn = QPushButton("Hoje")
        self.today_btn.setObjectName("today_button")
        
        date_layout.addWidget(self.prev_day_btn)
        date_layout.addWidget(self.date_label, 1)
        date_layout.addWidget(self.next_day_btn)
        date_layout.addWidget(self.today_btn)
        
        # Calendário
        self.calendar = QCalendarWidget()
        self.calendar.setSelectedDate(self.current_date)
        self.calendar.setGridVisible(True)
        self.calendar.setObjectName("agenda_calendar")
        
        # Estatísticas rápidas
        stats_group = QGroupBox("📊 Estatísticas do Dia")
        stats_layout = QVBoxLayout()
        
        self.total_events_label = QLabel("Total: 0")
        self.completed_events_label = QLabel("Concluídos: 0")
        self.productivity_label = QLabel("Produtividade: 0%")
        
        self.productivity_bar = QProgressBar()
        self.productivity_bar.setRange(0, 100)
        self.productivity_bar.setTextVisible(True)
        
        stats_layout.addWidget(self.total_events_label)
        stats_layout.addWidget(self.completed_events_label)
        stats_layout.addWidget(self.productivity_label)
        stats_layout.addWidget(self.productivity_bar)
        
        stats_group.setLayout(stats_layout)
        
        # Ações rápidas
        quick_actions = QWidget()
        quick_layout = QVBoxLayout(quick_actions)
        quick_layout.setSpacing(10)
        
        self.add_event_btn = QPushButton("➕ Adicionar Evento")
        self.add_event_btn.setObjectName("primary_button")
        
        self.find_slot_btn = QPushButton("🔍 Encontrar Slot")
        self.find_slot_btn.setObjectName("secondary_button")
        
        self.emergency_btn = QPushButton("🚨 Modo Emergência")
        self.emergency_btn.setObjectName("emergency_button")
        
        quick_layout.addWidget(self.add_event_btn)
        quick_layout.addWidget(self.find_slot_btn)
        quick_layout.addWidget(self.emergency_btn)
        quick_layout.addStretch()
        
        left_layout.addWidget(date_controls)
        left_layout.addWidget(self.calendar)
        left_layout.addWidget(stats_group)
        left_layout.addWidget(quick_actions)
        
        # Painel direito: Tabela e detalhes
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(16, 16, 16, 16)
        right_layout.setSpacing(20)
        
        # Tabs
        self.tab_widget = QTabWidget()
        
        # Tab 1: Agenda do Dia
        day_tab = QWidget()
        day_layout = QVBoxLayout(day_tab)
        
        # Tabela de eventos
        self.events_table = QTableWidget()
        self.events_table.setColumnCount(6)
        self.events_table.setHorizontalHeaderLabels([
            "",  # Checkbox
            "Hora", 
            "Título", 
            "Tipo", 
            "Prioridade", 
            "Duração"
        ])
        self.events_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.events_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.events_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.events_table.setAlternatingRowColors(True)
        
        day_layout.addWidget(self.events_table)
        
        # Tab 2: Prazos
        deadlines_tab = QWidget()
        deadlines_layout = QVBoxLayout(deadlines_tab)
        
        self.deadlines_list = QListWidget()
        self.deadlines_list.setObjectName("deadlines_list")
        
        deadlines_layout.addWidget(self.deadlines_list)
        
        # Tab 3: Otimizações
        optimizations_tab = QWidget()
        optimizations_layout = QVBoxLayout(optimizations_tab)
        
        self.optimizations_list = QListWidget()
        self.optimizations_list.setObjectName("optimizations_list")
        
        optimizations_layout.addWidget(self.optimizations_list)
        
        self.tab_widget.addTab(day_tab, "📅 Agenda do Dia")
        self.tab_widget.addTab(deadlines_tab, "⏳ Prazos")
        self.tab_widget.addTab(optimizations_tab, "💡 Otimizações")
        
        # Painel de detalhes
        details_group = QGroupBox("📝 Detalhes do Evento")
        details_layout = QVBoxLayout()
        
        self.details_widget = QWidget()
        self.details_layout = QVBoxLayout(self.details_widget)
        
        self.event_title_label = QLabel("Nenhum evento selecionado")
        self.event_title_label.setObjectName("event_title")
        
        self.event_time_label = QLabel()
        self.event_time_label.setObjectName("event_time")
        
        self.event_description_label = QLabel()
        self.event_description_label.setObjectName("event_description")
        self.event_description_label.setWordWrap(True)
        
        # Botões de ação do evento
        event_actions = QWidget()
        event_actions_layout = QHBoxLayout(event_actions)
        
        self.edit_event_btn = QPushButton("✏️ Editar")
        self.edit_event_btn.setObjectName("secondary_button")
        self.edit_event_btn.setEnabled(False)
        
        self.delete_event_btn = QPushButton("🗑️ Excluir")
        self.delete_event_btn.setObjectName("danger_button")
        self.delete_event_btn.setEnabled(False)
        
        self.complete_event_btn = QPushButton("✅ Concluir")
        self.complete_event_btn.setObjectName("success_button")
        self.complete_event_btn.setEnabled(False)
        
        event_actions_layout.addWidget(self.edit_event_btn)
        event_actions_layout.addWidget(self.delete_event_btn)
        event_actions_layout.addWidget(self.complete_event_btn)
        
        self.details_layout.addWidget(self.event_title_label)
        self.details_layout.addWidget(self.event_time_label)
        self.details_layout.addWidget(self.event_description_label)
        self.details_layout.addWidget(event_actions)
        self.details_layout.addStretch()
        
        details_layout.addWidget(self.details_widget)
        details_group.setLayout(details_layout)
        
        right_layout.addWidget(self.tab_widget, 3)  # 3 partes de 4
        right_layout.addWidget(details_group, 1)    # 1 parte de 4
        
        # Configura splitter
        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setSizes([300, 700])
        
        main_layout.addWidget(splitter)
        
        # Status bar
        self.status_label = QLabel("Pronto")
        self.status_label.setObjectName("status_label")
        main_layout.addWidget(self.status_label)
    
    def setup_toolbar(self):
        """Configura toolbar"""
        # Ações
        self.back_action = QAction("← Voltar", self)
        self.back_action.triggered.connect(lambda: self.navigate_to.emit('dashboard'))
        
        self.refresh_action = QAction("🔄 Atualizar", self)
        self.refresh_action.triggered.connect(self.refresh)
        
        self.weekly_view_action = QAction("📅 Vista Semanal", self)
        self.weekly_view_action.triggered.connect(self.show_weekly_view)
        
        self.monthly_view_action = QAction("📆 Vista Mensal", self)
        self.monthly_view_action.triggered.connect(self.show_monthly_view)
        
        self.print_action = QAction("🖨️ Imprimir", self)
        self.print_action.triggered.connect(self.print_agenda)
        
        self.export_action = QAction("📤 Exportar", self)
        self.export_action.triggered.connect(self.export_agenda)
        
        self.toolbar.addAction(self.back_action)
        self.toolbar.addSeparator()
        self.toolbar.addAction(self.refresh_action)
        self.toolbar.addAction(self.weekly_view_action)
        self.toolbar.addAction(self.monthly_view_action)
        self.toolbar.addSeparator()
        self.toolbar.addAction(self.print_action)
        self.toolbar.addAction(self.export_action)
    
    def setup_connections(self):
        """Configura conexões"""
        # Conexões de data
        self.prev_day_btn.clicked.connect(self.previous_day)
        self.next_day_btn.clicked.connect(self.next_day)
        self.today_btn.clicked.connect(self.go_to_today)
        self.calendar.clicked.connect(self.on_calendar_clicked)
        
        # Conexões de botões
        self.add_event_btn.clicked.connect(self.add_event)
        self.find_slot_btn.clicked.connect(self.find_free_slot)
        self.emergency_btn.clicked.connect(self.activate_emergency_mode)
        
        # Conexões da tabela
        self.events_table.itemClicked.connect(self.on_event_selected)
        self.events_table.cellDoubleClicked.connect(self.on_event_double_clicked)
        
        # Conexões dos botões de ação
        self.edit_event_btn.clicked.connect(self.edit_selected_event)
        self.delete_event_btn.clicked.connect(self.delete_selected_event)
        self.complete_event_btn.clicked.connect(self.complete_selected_event)
        
        # Conexões do controller
        if self.controller:
            self.controller.agenda_loaded.connect(self.on_agenda_loaded)
            self.controller.deadlines_loaded.connect(self.on_deadlines_loaded)
            self.controller.optimizations_loaded.connect(self.on_optimizations_loaded)
            self.controller.event_added.connect(self.on_event_added)
            self.controller.event_updated.connect(self.on_event_updated_with_id)

    
    def load_initial_data(self):
        """Carrega dados iniciais"""
        if self.controller:
            date_str = self.current_date.toString("yyyy-MM-dd")
            self.controller.load_agenda(date_str)
            self.controller.load_upcoming_deadlines()
            self.controller.load_optimizations()
    
    def refresh(self):
        """Recarrega todos os dados"""
        self.status_label.setText("Atualizando...")
        
        if self.controller:
            date_str = self.current_date.toString("yyyy-MM-dd")
            self.controller.load_agenda(date_str)
            self.controller.load_upcoming_deadlines()
            self.controller.load_optimizations()
        
        self.status_label.setText("Atualizado")
        QTimer.singleShot(2000, lambda: self.status_label.setText("Pronto"))
    
    def previous_day(self):
        """Vai para o dia anterior"""
        self.current_date = self.current_date.addDays(-1)
        self.update_date_display()
        self.load_agenda_for_date()
    
    def next_day(self):
        """Vai para o próximo dia"""
        self.current_date = self.current_date.addDays(1)
        self.update_date_display()
        self.load_agenda_for_date()
    
    def go_to_today(self):
        """Vai para hoje"""
        self.current_date = QDate.currentDate()
        self.calendar.setSelectedDate(self.current_date)
        self.update_date_display()
        self.load_agenda_for_date()
    
    def on_calendar_clicked(self, date):
        """Quando data é clicada no calendário"""
        self.current_date = date
        self.update_date_display()
        self.load_agenda_for_date()
    
    def update_date_display(self):
        """Atualiza display da data"""
        self.date_label.setText(self.current_date.toString("dddd, d 'de' MMMM"))
        self.calendar.setSelectedDate(self.current_date)
    
    def load_agenda_for_date(self):
        """Carrega agenda para a data atual"""
        if self.controller:
            date_str = self.current_date.toString("yyyy-MM-dd")
            self.controller.load_agenda(date_str)
    
    @pyqtSlot(list)
    def on_agenda_loaded(self, events):
        """Atualiza tabela com eventos do dia"""
        self.events_table.setRowCount(len(events))
        
        for row, event in enumerate(events):
            # Checkbox de conclusão
            checkbox_item = QTableWidgetItem()
            checkbox_item.setCheckState(
                Qt.CheckState.Checked if event.get('completed', False) 
                else Qt.CheckState.Unchecked
            )
            
            # Hora
            time_item = QTableWidgetItem(event.get('start_time', ''))
            
            # Título
            title_item = QTableWidgetItem(event.get('title', 'Sem título'))
            
            # Tipo
            type_item = QTableWidgetItem(event.get('type', '').title())
            
            # Prioridade
            priority = event.get('priority', 2)
            priority_text = {
                1: "Baixa", 2: "Média", 3: "Alta", 4: "Fixo", 5: "Bloqueio"
            }.get(priority, "Média")
            priority_item = QTableWidgetItem(priority_text)
            
            # Cor baseada na prioridade
            if priority >= 4:
                priority_item.setForeground(QBrush(QColor('#FF6B6B')))
            elif priority == 3:
                priority_item.setForeground(QBrush(QColor('#FFD166')))
            
            # Duração
            duration_item = QTableWidgetItem(f"{event.get('duration_minutes', 0)} min")
            
            self.events_table.setItem(row, 0, checkbox_item)
            self.events_table.setItem(row, 1, time_item)
            self.events_table.setItem(row, 2, title_item)
            self.events_table.setItem(row, 3, type_item)
            self.events_table.setItem(row, 4, priority_item)
            self.events_table.setItem(row, 5, duration_item)
            
            # Cor da linha baseada no tipo
            color = QColor(event.get('color', '#9B9B9B'))
            color.setAlpha(30)  # Transparência
            for col in range(6):
                item = self.events_table.item(row, col)
                if item:
                    item.setBackground(QBrush(color))
        
        # Atualiza estatísticas
        self.update_statistics(events)
    
    def update_statistics(self, events):
        """Atualiza estatísticas do dia"""
        total = len(events)
        completed = sum(1 for e in events if e.get('completed', False))
        productivity = int((completed / total * 100)) if total > 0 else 0
        
        self.total_events_label.setText(f"Total: {total}")
        self.completed_events_label.setText(f"Concluídos: {completed}")
        self.productivity_label.setText(f"Produtividade: {productivity}%")
        self.productivity_bar.setValue(productivity)
    
    @pyqtSlot(list)
    def on_deadlines_loaded(self, deadlines):
        """Atualiza lista de prazos"""
        self.deadlines_list.clear()
        
        for deadline in deadlines:
            days_until = deadline.get('days_until', 0)
            
            if days_until == 0:
                text = f"⚡ HOJE: {deadline.get('title')} ({deadline.get('time')})"
                color = '#FF6B6B'
            elif days_until <= 2:
                text = f"⚠️ {days_until}d: {deadline.get('title')} ({deadline.get('date')})"
                color = '#FFD166'
            else:
                text = f"⏳ {days_until}d: {deadline.get('title')} ({deadline.get('date')})"
                color = '#50E3C2'
            
            item = QListWidgetItem(text)
            item.setData(Qt.ItemDataRole.UserRole, deadline)
            item.setForeground(QBrush(QColor(color)))
            
            self.deadlines_list.addItem(item)
    
    @pyqtSlot(list)
    def on_optimizations_loaded(self, optimizations):
        """Atualiza lista de otimizações"""
        self.optimizations_list.clear()
        
        for opt in optimizations:
            text = f"{opt.get('type', 'Sugestão').title()}: {opt.get('message', '')}"
            
            item = QListWidgetItem(text)
            item.setData(Qt.ItemDataRole.UserRole, opt)
            
            # Ícone baseado no tipo
            if opt.get('type') == 'overload':
                item.setIcon(QIcon("⚠️"))
                item.setForeground(QBrush(QColor('#FF6B6B')))
            elif opt.get('type') == 'back_to_back':
                item.setIcon(QIcon("🔄"))
                item.setForeground(QBrush(QColor('#FFD166')))
            elif opt.get('type') == 'balance':
                item.setIcon(QIcon("⚖️"))
                item.setForeground(QBrush(QColor('#4A90E2')))
            
            self.optimizations_list.addItem(item)
    
    @pyqtSlot(dict)
    def on_event_added(self, event_data):
        """Quando novo evento é adicionado"""
        self.status_label.setText(f"Evento adicionado: {event_data.get('title')}")
        QMessageBox.information(self, "Sucesso", "Evento adicionado com sucesso!")
    
    @pyqtSlot(str, dict)
    def on_event_updated_with_id(self, event_id, update_data):
        """Quando evento é atualizado (com ID)"""
        self.status_label.setText(f"Evento '{event_id}' atualizado")
    
    def on_event_selected(self, item):
        """Quando evento é selecionado na tabela"""
        row = item.row()
        event_id = self.get_event_id_from_row(row)
        
        if event_id:
            # Encontra evento completo
            for event in self.get_current_events():
                if event.get('id') == event_id:
                    self.selected_event = event
                    self.show_event_details(event)
                    break
    
    def get_event_id_from_row(self, row):
        """Obtém ID do evento a partir da linha"""
        title_item = self.events_table.item(row, 2)
        if title_item:
            # Em um sistema real, teríamos o ID armazenado
            # Por enquanto, usamos o título como referência
            return title_item.text()
        return None
    
    def get_current_events(self):
        """Retorna lista atual de eventos (simulado)"""
        # Em um sistema real, isso viria do controller
        return []
    
    def show_event_details(self, event):
        """Mostra detalhes do evento selecionado"""
        self.event_title_label.setText(event.get('title', 'Sem título'))
        
        time_text = f"{event.get('start_time', '')} - {event.get('end_time', '')}"
        self.event_time_label.setText(f"⏰ {time_text}")
        
        desc = event.get('description', 'Sem descrição')
        self.event_description_label.setText(f"📝 {desc}")
        
        # Habilita botões
        self.edit_event_btn.setEnabled(True)
        self.delete_event_btn.setEnabled(True)
        self.complete_event_btn.setEnabled(True)
        
        # Ajusta texto do botão de conclusão
        if event.get('completed', False):
            self.complete_event_btn.setText("↪️ Reabrir")
        else:
            self.complete_event_btn.setText("✅ Concluir")
    
    def on_event_double_clicked(self, row, column):
        """Quando evento é duplo-clicado"""
        self.edit_selected_event()
    
    def add_event(self):
        """Abre diálogo para adicionar evento"""
        dialog = AddEventDialog(self.controller, self.current_date, self)
        if dialog.exec():
            self.refresh()
    
    def edit_selected_event(self):
        """Edita evento selecionado"""
        if not self.selected_event:
            QMessageBox.warning(self, "Aviso", "Selecione um evento primeiro.")
            return
        
        dialog = EditEventDialog(self.controller, self.selected_event, self)
        if dialog.exec():
            self.refresh()
    
    def delete_selected_event(self):
        """Exclui evento selecionado"""
        if not self.selected_event:
            return
        
        reply = QMessageBox.question(
            self, "Confirmar Exclusão",
            f"Tem certeza que deseja excluir '{self.selected_event.get('title')}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            if self.controller:
                self.controller.update_event(
                    self.selected_event['id'],
                    {'deleted': True}
                )
            self.refresh()
    
    def complete_selected_event(self):
        """Marca evento como concluído/reaberto"""
        if not self.selected_event:
            return
        
        completed = not self.selected_event.get('completed', False)
        
        if self.controller:
            self.controller.toggle_event_completion(
                self.selected_event['id'],
                completed
            )
        
        self.refresh()
    
    def find_free_slot(self):
        """Encontra slot livre"""
        dialog = FindSlotDialog(self.controller, self.current_date, self)
        dialog.exec()
    
    def activate_emergency_mode(self):
        """Ativa modo emergência"""
        dialog = EmergencyModeDialog(self.controller, self)
        dialog.exec()
    
    def show_weekly_view(self):
        """Mostra vista semanal"""
        QMessageBox.information(self, "Em Desenvolvimento", 
                              "Vista semanal em desenvolvimento.")
    
    def show_monthly_view(self):
        """Mostra vista mensal"""
        QMessageBox.information(self, "Em Desenvolvimento", 
                              "Vista mensal em desenvolvimento.")
    
    def print_agenda(self):
        """Imprime agenda"""
        QMessageBox.information(self, "Em Desenvolvimento", 
                              "Impressão em desenvolvimento.")
    
    def export_agenda(self):
        """Exporta agenda"""
        QMessageBox.information(self, "Em Desenvolvimento", 
                              "Exportação em desenvolvimento.")
    
    def on_view_activated(self):
        """Chamado quando a view é ativada"""
        logger.info("AgendaView ativada")
        self.go_to_today()
    
    def cleanup(self):
        """Limpeza antes de fechar"""
        pass


# ====== DIÁLOGOS ======

class AddEventDialog(QDialog):
    """Diálogo para adicionar evento"""
    
    def __init__(self, controller, default_date, parent=None):
        super().__init__(parent)
        self.controller = controller
        self.default_date = default_date
        
        self.setWindowTitle("➕ Adicionar Evento")
        self.setModal(True)
        self.setMinimumWidth(500)
        
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Formulário
        form_layout = QFormLayout()
        
        self.title_input = QLineEdit()
        self.title_input.setPlaceholderText("Título do evento")
        form_layout.addRow("Título:", self.title_input)
        
        # Data e hora
        datetime_widget = QWidget()
        datetime_layout = QHBoxLayout(datetime_widget)
        
        self.date_input = QDateTimeEdit()
        self.date_input.setDate(self.default_date)
        self.date_input.setCalendarPopup(True)
        self.date_input.setDisplayFormat("dd/MM/yyyy")
        
        self.start_time = QDateTimeEdit()
        self.start_time.setTime(QTime(9, 0))
        self.start_time.setDisplayFormat("HH:mm")
        
        self.end_time = QDateTimeEdit()
        self.end_time.setTime(QTime(10, 0))
        self.end_time.setDisplayFormat("HH:mm")
        
        datetime_layout.addWidget(QLabel("Data:"))
        datetime_layout.addWidget(self.date_input)
        datetime_layout.addWidget(QLabel("Das:"))
        datetime_layout.addWidget(self.start_time)
        datetime_layout.addWidget(QLabel("às:"))
        datetime_layout.addWidget(self.end_time)
        
        form_layout.addRow("Agendamento:", datetime_widget)
        
        # Tipo e prioridade
        type_priority_widget = QWidget()
        type_priority_layout = QHBoxLayout(type_priority_widget)
        
        self.type_combo = QComboBox()
        self.type_combo.addItems([
            "leitura", "revisao", "producao", "aula", 
            "orientacao", "lazer", "refeicao", "sono", "casual"
        ])
        
        self.priority_combo = QComboBox()
        self.priority_combo.addItems(["Baixa", "Média", "Alta", "Fixo", "Bloqueio"])
        self.priority_combo.setCurrentIndex(1)  # Média
        
        type_priority_layout.addWidget(QLabel("Tipo:"))
        type_priority_layout.addWidget(self.type_combo, 1)
        type_priority_layout.addWidget(QLabel("Prioridade:"))
        type_priority_layout.addWidget(self.priority_combo)
        
        form_layout.addRow("Categoria:", type_priority_widget)
        
        # Descrição
        self.description_input = QTextEdit()
        self.description_input.setMaximumHeight(100)
        self.description_input.setPlaceholderText("Descrição do evento...")
        form_layout.addRow("Descrição:", self.description_input)
        
        # Disciplina (opcional)
        self.discipline_input = QLineEdit()
        self.discipline_input.setPlaceholderText("Ex: Filosofia, Matemática")
        form_layout.addRow("Disciplina:", self.discipline_input)
        
        layout.addLayout(form_layout)
        
        # Botões
        button_layout = QHBoxLayout()
        
        save_button = QPushButton("💾 Salvar")
        save_button.setObjectName("primary_button")
        save_button.clicked.connect(self.save_event)
        
        cancel_button = QPushButton("Cancelar")
        cancel_button.clicked.connect(self.reject)
        
        button_layout.addStretch()
        button_layout.addWidget(save_button)
        button_layout.addWidget(cancel_button)
        
        layout.addLayout(button_layout)
    
    def save_event(self):
        """Salva o novo evento"""
        # Validação
        if not self.title_input.text().strip():
            QMessageBox.warning(self, "Aviso", "Por favor, insira um título.")
            return
        
        # Formata data e hora
        date_str = self.date_input.date().toString("yyyy-MM-dd")
        start_time_str = self.start_time.time().toString("HH:mm")
        end_time_str = self.end_time.time().toString("HH:mm")
        
        start_datetime = f"{date_str} {start_time_str}"
        end_datetime = f"{date_str} {end_time_str}"
        
        # Mapeia prioridade
        priority_map = {
            "Baixa": 1, "Média": 2, "Alta": 3, "Fixo": 4, "Bloqueio": 5
        }
        
        # Prepara dados
        event_data = {
            'title': self.title_input.text().strip(),
            'start': start_datetime,
            'end': end_datetime,
            'event_type': self.type_combo.currentText(),
            'priority': priority_map.get(self.priority_combo.currentText(), 2),
            'description': self.description_input.toPlainText().strip(),
            'discipline': self.discipline_input.text().strip() or None
        }
        
        # Envia para o controller
        if self.controller:
            self.controller.add_event(event_data)
        
        self.accept()


class EditEventDialog(AddEventDialog):
    """Diálogo para editar evento"""
    
    def __init__(self, controller, event_data, parent=None):
        super().__init__(controller, QDate.currentDate(), parent)
        self.event_data = event_data
        self.setWindowTitle("✏️ Editar Evento")
        
        # Preenche campos com dados existentes
        self.load_event_data()
    
    def load_event_data(self):
        """Preenche formulário com dados do evento"""
        self.title_input.setText(self.event_data.get('title', ''))
        
        # Data e hora
        start_str = self.event_data.get('start', '')
        if start_str:
            start_dt = QDateTime.fromString(start_str, Qt.DateFormat.ISODate)
            if start_dt.isValid():
                self.date_input.setDate(start_dt.date())
                self.start_time.setTime(start_dt.time())
        
        end_str = self.event_data.get('end', '')
        if end_str:
            end_dt = QDateTime.fromString(end_str, Qt.DateFormat.ISODate)
            if end_dt.isValid():
                self.end_time.setTime(end_dt.time())
        
        # Tipo
        event_type = self.event_data.get('type', 'casual')
        index = self.type_combo.findText(event_type)
        if index >= 0:
            self.type_combo.setCurrentIndex(index)
        
        # Prioridade
        priority = self.event_data.get('priority', 2)
        priority_text = {
            1: "Baixa", 2: "Média", 3: "Alta", 4: "Fixo", 5: "Bloqueio"
        }.get(priority, "Média")
        self.priority_combo.setCurrentText(priority_text)
        
        # Descrição e disciplina
        self.description_input.setText(self.event_data.get('description', ''))
        self.discipline_input.setText(self.event_data.get('discipline', ''))
    
    def save_event(self):
        """Atualiza evento existente"""
        # Validação
        if not self.title_input.text().strip():
            QMessageBox.warning(self, "Aviso", "Por favor, insira um título.")
            return
        
        # Formata data e hora
        date_str = self.date_input.date().toString("yyyy-MM-dd")
        start_time_str = self.start_time.time().toString("HH:mm")
        end_time_str = self.end_time.time().toString("HH:mm")
        
        start_datetime = f"{date_str} {start_time_str}"
        end_datetime = f"{date_str} {end_time_str}"
        
        # Mapeia prioridade
        priority_map = {
            "Baixa": 1, "Média": 2, "Alta": 3, "Fixo": 4, "Bloqueio": 5
        }
        
        # Prepara atualizações
        updates = {
            'title': self.title_input.text().strip(),
            'start': start_datetime,
            'end': end_datetime,
            'type': self.type_combo.currentText(),
            'priority': priority_map.get(self.priority_combo.currentText(), 2),
            'description': self.description_input.toPlainText().strip(),
            'discipline': self.discipline_input.text().strip() or None
        }
        
        # Envia para o controller
        if self.controller:
            self.controller.update_event(self.event_data['id'], updates)
        
        self.accept()


class FindSlotDialog(QDialog):
    """Diálogo para encontrar slot livre"""
    
    def __init__(self, controller, date, parent=None):
        super().__init__(parent)
        self.controller = controller
        self.date = date
        
        self.setWindowTitle("🔍 Encontrar Slot Livre")
        self.setModal(True)
        
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Configurações
        form_layout = QFormLayout()
        
        self.date_input = QDateTimeEdit()
        self.date_input.setDate(self.date)
        self.date_input.setCalendarPopup(True)
        form_layout.addRow("Data:", self.date_input)
        
        self.duration_input = QSpinBox()
        self.duration_input.setRange(15, 480)  # 15min a 8h
        self.duration_input.setValue(60)
        self.duration_input.setSuffix(" minutos")
        form_layout.addRow("Duração:", self.duration_input)
        
        self.start_hour = QSpinBox()
        self.start_hour.setRange(0, 23)
        self.start_hour.setValue(8)
        self.start_hour.setSuffix(":00")
        form_layout.addRow("Início após:", self.start_hour)
        
        self.end_hour = QSpinBox()
        self.end_hour.setRange(1, 24)
        self.end_hour.setValue(22)
        self.end_hour.setSuffix(":00")
        form_layout.addRow("Término antes:", self.end_hour)
        
        layout.addLayout(form_layout)
        
        # Resultados
        self.results_list = QListWidget()
        self.results_list.setMinimumHeight(150)
        layout.addWidget(QLabel("Slots disponíveis:"))
        layout.addWidget(self.results_list)
        
        # Botões
        button_layout = QHBoxLayout()
        
        find_button = QPushButton("🔍 Buscar")
        find_button.clicked.connect(self.find_slots)
        
        use_button = QPushButton("📅 Usar Este Slot")
        use_button.setEnabled(False)
        use_button.clicked.connect(self.use_selected_slot)
        
        cancel_button = QPushButton("Cancelar")
        cancel_button.clicked.connect(self.reject)
        
        button_layout.addWidget(find_button)
        button_layout.addWidget(use_button)
        button_layout.addStretch()
        button_layout.addWidget(cancel_button)
        
        layout.addLayout(button_layout)
        
        self.use_button = use_button
        self.results_list.itemSelectionChanged.connect(
            lambda: self.use_button.setEnabled(bool(self.results_list.selectedItems()))
        )
    
    def find_slots(self):
        """Busca slots livres"""
        date_str = self.date_input.date().toString("yyyy-MM-dd")
        duration = self.duration_input.value()
        start_hour = self.start_hour.value()
        end_hour = self.end_hour.value()
        
        if self.controller:
            self.controller.find_free_slots(date_str, duration, start_hour, end_hour)
            # Em um sistema real, conectaríamos ao sinal free_slots_found
    
    def use_selected_slot(self):
        """Usa slot selecionado"""
        selected = self.results_list.currentItem()
        if selected:
            slot_data = selected.data(Qt.ItemDataRole.UserRole)
            self.accept()
            # Em um sistema real, abriríamos o diálogo de adicionar evento
            # pré-preenchido com este slot


class EmergencyModeDialog(QDialog):
    """Diálogo para ativar modo emergência"""
    
    def __init__(self, controller, parent=None):
        super().__init__(parent)
        self.controller = controller
        
        self.setWindowTitle("🚨 Modo Emergência")
        self.setModal(True)
        
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Aviso
        warning_label = QLabel(
            "<b>⚠️ ATENÇÃO: Modo Emergência</b><br><br>"
            "Esta ação irá reorganizar sua agenda completamente para foco intensivo.<br>"
            "Eventos flexíveis serão reagendados e um cronograma intensivo será criado."
        )
        warning_label.setWordWrap(True)
        warning_label.setStyleSheet("color: #FF6B6B; padding: 10px;")
        layout.addWidget(warning_label)
        
        # Configurações
        form_layout = QFormLayout()
        
        self.objective_input = QLineEdit()
        self.objective_input.setPlaceholderText("Ex: Prova de Ética, Artigo Final")
        form_layout.addRow("Objetivo:", self.objective_input)
        
        self.days_input = QSpinBox()
        self.days_input.setRange(1, 14)
        self.days_input.setValue(3)
        form_layout.addRow("Dias de foco:", self.days_input)
        
        self.focus_input = QLineEdit()
        self.focus_input.setPlaceholderText("Ex: Filosofia Moral, Kant")
        form_layout.addRow("Área de foco:", self.focus_input)
        
        layout.addLayout(form_layout)
        
        # Lista de consequências
        consequences = QGroupBox("Consequências:")
        cons_layout = QVBoxLayout()
        
        cons_items = [
            "✅ Eventos flexíveis serão reagendados",
            "✅ Novo cronograma intensivo criado",
            "⏰ Sessões de 1.5h com pausas curtas",
            "⚠️ Sono reduzido em 1h/dia",
            "⚠️ Atividades de lazer suspensas",
            "📊 Progresso monitorado hora a hora"
        ]
        
        for item in cons_items:
            cons_layout.addWidget(QLabel(item))
        
        consequences.setLayout(cons_layout)
        layout.addWidget(consequences)
        
        # Botões
        button_layout = QHBoxLayout()
        
        activate_button = QPushButton("🚨 ATIVAR MODO EMERGÊNCIA")
        activate_button.setObjectName("emergency_button")
        activate_button.clicked.connect(self.activate_emergency)
        
        cancel_button = QPushButton("Cancelar")
        cancel_button.clicked.connect(self.reject)
        
        button_layout.addStretch()
        button_layout.addWidget(activate_button)
        button_layout.addWidget(cancel_button)
        
        layout.addLayout(button_layout)
    
    def activate_emergency(self):
        """Ativa modo emergência"""
        objective = self.objective_input.text().strip()
        if not objective:
            QMessageBox.warning(self, "Aviso", "Por favor, insira um objetivo.")
            return
        
        days = self.days_input.value()
        focus_area = self.focus_input.text().strip() or None
        
        if self.controller:
            self.controller.activate_emergency_mode(objective, days, focus_area)
        
        QMessageBox.information(self, "Modo Ativado", 
                              f"Modo emergência ativado para: {objective}")
        self.accept()