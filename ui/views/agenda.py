"""View de agenda mensal com painel diário e drag-and-drop."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from PyQt6.QtCore import (
    QEasingCurve,
    QDate,
    QMimeData,
    QPropertyAnimation,
    Qt,
    QTime,
    QTimer,
    pyqtSignal,
    pyqtSlot,
)
from PyQt6.QtGui import QAction, QColor, QDrag
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QCheckBox,
    QDialog,
    QFormLayout,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QGraphicsColorizeEffect,
    QGraphicsOpacityEffect,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QToolBar,
    QVBoxLayout,
    QWidget,
    QDateTimeEdit,
    QComboBox,
    QSpinBox,
    QTimeEdit,
)
from ui.utils.discipline_links import (
    append_event_link,
    ensure_discipline_note,
    list_disciplines,
    resolve_vault_root,
)
from ui.utils.nerd_icons import NerdIcons, nerd_font

try:
    from core.config.settings import settings as core_settings
except Exception:
    core_settings = None

logger = logging.getLogger("GLaDOS.UI.AgendaView")

PRIORITY_COLORS = {
    1: "#93C5FD",
    2: "#60A5FA",
    3: "#FBBF24",
    4: "#FB7185",
    5: "#EF4444",
}

TYPE_ICONS = {
    "leitura": NerdIcons.BOOK,
    "revisao": NerdIcons.REFRESH,
    "producao": NerdIcons.NOTE,
    "aula": NerdIcons.GRADUATION,
    "prova": NerdIcons.FLASK,
    "seminario": NerdIcons.BULLHORN,
    "orientacao": NerdIcons.COMPASS,
    "reuniao": NerdIcons.USERS,
    "revisao_dominical": NerdIcons.CALENDAR,
    "grupo_estudo": NerdIcons.USERS,
    "lazer": NerdIcons.TARGET,
    "refeicao": NerdIcons.CUTLERY,
    "sono": NerdIcons.BED,
    "casual": NerdIcons.PIN,
}

TYPE_COLORS = {
    "aula": "#FACC15",
}


def _normalize_event(raw_event: dict) -> dict:
    event = dict(raw_event)
    start_raw = event.get("start", "")
    end_raw = event.get("end", "")
    event.setdefault("type", event.get("event_type", "casual"))

    try:
        start_dt = datetime.fromisoformat(str(start_raw).replace("Z", "+00:00"))
    except Exception:
        start_dt = None

    try:
        end_dt = datetime.fromisoformat(str(end_raw).replace("Z", "+00:00"))
    except Exception:
        end_dt = None

    metadata = event.get("metadata", {}) or {}
    recurrence = metadata.get("recurrence", {}) or event.get("recurrence", {}) or {}
    recurrence_type = str(recurrence.get("type") or "").strip().lower()

    if (
        start_dt
        and end_dt
        and recurrence_type in {"daily", "weekly", "weekdays"}
        and end_dt.date() != start_dt.date()
        and end_dt.time() > start_dt.time()
    ):
        # Corrige ocorrências recorrentes que foram persistidas usando a data limite da série
        # no campo `end`, mas deveriam manter apenas a duração intradiária.
        end_dt = datetime.combine(start_dt.date(), end_dt.time())

    if start_dt:
        event["_start_dt"] = start_dt
        event["start_time"] = start_dt.strftime("%H:%M")
        event["date"] = start_dt.date().isoformat()
    else:
        event.setdefault("start_time", "--:--")

    if end_dt:
        event["_end_dt"] = end_dt
        event["end_time"] = end_dt.strftime("%H:%M")

    if start_dt and end_dt:
        event["duration_minutes"] = int((end_dt - start_dt).total_seconds() / 60)

    event.setdefault("priority", 2)
    event.setdefault("id", event.get("title", ""))
    event.setdefault("title", "Sem título")
    return event


class MonthDayEventList(QListWidget):
    event_clicked = pyqtSignal(dict)
    event_dropped = pyqtSignal(str, str, str)  # (event_id, source_date, target_date)

    MIME = "application/x-glados-agenda-event"

    def __init__(self, parent=None):
        super().__init__(parent)
        self.date_str = ""
        self._drag_start_pos = None
        self._drag_item: Optional[QListWidgetItem] = None
        self._dragging = False
        self._held_bg_role = int(Qt.ItemDataRole.UserRole) + 11
        self._held_fg_role = int(Qt.ItemDataRole.UserRole) + 12
        self.setObjectName("month_day_event_list")
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDropIndicatorShown(True)
        self.setDefaultDropAction(Qt.DropAction.MoveAction)
        # Evita movimentação interna automática da lista (causa glitches visuais)
        self.setDragDropMode(QAbstractItemView.DragDropMode.NoDragDrop)
        self.itemClicked.connect(self._on_item_clicked)

    def set_date(self, date_str: str):
        self.date_str = date_str

    def mimeData(self, items):  # noqa: N802
        if not items:
            return super().mimeData(items)
        event_data = items[0].data(Qt.ItemDataRole.UserRole) or {}
        payload = {
            "event_id": str(event_data.get("id", "")),
            "source_date": str(event_data.get("date", self.date_str)),
        }
        mime = QMimeData()
        mime.setData(self.MIME, json.dumps(payload).encode("utf-8"))
        return mime

    def dragEnterEvent(self, event):
        if event.mimeData().hasFormat(self.MIME):
            event.acceptProposedAction()
            return
        super().dragEnterEvent(event)

    def dragMoveEvent(self, event):
        if event.mimeData().hasFormat(self.MIME):
            event.acceptProposedAction()
            return
        super().dragMoveEvent(event)

    def dropEvent(self, event):
        if not event.mimeData().hasFormat(self.MIME):
            super().dropEvent(event)
            return
        try:
            data = json.loads(bytes(event.mimeData().data(self.MIME)).decode("utf-8"))
            event_id = str(data.get("event_id", ""))
            source_date = str(data.get("source_date", ""))
            if event_id and self.date_str:
                self.event_dropped.emit(event_id, source_date, self.date_str)
                event.acceptProposedAction()
                return
        except Exception as exc:
            logger.debug("Falha no drop do mês: %s", exc)
        event.ignore()

    def _on_item_clicked(self, item: QListWidgetItem):
        event_data = item.data(Qt.ItemDataRole.UserRole) or {}
        self.event_clicked.emit(event_data)

    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        if event.button() != Qt.MouseButton.LeftButton:
            return
        self._drag_start_pos = event.pos()
        self._drag_item = self.itemAt(event.pos())
        if self._drag_item and self._drag_item.data(Qt.ItemDataRole.UserRole):
            self._set_item_held(self._drag_item, True)
            self.setCursor(Qt.CursorShape.ClosedHandCursor)

    def mouseMoveEvent(self, event):
        if (
            not self._drag_item
            or not self._drag_start_pos
            or not (event.buttons() & Qt.MouseButton.LeftButton)
        ):
            super().mouseMoveEvent(event)
            return

        if (event.pos() - self._drag_start_pos).manhattanLength() < QApplication.startDragDistance():
            super().mouseMoveEvent(event)
            return

        mime = self.mimeData([self._drag_item])
        if not mime or not mime.hasFormat(self.MIME):
            return

        rect = self.visualItemRect(self._drag_item)
        drag = QDrag(self)
        drag.setMimeData(mime)
        drag.setPixmap(self.viewport().grab(rect))
        drag.setHotSpot(event.pos() - rect.topLeft())
        self._dragging = True
        drag.exec(Qt.DropAction.MoveAction)
        self._dragging = False
        self._set_item_held(self._drag_item, False)
        self._drag_item = None
        self._drag_start_pos = None
        self.unsetCursor()

    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)
        if self._drag_item and not self._dragging:
            self._set_item_held(self._drag_item, False)
        self._drag_item = None
        self._drag_start_pos = None
        self.unsetCursor()

    def _set_item_held(self, item: QListWidgetItem, held: bool):
        if item is None:
            return
        if held:
            try:
                if item.data(self._held_bg_role) is None:
                    item.setData(self._held_bg_role, item.background())
                if item.data(self._held_fg_role) is None:
                    item.setData(self._held_fg_role, item.foreground())
                color = item.background().color()
                if not color.isValid():
                    color = QColor("#60A5FA")
                    color.setAlpha(80)
                color = QColor(color)
                color.setAlpha(min(255, color.alpha() + 80))
                item.setBackground(color)
                item.setForeground(QColor("#FFFFFF"))
            except RuntimeError:
                # Item já foi destruído pelo Qt durante operação de drag/drop.
                return
            return

        try:
            original_bg = item.data(self._held_bg_role)
            original_fg = item.data(self._held_fg_role)
            if original_bg is not None:
                item.setBackground(original_bg)
                item.setData(self._held_bg_role, None)
            if original_fg is not None:
                item.setForeground(original_fg)
                item.setData(self._held_fg_role, None)
        except RuntimeError:
            # Item já foi destruído pelo Qt durante operação de drag/drop.
            return


class DayCellWidget(QFrame):
    day_selected = pyqtSignal(QDate)
    event_clicked = pyqtSignal(dict)
    event_dropped = pyqtSignal(str, str, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("agenda_month_day_cell")
        self.date = QDate.currentDate()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(3, 3, 3, 3)
        layout.setSpacing(2)

        self.day_label = QLabel("1")
        self.day_label.setObjectName("agenda_day_number")
        layout.addWidget(self.day_label)

        self.events_list = MonthDayEventList()
        self.events_list.setMaximumHeight(96)
        self.events_list.event_clicked.connect(self._relay_event_clicked)
        self.events_list.event_dropped.connect(self.event_dropped.emit)
        layout.addWidget(self.events_list)

    def set_day(self, date: QDate, in_current_month: bool, is_today: bool = False, is_selected: bool = False):
        self.date = date
        self.events_list.set_date(date.toString("yyyy-MM-dd"))
        self.day_label.setText(str(date.day()))
        if in_current_month:
            border_color = "#2A3140"
            if is_today:
                border_color = "#22C55E"
            if is_selected:
                border_color = "#7DD3FC"
            self.setStyleSheet(
                f"QFrame#agenda_month_day_cell {{ background: #1A1D24; border: 2px solid {border_color}; border-radius: 10px; }}"
            )
            self.day_label.setStyleSheet("color: #F8FAFC; font-weight: 600;")
        else:
            self.setStyleSheet("QFrame#agenda_month_day_cell { background: #13161C; border: 1px solid #202733; border-radius: 10px; }")
            self.day_label.setStyleSheet("color: #64748B;")

    def set_events(self, events: List[dict]):
        self.events_list.clear()
        display_events = [
            e for e in events
            if not e.get("_fixed_virtual", False) and not e.get("auto_generated", False)
        ]
        if not display_events:
            return

        for event in display_events[:8]:
            icon = TYPE_ICONS.get(event.get("type", "casual"), NerdIcons.PIN)
            item = QListWidgetItem(icon)
            item.setData(Qt.ItemDataRole.UserRole, event)
            color = QColor(
                TYPE_COLORS.get(
                    str(event.get("type", "casual")).strip().lower(),
                    PRIORITY_COLORS.get(int(event.get("priority", 2)), "#60A5FA"),
                )
            )
            color.setAlpha(70)
            item.setBackground(color)
            self.events_list.addItem(item)

    def mousePressEvent(self, event):
        self.day_selected.emit(self.date)
        super().mousePressEvent(event)

    def _relay_event_clicked(self, event_data: dict):
        self.day_selected.emit(self.date)
        self.event_clicked.emit(event_data)


class HourlyAgendaTable(QTableWidget):
    event_clicked = pyqtSignal(dict)
    event_retimed = pyqtSignal(str, str, str, int)  # (event_id, source_date, target_date, target_hour)

    MIME = MonthDayEventList.MIME

    def __init__(self, parent=None):
        super().__init__(24, 2, parent)
        self.current_date_str = ""
        self.setObjectName("hourly_agenda_table")
        self.setHorizontalHeaderLabels(["Hora", "Compromisso"])
        self.verticalHeader().setVisible(False)
        self.horizontalHeader().setStretchLastSection(True)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectItems)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDropIndicatorShown(True)
        self.setDefaultDropAction(Qt.DropAction.MoveAction)
        # Movimentação é totalmente customizada para evitar perda de conteúdo de célula.
        self.setDragDropMode(QAbstractItemView.DragDropMode.NoDragDrop)
        self.itemClicked.connect(self._on_item_clicked)
        self.setStyleSheet(
            "QTableWidget { color: #FFFFFF; gridline-color: #2A3140; }"
            "QHeaderView::section { color: #FFFFFF; background: #1A1D24; }"
        )

        for hour in range(24):
            hour_item = QTableWidgetItem(f"{hour:02d}:00")
            hour_item.setFlags(Qt.ItemFlag.ItemIsEnabled)
            hour_item.setForeground(QColor("#FFFFFF"))
            self.setItem(hour, 0, hour_item)

    def set_date(self, date_str: str):
        self.current_date_str = date_str

    def clear_events(self):
        for row in range(24):
            empty = QTableWidgetItem("")
            empty.setForeground(QColor("#FFFFFF"))
            self.setItem(row, 1, empty)

    def set_events(self, events: List[dict]):
        self.clear_events()

        buckets: Dict[int, List[dict]] = {}
        for event in events:
            start_dt = event.get("_start_dt")
            end_dt = event.get("_end_dt")
            if not start_dt:
                continue
            if not end_dt or end_dt <= start_dt:
                end_dt = start_dt + timedelta(minutes=max(30, int(event.get("duration_minutes", 30))))

            cursor = start_dt.replace(minute=0, second=0, microsecond=0)
            while cursor < end_dt:
                if not self.current_date_str or cursor.date().isoformat() == self.current_date_str:
                    buckets.setdefault(cursor.hour, []).append(event)
                cursor += timedelta(hours=1)

        for hour, hour_events in buckets.items():
            labels = []
            for event in hour_events:
                icon = TYPE_ICONS.get(event.get("type", "casual"), NerdIcons.PIN)
                labels.append(f"{icon} {event.get('title', 'Sem título')}")

            unique_labels = list(dict.fromkeys(labels))
            cell = QTableWidgetItem("\n".join(unique_labels))
            primary_event = hour_events[0]
            color = QColor(
                TYPE_COLORS.get(
                    str(primary_event.get("type", "casual")).strip().lower(),
                    PRIORITY_COLORS.get(int(primary_event.get("priority", 2)), "#60A5FA"),
                )
            )
            color.setAlpha(110)
            cell.setBackground(color)
            cell.setForeground(QColor("#FFFFFF"))
            if len(hour_events) == 1:
                cell.setData(Qt.ItemDataRole.UserRole, hour_events[0])
            self.setItem(hour, 1, cell)

    def mimeData(self, items):  # noqa: N802
        selected = self.currentItem()
        if not selected:
            return super().mimeData(items)
        event_data = selected.data(Qt.ItemDataRole.UserRole) or {}
        if not event_data:
            return super().mimeData(items)

        payload = {
            "event_id": str(event_data.get("id", "")),
            "source_date": str(event_data.get("date", self.current_date_str)),
        }
        mime = QMimeData()
        mime.setData(self.MIME, json.dumps(payload).encode("utf-8"))
        return mime

    def dragEnterEvent(self, event):
        if event.mimeData().hasFormat(self.MIME):
            event.acceptProposedAction()
            return
        super().dragEnterEvent(event)

    def dragMoveEvent(self, event):
        if event.mimeData().hasFormat(self.MIME):
            event.acceptProposedAction()
            return
        super().dragMoveEvent(event)

    def dropEvent(self, event):
        if not event.mimeData().hasFormat(self.MIME):
            super().dropEvent(event)
            return

        row = self.rowAt(event.position().toPoint().y())
        if row < 0:
            event.ignore()
            return

        try:
            data = json.loads(bytes(event.mimeData().data(self.MIME)).decode("utf-8"))
            event_id = str(data.get("event_id", ""))
            source_date = str(data.get("source_date", ""))
            if event_id and self.current_date_str:
                self.event_retimed.emit(event_id, source_date, self.current_date_str, row)
                event.acceptProposedAction()
                return
        except Exception as exc:
            logger.debug("Falha no drop de hora: %s", exc)

        event.ignore()

    def _on_item_clicked(self, item: QTableWidgetItem):
        if item.column() != 1:
            return
        event_data = item.data(Qt.ItemDataRole.UserRole)
        if event_data:
            self.event_clicked.emit(event_data)


class AgendaView(QWidget):
    navigate_to = pyqtSignal(str)

    def __init__(self, agenda_controller=None):
        super().__init__()
        self.controller = agenda_controller
        self.current_month = QDate.currentDate().addDays(1 - QDate.currentDate().day())
        self.selected_date = QDate.currentDate()
        self.selected_event: Optional[dict] = None

        self.events_by_date: Dict[str, List[dict]] = {}
        self._active_animations: List[QPropertyAnimation] = []
        self._day_cell_map: Dict[str, DayCellWidget] = {}

        self.setup_ui()
        self.setup_connections()
        self.setup_toolbar()
        self.load_month_data()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.toolbar = QToolBar()
        layout.addWidget(self.toolbar)

        controls = QWidget()
        controls_layout = QHBoxLayout(controls)
        controls_layout.setContentsMargins(8, 8, 8, 6)

        self.prev_month_btn = QPushButton("◀")
        self.next_month_btn = QPushButton("▶")
        self.today_btn = QPushButton("Hoje")
        self.routine_settings_btn = QPushButton(NerdIcons.SETTINGS)
        self.routine_settings_btn.setToolTip("Configurar rotina")
        self.routine_settings_btn.setFont(nerd_font(12))
        self.month_label = QLabel("")
        self.month_label.setObjectName("agenda_month_label")
        self.month_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        controls_layout.addWidget(self.prev_month_btn)
        controls_layout.addWidget(self.month_label, 1)
        controls_layout.addWidget(self.today_btn)
        controls_layout.addWidget(self.routine_settings_btn)
        controls_layout.addWidget(self.next_month_btn)

        layout.addWidget(controls)

        self.main_splitter = QSplitter(Qt.Orientation.Horizontal)

        month_panel = QWidget()
        month_layout = QVBoxLayout(month_panel)
        month_layout.setContentsMargins(6, 4, 6, 6)
        month_layout.setSpacing(6)

        week_header = QHBoxLayout()
        for label in ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]:
            day_header = QLabel(label)
            day_header.setAlignment(Qt.AlignmentFlag.AlignCenter)
            day_header.setStyleSheet("font-weight: 600; color: #93A4C3;")
            week_header.addWidget(day_header)
        month_layout.addLayout(week_header)

        self.month_grid = QGridLayout()
        self.month_grid.setContentsMargins(0, 0, 0, 0)
        self.month_grid.setSpacing(5)
        self.day_cells: List[DayCellWidget] = []

        for row in range(6):
            for col in range(7):
                cell = DayCellWidget()
                cell.day_selected.connect(self.on_day_selected)
                cell.event_clicked.connect(self.show_event_details)
                cell.event_dropped.connect(self.on_event_dropped_to_day)
                self.month_grid.addWidget(cell, row, col)
                self.day_cells.append(cell)
            self.month_grid.setRowStretch(row, 1)
        for col in range(7):
            self.month_grid.setColumnStretch(col, 1)

        month_layout.addLayout(self.month_grid)
        self.main_splitter.addWidget(month_panel)

        self.detail_panel = QWidget()
        detail_layout = QVBoxLayout(self.detail_panel)
        detail_layout.setContentsMargins(12, 6, 12, 12)

        self.day_detail_label = QLabel("")
        self.day_detail_label.setObjectName("agenda_day_detail_label")
        self.day_detail_label.setStyleSheet("color: #FFFFFF; font-weight: 600;")

        actions = QHBoxLayout()
        self.add_event_btn = QPushButton(f"{NerdIcons.PLUS} Adicionar compromisso")
        self.refresh_day_btn = QPushButton(f"{NerdIcons.REFRESH} Reorganizar agenda")
        self.refresh_day_btn.setToolTip(
            "Redistribui compromissos flexíveis respeitando aulas, refeições e blocos protegidos."
        )
        self.hide_day_detail_btn = QPushButton("Ocultar")
        actions.addWidget(self.add_event_btn)
        actions.addWidget(self.refresh_day_btn)
        actions.addWidget(self.hide_day_detail_btn)

        self.hour_table = HourlyAgendaTable()
        self.hour_table.setMinimumWidth(360)

        details_group = QGroupBox("Detalhes do compromisso")
        details_layout = QVBoxLayout(details_group)
        self.event_title_label = QLabel("Nenhum compromisso selecionado")
        self.event_time_label = QLabel("")
        self.event_description_label = QLabel("")
        self.event_description_label.setWordWrap(True)
        self.event_title_label.setStyleSheet("color: #FFFFFF;")
        self.event_time_label.setStyleSheet("color: #FFFFFF;")
        self.event_description_label.setStyleSheet("color: #FFFFFF;")
        details_layout.addWidget(self.event_title_label)
        details_layout.addWidget(self.event_time_label)
        details_layout.addWidget(self.event_description_label)

        self.delete_event_btn = QPushButton("Excluir")
        self.complete_event_btn = QPushButton("Concluir / Reabrir")
        self.delete_event_btn.setEnabled(False)
        self.complete_event_btn.setEnabled(False)

        detail_layout.addWidget(self.day_detail_label)
        detail_layout.addLayout(actions)
        detail_layout.addWidget(self.hour_table, 1)
        detail_layout.addWidget(details_group)
        detail_layout.addWidget(self.complete_event_btn)
        detail_layout.addWidget(self.delete_event_btn)

        self.main_splitter.addWidget(self.detail_panel)
        self.main_splitter.setSizes([1400, 0])
        layout.addWidget(self.main_splitter)
        self.detail_panel.setVisible(False)
        self.detail_panel.setMaximumWidth(0)
        self.detail_opacity = QGraphicsOpacityEffect(self.detail_panel)
        self.detail_opacity.setOpacity(0.0)
        self.detail_panel.setGraphicsEffect(self.detail_opacity)

        self.status_label = QLabel("Pronto")
        self.status_label.setContentsMargins(12, 8, 12, 12)
        layout.addWidget(self.status_label)

    def setup_toolbar(self):
        self.back_action = QAction("← Voltar", self)
        self.back_action.triggered.connect(lambda: self.navigate_to.emit("dashboard"))

        self.refresh_action = QAction(f"{NerdIcons.REFRESH} Reorganizar agenda", self)
        self.refresh_action.setToolTip(
            "Redistribui compromissos flexíveis respeitando aulas, refeições e blocos protegidos."
        )
        self.refresh_action.setStatusTip(
            "Reorganizar agenda respeitando horários reservados."
        )
        self.refresh_action.triggered.connect(self.rebalance_agenda)

        self.toolbar.addAction(self.back_action)
        self.toolbar.addSeparator()
        self.toolbar.addAction(self.refresh_action)

    def setup_connections(self):
        self.prev_month_btn.clicked.connect(self.previous_month)
        self.next_month_btn.clicked.connect(self.next_month)
        self.today_btn.clicked.connect(self.go_to_today)
        self.routine_settings_btn.clicked.connect(self.open_routine_settings)
        self.add_event_btn.clicked.connect(self.add_event)
        self.refresh_day_btn.clicked.connect(self.rebalance_agenda)
        self.hide_day_detail_btn.clicked.connect(self.hide_day_detail)

        self.hour_table.event_clicked.connect(self.show_event_details)
        self.hour_table.event_retimed.connect(self.on_event_retimed)

        self.delete_event_btn.clicked.connect(self.delete_selected_event)
        self.complete_event_btn.clicked.connect(self.toggle_selected_event)

        if self.controller:
            self.controller.agenda_updated.connect(self.on_agenda_updated)
            self.controller.event_added.connect(self.on_event_added)
            self.controller.event_updated.connect(self.on_event_updated)
            self.controller.event_deleted.connect(self.on_event_deleted)

    def load_month_data(self):
        self.events_by_date.clear()
        for date in self._month_grid_dates():
            day_str = date.toString("yyyy-MM-dd")
            self.events_by_date[day_str] = self._load_day_events(day_str)

        self.render_month()
        if self.detail_panel.isVisible():
            self.load_day_detail(self.selected_date)

    def _load_day_events(self, date_str: str) -> List[dict]:
        events = []

        try:
            if self.controller and hasattr(self.controller, "agenda_manager"):
                raw_events = self.controller.agenda_manager.get_day_events(date_str)
                events = [event.to_dict() if hasattr(event, "to_dict") else event for event in raw_events]
            elif self.controller and hasattr(self.controller, "load_agenda"):
                events = self.controller.load_agenda(date_str) or []
        except Exception as exc:
            logger.error("Erro ao carregar agenda de %s: %s", date_str, exc)

        normalized = [_normalize_event(event) for event in events]
        normalized.extend(self._build_fixed_events(date_str, normalized))
        normalized.sort(key=lambda e: e.get("start", ""))
        return normalized

    def _build_fixed_events(self, date_str: str, events: List[dict]) -> List[dict]:
        manager = getattr(self.controller, "agenda_manager", None)
        generated: List[dict] = []
        if manager and hasattr(manager, "get_virtual_fixed_events"):
            try:
                generated = [
                    _normalize_event({**event, "_fixed_virtual": True})
                    for event in (manager.get_virtual_fixed_events(date_str) or [])
                ]
            except Exception as exc:
                logger.debug("Falha ao carregar blocos virtuais da rotina para %s: %s", date_str, exc)

        existing_slots = {
            (event.get("type"), event.get("start_time"), event.get("title", "").lower())
            for event in events
        }
        return [
            event for event in generated
            if (event.get("type"), event.get("start_time"), event.get("title", "").lower()) not in existing_slots
        ]

    def _month_grid_dates(self) -> List[QDate]:
        first = QDate(self.current_month.year(), self.current_month.month(), 1)
        start = first.addDays(-(first.dayOfWeek() - 1))
        return [start.addDays(i) for i in range(42)]

    def render_month(self):
        self.month_label.setText(self.current_month.toString("MMMM yyyy"))
        dates = self._month_grid_dates()
        selected_str = self.selected_date.toString("yyyy-MM-dd")
        today_str = QDate.currentDate().toString("yyyy-MM-dd")
        self._day_cell_map.clear()

        for cell, date in zip(self.day_cells, dates):
            in_current_month = date.month() == self.current_month.month()
            cell.setVisible(in_current_month)
            if not in_current_month:
                continue
            date_str = date.toString("yyyy-MM-dd")
            self._day_cell_map[date_str] = cell
            cell.set_day(
                date,
                in_current_month,
                is_today=(date_str == today_str),
                is_selected=(date_str == selected_str),
            )
            day_events = self.events_by_date.get(date.toString("yyyy-MM-dd"), [])
            cell.set_events(day_events)

    def load_day_detail(self, date: QDate):
        self.selected_date = date
        self.render_month()
        date_str = date.toString("yyyy-MM-dd")
        if date_str not in self.events_by_date:
            self.events_by_date[date_str] = self._load_day_events(date_str)

        events = self.events_by_date.get(date_str, [])
        self.day_detail_label.setText(date.toString("dddd, dd/MM/yyyy"))
        self.hour_table.set_date(date_str)
        self.hour_table.set_events(events)

    def previous_month(self):
        self.current_month = self.current_month.addMonths(-1)
        self.load_month_data()

    def next_month(self):
        self.current_month = self.current_month.addMonths(1)
        self.load_month_data()

    def go_to_today(self):
        today = QDate.currentDate()
        self.current_month = QDate(today.year(), today.month(), 1)
        self.selected_date = today
        self.load_month_data()

    def _reload_agenda_view(self):
        self.load_month_data()

    def _apply_rebalance_feedback(self, rebalance_result: Dict[str, Any]):
        if rebalance_result.get("success"):
            moved = int(rebalance_result.get("moved_count", 0) or 0)
            unscheduled = int(rebalance_result.get("unscheduled_count", 0) or 0)
            if unscheduled > 0:
                self.status_label.setText(
                    "Agenda reorganizada respeitando horários reservados: "
                    f"{moved} compromisso(s) redistribuído(s), {unscheduled} sem novo encaixe"
                )
            else:
                self.status_label.setText(
                    "Agenda reorganizada respeitando horários reservados: "
                    f"{moved} compromisso(s) redistribuído(s)"
                )
        elif rebalance_result.get("error"):
            self.status_label.setText("A reorganização falhou, mas a agenda foi recarregada")
        else:
            self.status_label.setText("Agenda atualizada")
        QTimer.singleShot(1800, lambda: self.status_label.setText("Pronto"))

    def rebalance_agenda(self):
        self.status_label.setText(
            "Reorganizando agenda com base em aulas, refeições e blocos protegidos..."
        )
        rebalance_result = {}
        if self.controller and hasattr(self.controller, "rebalance_schedule"):
            rebalance_result = self.controller.rebalance_schedule() or {}
        self._reload_agenda_view()
        self._apply_rebalance_feedback(rebalance_result)

    def refresh(self):
        self.status_label.setText("Atualizando visualização da agenda...")
        self._reload_agenda_view()
        QTimer.singleShot(1200, lambda: self.status_label.setText("Pronto"))

    def open_routine_settings(self):
        if not self.controller:
            return

        initial = {}
        if hasattr(self.controller, "get_routine_preferences"):
            initial = self.controller.get_routine_preferences() or {}

        dialog = RoutineSettingsDialog(initial, self)
        if dialog.exec():
            payload = dialog.get_payload()
            if hasattr(self.controller, "update_routine_preferences"):
                result = self.controller.update_routine_preferences(payload)
                if result:
                    self.status_label.setText("Rotina atualizada")
                    self.rebalance_agenda()

    def on_day_selected(self, date: QDate):
        self.show_day_detail()
        self.load_day_detail(date)
        self._animate_day_cell_flash(date.toString("yyyy-MM-dd"), "#7DD3FC")

    def show_day_detail(self):
        self._animate_detail_panel(True)

    def hide_day_detail(self):
        self._animate_detail_panel(False)

    def on_event_dropped_to_day(self, event_id: str, source_date: str, target_date: str):
        if not event_id or source_date == target_date:
            return
        if not self.controller or not hasattr(self.controller, "move_event"):
            return

        self._apply_local_move(event_id, source_date, target_date)
        self._animate_day_cell_flash(target_date, "#38BDF8")
        self.status_label.setText(f"Compromisso movido para {target_date}")

        if self.controller.move_event(event_id, target_date):
            self.events_by_date[source_date] = self._load_day_events(source_date)
            self.events_by_date[target_date] = self._load_day_events(target_date)
        else:
            # Reverte para estado persistido em caso de falha.
            self.events_by_date[source_date] = self._load_day_events(source_date)
            self.events_by_date[target_date] = self._load_day_events(target_date)
        self.render_month()
        if self.detail_panel.isVisible():
            self.load_day_detail(self.selected_date)

    def on_event_retimed(self, event_id: str, source_date: str, target_date: str, target_hour: int):
        if not event_id:
            return
        if not self.controller or not hasattr(self.controller, "move_event"):
            return

        self._apply_local_move(event_id, source_date, target_date, target_hour)
        self._animate_day_cell_flash(target_date, "#38BDF8")
        self._animate_hour_cell_flash(target_hour)
        self.status_label.setText(f"Compromisso ajustado para {target_hour:02d}:00")

        if self.controller.move_event(event_id, target_date, target_hour):
            self.events_by_date[source_date] = self._load_day_events(source_date)
            self.events_by_date[target_date] = self._load_day_events(target_date)
        else:
            self.events_by_date[source_date] = self._load_day_events(source_date)
            self.events_by_date[target_date] = self._load_day_events(target_date)
        self.render_month()
        if self.detail_panel.isVisible():
            self.load_day_detail(self.selected_date)

    def _apply_local_move(self, event_id: str, source_date: str, target_date: str, target_hour: Optional[int] = None):
        """Atualiza UI imediatamente no drop antes de persistir no controller."""
        source_events = list(self.events_by_date.get(source_date, []))
        target_events = list(self.events_by_date.get(target_date, []))

        moved_event = None
        source_filtered = []
        for event in source_events:
            if str(event.get("id")) == str(event_id) and moved_event is None:
                moved_event = dict(event)
                continue
            source_filtered.append(event)

        if not moved_event:
            return

        start_dt = moved_event.get("_start_dt")
        end_dt = moved_event.get("_end_dt")
        if not start_dt:
            return

        duration = (end_dt - start_dt) if end_dt and end_dt > start_dt else timedelta(minutes=max(30, int(moved_event.get("duration_minutes", 30))))
        new_date = datetime.fromisoformat(f"{target_date}T00:00:00").date()
        new_hour = start_dt.hour if target_hour is None else max(0, min(23, int(target_hour)))
        new_minute = start_dt.minute if target_hour is None else 0
        new_start = datetime.combine(new_date, datetime.min.time()).replace(hour=new_hour, minute=new_minute)
        new_end = new_start + duration

        moved_event["start"] = new_start.isoformat()
        moved_event["end"] = new_end.isoformat()
        moved_event["_start_dt"] = new_start
        moved_event["_end_dt"] = new_end
        moved_event["start_time"] = new_start.strftime("%H:%M")
        moved_event["end_time"] = new_end.strftime("%H:%M")
        moved_event["date"] = target_date
        moved_event["duration_minutes"] = int(duration.total_seconds() // 60)

        target_events.append(moved_event)
        target_events.sort(key=lambda e: e.get("start", ""))
        source_filtered.sort(key=lambda e: e.get("start", ""))

        self.events_by_date[source_date] = source_filtered
        self.events_by_date[target_date] = target_events
        self.render_month()
        if self.detail_panel.isVisible():
            self.load_day_detail(self.selected_date)

    def _track_animation(self, animation: QPropertyAnimation):
        self._active_animations.append(animation)

        def _cleanup():
            if animation in self._active_animations:
                self._active_animations.remove(animation)
            animation.deleteLater()

        animation.finished.connect(_cleanup)
        animation.start()

    def _animate_detail_panel(self, show: bool):
        target_width = 480 if show else 0
        start_width = max(0, self.detail_panel.maximumWidth())

        if show:
            self.detail_panel.setVisible(True)

        width_anim = QPropertyAnimation(self.detail_panel, b"maximumWidth")
        width_anim.setDuration(220)
        width_anim.setEasingCurve(QEasingCurve.Type.OutCubic if show else QEasingCurve.Type.InCubic)
        width_anim.setStartValue(start_width)
        width_anim.setEndValue(target_width)

        opacity_anim = QPropertyAnimation(self.detail_opacity, b"opacity")
        opacity_anim.setDuration(220)
        opacity_anim.setStartValue(self.detail_opacity.opacity())
        opacity_anim.setEndValue(1.0 if show else 0.0)
        opacity_anim.setEasingCurve(QEasingCurve.Type.OutCubic if show else QEasingCurve.Type.InCubic)

        if not show:
            opacity_anim.finished.connect(lambda: self.detail_panel.setVisible(False))

        self.main_splitter.setSizes([1400, 0] if not show else [980, 480])
        self._track_animation(width_anim)
        self._track_animation(opacity_anim)

    def _animate_day_cell_flash(self, date_str: str, color_hex: str):
        cell = self._day_cell_map.get(date_str)
        if not cell:
            return

        effect = QGraphicsColorizeEffect(cell)
        effect.setColor(QColor(color_hex))
        effect.setStrength(0.0)
        cell.setGraphicsEffect(effect)

        flash_in = QPropertyAnimation(effect, b"strength")
        flash_in.setDuration(130)
        flash_in.setStartValue(0.0)
        flash_in.setEndValue(0.75)
        flash_in.setEasingCurve(QEasingCurve.Type.OutQuad)

        flash_out = QPropertyAnimation(effect, b"strength")
        flash_out.setDuration(210)
        flash_out.setStartValue(0.75)
        flash_out.setEndValue(0.0)
        flash_out.setEasingCurve(QEasingCurve.Type.InOutQuad)

        flash_in.finished.connect(lambda: self._track_animation(flash_out))
        flash_out.finished.connect(lambda: cell.setGraphicsEffect(None))

        self._track_animation(flash_in)

    def _animate_hour_cell_flash(self, hour: int):
        row = max(0, min(23, int(hour)))
        item = self.hour_table.item(row, 1)
        if not item:
            return
        original_bg = QColor(item.background().color())
        pulse = QColor("#38BDF8")
        pulse.setAlpha(170)
        item.setBackground(pulse)
        QTimer.singleShot(180, lambda: item.setBackground(original_bg))

    def show_event_details(self, event: dict):
        if event.get("type") == "revisao_dominical":
            self.navigate_to.emit("weekly_review")
            return

        self.selected_event = event
        self.event_title_label.setText(event.get("title", "Sem título"))
        self.event_time_label.setText(
            f"{event.get('start_time', '--:--')} - {event.get('end_time', '--:--')}"
        )
        description = event.get("description")
        if not description:
            metadata = event.get("metadata", {}) or {}
            description = metadata.get("description", "")
        self.event_description_label.setText(description or "Sem descrição")

        is_virtual_fixed = bool(event.get("_fixed_virtual", False))
        self.delete_event_btn.setEnabled(not is_virtual_fixed)
        self.complete_event_btn.setEnabled(not is_virtual_fixed)

    def add_event(self):
        dialog = AddEventDialog(self.controller, self.selected_date, self)
        if dialog.exec():
            self.rebalance_agenda()

    def delete_selected_event(self):
        if not self.selected_event:
            return

        event_id = self.selected_event.get("id")
        if not event_id or self.selected_event.get("_fixed_virtual", False):
            return

        if QMessageBox.question(
            self,
            "Excluir compromisso",
            f"Deseja excluir '{self.selected_event.get('title', 'evento')}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        ) != QMessageBox.StandardButton.Yes:
            return

        if self.controller and hasattr(self.controller, "delete_event"):
            self.controller.delete_event(event_id)
            self.rebalance_agenda()

    def toggle_selected_event(self):
        if not self.selected_event or self.selected_event.get("_fixed_virtual", False):
            return

        event_id = self.selected_event.get("id")
        completed = not bool(self.selected_event.get("completed", False))
        if self.controller and hasattr(self.controller, "toggle_event_completion"):
            self.controller.toggle_event_completion(event_id, completed)
            self.rebalance_agenda()

    @pyqtSlot(str, list)
    def on_agenda_updated(self, date_str: str, events: list):
        self.events_by_date[date_str] = [_normalize_event(evt) for evt in events]
        self.events_by_date[date_str].extend(self._build_fixed_events(date_str, self.events_by_date[date_str]))
        self.events_by_date[date_str].sort(key=lambda e: e.get("start", ""))
        self.render_month()
        if self.selected_date.toString("yyyy-MM-dd") == date_str:
            self.load_day_detail(self.selected_date)

    @pyqtSlot(dict)
    def on_event_added(self, event_data: dict):
        self.status_label.setText(f"Compromisso adicionado: {event_data.get('title', '')}")

    @pyqtSlot(str, dict)
    def on_event_updated(self, event_id: str, event_data: dict):
        self.status_label.setText(f"Compromisso atualizado: {event_id}")

    @pyqtSlot(str)
    def on_event_deleted(self, event_id: str):
        self.status_label.setText(f"Compromisso removido: {event_id}")

    def on_view_activated(self):
        self.go_to_today()

    def cleanup(self):
        pass


class RoutineSettingsDialog(QDialog):
    """Diálogo para configurar rotina diária e revisão dominical."""

    def __init__(self, initial: Optional[dict] = None, parent=None):
        super().__init__(parent)
        self.initial = initial or {}
        self.setWindowTitle("Configurações da Rotina")
        self.setModal(True)
        self.setMinimumWidth(420)
        self.setup_ui()

    def _to_qtime(self, value: str, fallback: QTime) -> QTime:
        t = QTime.fromString(str(value or ""), "HH:mm")
        return t if t.isValid() else fallback

    def setup_ui(self):
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.sleep_start = QTimeEdit()
        self.sleep_start.setDisplayFormat("HH:mm")
        self.sleep_start.setTime(self._to_qtime(self.initial.get("sleep_start", "23:00"), QTime(23, 0)))
        form.addRow("Dormir:", self.sleep_start)

        self.sleep_end = QTimeEdit()
        self.sleep_end.setDisplayFormat("HH:mm")
        self.sleep_end.setTime(self._to_qtime(self.initial.get("sleep_end", "07:00"), QTime(7, 0)))
        form.addRow("Acordar:", self.sleep_end)

        self.breakfast = QTimeEdit()
        self.breakfast.setDisplayFormat("HH:mm")
        self.breakfast.setTime(self._to_qtime(self.initial.get("breakfast_time", "08:00"), QTime(8, 0)))
        form.addRow("Café da manhã:", self.breakfast)

        self.lunch = QTimeEdit()
        self.lunch.setDisplayFormat("HH:mm")
        self.lunch.setTime(self._to_qtime(self.initial.get("lunch_time", "12:30"), QTime(12, 30)))
        form.addRow("Almoço:", self.lunch)

        self.dinner = QTimeEdit()
        self.dinner.setDisplayFormat("HH:mm")
        self.dinner.setTime(self._to_qtime(self.initial.get("dinner_time", "19:30"), QTime(19, 30)))
        form.addRow("Jantar:", self.dinner)

        self.weekly_review_time = QTimeEdit()
        self.weekly_review_time.setDisplayFormat("HH:mm")
        self.weekly_review_time.setTime(self._to_qtime(self.initial.get("weekly_review_time", "18:00"), QTime(18, 0)))
        form.addRow("Revisão (domingo):", self.weekly_review_time)

        layout.addLayout(form)

        info = QLabel(
            "A revisão semanal analisa seu desempenho de estudos "
            "(leituras + check-ins) e será agendada automaticamente "
            "em todos os domingos no horário definido."
        )
        info.setWordWrap(True)
        info.setStyleSheet("color: #9CA3AF;")
        layout.addWidget(info)

        buttons = QHBoxLayout()
        cancel_btn = QPushButton("Cancelar")
        save_btn = QPushButton("Salvar")
        cancel_btn.clicked.connect(self.reject)
        save_btn.clicked.connect(self.accept)
        buttons.addStretch()
        buttons.addWidget(save_btn)
        buttons.addWidget(cancel_btn)
        layout.addLayout(buttons)

    def get_payload(self) -> Dict[str, Any]:
        return {
            "sleep_start": self.sleep_start.time().toString("HH:mm"),
            "sleep_end": self.sleep_end.time().toString("HH:mm"),
            "breakfast_time": self.breakfast.time().toString("HH:mm"),
            "lunch_time": self.lunch.time().toString("HH:mm"),
            "dinner_time": self.dinner.time().toString("HH:mm"),
            "weekly_review_time": self.weekly_review_time.time().toString("HH:mm"),
        }


class AddEventDialog(QDialog):
    """Diálogo para adicionar evento manualmente."""

    def __init__(self, controller, default_date, parent=None):
        super().__init__(parent)
        self.controller = controller
        self.default_date = default_date
        self._vault_root = self._resolve_vault_root()

        self.setWindowTitle("Adicionar compromisso")
        self.setModal(True)
        self.setMinimumWidth(480)

        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.title_input = QLineEdit()
        self.title_input.setPlaceholderText("Título do compromisso")
        form.addRow("Título:", self.title_input)

        self.date_input = QDateTimeEdit()
        self.date_input.setDate(self.default_date)
        self.date_input.setDisplayFormat("dd/MM/yyyy")
        self.date_input.setCalendarPopup(True)

        time_row = QHBoxLayout()
        time_row.addWidget(self.date_input)

        self.start_time_input = QTimeEdit()
        self.start_time_input.setDisplayFormat("HH:mm")
        self.start_time_input.setTime(QTime(9, 0))

        self.end_time_input = QTimeEdit()
        self.end_time_input.setDisplayFormat("HH:mm")
        self.end_time_input.setTime(QTime(10, 0))

        time_row.addWidget(QLabel("Início"))
        time_row.addWidget(self.start_time_input)
        time_row.addWidget(QLabel("Fim"))
        time_row.addWidget(self.end_time_input)

        time_wrap = QWidget()
        time_wrap.setLayout(time_row)
        form.addRow("Quando:", time_wrap)

        self.recurrence_combo = QComboBox()
        self.recurrence_combo.addItem("Evento único", "none")
        self.recurrence_combo.addItem("Diário", "daily")
        self.recurrence_combo.addItem("Semanal", "weekly")
        form.addRow("Recorrência:", self.recurrence_combo)

        recurrence_days_wrap = QWidget()
        recurrence_days_layout = QHBoxLayout(recurrence_days_wrap)
        recurrence_days_layout.setContentsMargins(0, 0, 0, 0)
        recurrence_days_layout.setSpacing(6)
        self.weekday_checks: Dict[str, QCheckBox] = {}
        weekday_labels = [
            ("mon", "Seg"),
            ("tue", "Ter"),
            ("wed", "Qua"),
            ("thu", "Qui"),
            ("fri", "Sex"),
            ("sat", "Sáb"),
            ("sun", "Dom"),
        ]
        for key, label in weekday_labels:
            checkbox = QCheckBox(label)
            self.weekday_checks[key] = checkbox
            recurrence_days_layout.addWidget(checkbox)
        recurrence_days_layout.addStretch(1)
        form.addRow("Dias da semana:", recurrence_days_wrap)

        self.recurrence_end_date = QDateTimeEdit()
        self.recurrence_end_date.setDate(self.default_date)
        self.recurrence_end_date.setDisplayFormat("dd/MM/yyyy")
        self.recurrence_end_date.setCalendarPopup(True)
        form.addRow("Repetir até:", self.recurrence_end_date)

        self.type_combo = QComboBox()
        self.type_combo.addItems([
            "leitura",
            "revisao",
            "producao",
            "aula",
            "prova",
            "seminario",
            "orientacao",
            "reuniao",
            "lazer",
            "refeicao",
            "sono",
            "casual",
        ])

        self.priority_combo = QComboBox()
        self.priority_combo.addItems(["Baixa", "Média", "Alta", "Fixo", "Bloqueio"])
        self.priority_combo.setCurrentIndex(1)

        type_row = QHBoxLayout()
        type_row.addWidget(self.type_combo)
        type_row.addWidget(self.priority_combo)
        type_wrap = QWidget()
        type_wrap.setLayout(type_row)
        form.addRow("Categoria:", type_wrap)

        self.description_input = QTextEdit()
        self.description_input.setMaximumHeight(90)
        form.addRow("Descrição:", self.description_input)

        discipline_row = QHBoxLayout()
        self.discipline_input = QComboBox()
        self.discipline_input.setEditable(True)
        self.discipline_input.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self._reload_disciplines()
        self.new_discipline_button = QPushButton("Nova")
        self.new_discipline_button.clicked.connect(self._create_selected_discipline)
        discipline_row.addWidget(self.discipline_input, 1)
        discipline_row.addWidget(self.new_discipline_button)
        discipline_wrap = QWidget()
        discipline_wrap.setLayout(discipline_row)
        form.addRow("Disciplina:", discipline_wrap)

        layout.addLayout(form)

        buttons = QHBoxLayout()
        cancel_btn = QPushButton("Cancelar")
        save_btn = QPushButton("Salvar")
        cancel_btn.clicked.connect(self.reject)
        save_btn.clicked.connect(self.save_event)
        buttons.addStretch()
        buttons.addWidget(save_btn)
        buttons.addWidget(cancel_btn)
        layout.addLayout(buttons)
        self.recurrence_combo.currentIndexChanged.connect(self._update_recurrence_visibility)
        self._update_recurrence_visibility()

    def save_event(self):
        title = self.title_input.text().strip()
        if not title:
            QMessageBox.warning(self, "Aviso", "Informe um título para o compromisso.")
            return

        date_str = self.date_input.date().toString("yyyy-MM-dd")
        start = f"{date_str} {self.start_time_input.time().toString('HH:mm')}"
        end = f"{date_str} {self.end_time_input.time().toString('HH:mm')}"
        try:
            start_dt = datetime.strptime(start, "%Y-%m-%d %H:%M")
            end_dt = datetime.strptime(end, "%Y-%m-%d %H:%M")
        except ValueError:
            QMessageBox.warning(self, "Aviso", "Data/hora inválidas.")
            return
        if end_dt <= start_dt:
            QMessageBox.warning(self, "Aviso", "O horário de término deve ser posterior ao início.")
            return

        priority_map = {
            "Baixa": 1,
            "Média": 2,
            "Alta": 3,
            "Fixo": 4,
            "Bloqueio": 5,
        }

        payload = {
            "title": title,
            "start": start,
            "end": end,
            "event_type": self.type_combo.currentText(),
            "priority": priority_map.get(self.priority_combo.currentText(), 2),
            "description": self.description_input.toPlainText().strip(),
            "discipline": self._selected_discipline() or None,
        }
        recurrence = self._build_recurrence_definition(start_dt, end_dt)
        if recurrence is None:
            return

        discipline_name = self._selected_discipline()
        if discipline_name and self._vault_root:
            ensure_discipline_note(self._vault_root, discipline_name)

        occurrences = self._expand_occurrences(payload, start_dt, end_dt, recurrence)
        if not occurrences:
            QMessageBox.warning(self, "Recorrência", "Nenhuma ocorrência válida foi gerada.")
            return

        created_ids: List[str] = []
        if self.controller and hasattr(self.controller, "add_event"):
            for occurrence in occurrences:
                event_id = self.controller.add_event(occurrence)
                if not event_id:
                    QMessageBox.warning(self, "Erro", "Não foi possível salvar um dos compromissos.")
                    return
                created_ids.append(str(event_id))

        if discipline_name and self._vault_root:
            for index, occurrence in enumerate(occurrences):
                append_event_link(
                    self._vault_root,
                    discipline_name,
                    title=title,
                    start=str(occurrence.get("start") or ""),
                    end=str(occurrence.get("end") or ""),
                    event_id=created_ids[index] if index < len(created_ids) else "",
                )

        self.accept()

    def _update_recurrence_visibility(self):
        recurrence_type = self.recurrence_combo.currentData()
        is_weekly = recurrence_type == "weekly"
        has_recurrence = recurrence_type in {"daily", "weekly"}

        for checkbox in self.weekday_checks.values():
            checkbox.setVisible(is_weekly)
        self.recurrence_end_date.setVisible(has_recurrence)

    def _build_recurrence_definition(self, start_dt: datetime, end_dt: datetime) -> Optional[Dict[str, Any]]:
        recurrence_type = str(self.recurrence_combo.currentData() or "none")
        if recurrence_type == "none":
            return {"type": "none"}

        until_date = self.recurrence_end_date.date().toString("yyyy-MM-dd")
        try:
            until_dt = datetime.strptime(until_date, "%Y-%m-%d").date()
        except ValueError:
            QMessageBox.warning(self, "Recorrência", "Data limite inválida.")
            return None

        if until_dt < start_dt.date():
            QMessageBox.warning(self, "Recorrência", "A data limite deve ser igual ou posterior ao início.")
            return None

        if recurrence_type == "daily":
            return {"type": "daily", "end_date": until_date, "interval": 1}

        selected_days = [
            key for key, checkbox in self.weekday_checks.items() if checkbox.isChecked()
        ]
        if not selected_days:
            weekday_map = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
            selected_days = [weekday_map[start_dt.weekday()]]
        return {
            "type": "weekly",
            "end_date": until_date,
            "interval": 1,
            "days": selected_days,
        }

    def _expand_occurrences(
        self,
        payload: Dict[str, Any],
        start_dt: datetime,
        end_dt: datetime,
        recurrence: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        recurrence_type = str(recurrence.get("type") or "none")
        duration = end_dt - start_dt
        if duration.total_seconds() <= 0:
            return []

        if recurrence_type == "none":
            single = dict(payload)
            single["start"] = start_dt.isoformat()
            single["end"] = end_dt.isoformat()
            single["recurrence"] = recurrence
            return [single]

        try:
            until_date = datetime.strptime(str(recurrence.get("end_date") or ""), "%Y-%m-%d").date()
        except ValueError:
            return []

        weekday_map = {
            "mon": 0, "tue": 1, "wed": 2, "thu": 3,
            "fri": 4, "sat": 5, "sun": 6,
        }
        selected_weekdays = [weekday_map[key] for key in recurrence.get("days", []) if key in weekday_map]
        if recurrence_type == "weekly" and not selected_weekdays:
            selected_weekdays = [start_dt.weekday()]

        occurrences: List[Dict[str, Any]] = []
        cursor = start_dt
        while cursor.date() <= until_date:
            include = False
            if recurrence_type == "daily":
                include = True
            elif recurrence_type == "weekly":
                include = cursor.weekday() in selected_weekdays

            if include:
                occ_start = cursor.replace(
                    hour=start_dt.hour,
                    minute=start_dt.minute,
                    second=0,
                    microsecond=0,
                )
                occ_end = occ_start + duration
                occurrence = dict(payload)
                occurrence["start"] = occ_start.isoformat()
                occurrence["end"] = occ_end.isoformat()
                occurrence["recurrence"] = recurrence
                occurrences.append(occurrence)

            cursor += timedelta(days=1)

        return occurrences

    def _resolve_vault_root(self):
        candidates = []
        if self.controller and getattr(self.controller, "agenda_manager", None):
            manager = self.controller.agenda_manager
            candidates.append(getattr(manager, "vault_path", ""))
        candidates.append(getattr(getattr(core_settings, "paths", None), "vault", ""))
        return resolve_vault_root(*candidates)

    def _reload_disciplines(self):
        current = self._selected_discipline()
        self.discipline_input.clear()
        names = list_disciplines(self._vault_root) if self._vault_root else []
        self.discipline_input.addItems(names)
        if current:
            idx = self.discipline_input.findText(current)
            if idx >= 0:
                self.discipline_input.setCurrentIndex(idx)
            else:
                self.discipline_input.setEditText(current)

    def _selected_discipline(self) -> str:
        return self.discipline_input.currentText().strip() if self.discipline_input else ""

    def _create_selected_discipline(self):
        name = self._selected_discipline()
        if not name:
            QMessageBox.information(self, "Disciplina", "Informe o nome da nova disciplina.")
            self.discipline_input.setFocus()
            return
        created = ensure_discipline_note(self._vault_root, name) if self._vault_root else None
        if not created:
            QMessageBox.warning(self, "Disciplina", "Não foi possível criar a nota da disciplina.")
            return
        self._reload_disciplines()


class FindSlotDialog(QDialog):
    """Mantido para compatibilidade."""

    def __init__(self, controller, date, parent=None):
        super().__init__(parent)
        self.controller = controller
        self.date = date
        self.setWindowTitle("Encontrar slot livre")
        self.setModal(True)

        layout = QVBoxLayout(self)
        form_layout = QFormLayout()

        self.date_input = QDateTimeEdit()
        self.date_input.setDate(self.date)
        self.date_input.setCalendarPopup(True)
        form_layout.addRow("Data:", self.date_input)

        self.duration_input = QSpinBox()
        self.duration_input.setRange(15, 480)
        self.duration_input.setValue(60)
        self.duration_input.setSuffix(" min")
        form_layout.addRow("Duração:", self.duration_input)

        self.start_hour = QSpinBox()
        self.start_hour.setRange(0, 23)
        self.start_hour.setValue(8)
        form_layout.addRow("A partir de:", self.start_hour)

        self.end_hour = QSpinBox()
        self.end_hour.setRange(1, 24)
        self.end_hour.setValue(22)
        form_layout.addRow("Até:", self.end_hour)

        layout.addLayout(form_layout)

        self.results = QListWidget()
        layout.addWidget(self.results)

        buttons = QHBoxLayout()
        find_btn = QPushButton("Buscar")
        close_btn = QPushButton("Fechar")
        find_btn.clicked.connect(self.find_slots)
        close_btn.clicked.connect(self.reject)
        buttons.addWidget(find_btn)
        buttons.addStretch()
        buttons.addWidget(close_btn)
        layout.addLayout(buttons)

    def find_slots(self):
        self.results.clear()
        if not self.controller or not hasattr(self.controller, "find_free_slots"):
            return
        date_str = self.date_input.date().toString("yyyy-MM-dd")
        self.controller.find_free_slots(
            date_str,
            self.duration_input.value(),
            self.start_hour.value(),
            self.end_hour.value(),
        )


class EmergencyModeDialog(QDialog):
    """Mantido para compatibilidade."""

    def __init__(self, controller, parent=None):
        super().__init__(parent)
        self.controller = controller
        self.setWindowTitle("Modo emergência")
        self.setModal(True)

        layout = QVBoxLayout(self)
        self.objective_input = QLineEdit()
        self.days_input = QSpinBox()
        self.days_input.setRange(1, 14)
        self.days_input.setValue(3)
        self.focus_input = QLineEdit()

        form_layout = QFormLayout()
        form_layout.addRow("Objetivo:", self.objective_input)
        form_layout.addRow("Dias:", self.days_input)
        form_layout.addRow("Foco:", self.focus_input)
        layout.addLayout(form_layout)

        buttons = QHBoxLayout()
        activate_btn = QPushButton("Ativar")
        cancel_btn = QPushButton("Cancelar")
        activate_btn.clicked.connect(self.activate_emergency)
        cancel_btn.clicked.connect(self.reject)
        buttons.addStretch()
        buttons.addWidget(activate_btn)
        buttons.addWidget(cancel_btn)
        layout.addLayout(buttons)

    def activate_emergency(self):
        objective = self.objective_input.text().strip()
        if not objective:
            QMessageBox.warning(self, "Aviso", "Informe um objetivo.")
            return

        if self.controller and hasattr(self.controller, "activate_emergency_mode"):
            self.controller.activate_emergency_mode(
                objective,
                self.days_input.value(),
                self.focus_input.text().strip() or None,
            )
        self.accept()
