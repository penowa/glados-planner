"""Diálogo com lista consolidada de compromissos agendados."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional, Tuple

from PyQt6.QtCore import QDate, Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QComboBox,
    QDateEdit,
    QDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from core.modules.commitment_groups import (
    CommitmentGroupKey,
    event_group_key_from_mapping,
)

PRIORITY_COLORS = {
    1: "#93C5FD",
    2: "#60A5FA",
    3: "#FBBF24",
    4: "#FB7185",
    5: "#EF4444",
}

TYPE_COLORS = {
    "aula": "#FACC15",
}

TYPE_LABELS = {
    "leitura": "Leitura",
    "revisao": "Revisão",
    "dissertacao": "Dissertação",
    "producao": "Produção",
    "aula": "Aula",
    "prova": "Prova",
    "seminario": "Seminário",
    "orientacao": "Orientação",
    "reuniao": "Reunião",
    "grupo_estudo": "Grupo de estudo",
    "lazer": "Lazer",
    "casual": "Casual",
    "transcricao": "Transcrição",
    "checkin": "Check-in",
    "revisao_dominical": "Revisão dominical",
}


@dataclass
class CommitmentSummary:
    group_key: CommitmentGroupKey
    event_type: str
    title: str
    color: str
    expected_end: datetime
    session_count: int = 1
    priority: int = 2
    sort_key: Tuple[str, str] = field(default_factory=tuple)


def _event_color(event_type: str, priority: int) -> str:
    normalized_type = str(event_type or "casual").strip().lower()
    if normalized_type == "producao":
        normalized_type = "dissertacao"
    return TYPE_COLORS.get(
        normalized_type,
        PRIORITY_COLORS.get(int(priority or 2), "#93C5FD"),
    )


def _to_datetime(value: Any) -> Optional[datetime]:
    if isinstance(value, datetime):
        return value
    if not value:
        return None
    text = str(value).strip().replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(text)
    except Exception:
        return None


def _normalize_event(raw_event: Any) -> Optional[Dict[str, Any]]:
    if raw_event is None:
        return None

    if hasattr(raw_event, "to_dict"):
        event = dict(raw_event.to_dict())
    elif isinstance(raw_event, dict):
        event = dict(raw_event)
    else:
        event_type = getattr(getattr(raw_event, "type", None), "value", None) or getattr(raw_event, "type", "casual")
        priority = getattr(raw_event, "priority", 2)
        if hasattr(priority, "value"):
            priority = priority.value
        event = {
            "id": getattr(raw_event, "id", ""),
            "type": event_type,
            "title": getattr(raw_event, "title", "Sem título"),
            "start": getattr(getattr(raw_event, "start", None), "isoformat", lambda: "")(),
            "end": getattr(getattr(raw_event, "end", None), "isoformat", lambda: "")(),
            "completed": bool(getattr(raw_event, "completed", False)),
            "book_id": getattr(raw_event, "book_id", None),
            "discipline": getattr(raw_event, "discipline", None),
            "priority": priority,
            "metadata": getattr(raw_event, "metadata", {}) or {},
        }

    event_type = str(event.get("type") or event.get("event_type") or "casual").strip().lower()
    if event_type == "producao":
        event_type = "dissertacao"
    event["type"] = event_type

    priority = event.get("priority", 2)
    if hasattr(priority, "value"):
        priority = priority.value
    try:
        event["priority"] = int(priority)
    except Exception:
        event["priority"] = 2

    metadata = event.get("metadata") or {}
    event["metadata"] = metadata
    event.setdefault("book_id", metadata.get("book_id"))
    event.setdefault("title", "Sem título")
    event["start_dt"] = _to_datetime(event.get("start"))
    event["end_dt"] = _to_datetime(event.get("end"))
    return event


def _strip_title_prefix(title: str, prefixes: Iterable[str]) -> str:
    cleaned = re.sub(r"\s+", " ", str(title or "").strip())
    lowered = cleaned.lower()
    for prefix in prefixes:
        normalized_prefix = str(prefix).strip().lower()
        if lowered.startswith(normalized_prefix):
            cleaned = cleaned[len(normalized_prefix) :].strip()
            if cleaned.startswith(":"):
                cleaned = cleaned[1:].strip()
            break
    return cleaned or "Sem título"


def _format_commitment_title(event_type: str, sample_title: str) -> str:
    label = TYPE_LABELS.get(event_type, event_type.replace("_", " ").capitalize())
    raw_title = str(sample_title or "").strip() or "Sem título"
    lowered = raw_title.lower()

    if lowered.startswith(f"{label.lower()}:"):
        return raw_title

    if event_type == "leitura":
        clean = _strip_title_prefix(raw_title, ("Leitura:",))
        return f"Leitura: {clean}"

    if event_type == "revisao":
        clean = _strip_title_prefix(raw_title, ("Revisão:",))
        return f"Revisão: {clean}"

    if event_type in {"dissertacao", "producao"} and lowered.startswith("dissertação:"):
        return raw_title

    if lowered.startswith(f"{label.lower()} "):
        return raw_title

    return f"{label}: {raw_title}"


def collect_commitment_summaries(events: Iterable[Any]) -> List[CommitmentSummary]:
    grouped: Dict[CommitmentGroupKey, Dict[str, Any]] = {}

    for raw_event in events or []:
        event = _normalize_event(raw_event)
        if not event:
            continue

        group_key = event_group_key_from_mapping(event)
        if not group_key:
            continue

        end_dt = event.get("end_dt")
        if not end_dt:
            continue

        bucket = grouped.get(group_key)
        if bucket is None:
            bucket = {
                "event_type": group_key[0],
                "sample_title": event.get("title", "Sem título"),
                "priority": event.get("priority", 2),
                "expected_end": end_dt,
                "session_count": 0,
            }
            grouped[group_key] = bucket

        bucket["session_count"] += 1
        if end_dt > bucket["expected_end"]:
            bucket["expected_end"] = end_dt
        if int(event.get("priority", 2)) > int(bucket.get("priority", 2)):
            bucket["priority"] = int(event.get("priority", 2))

    summaries: List[CommitmentSummary] = []
    for group_key, bucket in grouped.items():
        event_type = bucket["event_type"]
        title = _format_commitment_title(event_type, bucket["sample_title"])
        priority = int(bucket.get("priority", 2))
        summaries.append(
            CommitmentSummary(
                group_key=group_key,
                event_type=event_type,
                title=title,
                color=_event_color(event_type, priority),
                expected_end=bucket["expected_end"],
                session_count=int(bucket.get("session_count", 1)),
                priority=priority,
                sort_key=(title.lower(), group_key[2]),
            )
        )

    summaries.sort(key=lambda item: (item.expected_end, item.sort_key))
    return summaries


def _hex_to_rgba(hex_color: str, alpha: float) -> str:
    color = str(hex_color or "").strip().lstrip("#")
    if len(color) != 6:
        return "rgba(255,255,255,0.04)"
    try:
        red = int(color[0:2], 16)
        green = int(color[2:4], 16)
        blue = int(color[4:6], 16)
    except ValueError:
        return "rgba(255,255,255,0.04)"
    normalized_alpha = max(0.0, min(float(alpha), 1.0))
    return f"rgba({red},{green},{blue},{normalized_alpha:.2f})"


def _format_expected_end(value: datetime) -> str:
    return value.strftime("Previsto até %d/%m/%Y às %H:%M")


class CommitmentActionDialog(QDialog):
    """Pop-up com dropdown para escolher a ação do compromisso."""

    ACTION_EDIT = "editar"
    ACTION_REMOVE = "remover"

    def __init__(self, summary: CommitmentSummary, parent=None):
        super().__init__(parent)
        self.summary = summary
        self.selected_action = ""
        self.setWindowTitle("Ação do compromisso")
        self.setModal(True)
        self.setMinimumWidth(360)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        title = QLabel(self.summary.title)
        title.setWordWrap(True)
        title.setStyleSheet("font-size: 14px; font-weight: 600; color: #FFFFFF;")
        layout.addWidget(title)

        form = QFormLayout()
        self.action_combo = QComboBox()
        self.action_combo.addItem("Editar", self.ACTION_EDIT)
        self.action_combo.addItem("Remover", self.ACTION_REMOVE)
        form.addRow("Ação:", self.action_combo)
        layout.addLayout(form)

        buttons = QHBoxLayout()
        confirm_btn = QPushButton("Continuar")
        cancel_btn = QPushButton("Cancelar")
        confirm_btn.clicked.connect(self._on_confirm)
        cancel_btn.clicked.connect(self.reject)
        buttons.addStretch()
        buttons.addWidget(confirm_btn)
        buttons.addWidget(cancel_btn)
        layout.addLayout(buttons)

    def _on_confirm(self) -> None:
        self.selected_action = str(self.action_combo.currentData() or "")
        self.accept()


class CommitmentDeadlineDialog(QDialog):
    """Diálogo para escolher nova data de conclusão."""

    def __init__(self, summary: CommitmentSummary, parent=None):
        super().__init__(parent)
        self.summary = summary
        self.setWindowTitle("Nova data de conclusão")
        self.setModal(True)
        self.setMinimumWidth(340)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        info = QLabel(
            f"Escolha a nova data prevista para concluir:\n{self.summary.title}"
        )
        info.setWordWrap(True)
        info.setStyleSheet("color: #D1D5DB;")
        layout.addWidget(info)

        form = QFormLayout()
        self.deadline_input = QDateEdit()
        self.deadline_input.setCalendarPopup(True)
        self.deadline_input.setDisplayFormat("dd/MM/yyyy")
        self.deadline_input.setMinimumDate(QDate.currentDate().addDays(1))
        initial = QDate(
            self.summary.expected_end.year,
            self.summary.expected_end.month,
            self.summary.expected_end.day,
        )
        if initial <= QDate.currentDate():
            initial = QDate.currentDate().addDays(7)
        self.deadline_input.setDate(initial)
        form.addRow("Concluir até:", self.deadline_input)
        layout.addLayout(form)

        buttons = QHBoxLayout()
        save_btn = QPushButton("Remanejar sessões")
        cancel_btn = QPushButton("Cancelar")
        save_btn.clicked.connect(self.accept)
        cancel_btn.clicked.connect(self.reject)
        buttons.addStretch()
        buttons.addWidget(save_btn)
        buttons.addWidget(cancel_btn)
        layout.addLayout(buttons)

    def selected_deadline(self) -> str:
        return self.deadline_input.date().toString("yyyy-MM-dd")


class CommitmentCard(QFrame):
    clicked = pyqtSignal(object)

    def __init__(self, summary: CommitmentSummary, parent=None):
        super().__init__(parent)
        self.summary = summary
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setObjectName("commitment_card")
        self.setStyleSheet(
            f"QFrame#commitment_card {{ background-color: {_hex_to_rgba(summary.color, 0.14)}; "
            f"border-left: 4px solid {summary.color}; border-radius: 8px; }}"
            "QFrame#commitment_card:hover { background-color: rgba(255,255,255,0.06); }"
        )
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(4)

        title = QLabel(summary.title)
        title.setWordWrap(True)
        title.setStyleSheet("font-size: 14px; font-weight: 600; color: #FFFFFF;")
        layout.addWidget(title)

        end_label = QLabel(_format_expected_end(summary.expected_end))
        end_label.setWordWrap(True)
        end_label.setStyleSheet("font-size: 12px; color: #D1D5DB;")
        layout.addWidget(end_label)

        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.summary)
        super().mousePressEvent(event)


class CommitmentsListDialog(QDialog):
    """Lista consolidada de compromissos, agrupada por cor da agenda."""

    def __init__(self, agenda_backend=None, parent=None):
        super().__init__(parent)
        self.agenda_backend = agenda_backend
        self.setWindowTitle("Lista de Compromissos")
        self.setModal(True)
        self.resize(560, 720)
        self._build_ui()
        self.refresh()

    def _resolve_events(self) -> List[Any]:
        manager = None
        if self.agenda_backend is not None:
            if hasattr(self.agenda_backend, "agenda_manager"):
                manager = self.agenda_backend.agenda_manager
            elif hasattr(self.agenda_backend, "events"):
                manager = self.agenda_backend

        if manager is None:
            return []

        events_map = getattr(manager, "events", None)
        if isinstance(events_map, dict):
            return list(events_map.values())
        return []

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        header = QLabel(
            "Compromissos agendados agrupados por tipo. "
            "Clique em um card para editar a data de conclusão ou remover o compromisso."
        )
        header.setWordWrap(True)
        header.setStyleSheet("color: #9CA3AF; font-size: 12px;")
        root.addWidget(header)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.list_host = QWidget()
        self.list_layout = QVBoxLayout(self.list_host)
        self.list_layout.setContentsMargins(0, 0, 0, 0)
        self.list_layout.setSpacing(14)
        self.scroll_area.setWidget(self.list_host)
        root.addWidget(self.scroll_area, 1)

        actions = QHBoxLayout()
        refresh_btn = QPushButton("Atualizar")
        refresh_btn.clicked.connect(self.refresh)
        close_btn = QPushButton("Fechar")
        close_btn.clicked.connect(self.accept)
        actions.addWidget(refresh_btn)
        actions.addStretch()
        actions.addWidget(close_btn)
        root.addLayout(actions)

    def refresh(self) -> None:
        summaries = collect_commitment_summaries(self._resolve_events())
        self._render_summaries(summaries)

    def _clear_layout(self) -> None:
        while self.list_layout.count():
            item = self.list_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

    def _render_summaries(self, summaries: List[CommitmentSummary]) -> None:
        self._clear_layout()

        if not summaries:
            empty = QLabel("Nenhum compromisso agendado encontrado.")
            empty.setWordWrap(True)
            empty.setStyleSheet("color: #8F8F8F; font-size: 13px;")
            self.list_layout.addWidget(empty)
            self.list_layout.addStretch()
            return

        sections: Dict[str, List[CommitmentSummary]] = {}
        for summary in summaries:
            sections.setdefault(summary.color, []).append(summary)

        ordered_colors = sorted(
            sections.keys(),
            key=lambda color: (
                min(item.expected_end for item in sections[color]),
                color,
            ),
        )

        for color in ordered_colors:
            section_items = sections[color]
            self.list_layout.addWidget(self._build_color_separator(color))

            for summary in section_items:
                card = CommitmentCard(summary)
                card.clicked.connect(self._on_card_clicked)
                self.list_layout.addWidget(card)

        self.list_layout.addStretch()

    def _build_color_separator(self, color: str) -> QFrame:
        line = QFrame()
        line.setFixedHeight(3)
        line.setStyleSheet(
            f"QFrame {{ background-color: {color}; border-radius: 2px; margin-top: 4px; }}"
        )
        return line

    def _on_card_clicked(self, summary: CommitmentSummary) -> None:
        action_dialog = CommitmentActionDialog(summary, self)
        if action_dialog.exec() != QDialog.DialogCode.Accepted:
            return

        if action_dialog.selected_action == CommitmentActionDialog.ACTION_EDIT:
            self._handle_edit(summary)
            return

        if action_dialog.selected_action == CommitmentActionDialog.ACTION_REMOVE:
            self._handle_remove(summary)

    def _handle_edit(self, summary: CommitmentSummary) -> None:
        deadline_dialog = CommitmentDeadlineDialog(summary, self)
        if deadline_dialog.exec() != QDialog.DialogCode.Accepted:
            return

        new_deadline = deadline_dialog.selected_deadline()
        if not self.agenda_backend or not hasattr(self.agenda_backend, "reschedule_commitment"):
            QMessageBox.warning(self, "Agenda", "Backend de agenda indisponível.")
            return

        result = self.agenda_backend.reschedule_commitment(summary.group_key, new_deadline)
        if result.get("success"):
            QMessageBox.information(
                self,
                "Compromisso remanejado",
                "As sessões foram redistribuídas conforme a nova data de conclusão.",
            )
            self._refresh_agenda_views()
            self.refresh()
            return

        QMessageBox.warning(
            self,
            "Falha ao remanejar",
            str(result.get("error") or "Não foi possível remanejar o compromisso."),
        )

    def _handle_remove(self, summary: CommitmentSummary) -> None:
        answer = QMessageBox.question(
            self,
            "Remover compromisso",
            f"Deseja remover este compromisso da agenda?\n\n{summary.title}",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return

        if not self.agenda_backend or not hasattr(self.agenda_backend, "remove_commitment"):
            QMessageBox.warning(self, "Agenda", "Backend de agenda indisponível.")
            return

        result = self.agenda_backend.remove_commitment(summary.group_key)
        if result.get("success"):
            QMessageBox.information(
                self,
                "Compromisso removido",
                "O compromisso foi removido e a agenda foi reorganizada.",
            )
            self._refresh_agenda_views()
            self.refresh()
            return

        QMessageBox.warning(
            self,
            "Falha ao remover",
            str(result.get("error") or "Não foi possível remover o compromisso."),
        )

    def _refresh_agenda_views(self) -> None:
        parent = self.parent()
        if parent and hasattr(parent, "load_month_data"):
            parent.load_month_data()
        elif parent and hasattr(parent, "_reload_agenda_view"):
            parent._reload_agenda_view()
