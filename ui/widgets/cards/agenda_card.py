"""
Card para exibição de agenda/tarefas - VERSÃO OTIMIZADA COM TIMER E CHECK-IN
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QFrame, QCheckBox, QScrollArea,
    QProgressBar, QMenu, QToolButton, QGridLayout
)
from PyQt6.QtCore import Qt, pyqtSignal, pyqtSlot, QTimer, QTime, QDateTime, QObject
from PyQt6.QtGui import QFont, QColor, QPainter, QPen, QAction, QCursor
import logging
from datetime import datetime, timedelta

from .base_card import PhilosophyCard

logger = logging.getLogger('GLaDOS.UI.AgendaCard')


class AgendaCard(PhilosophyCard):
    """Card otimizado para exibição de agenda com timer e check-in"""
    
    # Sinais
    item_clicked = pyqtSignal(dict)
    item_completed = pyqtSignal(str, bool)
    navigate_to_detailed_view = pyqtSignal()
    quick_action = pyqtSignal(str, dict)
    request_checkin = pyqtSignal()
    add_event_requested = pyqtSignal()

    # Sinais adicionais para compatibilidade com dashboard.py
    navigate_to_agenda = pyqtSignal()  # Alias para navigate_to_detailed_view
    start_reading_session = pyqtSignal(dict)  # Para iniciar sessão de leitura
    edit_reading_session = pyqtSignal(dict)   # Para editar sessão de leitura
    skip_reading_session = pyqtSignal(dict)   # Para pular sessão de leitura
    
    def __init__(self, agenda_controller=None, parent=None):
        super().__init__(parent)
        
        self.controller = agenda_controller
        self.agenda_data = {}
        self.items = []
        self.next_event_timer = None
        self.next_event_time = None
        self._is_active = True  # Flag para controlar se o widget está ativo
        self._widgets_initialized = False  # Flag para verificar se widgets foram inicializados
        
        self.setup_ui()
        self.setup_connections()
        self.setup_timers()
        
        # Conectar alias para compatibilidade
        self.navigate_to_detailed_view.connect(
            lambda: self.navigate_to_agenda.emit()
        )
        
        logger.info("AgendaCard otimizado inicializado")
    
    def setup_ui(self):
        """Configura interface do card otimizada"""
        self.set_title('📅 Próximos Compromissos')
        self.set_minimizable(True)
        self.set_draggable(True)
        
        # Cabeçalho compacto com timer
        header_widget = QWidget()
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(0, 0, 0, 8)
        
        # Timer para próximo evento
        self.timer_widget = QWidget()
        timer_layout = QVBoxLayout(self.timer_widget)
        timer_layout.setSpacing(2)
        
        self.timer_label = QLabel("--:--")
        self.timer_label.setObjectName("timer_display")
        self.timer_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.next_event_name = QLabel("Sem próximos eventos")
        self.next_event_name.setObjectName("next_event_name")
        self.next_event_name.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        timer_layout.addWidget(self.timer_label)
        timer_layout.addWidget(self.next_event_name)
        
        # Estatísticas rápidas
        self.stats_widget = QWidget()
        stats_layout = QGridLayout(self.stats_widget)
        stats_layout.setHorizontalSpacing(10)
        stats_layout.setVerticalSpacing(2)
        
        self.total_label = self.create_stat_label("0", "Total")
        self.completed_label = self.create_stat_label("0", "Concluídos")
        self.remaining_label = self.create_stat_label("0", "Restantes")
        
        stats_layout.addWidget(self.total_label, 0, 0)
        stats_layout.addWidget(self.completed_label, 0, 1)
        stats_layout.addWidget(self.remaining_label, 0, 2)
        
        # Botão de check-in
        self.checkin_button = QPushButton("🔔")
        self.checkin_button.setObjectName("checkin_button")
        self.checkin_button.setFixedSize(40, 40)
        self.checkin_button.setToolTip("Daily Check-in")
        self.checkin_button.clicked.connect(self.on_checkin_clicked)
        
        header_layout.addWidget(self.timer_widget, 1)
        header_layout.addWidget(self.stats_widget, 2)
        header_layout.addWidget(self.checkin_button)
        
        # Lista de próximos 3 compromissos
        self.events_list = QWidget()
        self.events_layout = QVBoxLayout(self.events_list)
        self.events_layout.setSpacing(4)
        self.events_layout.setContentsMargins(0, 5, 0, 5)
        
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_area.setWidget(self.events_list)
        self.scroll_area.setMinimumHeight(180)
        self.scroll_area.setMaximumHeight(220)
        
        # Botões de ação
        self.actions_widget = QWidget()
        actions_layout = QHBoxLayout(self.actions_widget)
        actions_layout.setContentsMargins(0, 5, 0, 0)
        
        self.add_button = QPushButton("➕ Adicionar")
        self.add_button.setObjectName("action_button")
        self.add_button.clicked.connect(self.on_add_event)
        
        self.details_button = QPushButton("📋 Ver Detalhes")
        self.details_button.setObjectName("action_button")
        self.details_button.clicked.connect(self.on_view_details)
        
        actions_layout.addWidget(self.add_button)
        actions_layout.addWidget(self.details_button)
        
        # Layout principal do conteúdo
        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setSpacing(8)
        
        self.content_layout.addWidget(header_widget)
        self.content_layout.addWidget(self.scroll_area, 1)
        self.content_layout.addWidget(self.actions_widget)
        
        self.set_content(self.content_widget)
        
        # Estado inicial
        self.show_loading_state()
        
        # Marcar widgets como inicializados
        self._widgets_initialized = True
    
    def create_stat_label(self, value, description):
        """Cria label de estatística formatada"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        value_label = QLabel(value)
        value_label.setObjectName("stat_value")
        value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        desc_label = QLabel(description)
        desc_label.setObjectName("stat_desc")
        desc_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        layout.addWidget(value_label)
        layout.addWidget(desc_label)
        
        return widget
    
    def setup_connections(self):
        """Configura conexões com o controller"""
        if self.controller:
            self.controller.agenda_loaded.connect(self.on_agenda_loaded)
            self.controller.event_added.connect(self.on_event_added)
            self.controller.event_updated.connect(self.on_event_updated)
            self.controller.event_completed.connect(self.on_event_completed)
            
            # Carrega dados iniciais
            QTimer.singleShot(100, self.load_initial_data)
    
    def setup_timers(self):
        """Configura timers para atualização automática"""
        # Timer para atualização do relógio
        self.clock_timer = QTimer()
        self.clock_timer.timeout.connect(self.update_clock)
        self.clock_timer.start(1000)  # 1 segundo
        
        # Timer para atualização do countdown
        self.countdown_timer = QTimer()
        self.countdown_timer.timeout.connect(self.update_countdown)
        self.countdown_timer.start(1000)  # 1 segundo
    
    def load_initial_data(self):
        """Carrega dados iniciais da agenda"""
        if not self._is_active:
            return
            
        try:
            from datetime import datetime
            self.current_date = datetime.now().strftime("%Y-%m-%d")
            
            if self.controller:
                events = self.controller.load_agenda(self.current_date)
                self.on_agenda_loaded(events)
        except Exception as e:
            logger.error(f"Erro ao carregar dados iniciais: {e}")
            if self._is_active:
                self.show_error_state("Erro ao carregar agenda")
    
    def show_loading_state(self):
        """Mostra estado de carregamento"""
        if not self._is_active or not self._widgets_initialized:
            return
            
        try:
            self.clear_events()
            
            loading_widget = QWidget()
            loading_layout = QVBoxLayout(loading_widget)
            loading_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            
            loading_label = QLabel("Carregando agenda...")
            loading_label.setObjectName("loading_label")
            
            loading_layout.addWidget(loading_label)
            self.events_layout.addWidget(loading_widget)
            
            # Atualiza estatísticas
            self.update_stats(0, 0, 0)
        except RuntimeError as e:
            logger.warning(f"Widget deletado durante show_loading_state: {e}")
            self._is_active = False
    
    def show_empty_state(self):
        """Mostra estado vazio"""
        if not self._is_active or not self._widgets_initialized:
            return
            
        try:
            self.clear_events()
            
            empty_widget = QWidget()
            empty_layout = QVBoxLayout(empty_widget)
            empty_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty_layout.setSpacing(10)
            
            empty_icon = QLabel("📅")
            empty_icon.setObjectName("empty_icon")
            empty_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
            
            empty_label = QLabel("Nenhum evento hoje")
            empty_label.setObjectName("empty_label")
            empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            
            empty_button = QPushButton("Adicionar Primeiro Evento")
            empty_button.setObjectName("empty_button")
            empty_button.clicked.connect(self.on_add_event)
            
            empty_layout.addWidget(empty_icon)
            empty_layout.addWidget(empty_label)
            empty_layout.addWidget(empty_button)
            
            self.events_layout.addWidget(empty_widget)
            
            # Atualiza estatísticas e timer
            self.update_stats(0, 0, 0)
            self.update_timer_display(None)
        except RuntimeError as e:
            logger.warning(f"Widget deletado durante show_empty_state: {e}")
            self._is_active = False
    
    def show_error_state(self, message):
        """Mostra estado de erro"""
        if not self._is_active or not self._widgets_initialized:
            return
            
        try:
            self.clear_events()
            
            error_widget = QWidget()
            error_layout = QVBoxLayout(error_widget)
            error_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            
            error_icon = QLabel("⚠️")
            error_icon.setObjectName("error_icon")
            error_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
            
            error_label = QLabel(message)
            error_label.setObjectName("error_label")
            error_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            
            retry_button = QPushButton("Tentar novamente")
            retry_button.setObjectName("retry_button")
            retry_button.clicked.connect(self.refresh)
            
            error_layout.addWidget(error_icon)
            error_layout.addWidget(error_label)
            error_layout.addWidget(retry_button)
            
            self.events_layout.addWidget(error_widget)
        except RuntimeError as e:
            logger.warning(f"Widget deletado durante show_error_state: {e}")
            self._is_active = False
    
    def clear_events(self):
        """Remove todos os eventos da lista"""
        if not self._is_active or not hasattr(self, 'events_layout'):
            return
            
        try:
            while self.events_layout.count():
                child = self.events_layout.takeAt(0)
                if child and child.widget():
                    child.widget().deleteLater()
        except RuntimeError as e:
            logger.debug(f"Layout já deletado durante clear_events: {e}")
            self._is_active = False
    
    @pyqtSlot(list)
    def on_agenda_loaded(self, events):
        """Atualiza o card com os eventos do dia"""
        if not self._is_active or not self._widgets_initialized:
            return
            
        self.items = events
        
        if not events:
            self.show_empty_state()
            return
        
        try:
            self.clear_events()
            
            # Ordena eventos por horário e filtra não concluídos
            events.sort(key=lambda e: e.get('start', ''))
            upcoming_events = [e for e in events if not e.get('completed', False)]
            completed_events = [e for e in events if e.get('completed', False)]
            
            # Atualiza estatísticas
            total_count = len(events)
            completed_count = len(completed_events)
            upcoming_count = len(upcoming_events)
            
            self.update_stats(total_count, completed_count, upcoming_count)
            
            # Mostra apenas os próximos 3 eventos
            display_events = upcoming_events[:3]
            
            for event in display_events:
                item_widget = self.create_compact_event_widget(event)
                self.events_layout.addWidget(item_widget)
            
            # Se houver mais eventos, mostra contador
            if len(upcoming_events) > 3:
                more_label = QLabel(f"... e mais {len(upcoming_events) - 3} eventos")
                more_label.setObjectName("more_events")
                more_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                self.events_layout.addWidget(more_label)
            
            # Atualiza timer do próximo evento
            self.update_next_event_timer(upcoming_events)
            
            logger.debug(f"Agenda atualizada: {total_count} eventos")
        except RuntimeError as e:
            logger.warning(f"Widget deletado durante on_agenda_loaded: {e}")
            self._is_active = False
    
    @pyqtSlot(dict)
    def on_event_added(self, event_data):
        """Quando novo evento é adicionado"""
        logger.info(f"Evento adicionado: {event_data.get('title')}")
        self.refresh()
    
    @pyqtSlot(str, dict)
    def on_event_updated(self, event_id, update_data):
        """Quando evento é atualizado"""
        logger.debug(f"Evento atualizado: {event_id}")
        
        # Atualiza evento na lista local
        for event in self.items:
            if event['id'] == event_id:
                event.update(update_data)
                break
        
        # Recarrega para refletir mudanças
        self.refresh()
    
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
        try:
            if self._is_active and hasattr(self, 'events_layout'):
                for i in range(self.events_layout.count()):
                    item_widget = self.events_layout.itemAt(i).widget()
                    if item_widget and hasattr(item_widget, 'event_id'):
                        if item_widget.event_id == event_id:
                            item_widget.set_completed(completed)
                            break
        except RuntimeError:
            self._is_active = False
        
        # Atualiza estatísticas
        self.update_stats_from_items()
    
    def create_compact_event_widget(self, event_data):
        """Cria widget compacto para evento"""
        widget = CompactEventWidget(event_data)
        widget.clicked.connect(lambda: self.item_clicked.emit(event_data))
        widget.completed_changed.connect(
            lambda event_id, completed: self.on_item_completed(event_id, completed)
        )
        
        return widget
    
    def update_stats(self, total, completed, remaining):
        """Atualiza estatísticas do card"""
        if not self._is_active or not self._widgets_initialized:
            return
            
        try:
            if hasattr(self.total_label, 'findChild'):
                total_label = self.total_label.findChild(QLabel, "stat_value")
                completed_label = self.completed_label.findChild(QLabel, "stat_value")
                remaining_label = self.remaining_label.findChild(QLabel, "stat_value")
                
                if total_label:
                    total_label.setText(str(total))
                if completed_label:
                    completed_label.setText(str(completed))
                if remaining_label:
                    remaining_label.setText(str(remaining))
        except RuntimeError as e:
            logger.warning(f"Widget deletado durante update_stats: {e}")
            self._is_active = False
    
    def update_stats_from_items(self):
        """Calcula e atualiza estatísticas dos itens atuais"""
        if not self._is_active or not self.items:
            return
        
        completed_events = [e for e in self.items if e.get('completed', False)]
        upcoming_events = [e for e in self.items if not e.get('completed', False)]
        
        total_count = len(self.items)
        completed_count = len(completed_events)
        upcoming_count = len(upcoming_events)
        
        self.update_stats(total_count, completed_count, upcoming_count)
        
        # Atualiza próximo evento
        self.update_next_event_timer(upcoming_events)
    
    def update_next_event_timer(self, upcoming_events):
        """Atualiza timer do próximo evento"""
        if not self._is_active or not self._widgets_initialized:
            return
            
        if not upcoming_events:
            self.update_timer_display(None)
            return
        
        # Encontra o próximo evento
        now = datetime.now()
        next_event = None
        
        for event in upcoming_events:
            event_time_str = event.get('start', '')
            try:
                event_time = datetime.fromisoformat(event_time_str.replace('Z', '+00:00'))
                
                # Se o evento já passou hoje, pule
                if event_time.date() == now.date() and event_time.time() < now.time():
                    continue
                
                if not next_event or event_time < next_event[0]:
                    next_event = (event_time, event)
            except Exception as e:
                logger.error(f"Erro ao processar horário do evento: {e}")
                continue
        
        if next_event:
            event_time, event = next_event
            self.next_event_time = event_time
            self.next_event_name.setText(event.get('title', 'Próximo evento')[:20])
            self.update_countdown()
        else:
            self.update_timer_display(None)
    
    def update_countdown(self):
        """Atualiza contagem regressiva para próximo evento"""
        if not self._is_active or not self._widgets_initialized:
            return
            
        try:
            if not self.next_event_time:
                self.timer_label.setText("--:--")
                return
            
            now = datetime.now()
            
            # Se o evento é hoje
            if self.next_event_time.date() == now.date():
                time_diff = self.next_event_time - now
                
                if time_diff.total_seconds() > 0:
                    # Formato: HH:MM:SS
                    hours, remainder = divmod(int(time_diff.total_seconds()), 3600)
                    minutes, seconds = divmod(remainder, 60)
                    
                    if hours > 0:
                        self.timer_label.setText(f"{hours:02d}:{minutes:02d}:{seconds:02d}")
                    else:
                        self.timer_label.setText(f"{minutes:02d}:{seconds:02d}")
                else:
                    # Evento em andamento ou atrasado
                    self.timer_label.setText("AGORA")
                    self.timer_label.setStyleSheet("color: #FF6B6B; font-weight: bold;")
            else:
                # Evento em outro dia
                days_diff = (self.next_event_time.date() - now.date()).days
                if days_diff == 1:
                    self.timer_label.setText("AMANHÃ")
                else:
                    self.timer_label.setText(f"+{days_diff}d")
        except RuntimeError as e:
            logger.warning(f"Widget deletado durante update_countdown: {e}")
            self._is_active = False
            self.stop_timers()
    
    def update_timer_display(self, event_data):
        """Atualiza display do timer"""
        if not self._is_active or not self._widgets_initialized:
            return
            
        try:
            if not event_data:
                self.timer_label.setText("--:--")
                self.next_event_name.setText("Sem próximos eventos")
                self.timer_label.setStyleSheet("")
            else:
                self.next_event_name.setText(event_data.get('title', 'Próximo evento')[:20])
        except RuntimeError as e:
            logger.warning(f"Widget deletado durante update_timer_display: {e}")
            self._is_active = False
            self.stop_timers()
    
    def update_clock(self):
        """Atualiza relógio (para uso futuro)"""
        if not self._is_active:
            return
    
    def on_add_event(self):
        """Solicita adição de novo evento"""
        self.add_event_requested.emit()
    
    def on_view_details(self):
        """Navega para view detalhada da agenda"""
        self.navigate_to_detailed_view.emit()
    
    def on_checkin_clicked(self):
        """Solicita check-in diário"""
        self.request_checkin.emit()
    
    def refresh(self):
        """Recarrega agenda"""
        if not self._is_active:
            return
            
        if self.controller:
            try:
                events = self.controller.load_agenda(self.current_date)
                self.on_agenda_loaded(events)
            except Exception as e:
                logger.error(f"Erro ao recarregar agenda: {e}")
                if self._is_active:
                    self.show_error_state("Erro ao recarregar")
    
    def on_item_completed(self, event_id, completed):
        """Quando item é marcado como concluído"""
        if not self._is_active:
            return
            
        if self.controller:
            success = self.controller.toggle_event_completion(event_id, completed)
            
            if not success:
                logger.error(f"Falha ao atualizar evento {event_id}")
                # Reverte visualmente
                try:
                    if hasattr(self, 'events_layout'):
                        for i in range(self.events_layout.count()):
                            item_widget = self.events_layout.itemAt(i).widget()
                            if item_widget and hasattr(item_widget, 'event_id'):
                                if item_widget.event_id == event_id:
                                    item_widget.checkbox.blockSignals(True)
                                    item_widget.checkbox.setChecked(not completed)
                                    item_widget.checkbox.blockSignals(False)
                                    break
                except RuntimeError:
                    self._is_active = False

    def stop_timers(self):
        """Para todos os timers para evitar acessos a widgets deletados"""
        if hasattr(self, 'clock_timer'):
            try:
                self.clock_timer.stop()
            except RuntimeError:
                pass
        if hasattr(self, 'countdown_timer'):
            try:
                self.countdown_timer.stop()
            except RuntimeError:
                pass
    
    def cleanup(self):
        """Limpa recursos do card"""
        self._is_active = False
        
        try:
            # Desconectar sinais
            if self.controller:
                try:
                    self.controller.agenda_loaded.disconnect(self.on_agenda_loaded)
                    self.controller.event_added.disconnect(self.on_event_added)
                    self.controller.event_updated.disconnect(self.on_event_updated)
                    self.controller.event_completed.disconnect(self.on_event_completed)
                except (TypeError, RuntimeError):
                    pass
            
            # Parar timers
            self.stop_timers()
            
            # Limpar eventos
            if hasattr(self, 'events_layout'):
                self.clear_events()
                
        except Exception as e:
            logger.debug(f"Erro durante cleanup: {e}")
        
        logger.debug("AgendaCard limpo")
    
    def closeEvent(self, event):
        """Evento de fechamento"""
        self.cleanup()
        super().closeEvent(event)
    
    def deleteLater(self):
        """Sobrescreve deleteLater para garantir limpeza"""
        self.cleanup()
        super().deleteLater()


