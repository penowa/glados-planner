"""Card com lista dos próximos compromissos."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from PyQt6.QtWidgets import QFrame, QLabel, QSizePolicy, QVBoxLayout, QWidget
from PyQt6.QtCore import Qt


class UpcomingCommitmentsCard(QFrame):
    """Card simples com os próximos compromissos em formato de lista."""

    TYPE_COLORS = {
        "aula": "#4A90E2",
        "leitura": "#2ECC71",
        "producao": "#E67E22",
        "revisao": "#1ABC9C",
        "orientacao": "#C0392B",
        "reuniao": "#2980B9",
        "grupo_estudo": "#16A085",
        "refeicao": "#F1C40F",
        "sono": "#7F8C8D",
        "lazer": "#9B59B6",
        "casual": "#95A5A6",
        "prova": "#E74C3C",
        "seminario": "#D35400",
        "transcricao": "#34495E",
        "checkin": "#27AE60",
        "revisao_dominical": "#8E44AD",
    }

    def __init__(
        self,
        agenda_backend: Any = None,
        max_items: int = 7,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self.agenda_backend = agenda_backend
        self._max_items_cap = max(1, int(max_items))
        self.max_items = self._max_items_cap
        self.setObjectName("upcoming_commitments_card")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        title = QLabel("Próximos compromissos")
        title.setStyleSheet("font-size: 16px; font-weight: 600;")
        layout.addWidget(title)

        subtitle = QLabel("Lista dos compromissos marcados a partir de agora.")
        subtitle.setStyleSheet("font-size: 12px; color: #8A94A6;")
        layout.addWidget(subtitle)

        self.list_container = QWidget()
        self.list_layout = QVBoxLayout(self.list_container)
        self.list_layout.setContentsMargins(0, 6, 0, 0)
        self.list_layout.setSpacing(8)
        self.list_layout.setSizeConstraint(QVBoxLayout.SizeConstraint.SetMinimumSize)
        self.list_container.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        layout.addWidget(self.list_container, 1)

    def refresh(self) -> None:
        self._update_max_items_for_available_height()
        events = self._collect_upcoming_events()
        self._render_events(events)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        if self._update_max_items_for_available_height():
            self.refresh()

    def _update_max_items_for_available_height(self) -> bool:
        available_height = max(0, self.list_container.height() - self.list_layout.contentsMargins().top())
        item_height = self._estimate_item_height()
        per_item = max(1, item_height + self.list_layout.spacing())
        calculated = max(1, available_height // per_item) if available_height > 0 else 1
        new_max_items = min(self._max_items_cap, int(calculated))
        if new_max_items != self.max_items:
            self.max_items = new_max_items
            return True
        return False

    def _estimate_item_height(self) -> int:
        title_height = self.fontMetrics().height() + 8
        meta_height = self.fontMetrics().height() + 6
        item_margins = 20  # 10px top + 10px bottom
        item_inner_spacing = 6
        return title_height + meta_height + item_margins + item_inner_spacing

    def _collect_upcoming_events(self) -> List[Dict[str, Any]]:
        now = datetime.now()
        manager = self._resolve_agenda_manager()
        if manager and hasattr(manager, "events"):
            raw_events = list(getattr(manager, "events", {}).values())
            normalized = [self._normalize_event(event) for event in raw_events]
        else:
            normalized = self._collect_from_controller(now)

        upcoming = [
            event for event in normalized
            if event and not event.get("completed", False)
            and event.get("end") and event["end"] >= now
        ]
        upcoming.sort(key=lambda item: item["start"])
        return upcoming[: self.max_items]

    def _collect_from_controller(self, now: datetime) -> List[Dict[str, Any]]:
        collected: List[Dict[str, Any]] = []
        if not self.agenda_backend or not hasattr(self.agenda_backend, "get_day_events"):
            return collected

        for offset in range(7):
            day = (now + timedelta(days=offset)).date().isoformat()
            try:
                events = self.agenda_backend.get_day_events(day)
            except Exception:
                continue
            for event in events or []:
                normalized = self._normalize_event(event)
                if normalized:
                    collected.append(normalized)
        return collected

    def _resolve_agenda_manager(self) -> Any:
        if self.agenda_backend is None:
            return None
        if hasattr(self.agenda_backend, "agenda_manager"):
            return self.agenda_backend.agenda_manager
        if hasattr(self.agenda_backend, "events"):
            return self.agenda_backend
        return None

    def _normalize_event(self, event: Any) -> Optional[Dict[str, Any]]:
        if event is None:
            return None

        if hasattr(event, "start"):
            start = getattr(event, "start", None)
            end = getattr(event, "end", None)
            event_type = getattr(getattr(event, "type", None), "value", None) or str(getattr(event, "type", "casual"))
            return {
                "title": str(getattr(event, "title", "Sem título")),
                "start": self._to_datetime(start),
                "end": self._to_datetime(end),
                "type": str(event_type).lower(),
                "completed": bool(getattr(event, "completed", False)),
            }

        if isinstance(event, dict):
            start = event.get("start") or event.get("start_time")
            end = event.get("end") or event.get("end_time")
            event_type = event.get("type") or event.get("event_type") or "casual"
            return {
                "title": str(event.get("title") or event.get("description") or "Sem título"),
                "start": self._to_datetime(start),
                "end": self._to_datetime(end),
                "type": str(event_type).lower(),
                "completed": bool(event.get("completed", False)),
            }
        return None

    def _to_datetime(self, value: Any) -> Optional[datetime]:
        if isinstance(value, datetime):
            return value
        if not value:
            return None
        text = str(value).strip().replace("Z", "+00:00")
        try:
            return datetime.fromisoformat(text)
        except Exception:
            return None

    def _render_events(self, events: List[Dict[str, Any]]) -> None:
        self._clear_list_layout()

        if not events:
            empty = QLabel("Nenhum compromisso marcado nos próximos dias.")
            empty.setWordWrap(True)
            empty.setStyleSheet("color: #8A94A6; font-size: 13px;")
            self.list_layout.addWidget(empty)
            self.list_layout.addStretch()
            return

        for event in events:
            event_type = event.get("type", "casual")
            color = self.TYPE_COLORS.get(event_type, "#6C757D")

            item = QFrame()
            item.setStyleSheet(
                f"QFrame {{ background-color: {self._hex_to_rgba(color, 0.14)}; border-left: 4px solid {color}; border-radius: 6px; }}"
            )
            item_layout = QVBoxLayout(item)
            item_layout.setContentsMargins(10, 10, 10, 10)
            item_layout.setSpacing(6)

            title = QLabel(event.get("title", "Sem título"))
            title.setWordWrap(True)
            title.setTextFormat(Qt.TextFormat.PlainText)
            title.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
            title.setStyleSheet("font-size: 13px; font-weight: 600; color: #FFFFFF;")
            title.setMinimumHeight(title.fontMetrics().height() + 4)
            item_layout.addWidget(title)

            meta = QLabel(f"{self._format_date_time(event.get('start'))}  •  {self._humanize_type(event_type)}")
            meta.setAlignment(Qt.AlignmentFlag.AlignLeft)
            meta.setWordWrap(True)
            meta.setStyleSheet("font-size: 12px; color: #FFFFFF;")
            meta.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
            meta.setMinimumHeight(meta.fontMetrics().height() + 2)
            item_layout.addWidget(meta)

            self.list_layout.addWidget(item)

        self.list_layout.addStretch()

    def _clear_list_layout(self) -> None:
        while self.list_layout.count():
            item = self.list_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

    def _format_date_time(self, dt: Optional[datetime]) -> str:
        if not dt:
            return "Data não disponível"
        today = datetime.now().date()
        target = dt.date()
        if target == today:
            day_label = "Hoje"
        elif target == today + timedelta(days=1):
            day_label = "Amanhã"
        else:
            day_label = dt.strftime("%d/%m")
        return f"{day_label} {dt.strftime('%H:%M')}"

    def _humanize_type(self, event_type: str) -> str:
        return event_type.replace("_", " ").strip().capitalize()

    def _hex_to_rgba(self, hex_color: str, alpha: float) -> str:
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
