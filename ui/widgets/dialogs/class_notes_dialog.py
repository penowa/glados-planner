"""Diálogo para seleção de obras em notas de aula."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

from ui.utils.class_notes import WorkMaterial, load_discipline_works


@dataclass(frozen=True)
class ClassNotesSelection:
    """Resultado da seleção de obras para uma aula."""

    event_data: dict[str, Any]
    discipline: str
    selected_works: list[WorkMaterial]


class ClassNotesDialog(QDialog):
    """Permite escolher quais obras de uma disciplina serão tratadas na aula."""

    def __init__(
        self,
        *,
        vault_root: Path,
        event_data: dict[str, Any],
        parent=None,
    ):
        super().__init__(parent)
        self.vault_root = Path(vault_root)
        self.event_data = dict(event_data or {})
        self.discipline = str(
            self.event_data.get("discipline")
            or self.event_data.get("metadata", {}).get("discipline")
            or ""
        ).strip()
        self.available_works = load_discipline_works(self.vault_root, self.discipline) if self.discipline else []
        self.selection: Optional[ClassNotesSelection] = None

        self.setModal(True)
        self.setWindowTitle("Anotações em aula")
        self.resize(620, 460)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        title = QLabel("Selecione as obras tratadas nesta aula")
        title.setStyleSheet("font-size: 16px; font-weight: 600;")
        layout.addWidget(title)

        event_title = str(self.event_data.get("title") or "Aula").strip()
        summary = QLabel(
            f"Disciplina: <b>{self.discipline or 'Não informada'}</b><br>"
            f"Evento: {event_title}"
        )
        summary.setWordWrap(True)
        summary.setTextFormat(Qt.TextFormat.RichText)
        layout.addWidget(summary)

        self.list_widget = QListWidget()
        self.list_widget.setAlternatingRowColors(True)
        self._populate_list()
        layout.addWidget(self.list_widget, 1)

        self.empty_label = QLabel("")
        self.empty_label.setWordWrap(True)
        self.empty_label.setStyleSheet("color: #B0B0B0;")
        if not self.available_works:
            self.empty_label.setText(
                "Nenhuma obra vinculada foi encontrada na nota da disciplina. "
                "Vincule obras em 05-DISCIPLINAS para habilitar a seleção."
            )
        layout.addWidget(self.empty_label)

        actions = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self.select_all_button = QPushButton("Selecionar todas")
        self.clear_button = QPushButton("Limpar")
        actions.addButton(self.select_all_button, QDialogButtonBox.ButtonRole.ActionRole)
        actions.addButton(self.clear_button, QDialogButtonBox.ButtonRole.ActionRole)
        actions.accepted.connect(self._confirm_selection)
        actions.rejected.connect(self.reject)
        self.select_all_button.clicked.connect(self._select_all)
        self.clear_button.clicked.connect(self._clear_selection)
        layout.addWidget(actions)

        if not self.available_works:
            ok_button = actions.button(QDialogButtonBox.StandardButton.Ok)
            if ok_button:
                ok_button.setEnabled(False)

    def _populate_list(self) -> None:
        for work in self.available_works:
            item = QListWidgetItem(work.title)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Checked)
            item.setToolTip(str(work.primary_note_abs))
            item.setData(Qt.ItemDataRole.UserRole, work)
            self.list_widget.addItem(item)

    def _select_all(self) -> None:
        for row in range(self.list_widget.count()):
            item = self.list_widget.item(row)
            item.setCheckState(Qt.CheckState.Checked)

    def _clear_selection(self) -> None:
        for row in range(self.list_widget.count()):
            item = self.list_widget.item(row)
            item.setCheckState(Qt.CheckState.Unchecked)

    def _confirm_selection(self) -> None:
        selected: list[WorkMaterial] = []
        for row in range(self.list_widget.count()):
            item = self.list_widget.item(row)
            if item.checkState() == Qt.CheckState.Checked:
                work = item.data(Qt.ItemDataRole.UserRole)
                if isinstance(work, WorkMaterial):
                    selected.append(work)

        if not selected:
            QMessageBox.information(self, "Obras", "Selecione ao menos uma obra para gerar a nota da aula.")
            return

        self.selection = ClassNotesSelection(
            event_data=self.event_data,
            discipline=self.discipline,
            selected_works=selected,
        )
        self.accept()