class CompactEventWidget(QWidget):
    """Widget compacto para exibição de evento"""
    
    clicked = pyqtSignal(dict)
    completed_changed = pyqtSignal(str, bool)
    
    def __init__(self, event_data, parent=None):
        super().__init__(parent)
        self.event_data = event_data
        self.event_id = event_data.get('id', '')
        self._is_active = True
        
        self.setup_ui()
        self.setup_connections()
    
    def setup_ui(self):
        """Configura interface compacta"""
        self.setObjectName("compact_event_widget")
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(10)
        
        # Checkbox
        self.checkbox = QCheckBox()
        self.checkbox.setChecked(self.event_data.get('completed', False))
        self.checkbox.setFixedSize(18, 18)
        
        # Indicador de cor do tipo
        color = self.event_data.get('color', '#9B9B9B')
        self.color_indicator = QLabel()
        self.color_indicator.setFixedSize(4, 24)
        self.color_indicator.setStyleSheet(f"background-color: {color}; border-radius: 2px;")
        
        # Informações principais
        info_widget = QWidget()
        info_layout = QVBoxLayout(info_widget)
        info_layout.setContentsMargins(0, 0, 0, 0)
        info_layout.setSpacing(2)
        
        # Título (com ellipsis para textos longos)
        title = self.event_data.get('title', 'Sem título')
        self.title_label = QLabel(title)
        self.title_label.setObjectName("event_title")
        self.title_label.setMaximumWidth(200)
        self.title_label.setToolTip(title)
        
        # Horário e tipo
        time_type_widget = QWidget()
        time_type_layout = QHBoxLayout(time_type_widget)
        time_type_layout.setContentsMargins(0, 0, 0, 0)
        
        self.time_label = QLabel(self.event_data.get('start_time', ''))
        self.time_label.setObjectName("event_time")
        
        event_type = self.event_data.get('type', 'casual')
        self.type_label = QLabel(event_type[:10])
        self.type_label.setObjectName("event_type")
        
        time_type_layout.addWidget(self.time_label)
        time_type_layout.addStretch()
        time_type_layout.addWidget(self.type_label)
        
        info_layout.addWidget(self.title_label)
        info_layout.addWidget(time_type_widget)
        
        layout.addWidget(self.checkbox)
        layout.addWidget(self.color_indicator)
        layout.addWidget(info_widget, 1)
        
        # Aplica estilo de concluído
        if self.event_data.get('completed', False):
            self.set_completed(True)
    
    def setup_connections(self):
        """Configura conexões"""
        self.checkbox.stateChanged.connect(self.on_checkbox_changed)
    
    def on_checkbox_changed(self, state):
        """Quando checkbox é alterado"""
        if not self._is_active:
            return
        completed = (state == Qt.CheckState.Checked.value)
        self.completed_changed.emit(self.event_id, completed)
        self.set_completed(completed)
    
    def set_completed(self, completed):
        """Marca item como completo/incompleto"""
        if not self._is_active:
            return
        style = "text-decoration: line-through; color: #888;" if completed else ""
        self.title_label.setStyleSheet(style)
        self.time_label.setStyleSheet(style)
        self.type_label.setStyleSheet(style)
    
    def mousePressEvent(self, event):
        """Quando widget é clicado"""
        if not self._is_active:
            return
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.event_data)
        super().mousePressEvent(event)
    
    def cleanup(self):
        """Limpa recursos do widget"""
        self._is_active = False
        try:
            self.checkbox.stateChanged.disconnect()
        except:
            pass


# Alias para compatibilidade - mantém o nome antigo para importação
AgendaEventWidget = CompactEventWidget