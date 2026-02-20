"""
View base para criação de plano de revisão de obras.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QLabel,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)


class ReviewPlanView(QWidget):
    """Formulário base para configuração de plano de revisão."""

    changed = pyqtSignal()

    def __init__(
        self,
        parent=None,
        *,
        book_id: Optional[str] = None,
        book_title: str = "",
        book_options: Optional[List[Dict[str, Any]]] = None,
    ):
        super().__init__(parent)
        self._fixed_book_id = str(book_id).strip() if book_id else ""
        self._fixed_book_title = str(book_title or "").strip()
        self._book_options = list(book_options or [])
        self._setup_ui()
        self._setup_connections()
        self._update_preview()

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(10)

        intro = QLabel(
            "Defina o plano de revisão para a obra concluída.\n"
            "As sessões serão alocadas automaticamente na agenda."
        )
        intro.setWordWrap(True)
        root.addWidget(intro)

        form = QFormLayout()
        form.setHorizontalSpacing(12)
        form.setVerticalSpacing(8)

        if self._fixed_book_id:
            resolved_title = self._fixed_book_title or "Livro selecionado"
            self.book_label = QLabel(f"{resolved_title} ({self._fixed_book_id})")
            self.book_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            form.addRow("Livro:", self.book_label)
            self.book_combo = None
        else:
            self.book_combo = QComboBox()
            self.book_combo.addItem("Selecione um livro...", None)
            for option in self._book_options:
                option_id = str(option.get("book_id", "")).strip()
                if not option_id:
                    continue
                title = str(option.get("title", "Livro")).strip() or "Livro"
                author = str(option.get("author", "")).strip()
                completion = float(option.get("completion", 0.0) or 0.0)
                suffix = f" ({completion:.0f}%)"
                label = f"{title} — {author}{suffix}" if author else f"{title}{suffix}"
                self.book_combo.addItem(label, option_id)
            form.addRow("Livro:", self.book_combo)

        self.plan_days_combo = QComboBox()
        self.plan_days_combo.addItem("3 dias", 3)
        self.plan_days_combo.addItem("7 dias", 7)
        self.plan_days_combo.addItem("14 dias", 14)
        self.plan_days_combo.setCurrentIndex(1)
        form.addRow("Horizonte:", self.plan_days_combo)

        self.hours_per_session_spin = QDoubleSpinBox()
        self.hours_per_session_spin.setRange(0.5, 8.0)
        self.hours_per_session_spin.setSingleStep(0.5)
        self.hours_per_session_spin.setDecimals(1)
        self.hours_per_session_spin.setValue(1.0)
        self.hours_per_session_spin.setSuffix(" h")
        form.addRow("Horas por sessão:", self.hours_per_session_spin)

        self.sessions_per_day_spin = QSpinBox()
        self.sessions_per_day_spin.setRange(1, 8)
        self.sessions_per_day_spin.setValue(1)
        form.addRow("Sessões por dia:", self.sessions_per_day_spin)

        root.addLayout(form)

        self.preview_label = QLabel("")
        self.preview_label.setWordWrap(True)
        self.preview_label.setStyleSheet("color: #8A94A6;")
        root.addWidget(self.preview_label)

        self.error_label = QLabel("")
        self.error_label.setWordWrap(True)
        self.error_label.setStyleSheet("color: #EF4444;")
        root.addWidget(self.error_label)

    def _setup_connections(self):
        self.plan_days_combo.currentIndexChanged.connect(self._emit_change)
        self.hours_per_session_spin.valueChanged.connect(self._emit_change)
        self.sessions_per_day_spin.valueChanged.connect(self._emit_change)
        if self.book_combo is not None:
            self.book_combo.currentIndexChanged.connect(self._emit_change)

    def _emit_change(self):
        self._update_preview()
        self.changed.emit()

    def _update_preview(self):
        values = self.values()
        sessions = int(values.get("plan_days", 0)) * int(values.get("sessions_per_day", 0))
        minutes = int(round(float(values.get("hours_per_session", 0.0)) * 60))
        self.preview_label.setText(
            f"Resumo: {sessions} sessão(ões), {minutes} minutos cada."
        )
        if values.get("book_id"):
            self.error_label.setText("")
        else:
            self.error_label.setText("Selecione um livro para continuar.")

    def has_valid_selection(self) -> bool:
        return bool(self.values().get("book_id"))

    def values(self) -> Dict[str, Any]:
        book_id = self._fixed_book_id
        if not book_id and self.book_combo is not None:
            current = self.book_combo.currentData()
            if current:
                book_id = str(current).strip()

        title = self._fixed_book_title
        if not title and self.book_combo is not None:
            title = str(self.book_combo.currentText() or "").split("—", 1)[0].strip()

        return {
            "book_id": book_id,
            "book_title": title,
            "plan_days": int(self.plan_days_combo.currentData() or 7),
            "hours_per_session": float(self.hours_per_session_spin.value()),
            "sessions_per_day": int(self.sessions_per_day_spin.value()),
        }


class ReviewPlanDialog(QDialog):
    """Diálogo que encapsula a view base de plano de revisão."""

    def __init__(
        self,
        parent=None,
        *,
        book_id: Optional[str] = None,
        book_title: str = "",
        book_options: Optional[List[Dict[str, Any]]] = None,
    ):
        super().__init__(parent)
        self.setWindowTitle("Plano de Revisão")
        self.setModal(True)
        self.resize(520, 340)

        root = QVBoxLayout(self)
        self.review_view = ReviewPlanView(
            self,
            book_id=book_id,
            book_title=book_title,
            book_options=book_options,
        )
        root.addWidget(self.review_view, 1)

        self.buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self.buttons.accepted.connect(self._on_accept)
        self.buttons.rejected.connect(self.reject)
        root.addWidget(self.buttons)

        self._ok_button = self.buttons.button(QDialogButtonBox.StandardButton.Ok)
        self._ok_button.setText("Criar plano")
        self.review_view.changed.connect(self._sync_buttons_state)
        self._sync_buttons_state()

    def _sync_buttons_state(self):
        self._ok_button.setEnabled(self.review_view.has_valid_selection())

    def _on_accept(self):
        if not self.review_view.has_valid_selection():
            self.review_view.error_label.setText("Selecione um livro para criar o plano.")
            return
        self.accept()

    def values(self) -> Dict[str, Any]:
        return self.review_view.values()
