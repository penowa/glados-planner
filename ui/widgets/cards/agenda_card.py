"""Card de agenda com visual semanal."""
from datetime import date, datetime, timedelta
import logging
from typing import Any, Dict, List

from PyQt6.QtCore import Qt, QTimer, pyqtSignal, pyqtSlot
from PyQt6.QtWidgets import (
    QCheckBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from .base_card import PhilosophyCard

logger = logging.getLogger("GLaDOS.UI.AgendaCard")


class AgendaCard(PhilosophyCard):
    """Card para exibição da agenda semanal com ações rápidas."""

    item_clicked = pyqtSignal(dict)
    item_completed = pyqtSignal(str, bool)
    navigate_to_detailed_view = pyqtSignal()
    quick_action = pyqtSignal(str, dict)
    request_checkin = pyqtSignal()
    add_event_requested = pyqtSignal()

    # Compatibilidade com dashboard.py
    navigate_to_agenda = pyqtSignal()
    start_reading_session = pyqtSignal(dict)
    edit_reading_session = pyqtSignal(dict)
    skip_reading_session = pyqtSignal(dict)

    def __init__(self, agenda_controller=None, parent=None):
        super().__init__(parent)

        self.controller = agenda_controller
        self.items: List[Dict[str, Any]] = []
        self.current_week_start = self._get_week_start(date.today())
        self._is_active = True

        self._build_ui()
        self._setup_connections()
        self._setup_timers()

        self.navigate_to_detailed_view.connect(lambda: self.navigate_to_agenda.emit())
        self.refresh()

    def _build_ui(self):
        self.set_title("📅 Agenda da Semana")
        self.set_minimizable(True)
        self.set_draggable(True)

        main = QWidget()
        layout = QVBoxLayout(main)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        header = QWidget()
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 0)

        self.timer_label = QLabel("--:--")
        self.timer_label.setObjectName("timer_display")
        self.start_session_button = QPushButton("Iniciar sessão agendada")
        self.start_session_button.setObjectName("primary_button")
        self.start_session_button.setVisible(False)
        self.start_session_button.clicked.connect(self._start_next_reading_session)
        self.next_event_name = QLabel("Sem próximos eventos")
        self.next_event_name.setObjectName("next_event_name")

        timer_box = QWidget()
        timer_box_layout = QVBoxLayout(timer_box)
        timer_box_layout.setContentsMargins(0, 0, 0, 0)
        timer_box_layout.setSpacing(2)
        timer_box_layout.addWidget(self.timer_label)
        timer_box_layout.addWidget(self.start_session_button)
        timer_box_layout.addWidget(self.next_event_name)

        stats = QWidget()
        stats_layout = QGridLayout(stats)
        stats_layout.setContentsMargins(0, 0, 0, 0)
        stats_layout.setHorizontalSpacing(8)

        self.total_label = self._create_stat_label("0", "Total")
        self.completed_label = self._create_stat_label("0", "Concluídos")
        self.remaining_label = self._create_stat_label("0", "Restantes")

        stats_layout.addWidget(self.total_label, 0, 0)
        stats_layout.addWidget(self.completed_label, 0, 1)
        stats_layout.addWidget(self.remaining_label, 0, 2)

        self.checkin_button = QPushButton("🔔")
        self.checkin_button.setObjectName("checkin_button")
        self.checkin_button.setFixedSize(40, 40)
        self.checkin_button.setToolTip("Daily Check-in")

        header_layout.addWidget(timer_box, 1)
        header_layout.addWidget(stats, 2)
        header_layout.addWidget(self.checkin_button)

        nav = QWidget()
        nav_layout = QHBoxLayout(nav)
        nav_layout.setContentsMargins(0, 0, 0, 0)

        self.prev_week_button = QPushButton("◀ Semana")
        self.today_button = QPushButton("Hoje")
        self.next_week_button = QPushButton("Semana ▶")
        self.week_label = QLabel("")
        self.week_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        nav_layout.addWidget(self.prev_week_button)
        nav_layout.addWidget(self.today_button)
        nav_layout.addWidget(self.week_label, 1)
        nav_layout.addWidget(self.next_week_button)

        self.calendar_scroll = QScrollArea()
        self.calendar_scroll.setWidgetResizable(True)
        self.calendar_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.calendar_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.calendar_widget = QWidget()
        self.calendar_grid = QGridLayout(self.calendar_widget)
        self.calendar_grid.setContentsMargins(0, 0, 0, 0)
        self.calendar_grid.setSpacing(6)
        self.calendar_scroll.setWidget(self.calendar_widget)

        self.day_layouts: List[QVBoxLayout] = []
        self._build_week_grid()

        actions = QWidget()
        actions_layout = QHBoxLayout(actions)
        actions_layout.setContentsMargins(0, 0, 0, 0)

        self.add_button = QPushButton("➕ Adicionar")
        self.add_button.setObjectName("action_button")
        self.details_button = QPushButton("📋 Ver Detalhes")
        self.details_button.setObjectName("action_button")

        actions_layout.addWidget(self.add_button)
        actions_layout.addWidget(self.details_button)

        layout.addWidget(header)
        layout.addWidget(nav)
        layout.addWidget(self.calendar_scroll)
        layout.addWidget(actions)

        self.set_content(main)

    def _build_week_grid(self):
        self.day_layouts.clear()

        for col in range(7):
            day_label = QLabel("")
            day_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            day_label.setObjectName("week_day_header")
            self.calendar_grid.addWidget(day_label, 0, col)

            day_frame = QFrame()
            day_frame.setObjectName("week_day_column")
            day_layout = QVBoxLayout(day_frame)
            day_layout.setContentsMargins(6, 6, 6, 6)
            day_layout.setSpacing(4)

            self.day_layouts.append(day_layout)
            self.calendar_grid.addWidget(day_frame, 1, col)

    def _create_stat_label(self, value: str, description: str) -> QWidget:
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

    def _setup_connections(self):
        self.checkin_button.clicked.connect(self.on_checkin_clicked)
        self.add_button.clicked.connect(self.on_add_event)
        self.details_button.clicked.connect(self.on_view_details)

        self.prev_week_button.clicked.connect(self.show_previous_week)
        self.today_button.clicked.connect(self.show_current_week)
        self.next_week_button.clicked.connect(self.show_next_week)

        if not self.controller:
            return

        try:
            self.controller.agenda_loaded.connect(self.on_agenda_loaded)
        except Exception:
            pass

        try:
            self.controller.event_added.connect(self.on_event_added)
            self.controller.event_updated.connect(self.on_event_updated)
            self.controller.event_completed.connect(self.on_event_completed)
        except Exception:
            pass

    def _setup_timers(self):
        self.countdown_timer = QTimer()
        self.countdown_timer.timeout.connect(self.update_countdown)
        self.countdown_timer.start(1000)

    def _get_week_start(self, target_date: date) -> date:
        return target_date - timedelta(days=target_date.weekday())

    def _normalize_event(self, event: Any) -> Dict[str, Any]:
        if isinstance(event, dict):
            data = dict(event)
        elif hasattr(event, "to_dict"):
            data = event.to_dict()
        else:
            data = {
                "id": getattr(event, "id", ""),
                "title": getattr(event, "title", "Sem título"),
                "type": getattr(getattr(event, "type", None), "value", "casual"),
                "start": getattr(getattr(event, "start", None), "isoformat", lambda: "")(),
                "end": getattr(getattr(event, "end", None), "isoformat", lambda: "")(),
                "completed": getattr(event, "completed", False),
                "auto_generated": getattr(event, "auto_generated", False),
            }

        start_str = data.get("start", "")
        try:
            start_dt = datetime.fromisoformat(start_str.replace("Z", "+00:00"))
            data["start_time"] = start_dt.strftime("%H:%M")
            data["_start_dt"] = start_dt
        except Exception:
            data.setdefault("start_time", "--:--")

        return data

    def _load_day_events(self, day: date) -> List[Dict[str, Any]]:
        date_str = day.strftime("%Y-%m-%d")

        try:
            if self.controller and hasattr(self.controller, "load_agenda"):
                events = self.controller.load_agenda(date_str)
                if isinstance(events, list):
                    logger.debug("AgendaCard: %s eventos via controller.load_agenda(%s)", len(events), date_str)
                    return [self._normalize_event(event) for event in events]

            if self.controller and hasattr(self.controller, "agenda_manager"):
                manager = self.controller.agenda_manager
                if hasattr(manager, "get_day_events"):
                    events = manager.get_day_events(date_str)
                    logger.debug("AgendaCard: %s eventos via controller.agenda_manager.get_day_events(%s)", len(events), date_str)
                    return [self._normalize_event(event) for event in events]

            if self.controller and hasattr(self.controller, "get_day_events"):
                events = self.controller.get_day_events(date_str) or []
                logger.debug("AgendaCard: %s eventos via controller.get_day_events(%s)", len(events), date_str)
                return [self._normalize_event(event) for event in events]
        except Exception as exc:
            logger.error("Erro ao carregar agenda de %s: %s", date_str, exc)

        return []

    def _render_week(self):
        week_events: List[Dict[str, Any]] = []

        for col in range(7):
            day = self.current_week_start + timedelta(days=col)
            day_header = self.calendar_grid.itemAtPosition(0, col).widget()
            day_header.setText(day.strftime("%a\n%d/%m"))

            day_layout = self.day_layouts[col]
            self._clear_layout(day_layout)

            events = self._load_day_events(day)
            events.sort(key=lambda evt: evt.get("start", ""))
            week_events.extend(events)

            if not events:
                empty = QLabel("Sem eventos")
                empty.setObjectName("week_day_empty")
                empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
                day_layout.addWidget(empty)
                day_layout.addStretch()
                continue

            for event in events:
                event_widget = CompactEventWidget(event)
                event_widget.clicked.connect(lambda evt=event: self.item_clicked.emit(evt))
                event_widget.completed_changed.connect(self.on_item_completed)
                day_layout.addWidget(event_widget)

            day_layout.addStretch()

        self.items = week_events
        self._update_week_label()
        self.update_stats_from_items()
        self.update_next_event_timer([evt for evt in self.items if not evt.get("completed", False)])

    def _update_week_label(self):
        end = self.current_week_start + timedelta(days=6)
        self.week_label.setText(
            f"{self.current_week_start.strftime('%d/%m')} - {end.strftime('%d/%m/%Y')}"
        )

    def _clear_layout(self, layout: QVBoxLayout):
        while layout.count():
            child = layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

    def show_current_week(self):
        self.current_week_start = self._get_week_start(date.today())
        self.refresh()

    def show_previous_week(self):
        self.current_week_start -= timedelta(days=7)
        self.refresh()

    def show_next_week(self):
        self.current_week_start += timedelta(days=7)
        self.refresh()

    @pyqtSlot(list)
    def on_agenda_loaded(self, events):
        # Compatibilidade: sempre renderiza semana atual em vez de lista diária.
        if not self._is_active:
            return
        self.refresh()

    @pyqtSlot(dict)
    def on_event_added(self, event_data):
        logger.info("Evento adicionado: %s", event_data.get("title"))
        self.refresh()

    @pyqtSlot(str, dict)
    def on_event_updated(self, event_id, update_data):
        logger.debug("Evento atualizado: %s", event_id)
        self.refresh()

    @pyqtSlot(str, bool)
    def on_event_completed(self, event_id, completed):
        logger.debug("Evento concluído atualizado: %s=%s", event_id, completed)
        self.refresh()

    def update_stats(self, total: int, completed: int, remaining: int):
        total_label = self.total_label.findChild(QLabel, "stat_value")
        completed_label = self.completed_label.findChild(QLabel, "stat_value")
        remaining_label = self.remaining_label.findChild(QLabel, "stat_value")

        if total_label:
            total_label.setText(str(total))
        if completed_label:
            completed_label.setText(str(completed))
        if remaining_label:
            remaining_label.setText(str(remaining))

    def update_stats_from_items(self):
        total = len(self.items)
        completed = len([evt for evt in self.items if evt.get("completed", False)])
        remaining = max(total - completed, 0)
        self.update_stats(total, completed, remaining)

    def update_next_event_timer(self, upcoming_events: List[Dict[str, Any]]):
        if not upcoming_events:
            self.next_event_name.setText("Sem próximos eventos")
            self.timer_label.setText("--:--")
            self.next_event_time = None
            self.next_event_data = None
            self.start_session_button.setVisible(False)
            self.timer_label.setVisible(True)
            return

        now = datetime.now()
        future = []
        for event in upcoming_events:
            try:
                evt_dt = event.get("_start_dt")
                if not evt_dt:
                    evt_dt = datetime.fromisoformat(event.get("start", "").replace("Z", "+00:00"))
                if evt_dt >= now:
                    future.append((evt_dt, event))
            except Exception:
                continue

        if not future:
            self.next_event_name.setText("Sem próximos eventos")
            self.timer_label.setText("--:--")
            self.next_event_time = None
            self.next_event_data = None
            self.start_session_button.setVisible(False)
            self.timer_label.setVisible(True)
            return

        future.sort(key=lambda item: item[0])
        self.next_event_time, next_event = future[0]
        self.next_event_data = next_event
        self.next_event_name.setText(next_event.get("title", "Próximo evento")[:30])
        self.update_countdown()

    def update_countdown(self):
        if not getattr(self, "next_event_time", None):
            self.start_session_button.setVisible(False)
            self.timer_label.setVisible(True)
            self.timer_label.setText("--:--")
            return

        now = datetime.now()
        delta = self.next_event_time - now
        next_event = getattr(self, "next_event_data", None) or {}
        is_reading = self._is_reading_event(next_event)

        if is_reading and delta.total_seconds() <= 300:
            self.timer_label.setVisible(False)
            self.start_session_button.setVisible(True)
        else:
            self.start_session_button.setVisible(False)
            self.timer_label.setVisible(True)

        if delta.total_seconds() <= 0:
            self.timer_label.setText("AGORA")
            return

        total_seconds = int(delta.total_seconds())
        hours, remainder = divmod(total_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)

        if hours > 0:
            self.timer_label.setText(f"{hours:02d}:{minutes:02d}:{seconds:02d}")
        else:
            self.timer_label.setText(f"{minutes:02d}:{seconds:02d}")

    def _is_reading_event(self, event: Dict[str, Any]) -> bool:
        event_type = str(event.get("type", "")).strip().lower()
        return event_type == "leitura"

    def _start_next_reading_session(self):
        event_data = getattr(self, "next_event_data", None)
        if not event_data:
            return
        self.start_reading_session.emit(event_data)

    def on_add_event(self):
        self.add_event_requested.emit()

    def on_view_details(self):
        self.navigate_to_detailed_view.emit()

    def on_checkin_clicked(self):
        self.request_checkin.emit()

    def on_item_completed(self, event_id: str, completed: bool):
        self.item_completed.emit(event_id, completed)

        try:
            if self.controller and hasattr(self.controller, "toggle_event_completion"):
                self.controller.toggle_event_completion(event_id, completed)
                self.refresh()
                return

            if self.controller and hasattr(self.controller, "agenda_manager"):
                manager = self.controller.agenda_manager
                if event_id in manager.events:
                    manager.events[event_id].completed = completed
                    manager._save_events()
                    self.refresh()
                    return
        except Exception as exc:
            logger.error("Erro ao concluir evento %s: %s", event_id, exc)

    def refresh(self):
        if not self._is_active:
            return
        self._render_week()

    def set_current_book(self, _book_data: dict):
        # Compatibilidade com chamadas do dashboard.
        pass

    def cleanup(self):
        self._is_active = False

        if hasattr(self, "countdown_timer"):
            try:
                self.countdown_timer.stop()
            except RuntimeError:
                pass

        if self.controller:
            try:
                self.controller.agenda_loaded.disconnect(self.on_agenda_loaded)
            except Exception:
                pass
            try:
                self.controller.event_added.disconnect(self.on_event_added)
                self.controller.event_updated.disconnect(self.on_event_updated)
                self.controller.event_completed.disconnect(self.on_event_completed)
            except Exception:
                pass

    def closeEvent(self, event):
        self.cleanup()
        super().closeEvent(event)

    def deleteLater(self):
        self.cleanup()
        super().deleteLater()


