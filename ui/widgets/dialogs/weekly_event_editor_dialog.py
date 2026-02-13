"""Diálogo para edição e exclusão de eventos da semana."""

from datetime import datetime, timedelta
from typing import Dict, List, Optional

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ui.widgets.cards.event_creation_card import EventCreationCard


class WeeklyEventEditorDialog(QDialog):
    """Editor semanal de eventos com lista + formulário."""

    event_changed = pyqtSignal()

    def __init__(self, agenda_backend=None, reading_manager=None, week_start=None, parent=None):
        super().__init__(parent)
        self.agenda_backend = agenda_backend
        self.reading_manager = reading_manager
        self.week_start = week_start or datetime.now().date() - timedelta(days=datetime.now().weekday())
        self.week_end = self.week_start + timedelta(days=6)
        self.agenda_manager = self._resolve_agenda_manager()

        self.events_by_id: Dict[str, Dict] = {}
        self.current_event_id: Optional[str] = None

        self.setWindowTitle("Detalhes da Semana")
        self.resize(1200, 800)

        self._build_ui()
        self._load_week_events()

    def _resolve_agenda_manager(self):
        if self.agenda_backend is None:
            return None

        if hasattr(self.agenda_backend, "agenda_manager"):
            return self.agenda_backend.agenda_manager

        if hasattr(self.agenda_backend, "events") and hasattr(self.agenda_backend, "_save_events"):
            return self.agenda_backend

        return None

    def _build_ui(self):
        root = QVBoxLayout(self)

        header = QLabel(
            f"Eventos da semana: {self.week_start.strftime('%d/%m/%Y')} - {self.week_end.strftime('%d/%m/%Y')}"
        )
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(header)

        content = QWidget()
        content_layout = QHBoxLayout(content)

        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)

        self.events_list = QListWidget()
        self.events_list.currentItemChanged.connect(self._on_selected_event_changed)

        self.reload_button = QPushButton("Atualizar Lista")
        self.reload_button.clicked.connect(self._load_week_events)

        left_layout.addWidget(self.events_list, 1)
        left_layout.addWidget(self.reload_button)

        self.editor = EventCreationCard(
            agenda_controller=self.agenda_backend,
            reading_manager=self.reading_manager,
            parent=self,
        )
        self.editor.set_title("Editar Evento")
        if hasattr(self.editor, "save_btn"):
            self.editor.save_btn.hide()
        if hasattr(self.editor, "cancel_btn"):
            self.editor.cancel_btn.hide()

        content_layout.addWidget(left_panel, 1)
        content_layout.addWidget(self.editor, 2)

        root.addWidget(content, 1)

        actions = QHBoxLayout()
        self.save_button = QPushButton("Salvar Alterações")
        self.delete_button = QPushButton("Excluir Evento")
        self.close_button = QPushButton("Fechar")

        self.save_button.clicked.connect(self._on_save_clicked)
        self.delete_button.clicked.connect(self._on_delete_clicked)
        self.close_button.clicked.connect(self.close)

        actions.addWidget(self.save_button)
        actions.addWidget(self.delete_button)
        actions.addStretch()
        actions.addWidget(self.close_button)
        root.addLayout(actions)

    def _event_obj_to_dict(self, event_obj) -> Dict:
        if isinstance(event_obj, dict):
            data = dict(event_obj)
        elif hasattr(event_obj, "to_dict"):
            data = event_obj.to_dict()
        else:
            data = {
                "id": getattr(event_obj, "id", ""),
                "type": getattr(getattr(event_obj, "type", None), "value", "casual"),
                "title": getattr(event_obj, "title", "Sem título"),
                "start": getattr(getattr(event_obj, "start", None), "isoformat", lambda: "")(),
                "end": getattr(getattr(event_obj, "end", None), "isoformat", lambda: "")(),
                "completed": getattr(event_obj, "completed", False),
                "auto_generated": getattr(event_obj, "auto_generated", False),
                "metadata": getattr(event_obj, "metadata", {}) or {},
                "book_id": getattr(event_obj, "book_id", None),
                "discipline": getattr(event_obj, "discipline", None),
                "difficulty": getattr(event_obj, "difficulty", 3),
                "progress_notes": getattr(event_obj, "progress_notes", []),
            }

        priority = data.get("priority")
        if hasattr(priority, "value"):
            data["priority"] = priority.value

        metadata = data.get("metadata") or {}
        if not data.get("discipline") and metadata.get("discipline"):
            data["discipline"] = metadata.get("discipline")

        return data

    def _load_week_events(self):
        self.events_list.clear()
        self.events_by_id.clear()
        self.current_event_id = None

        if not self.agenda_manager:
            self.editor.status_label.setText("Backend de agenda indisponível")
            self.editor.status_label.setStyleSheet("color: #EF4444;")
            return

        week_events: List[Dict] = []
        for event_id, event_obj in getattr(self.agenda_manager, "events", {}).items():
            data = self._event_obj_to_dict(event_obj)
            try:
                start_dt = datetime.fromisoformat(str(data.get("start", "")).replace("Z", "+00:00"))
            except Exception:
                continue

            if self.week_start <= start_dt.date() <= self.week_end:
                week_events.append(data)

        week_events.sort(key=lambda item: item.get("start", ""))

        for data in week_events:
            event_id = data.get("id")
            if not event_id:
                continue

            try:
                dt = datetime.fromisoformat(str(data.get("start", "")).replace("Z", "+00:00"))
                prefix = dt.strftime("%a %d/%m %H:%M")
            except Exception:
                prefix = "Sem data"

            title = data.get("title", "Sem título")
            state = "(Concluído)" if data.get("completed", False) else ""
            item = QListWidgetItem(f"{prefix} - {title} {state}".strip())
            item.setData(Qt.ItemDataRole.UserRole, event_id)

            self.events_by_id[event_id] = data
            self.events_list.addItem(item)

        if self.events_list.count() > 0:
            self.events_list.setCurrentRow(0)
        else:
            self.editor.clear_form()
            self.editor.status_label.setText("Nenhum evento nesta semana")

    def _on_selected_event_changed(self, current, _previous):
        if not current:
            self.current_event_id = None
            return

        event_id = current.data(Qt.ItemDataRole.UserRole)
        self.current_event_id = event_id
        event_data = self.events_by_id.get(event_id)

        if event_data:
            self.editor.load_event_data(event_data)

    def _on_save_clicked(self):
        if not self.current_event_id:
            self.editor.status_label.setText("Selecione um evento para editar")
            self.editor.status_label.setStyleSheet("color: #EF4444;")
            return

        if not self.editor._validate_form():
            return

        if not self.agenda_manager:
            self.editor.status_label.setText("Backend de agenda indisponível")
            self.editor.status_label.setStyleSheet("color: #EF4444;")
            return

        current_obj = self.agenda_manager.events.get(self.current_event_id)
        if not current_obj:
            self.editor.status_label.setText("Evento não encontrado")
            self.editor.status_label.setStyleSheet("color: #EF4444;")
            return

        new_data = self.editor._prepare_event_data()
        original_data = self.events_by_id.get(self.current_event_id, {})

        try:
            current_obj.title = new_data["title"]
            current_obj.start = datetime.fromisoformat(str(new_data["start"]).replace("Z", "+00:00"))
            current_obj.end = datetime.fromisoformat(str(new_data["end"]).replace("Z", "+00:00"))

            if hasattr(current_obj, "type"):
                current_obj.type = type(current_obj.type)(new_data.get("type", "casual"))

            if hasattr(current_obj, "priority"):
                priority_map = {"low": 1, "medium": 2, "high": 3, "fixed": 4, "blocking": 5}
                new_priority = priority_map.get(new_data.get("priority", "medium"), 2)
                current_obj.priority = type(current_obj.priority)(new_priority)

            current_obj.difficulty = int(new_data.get("difficulty", getattr(current_obj, "difficulty", 3)))
            current_obj.discipline = new_data.get("discipline") or None

            if "book_id" in original_data:
                current_obj.book_id = original_data.get("book_id")
            if self.editor.current_book_id:
                current_obj.book_id = self.editor.current_book_id

            notes = new_data.get("progress_notes", [])
            if isinstance(notes, list):
                current_obj.progress_notes = notes

            original_metadata = dict(getattr(current_obj, "metadata", {}) or {})
            merged_metadata = {**original_metadata, **new_data.get("metadata", {})}
            merged_metadata["description"] = new_data.get("description", "")
            merged_metadata["is_flexible"] = new_data.get("is_flexible", True)
            merged_metadata["is_blocking"] = new_data.get("is_blocking", False)
            merged_metadata["all_day"] = new_data.get("all_day", False)
            merged_metadata["recurrence"] = new_data.get("recurrence", {"type": "none"})
            if new_data.get("tags"):
                merged_metadata["tags"] = new_data.get("tags")
            current_obj.metadata = merged_metadata

            self.agenda_manager._save_events()

            self.editor.status_label.setText("✅ Evento atualizado com sucesso")
            self.editor.status_label.setStyleSheet("color: #10B981;")
            self.event_changed.emit()

            selected_id = self.current_event_id
            self._load_week_events()
            self._reselect_event(selected_id)
        except Exception as exc:
            self.editor.status_label.setText(f"❌ Erro ao atualizar: {exc}")
            self.editor.status_label.setStyleSheet("color: #EF4444;")

    def _reselect_event(self, event_id: str):
        for idx in range(self.events_list.count()):
            item = self.events_list.item(idx)
            if item.data(Qt.ItemDataRole.UserRole) == event_id:
                self.events_list.setCurrentRow(idx)
                return

    def _on_delete_clicked(self):
        if not self.current_event_id:
            self.editor.status_label.setText("Selecione um evento para excluir")
            self.editor.status_label.setStyleSheet("color: #EF4444;")
            return

        if not self.agenda_manager:
            self.editor.status_label.setText("Backend de agenda indisponível")
            self.editor.status_label.setStyleSheet("color: #EF4444;")
            return

        event_data = self.events_by_id.get(self.current_event_id, {})
        title = event_data.get("title", "este evento")
        response = QMessageBox.question(
            self,
            "Excluir Evento",
            f"Deseja excluir '{title}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if response != QMessageBox.StandardButton.Yes:
            return

        try:
            self.agenda_manager.events.pop(self.current_event_id, None)
            self.agenda_manager._save_events()
            self.event_changed.emit()
            self._load_week_events()
            self.editor.status_label.setText("🗑️ Evento excluído")
            self.editor.status_label.setStyleSheet("color: #10B981;")
        except Exception as exc:
            self.editor.status_label.setText(f"❌ Erro ao excluir: {exc}")
            self.editor.status_label.setStyleSheet("color: #EF4444;")