class CompactEventWidget(QWidget):
    """Widget compacto para eventos dentro do calendário semanal."""

    clicked = pyqtSignal(dict)
    completed_changed = pyqtSignal(str, bool)

    def __init__(self, event_data, parent=None):
        super().__init__(parent)
        self.event_data = event_data
        self.event_id = event_data.get("id", "")

        self._build_ui()

    def _build_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 4, 6, 4)
        layout.setSpacing(6)

        self.checkbox = QCheckBox()
        self.checkbox.setChecked(self.event_data.get("completed", False))
        self.checkbox.setFixedSize(16, 16)
        self.checkbox.stateChanged.connect(self._on_checkbox_changed)

        tag = "🤖" if self.event_data.get("auto_generated") else "👤"
        time_text = self.event_data.get("start_time", "--:--")
        title = self.event_data.get("title", "Sem título")

        self.label = QLabel(f"{tag} {time_text} {title}")
        self.label.setWordWrap(True)
        self.label.setObjectName("week_event_label")
        self.label.setToolTip(title)

        layout.addWidget(self.checkbox)
        layout.addWidget(self.label, 1)

        self._apply_completed_style(self.event_data.get("completed", False))

    def _on_checkbox_changed(self, state):
        completed = state == Qt.CheckState.Checked.value
        self._apply_completed_style(completed)
        self.completed_changed.emit(self.event_id, completed)

    def _apply_completed_style(self, completed: bool):
        if completed:
            self.label.setStyleSheet("color: #888; text-decoration: line-through;")
        else:
            self.label.setStyleSheet("")

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.event_data)
        super().mousePressEvent(event)


AgendaEventWidget = CompactEventWidget
