"""
Workspace de revisão com mapa mental interativo.
"""
from __future__ import annotations

from collections import deque
import json
import logging
import re
import shutil
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from PyQt6.QtCore import QEvent, QPoint, QPointF, QSize, Qt, QTimer, QMimeData, pyqtSignal
from PyQt6.QtGui import (
    QAction,
    QColor,
    QDrag,
    QIcon,
    QKeySequence,
    QMouseEvent,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
    QShortcut,
)
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QButtonGroup,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QGraphicsItem,
    QFrame,
    QGraphicsPathItem,
    QGraphicsRectItem,
    QGraphicsScene,
    QGraphicsSimpleTextItem,
    QGraphicsTextItem,
    QGraphicsView,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMenu,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSplitter,
    QStackedWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
    QSpinBox,
    QApplication,
)
from ui.utils.nerd_icons import LEGACY_LINK_ICON, NerdIcons

from core.modules.mindmap_review_module import MindmapReviewModule
from core.modules.pomodoro_timer import PomodoroTimer
from core.modules.review_system import ReviewSystem
from ui.utils.discipline_links import (
    append_annotation_note_links,
    append_book_note_links,
    find_primary_book_note,
)

logger = logging.getLogger("GLaDOS.UI.ReviewWorkspaceView")


class PendingDisciplineWorksDialog(QDialog):
    """Permite escolher como novas obras serão conectadas ao mapa da disciplina."""

    def __init__(
        self,
        *,
        discipline: str,
        pending_works: List[Dict[str, Any]],
        parent_choices: List[Dict[str, str]],
        parent=None,
    ):
        super().__init__(parent)
        self.setWindowTitle("Novas obras no mapa")
        self.setModal(True)
        self.resize(780, 420)

        self._pending_works = list(pending_works or [])
        self._choice_groups: Dict[str, QButtonGroup] = {}
        self._apply_styles()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        title = QLabel("Escolha como conectar as novas obras")
        title.setStyleSheet("font-size: 16px; font-weight: 700; color: #F3F6FB;")
        layout.addWidget(title)

        helper = QLabel(
            f"Novas obras foram encontradas na disciplina '{discipline}'. "
            "Defina se cada obra deve nascer ligada à raiz da disciplina, a outra obra, "
            "ou como card órfão."
        )
        helper.setWordWrap(True)
        helper.setStyleSheet("color: #AAB2C2;")
        layout.addWidget(helper)

        rules = QLabel(
            "Regras: capítulos nunca aparecem como destino. "
            "O vínculo sempre será feito com a raiz da disciplina ou com outra obra."
        )
        rules.setWordWrap(True)
        rules.setStyleSheet("color: #8F9AAF; font-size: 11px;")
        layout.addWidget(rules)

        summary = QLabel(
            f"{len(self._pending_works)} obra(s) aguardando posição no mapa."
        )
        summary.setStyleSheet(
            "background:#11161F; border:1px solid #2C3648; border-radius:8px; "
            "padding:8px 10px; color:#D7DEEA; font-weight:600;"
        )
        layout.addWidget(summary)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        cards_host = QWidget()
        cards_layout = QVBoxLayout(cards_host)
        cards_layout.setContentsMargins(0, 0, 6, 0)
        cards_layout.setSpacing(10)

        for entry in self._pending_works:
            work_key = str(entry.get("work_key") or "").strip()
            work_label = str(entry.get("label") or entry.get("work") or "Obra").strip()
            author_name = str(entry.get("author") or "").strip()
            work_title = str(entry.get("work") or "").strip()

            card = QFrame()
            card.setObjectName("pending_work_card")
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(14, 14, 14, 14)
            card_layout.setSpacing(8)

            heading = QLabel(work_label)
            heading.setStyleSheet("font-size: 14px; font-weight: 700; color: #F4F7FC;")
            card_layout.addWidget(heading)

            meta_parts: List[str] = []
            if author_name:
                meta_parts.append(f"Autor: {author_name}")
            if work_title and work_title != work_label:
                meta_parts.append(f"Obra: {work_title}")
            if not meta_parts:
                meta_parts.append("Nova obra encontrada na nota da disciplina")
            meta = QLabel(" | ".join(meta_parts))
            meta.setWordWrap(True)
            meta.setStyleSheet("color: #9EABBF; font-size: 11px;")
            card_layout.addWidget(meta)

            hint = QLabel("Escolha abaixo onde essa obra deve nascer conectada no mapa:")
            hint.setWordWrap(True)
            hint.setStyleSheet("color: #C7D1E0; font-size: 12px;")
            card_layout.addWidget(hint)

            options_wrap = QWidget()
            options_layout = QVBoxLayout(options_wrap)
            options_layout.setContentsMargins(0, 2, 0, 0)
            options_layout.setSpacing(8)

            button_group = QButtonGroup(self)
            button_group.setExclusive(True)
            for index, choice in enumerate(parent_choices):
                option_button = QPushButton(str(choice.get("label") or "Destino"))
                option_button.setCheckable(True)
                option_button.setObjectName("pending_choice_button")
                option_button.setProperty("choice_mode", str(choice.get("mode") or ""))
                option_button.setProperty("choice_target_id", str(choice.get("target_id") or ""))
                option_button.setProperty("choice_label", str(choice.get("label") or ""))
                if index == 0:
                    option_button.setChecked(True)
                button_group.addButton(option_button, index)
                options_layout.addWidget(option_button)

            card_layout.addWidget(options_wrap)
            cards_layout.addWidget(card)
            if work_key:
                self._choice_groups[work_key] = button_group

        cards_layout.addStretch(1)
        scroll.setWidget(cards_host)
        layout.addWidget(scroll, 1)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        ok_button = buttons.button(QDialogButtonBox.StandardButton.Ok)
        cancel_button = buttons.button(QDialogButtonBox.StandardButton.Cancel)
        if ok_button is not None:
            ok_button.setText("Adicionar ao mapa")
        if cancel_button is not None:
            cancel_button.setText("Decidir depois")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def selections(self) -> Dict[str, Dict[str, str]]:
        resolved: Dict[str, Dict[str, str]] = {}
        for work_key, button_group in self._choice_groups.items():
            checked = button_group.checkedButton()
            if checked is None:
                continue
            resolved[work_key] = {
                "mode": str(checked.property("choice_mode") or "").strip(),
                "target_id": str(checked.property("choice_target_id") or "").strip(),
                "label": str(checked.property("choice_label") or "").strip(),
            }
        return resolved

    def _apply_styles(self) -> None:
        self.setStyleSheet(
            "QDialog{background-color:#171C25; color:#E7ECF5;}"
            "QLabel{color:#DCE3EF;}"
            "QFrame#pending_work_card{background:#11161F; border:1px solid #2C3648; border-radius:12px;}"
            "QListWidget{background:#11161F; border:1px solid #2C3648; border-radius:8px; color:#DCE3EF; padding:4px;}"
            "QListWidget::item{padding:6px 8px; border-radius:6px;}"
            "QListWidget::item:selected{background:#222A38;}"
            "QScrollArea{background:transparent; border:none;}"
            "QComboBox{background:#11161F; border:1px solid #344055; border-radius:7px; color:#F0F4FB; padding:7px 10px; min-height:30px;}"
            "QComboBox:hover{border-color:#52627F;}"
            "QComboBox::drop-down{border:none; width:28px;}"
            "QComboBox QAbstractItemView{background:#11161F; color:#F0F4FB; border:1px solid #344055; selection-background-color:#253047;}"
            "QPushButton{background:#202734; color:#EEF3FB; border:1px solid #344055; border-radius:8px; padding:8px 14px;}"
            "QPushButton:hover{background:#283244; border-color:#4F6283;}"
            "QPushButton:pressed{background:#1A2230;}"
            "QPushButton#pending_choice_button{background:#161D28; color:#DDE5F1; border:1px solid #334155; text-align:left; padding:10px 12px;}"
            "QPushButton#pending_choice_button:hover{background:#1B2431; border-color:#52627F;}"
            "QPushButton#pending_choice_button:checked{background:#24344B; border:1px solid #79A6E3; color:#F4F8FF;}"
        )


class PendingDisciplineAnnotationsDialog(QDialog):
    """Permite escolher onde novas anotações órfãs devem nascer no mapa."""

    def __init__(
        self,
        *,
        discipline: str,
        pending_annotations: List[Dict[str, Any]],
        parent_choices: List[Dict[str, str]],
        parent=None,
    ):
        super().__init__(parent)
        self.setWindowTitle("Novas anotações no mapa")
        self.setModal(True)
        self.resize(780, 420)

        self._pending_annotations = list(pending_annotations or [])
        self._choice_groups: Dict[str, QButtonGroup] = {}
        self._apply_styles()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        title = QLabel("Escolha em qual ramo conectar as novas anotações")
        title.setStyleSheet("font-size: 16px; font-weight: 700; color: #F3F6FB;")
        layout.addWidget(title)

        helper = QLabel(
            f"Novas anotações foram encontradas na disciplina '{discipline}'. "
            "Defina em qual ramo do mapa cada anotação deve ficar ligada, "
            "ou mantenha-a como card órfão."
        )
        helper.setWordWrap(True)
        helper.setStyleSheet("color: #AAB2C2;")
        layout.addWidget(helper)

        rules = QLabel(
            "Regras: capítulos e outras anotações não aparecem como destino. "
            "O vínculo pode ser feito com a raiz da disciplina ou com outro nódulo do mapa."
        )
        rules.setWordWrap(True)
        rules.setStyleSheet("color: #8F9AAF; font-size: 11px;")
        layout.addWidget(rules)

        summary = QLabel(
            f"{len(self._pending_annotations)} anotação(ões) aguardando posição no mapa."
        )
        summary.setStyleSheet(
            "background:#11161F; border:1px solid #2C3648; border-radius:8px; "
            "padding:8px 10px; color:#D7DEEA; font-weight:600;"
        )
        layout.addWidget(summary)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        cards_host = QWidget()
        cards_layout = QVBoxLayout(cards_host)
        cards_layout.setContentsMargins(0, 0, 6, 0)
        cards_layout.setSpacing(10)

        for entry in self._pending_annotations:
            annotation_key = str(entry.get("annotation_key") or "").strip()
            note_title = str(entry.get("title") or entry.get("relative_path") or "Anotação").strip()
            relative_path = str(entry.get("relative_path") or "").strip()
            reason = str(entry.get("reason_label") or "").strip()

            card = QFrame()
            card.setObjectName("pending_work_card")
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(14, 14, 14, 14)
            card_layout.setSpacing(8)

            heading = QLabel(note_title)
            heading.setStyleSheet("font-size: 14px; font-weight: 700; color: #F4F7FC;")
            card_layout.addWidget(heading)

            meta_parts: List[str] = []
            if relative_path:
                meta_parts.append(f"Caminho: {relative_path}")
            if reason:
                meta_parts.append(reason)
            if not meta_parts:
                meta_parts.append("Nova anotação vinculada à disciplina")
            meta = QLabel(" | ".join(meta_parts))
            meta.setWordWrap(True)
            meta.setStyleSheet("color: #9EABBF; font-size: 11px;")
            card_layout.addWidget(meta)

            hint = QLabel("Escolha abaixo onde essa anotação deve ficar conectada no mapa:")
            hint.setWordWrap(True)
            hint.setStyleSheet("color: #C7D1E0; font-size: 12px;")
            card_layout.addWidget(hint)

            options_wrap = QWidget()
            options_layout = QVBoxLayout(options_wrap)
            options_layout.setContentsMargins(0, 2, 0, 0)
            options_layout.setSpacing(8)

            button_group = QButtonGroup(self)
            button_group.setExclusive(True)
            for index, choice in enumerate(parent_choices):
                option_button = QPushButton(str(choice.get("label") or "Destino"))
                option_button.setCheckable(True)
                option_button.setObjectName("pending_choice_button")
                option_button.setProperty("choice_mode", str(choice.get("mode") or ""))
                option_button.setProperty("choice_target_id", str(choice.get("target_id") or ""))
                option_button.setProperty("choice_label", str(choice.get("label") or ""))
                if index == 0:
                    option_button.setChecked(True)
                button_group.addButton(option_button, index)
                options_layout.addWidget(option_button)

            card_layout.addWidget(options_wrap)
            cards_layout.addWidget(card)
            if annotation_key:
                self._choice_groups[annotation_key] = button_group

        cards_layout.addStretch(1)
        scroll.setWidget(cards_host)
        layout.addWidget(scroll, 1)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        ok_button = buttons.button(QDialogButtonBox.StandardButton.Ok)
        cancel_button = buttons.button(QDialogButtonBox.StandardButton.Cancel)
        if ok_button is not None:
            ok_button.setText("Conectar no mapa")
        if cancel_button is not None:
            cancel_button.setText("Decidir depois")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def selections(self) -> Dict[str, Dict[str, str]]:
        resolved: Dict[str, Dict[str, str]] = {}
        for annotation_key, button_group in self._choice_groups.items():
            checked = button_group.checkedButton()
            if checked is None:
                continue
            resolved[annotation_key] = {
                "mode": str(checked.property("choice_mode") or "").strip(),
                "target_id": str(checked.property("choice_target_id") or "").strip(),
                "label": str(checked.property("choice_label") or "").strip(),
            }
        return resolved

    def _apply_styles(self) -> None:
        self.setStyleSheet(
            "QDialog{background-color:#171C25; color:#E7ECF5;}"
            "QLabel{color:#DCE3EF;}"
            "QFrame#pending_work_card{background:#11161F; border:1px solid #2C3648; border-radius:12px;}"
            "QListWidget{background:#11161F; border:1px solid #2C3648; border-radius:8px; color:#DCE3EF; padding:4px;}"
            "QListWidget::item{padding:6px 8px; border-radius:6px;}"
            "QListWidget::item:selected{background:#222A38;}"
            "QScrollArea{background:transparent; border:none;}"
            "QComboBox{background:#11161F; border:1px solid #344055; border-radius:7px; color:#F0F4FB; padding:7px 10px; min-height:30px;}"
            "QComboBox:hover{border-color:#52627F;}"
            "QComboBox::drop-down{border:none; width:28px;}"
            "QComboBox QAbstractItemView{background:#11161F; color:#F0F4FB; border:1px solid #344055; selection-background-color:#253047;}"
            "QPushButton{background:#202734; color:#EEF3FB; border:1px solid #344055; border-radius:8px; padding:8px 14px;}"
            "QPushButton:hover{background:#283244; border-color:#4F6283;}"
            "QPushButton:pressed{background:#1A2230;}"
            "QPushButton#pending_choice_button{background:#161D28; color:#DDE5F1; border:1px solid #334155; text-align:left; padding:10px 12px;}"
            "QPushButton#pending_choice_button:hover{background:#1B2431; border-color:#52627F;}"
            "QPushButton#pending_choice_button:checked{background:#24344B; border:1px solid #79A6E3; color:#F4F8FF;}"
        )


class PomodoroConfigDialog(QDialog):
    """Diálogo de configuração de Pomodoro para a review view."""

    def __init__(self, pomodoro: PomodoroTimer, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Configurações Pomodoro")
        self.setModal(True)
        self.resize(320, 220)
        self._pomodoro = pomodoro

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.work_spin = QSpinBox()
        self.work_spin.setRange(5, 180)
        self.work_spin.setValue(max(1, int(self._pomodoro.work_duration // 60)))

        self.break_spin = QSpinBox()
        self.break_spin.setRange(1, 60)
        self.break_spin.setValue(max(1, int(self._pomodoro.break_duration // 60)))

        self.long_break_spin = QSpinBox()
        self.long_break_spin.setRange(5, 120)
        self.long_break_spin.setValue(max(1, int(self._pomodoro.long_break_duration // 60)))

        self.sessions_spin = QSpinBox()
        self.sessions_spin.setRange(2, 12)
        self.sessions_spin.setValue(max(2, int(self._pomodoro.sessions_before_long_break)))

        form.addRow("Foco (min):", self.work_spin)
        form.addRow("Pausa curta (min):", self.break_spin)
        form.addRow("Pausa longa (min):", self.long_break_spin)
        form.addRow("Sessões/pausa longa:", self.sessions_spin)
        layout.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def get_values(self) -> Dict[str, int]:
        return {
            "work_minutes": self.work_spin.value(),
            "break_minutes": self.break_spin.value(),
            "long_break_minutes": self.long_break_spin.value(),
            "sessions_before_long_break": self.sessions_spin.value(),
        }


class ReviewQuestionDialog(QDialog):
    """Dialog de pergunta periódica com resposta oculta."""

    def __init__(
        self,
        question: str,
        answer: str,
        chapter_label: str,
        difficulty: int,
        parent=None,
    ):
        super().__init__(parent)
        self.setWindowTitle("Pergunta de revisão")
        self.setModal(True)
        self.resize(620, 360)
        self.answer_revealed = False

        root = QVBoxLayout(self)

        header = QLabel(
            f"Capítulo: {chapter_label or 'N/A'} | Dificuldade: {max(1, min(int(difficulty or 3), 5))}/5"
        )
        header.setStyleSheet("color: #AAB2C2;")
        root.addWidget(header)

        question_box = QFrame()
        question_box.setStyleSheet(
            "QFrame { background-color: #1E2430; border: 1px solid #394257; border-radius: 8px; }"
        )
        question_layout = QVBoxLayout(question_box)
        question_layout.setContentsMargins(12, 10, 12, 10)

        question_label = QLabel(question or "Sem pergunta.")
        question_label.setWordWrap(True)
        question_label.setStyleSheet("font-size: 14px; color: #E8ECF5;")
        question_layout.addWidget(question_label)
        root.addWidget(question_box)

        self.answer_label = QLabel("Resposta oculta")
        self.answer_label.setWordWrap(True)
        self.answer_label.setStyleSheet("color: #7D8798;")
        root.addWidget(self.answer_label)

        actions = QHBoxLayout()
        self.show_answer_button = QPushButton("Mostrar resposta")
        self.close_button = QPushButton("Fechar")
        actions.addStretch(1)
        actions.addWidget(self.show_answer_button)
        actions.addWidget(self.close_button)
        root.addLayout(actions)

        self._answer = answer or "Sem resposta registrada."
        self.show_answer_button.clicked.connect(self._reveal_answer)
        self.close_button.clicked.connect(self.accept)

    def _reveal_answer(self):
        self.answer_revealed = True
        self.answer_label.setText(self._answer)
        self.answer_label.setStyleSheet("color: #E7F0DB;")
        self.show_answer_button.setEnabled(False)


class CanvasActionDragButton(QPushButton):
    """Botão que inicia ação por drag-and-drop para o canvas."""

    MIME_TYPE = "application/x-glados-review-canvas-action"

    def __init__(self, action_key: str, parent=None, enable_drag: bool = False):
        super().__init__(parent)
        self.action_key = str(action_key or "").strip()
        self.enable_drag = bool(enable_drag)
        self._drag_start_pos: Optional[QPoint] = None
        if self.enable_drag:
            self.setCursor(Qt.CursorShape.OpenHandCursor)
        else:
            self.setCursor(Qt.CursorShape.PointingHandCursor)

    def mousePressEvent(self, event):
        if not self.enable_drag:
            super().mousePressEvent(event)
            return
        if event.button() == Qt.MouseButton.LeftButton:
            local = event.position().toPoint() if hasattr(event, "position") else event.pos()
            self._drag_start_pos = local
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        if not self.enable_drag:
            super().mouseReleaseEvent(event)
            return
        self._drag_start_pos = None
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        super().mouseReleaseEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        if not self.enable_drag:
            super().mouseMoveEvent(event)
            return
        if not (event.buttons() & Qt.MouseButton.LeftButton):
            return
        if self._drag_start_pos is None:
            return

        local = event.position().toPoint() if hasattr(event, "position") else event.pos()
        distance = (local - self._drag_start_pos).manhattanLength()
        start_distance = max(6, int(QApplication.startDragDistance()))
        if distance < start_distance:
            return

        drag = QDrag(self)
        mime = QMimeData()
        mime.setData(self.MIME_TYPE, self.action_key.encode("utf-8"))
        mime.setText(self.action_key)
        drag.setMimeData(mime)

        icon_size = max(22, min(self.width(), self.height()) - 12)
        pixmap = self.icon().pixmap(icon_size, icon_size)
        if not pixmap.isNull():
            drag.setPixmap(pixmap)
            drag.setHotSpot(QPoint(icon_size // 2, icon_size // 2))

        self.setCursor(Qt.CursorShape.OpenHandCursor)
        self._drag_start_pos = None
        drag.exec(Qt.DropAction.CopyAction)
        event.accept()


class MindmapCanvasView(QGraphicsView):
    """View gráfica com zoom por scroll e pan por arrasto."""

    _DEFAULT_MIN_ZOOM = 0.25
    _ABSOLUTE_MIN_ZOOM = 0.01
    _MAX_ZOOM = 4.0

    def __init__(self, scene: QGraphicsScene, parent=None):
        super().__init__(scene, parent)
        self.setRenderHints(
            QPainter.RenderHint.Antialiasing
            | QPainter.RenderHint.TextAntialiasing
            | QPainter.RenderHint.SmoothPixmapTransform
        )
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorViewCenter)
        self._zoom_factor = 1.0
        self._drop_handler = None
        self.setAcceptDrops(True)
        self.viewport().setAcceptDrops(True)
        self.viewport().installEventFilter(self)

    def wheelEvent(self, event):
        if event.angleDelta().y() > 0:
            self.zoom_by(1.12)
        else:
            self.zoom_by(0.88)

    def _fit_zoom_factor(self) -> Optional[float]:
        scene_rect = self.sceneRect()
        viewport_rect = self.viewport().rect()
        if (
            not scene_rect.isValid()
            or scene_rect.width() <= 0
            or scene_rect.height() <= 0
            or viewport_rect.width() <= 0
            or viewport_rect.height() <= 0
        ):
            return None
        return min(
            viewport_rect.width() / scene_rect.width(),
            viewport_rect.height() / scene_rect.height(),
        )

    def _minimum_zoom_factor(self) -> float:
        fit_zoom = self._fit_zoom_factor()
        if fit_zoom is None or fit_zoom >= self._DEFAULT_MIN_ZOOM:
            return self._DEFAULT_MIN_ZOOM
        return max(self._ABSOLUTE_MIN_ZOOM, fit_zoom * 0.9)

    def zoom_by(self, factor: float):
        current = self.transform().m11()
        if current <= 0:
            self.resetTransform()
            current = 1.0

        target = current * factor
        target = max(self._minimum_zoom_factor(), min(target, self._MAX_ZOOM))
        if abs(target - current) < 1e-4:
            return

        scale_step = target / current
        self.scale(scale_step, scale_step)
        self._zoom_factor = self.transform().m11()

    def reset_zoom(self):
        scene_rect = self.sceneRect()
        self.resetTransform()
        self._zoom_factor = 1.0
        if scene_rect.isValid():
            self.centerOn(scene_rect.center())

        fit_zoom = self._fit_zoom_factor()
        if fit_zoom is not None and fit_zoom < 1.0 and scene_rect.isValid():
            self.fitInView(scene_rect, Qt.AspectRatioMode.KeepAspectRatio)
            self.centerOn(scene_rect.center())
            self._zoom_factor = self.transform().m11()

    def pan_by(self, dx: int, dy: int):
        hbar = self.horizontalScrollBar()
        vbar = self.verticalScrollBar()
        hbar.setValue(hbar.value() + int(dx))
        vbar.setValue(vbar.value() + int(dy))

    def set_drop_handler(self, handler):
        self._drop_handler = handler

    def _supports_drop(self, mime) -> bool:
        return bool(mime and (mime.hasFormat(CanvasActionDragButton.MIME_TYPE) or mime.hasUrls()))

    def _dispatch_drop(self, event) -> bool:
        if not callable(self._drop_handler):
            return False

        scene_pos = self.mapToScene(event.position().toPoint())
        mime = event.mimeData()

        if mime.hasFormat(CanvasActionDragButton.MIME_TYPE):
            raw = bytes(mime.data(CanvasActionDragButton.MIME_TYPE)).decode("utf-8", errors="ignore").strip()
            if raw:
                self._drop_handler(raw, scene_pos, None)
                return True

        if mime.hasUrls():
            for url in mime.urls():
                if not url.isLocalFile():
                    continue
                path = Path(url.toLocalFile())
                if path.suffix.lower() not in {".png", ".jpg", ".jpeg", ".bmp", ".gif", ".webp"}:
                    continue
                self._drop_handler("image_from_file", scene_pos, str(path))
                return True

        return False

    def eventFilter(self, watched, event):
        if watched is self.viewport():
            event_type = event.type()
            if event_type in (QEvent.Type.DragEnter, QEvent.Type.DragMove):
                if self._supports_drop(event.mimeData()):
                    event.acceptProposedAction()
                    return True
            elif event_type == QEvent.Type.Drop:
                if self._dispatch_drop(event):
                    event.acceptProposedAction()
                    return True
        return super().eventFilter(watched, event)

    def dragEnterEvent(self, event):
        if self._supports_drop(event.mimeData()):
            event.acceptProposedAction()
            return
        super().dragEnterEvent(event)

    def dragMoveEvent(self, event):
        if self._supports_drop(event.mimeData()):
            event.acceptProposedAction()
            return
        super().dragMoveEvent(event)

    def dropEvent(self, event):
        if self._dispatch_drop(event):
            event.acceptProposedAction()
            return

        super().dropEvent(event)


class MindmapNodeItem(QGraphicsRectItem):
    """Item de card para nós do canvas."""

    def __init__(
        self,
        node_data: Dict[str, Any],
        color_lookup,
        on_left_click,
        on_right_click,
        on_position_changed,
        on_size_changed=None,
        on_connector_drag_started=None,
        on_connector_drag_moved=None,
        on_connector_drag_finished=None,
        image_path_resolver=None,
    ):
        width = max(120, int(float(node_data.get("width", 220) or 220)))
        height = max(64, int(float(node_data.get("height", 90) or 90)))
        super().__init__(0, 0, width, height)
        self.node_data = node_data
        self._color_lookup = color_lookup
        self._on_left_click = on_left_click
        self._on_right_click = on_right_click
        self._on_position_changed = on_position_changed
        self._on_size_changed = on_size_changed
        self._on_connector_drag_started = on_connector_drag_started
        self._on_connector_drag_moved = on_connector_drag_moved
        self._on_connector_drag_finished = on_connector_drag_finished
        self._image_path_resolver = image_path_resolver

        self.setFlag(QGraphicsRectItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.setFlag(QGraphicsRectItem.GraphicsItemFlag.ItemIsMovable, True)
        self.setFlag(QGraphicsRectItem.GraphicsItemFlag.ItemSendsGeometryChanges, True)
        self.setAcceptHoverEvents(True)
        self.setZValue(10)

        x = float(node_data.get("x", 0) or 0)
        y = float(node_data.get("y", 0) or 0)
        self.setPos(QPointF(x, y))

        self.title = QGraphicsTextItem(self)
        self.title.setDefaultTextColor(QColor("#F5F8FD"))
        self.title.setTextWidth(width - 16)
        self.title.setPos(8, 8)
        self.title.setPlainText(self._label_text())

        self.favorite_badge = QGraphicsSimpleTextItem("★", self)
        self.favorite_badge.setBrush(QColor("#FFE082"))
        self.favorite_badge.setPos(width - 20, 4)

        self._image_pixmap = QPixmap()
        self._hovered = False
        self._press_scene_pos: Optional[QPointF] = None
        self._resizing = False
        self._resize_start_scene_pos: Optional[QPointF] = None
        self._resize_start_width = float(width)
        self._resize_start_height = float(height)
        self._connector_drag_side: Optional[str] = None
        self.refresh_style()

    def _label_text(self) -> str:
        node_type = str(self.node_data.get("type") or "").strip().lower()
        if node_type == "file":
            file_ref = str(self.node_data.get("file") or "").strip()
            if file_ref:
                return Path(file_ref).stem
            return "Arquivo"
        if node_type == "image":
            caption = str(self.node_data.get("caption") or "").strip()
            if caption:
                return caption
            image_ref = str(self.node_data.get("image") or "").strip()
            if image_ref:
                return Path(image_ref).stem
            return "Imagem"
        text = str(self.node_data.get("text") or "").strip()
        if not text:
            return str(self.node_data.get("id") or "Nó")
        return text

    def is_favorite(self) -> bool:
        return bool(self.node_data.get("favorite", False))

    def is_image_card(self) -> bool:
        return str(self.node_data.get("type") or "").strip().lower() == "image"

    def _min_width(self) -> int:
        return 190 if self.is_image_card() else 120

    def _min_height(self) -> int:
        return 140 if self.is_image_card() else 64

    def _connector_centers(self) -> Dict[str, QPointF]:
        rect = self.rect()
        return {
            "left": QPointF(rect.left(), rect.center().y()),
            "right": QPointF(rect.right(), rect.center().y()),
            "top": QPointF(rect.center().x(), rect.top()),
            "bottom": QPointF(rect.center().x(), rect.bottom()),
        }

    def _connector_side_at(self, pos: QPointF) -> Optional[str]:
        threshold = 9.0
        for side, center in self._connector_centers().items():
            if (center - pos).manhattanLength() <= threshold:
                return side
        return None

    def connector_scene_pos(self, side: str) -> QPointF:
        center = self._connector_centers().get(str(side or "right").strip().lower())
        if not center:
            center = self._connector_centers()["right"]
        return self.mapToScene(center)

    def closest_side_for_scene_pos(self, scene_pos: QPointF) -> str:
        local = self.mapFromScene(scene_pos)
        points = self._connector_centers()
        best_side = "left"
        best_dist = float("inf")
        for side, center in points.items():
            distance = (center - local).manhattanLength()
            if distance < best_dist:
                best_dist = distance
                best_side = side
        return best_side

    def _is_on_resize_handle(self, pos: QPointF) -> bool:
        rect = self.rect()
        handle = 14.0
        return (
            pos.x() >= rect.right() - handle
            and pos.y() >= rect.bottom() - handle
        )

    def refresh_content(self):
        width = max(self._min_width(), int(float(self.node_data.get("width", self.rect().width()) or self.rect().width())))
        height = max(self._min_height(), int(float(self.node_data.get("height", self.rect().height()) or self.rect().height())))
        self.setRect(0, 0, width, height)

        self.title.setTextWidth(max(40.0, float(width - 16)))
        self.title.setPlainText(self._label_text())
        self.favorite_badge.setPos(width - 20, 4)

        if self.is_image_card():
            caption = str(self.node_data.get("caption") or "").strip()
            self.title.setVisible(bool(caption))
            self.title.setPos(8, max(6, height - 28))
        else:
            self.title.setVisible(True)
            self.title.setPos(8, 8)

        self._load_image_pixmap()
        self.update()

    def _load_image_pixmap(self):
        self._image_pixmap = QPixmap()
        if not self.is_image_card() or not callable(self._image_path_resolver):
            return
        try:
            image_path = self._image_path_resolver(self.node_data)
        except Exception:
            image_path = None
        if not image_path:
            return
        pixmap = QPixmap(str(image_path))
        if pixmap.isNull():
            return
        self._image_pixmap = pixmap

    def refresh_style(self):
        color_id = str(self.node_data.get("color") or "0")
        fill = self._color_lookup(color_id)

        if self.is_favorite():
            self._pen = QPen(QColor("#FFD54F"), 2.8)
        else:
            self._pen = QPen(fill.darker(150), 1.4)

        self._brush = fill
        self.favorite_badge.setVisible(self.is_favorite())
        self.refresh_content()
        self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.RightButton:
            if callable(self._on_right_click):
                screen_pos = event.screenPos()
                global_pos = screen_pos.toPoint() if hasattr(screen_pos, "toPoint") else screen_pos
                if not isinstance(global_pos, QPoint):
                    global_pos = QPoint(int(global_pos.x()), int(global_pos.y()))
                self._on_right_click(self, global_pos)
            self.setSelected(True)
            event.accept()
            return
        if event.button() == Qt.MouseButton.LeftButton:
            if self._is_on_resize_handle(event.pos()):
                self._resizing = True
                self._resize_start_scene_pos = event.scenePos()
                self._resize_start_width = float(self.rect().width())
                self._resize_start_height = float(self.rect().height())
                self.setSelected(True)
                event.accept()
                return

            side = self._connector_side_at(event.pos())
            if side and callable(self._on_connector_drag_started):
                self._connector_drag_side = side
                self.setSelected(True)
                self._on_connector_drag_started(self, side, event.scenePos())
                event.accept()
                return
            self._press_scene_pos = event.scenePos()
        self.setSelected(True)
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._resizing:
            if self._resize_start_scene_pos is None:
                event.accept()
                return
            delta_x = float(event.scenePos().x()) - float(self._resize_start_scene_pos.x())
            delta_y = float(event.scenePos().y()) - float(self._resize_start_scene_pos.y())
            width = max(self._min_width(), int(self._resize_start_width + delta_x))
            height = max(self._min_height(), int(self._resize_start_height + delta_y))
            self.node_data["width"] = int(width)
            self.node_data["height"] = int(height)
            self.refresh_content()
            if callable(self._on_size_changed):
                self._on_size_changed(self)
            event.accept()
            return

        if self._connector_drag_side:
            if callable(self._on_connector_drag_moved):
                self._on_connector_drag_moved(event.scenePos())
            event.accept()
            return

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self._resizing:
            self._resizing = False
            self._resize_start_scene_pos = None
            if callable(self._on_size_changed):
                self._on_size_changed(self)
            event.accept()
            return

        if self._connector_drag_side:
            if callable(self._on_connector_drag_finished):
                self._on_connector_drag_finished(event.scenePos())
            self._connector_drag_side = None
            event.accept()
            return

        super().mouseReleaseEvent(event)
        if event.button() != Qt.MouseButton.LeftButton:
            return
        if self._press_scene_pos is None:
            return
        delta_x = abs(float(event.scenePos().x()) - float(self._press_scene_pos.x()))
        delta_y = abs(float(event.scenePos().y()) - float(self._press_scene_pos.y()))
        self._press_scene_pos = None
        if (delta_x + delta_y) <= 4.0 and callable(self._on_left_click):
            self._on_left_click(self)

    def itemChange(self, change, value):
        if change == QGraphicsRectItem.GraphicsItemChange.ItemPositionHasChanged:
            if callable(self._on_position_changed):
                self._on_position_changed(self)
        return super().itemChange(change, value)

    def hoverEnterEvent(self, event):
        self._hovered = True
        self.update()
        super().hoverEnterEvent(event)

    def hoverMoveEvent(self, event):
        if self._is_on_resize_handle(event.pos()):
            self.setCursor(Qt.CursorShape.SizeFDiagCursor)
        elif self._connector_side_at(event.pos()):
            self.setCursor(Qt.CursorShape.CrossCursor)
        else:
            self.setCursor(Qt.CursorShape.OpenHandCursor)
        super().hoverMoveEvent(event)

    def hoverLeaveEvent(self, event):
        self._hovered = False
        self.setCursor(Qt.CursorShape.ArrowCursor)
        self.update()
        super().hoverLeaveEvent(event)

    def paint(self, painter, option, widget=None):
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        pen = QPen(self._pen)
        if self.isSelected():
            pen.setWidthF(max(2.0, pen.widthF() + 0.8))
        if self._hovered and not self.isSelected():
            pen.setWidthF(pen.widthF() + 0.5)

        brush_color = QColor(self._brush)
        if self._hovered:
            brush_color = brush_color.lighter(112)

        painter.setPen(pen)
        painter.setBrush(brush_color)
        painter.drawRoundedRect(self.rect(), 10, 10)

        if self.is_image_card() and not self._image_pixmap.isNull():
            image_rect = self.rect().adjusted(8, 8, -8, -8)
            if self.title.isVisible():
                image_rect.setBottom(image_rect.bottom() - 28)
            if image_rect.width() > 8 and image_rect.height() > 8:
                scaled = self._image_pixmap.scaled(
                    int(image_rect.width()),
                    int(image_rect.height()),
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
                x = image_rect.left() + (image_rect.width() - scaled.width()) / 2.0
                y = image_rect.top() + (image_rect.height() - scaled.height()) / 2.0
                painter.drawPixmap(int(x), int(y), scaled)

        if self._hovered or self.isSelected():
            painter.setPen(QPen(QColor("#697388"), 1.0))
            painter.setBrush(QColor("#E6ECF9"))
            for center in self._connector_centers().values():
                painter.drawEllipse(center, 3.6, 3.6)

            rect = self.rect()
            painter.setPen(QPen(QColor("#D7DEED"), 1.2))
            painter.drawLine(
                QPointF(rect.right() - 11, rect.bottom() - 4),
                QPointF(rect.right() - 4, rect.bottom() - 11),
            )
            painter.drawLine(
                QPointF(rect.right() - 8, rect.bottom() - 4),
                QPointF(rect.right() - 4, rect.bottom() - 8),
            )
        painter.restore()


class MindmapEdgeItem(QGraphicsPathItem):
    """Aresta curva que se adapta à posição dos cards conectados."""

    def __init__(
        self,
        from_item: MindmapNodeItem,
        to_item: MindmapNodeItem,
        color: QColor,
        from_side: str = "right",
        to_side: str = "left",
        label: str = "",
    ):
        super().__init__()
        self.from_item = from_item
        self.to_item = to_item
        self.from_side = str(from_side or "right").strip().lower()
        self.to_side = str(to_side or "left").strip().lower()
        self.label_text = str(label or "").strip()
        self.setPen(QPen(QColor(color), 1.8))
        self.setZValue(1)

        self.label_item: Optional[QGraphicsSimpleTextItem] = None
        if self.label_text:
            self.label_item = QGraphicsSimpleTextItem(self.label_text, self)
            self.label_item.setBrush(QColor("#AEB7C6"))
            self.label_item.setZValue(2)

        self.update_path()

    def _anchor(self, item: MindmapNodeItem, side: str) -> QPointF:
        rect = item.sceneBoundingRect()
        normalized = str(side or "").strip().lower()
        if normalized == "left":
            return QPointF(rect.left(), rect.center().y())
        if normalized == "top":
            return QPointF(rect.center().x(), rect.top())
        if normalized == "bottom":
            return QPointF(rect.center().x(), rect.bottom())
        return QPointF(rect.right(), rect.center().y())

    def update_path(self):
        start = self._anchor(self.from_item, self.from_side)
        end = self._anchor(self.to_item, self.to_side)

        horizontal_delta = abs(end.x() - start.x())
        control_dx = max(54.0, horizontal_delta * 0.42)

        if end.x() >= start.x():
            c1 = QPointF(start.x() + control_dx, start.y())
            c2 = QPointF(end.x() - control_dx, end.y())
        else:
            c1 = QPointF(start.x() - control_dx, start.y())
            c2 = QPointF(end.x() + control_dx, end.y())

        path = QPainterPath(start)
        path.cubicTo(c1, c2, end)
        self.setPath(path)

        if self.label_item:
            middle = path.pointAtPercent(0.5)
            self.label_item.setPos(middle.x() + 4, middle.y() + 2)


class ReviewWorkspaceView(QWidget):
    """Workspace de revisão focado em navegação por mapa mental."""

    navigate_to = pyqtSignal(str)

    USER_NOTES_DIR = "02-ANOTAÇÕES"
    REVIEW_DIR = "03-REVISÃO"
    MINDMAPS_DIR = "04-MAPAS MENTAIS"

    COLOR_PALETTE = {
        "1": ("Resumo", QColor("#4A90E2")),
        "2": ("Nota da obra", QColor("#5FAF5A")),
        "3": ("Pré-texto", QColor("#D9A63E")),
        "4": ("Raiz", QColor("#6E5AA6")),
        "5": ("Capítulo", QColor("#C97843")),
        "6": ("Nota do usuário", QColor("#4FA7A7")),
    }

    def __init__(self, controllers: Optional[Dict[str, Any]] = None, parent=None):
        super().__init__(parent)
        self.controllers = controllers or {}
        self.reading_controller = self.controllers.get("reading")
        self.agenda_controller = self.controllers.get("agenda")

        self.mindmap_module = MindmapReviewModule()
        self.review_system = self._resolve_review_system()
        self.pomodoro = self._create_pomodoro()

        self.current_book_id: str = ""
        self.current_book_title: str = "Revisão"
        self.current_book_dir: Optional[Path] = None
        self.current_scope_type: str = "book"
        self.current_discipline: str = ""
        self.current_discipline_note_path: Optional[Path] = None
        self.current_canvas_path: Optional[Path] = None
        self.current_canvas_payload: Dict[str, Any] = {"nodes": [], "edges": []}
        self.current_source_note_path: Optional[Path] = None
        self._node_items: Dict[str, MindmapNodeItem] = {}
        self._edge_items: list[MindmapEdgeItem] = []
        self._edges_by_node: Dict[str, list[MindmapEdgeItem]] = {}
        self._opened_node_id: str = ""
        self._edge_drag_source_item: Optional[MindmapNodeItem] = None
        self._edge_drag_source_side: str = "right"
        self._edge_drag_preview: Optional[QGraphicsPathItem] = None
        self._editing_card_node_id: str = ""
        self._editing_card_mode: str = "text"
        self._isolated_spawn_index: int = 0
        self._suppress_pending_work_dialog = False
        self._suppress_pending_annotation_dialog = False
        self.auto_layout_button: Optional[CanvasActionDragButton] = None

        self._fullscreen_active = False
        self._window_was_maximized = False
        self._window_was_fullscreen = False
        self._is_active = False

        self._question_prompt_enabled = True
        self._question_interval_minutes = 10
        self._question_pan_step = 130
        self._next_question_prompt_at: Optional[datetime] = None

        self.ui_timer = QTimer(self)
        self.ui_timer.timeout.connect(self._tick_ui)
        self.ui_timer.start(1000)

        self.question_timer = QTimer(self)
        self.question_timer.timeout.connect(self._check_question_prompt)
        self.question_timer.start(30000)
        self.persist_move_timer = QTimer(self)
        self.persist_move_timer.setSingleShot(True)
        self.persist_move_timer.setInterval(420)
        self.persist_move_timer.timeout.connect(self._persist_canvas_payload)

        self._setup_ui()
        self._setup_connections()
        self._load_review_settings()
        self._tick_ui()

    def _resolve_reading_manager(self):
        if self.reading_controller and getattr(self.reading_controller, "reading_manager", None):
            return self.reading_controller.reading_manager
        return None

    def _resolve_review_system(self) -> Optional[ReviewSystem]:
        try:
            if self.agenda_controller and getattr(self.agenda_controller, "agenda_manager", None):
                manager = self.agenda_controller.agenda_manager
                if getattr(manager, "review_system", None):
                    return manager.review_system
        except Exception:
            pass

        manager = self._resolve_reading_manager()
        if not manager:
            return None

        try:
            return ReviewSystem(str(manager.vault_path))
        except Exception as exc:
            logger.warning("Falha ao criar ReviewSystem local: %s", exc)
            return None

    def _create_pomodoro(self) -> Optional[PomodoroTimer]:
        manager = self._resolve_reading_manager()
        if not manager:
            return None
        try:
            return PomodoroTimer(str(manager.vault_path))
        except Exception as exc:
            logger.warning("Falha ao inicializar Pomodoro para review view: %s", exc)
            return None

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        self.header = QWidget()
        header_layout = QHBoxLayout(self.header)
        header_layout.setContentsMargins(8, 6, 8, 4)
        header_layout.setSpacing(6)

        self.pomodoro_timer_button = QPushButton("25:00")
        self.pomodoro_timer_button.setObjectName("review_pomodoro_timer")
        self.pomodoro_timer_button.setFixedWidth(120)
        self.pomodoro_timer_button.setStyleSheet(
            "QPushButton {"
            "background-color: #232733; color: #FFFFFF;"
            "border: 1px solid #4A5263; border-radius: 6px;"
            "font-weight: 700; padding: 4px 8px;"
            "}"
            "QPushButton:hover { background-color: #2A2F3D; }"
        )

        self.book_label = QLabel("Review Workspace")
        self.book_label.setStyleSheet("font-size: 14px; font-weight: 700;")
        self.status_label = QLabel("Selecione uma revisão para iniciar")
        self.status_label.setStyleSheet("color: #98A2B3;")

        self.zoom_out_button = QPushButton("−")
        self.zoom_out_button.setToolTip("Reduzir zoom")
        self.zoom_reset_button = QPushButton("◎")
        self.zoom_reset_button.setToolTip("Ajustar mapa à tela")
        self.zoom_in_button = QPushButton("+")
        self.zoom_in_button.setToolTip("Aumentar zoom")
        for button in (self.zoom_out_button, self.zoom_reset_button, self.zoom_in_button):
            button.setObjectName("review_round_icon_button")
            button.setFixedSize(38, 38)
            self._apply_round_icon_button_style(button, radius=19)

        header_layout.addWidget(self.pomodoro_timer_button)
        header_layout.addWidget(self.book_label, 1)
        header_layout.addWidget(self.status_label, 2)
        header_layout.addWidget(self.zoom_out_button)
        header_layout.addWidget(self.zoom_reset_button)
        header_layout.addWidget(self.zoom_in_button)
        root.addWidget(self.header)

        self.main_splitter = QSplitter(Qt.Orientation.Horizontal)

        self.scene = QGraphicsScene(self)
        self.canvas_view = MindmapCanvasView(self.scene, self)
        self.canvas_view.setObjectName("review_canvas")

        left_panel = QFrame()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(4, 4, 4, 4)
        left_layout.setSpacing(4)
        left_layout.addWidget(self.canvas_view, 1)

        right_panel = QFrame()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(4, 4, 4, 4)
        right_layout.setSpacing(4)

        self.side_splitter = QSplitter(Qt.Orientation.Vertical)

        viewer_container = QWidget()
        viewer_layout = QVBoxLayout(viewer_container)
        viewer_layout.setContentsMargins(0, 0, 0, 0)
        viewer_layout.setSpacing(4)

        self.viewer_title_label = QLabel("Conteúdo do card")
        self.viewer_title_label.setStyleSheet("font-weight: 700;")
        self.note_viewer = QTextEdit()
        self.note_viewer.setReadOnly(True)
        self.note_viewer.setPlaceholderText("Clique em um card para abrir a nota")
        self.note_viewer.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.note_viewer.setStyleSheet(
            "background-color: #11161F; border: 1px solid #2C3648; border-radius: 6px;"
        )
        self.capture_selection_button = QPushButton("Criar nota a partir da seleção")
        self.capture_selection_button.setVisible(False)

        viewer_layout.addWidget(self.viewer_title_label)
        viewer_layout.addWidget(self.note_viewer, 1)
        viewer_layout.addWidget(self.capture_selection_button)

        editor_container = QWidget()
        editor_layout = QVBoxLayout(editor_container)
        editor_layout.setContentsMargins(0, 0, 0, 0)
        editor_layout.setSpacing(4)

        self.editor_mode_label = QLabel("Editor")
        self.editor_mode_label.setStyleSheet("font-weight: 700;")

        self.editor_stack = QStackedWidget()

        self.card_editor_page = QWidget()
        card_layout = QVBoxLayout(self.card_editor_page)
        card_layout.setContentsMargins(0, 0, 0, 0)
        card_layout.setSpacing(4)

        self.card_title_input = QLineEdit()
        self.card_title_input.setPlaceholderText("Título do card")

        self.card_body_label = QLabel("Conteúdo")
        self.card_body_editor = QTextEdit()
        self.card_body_editor.setPlaceholderText("Escreva o conteúdo do card...")
        self.card_body_editor.setStyleSheet(
            "background-color: #11161F; border: 1px solid #2C3648; border-radius: 6px;"
        )

        self.card_image_row = QWidget()
        image_row_layout = QHBoxLayout(self.card_image_row)
        image_row_layout.setContentsMargins(0, 0, 0, 0)
        image_row_layout.setSpacing(6)
        self.card_image_path_input = QLineEdit()
        self.card_image_path_input.setPlaceholderText("Imagem do card")
        self.card_pick_image_button = QPushButton("Selecionar")
        image_row_layout.addWidget(self.card_image_path_input, 1)
        image_row_layout.addWidget(self.card_pick_image_button)

        self.card_save_button = QPushButton("Salvar card")
        self.card_feedback_label = QLabel("")
        self.card_feedback_label.setStyleSheet("color: #8FBF7F;")

        card_layout.addWidget(self.card_title_input)
        card_layout.addWidget(self.card_body_label)
        card_layout.addWidget(self.card_body_editor, 1)
        card_layout.addWidget(self.card_image_row)
        card_layout.addWidget(self.card_save_button)
        card_layout.addWidget(self.card_feedback_label)

        self.note_editor_page = QWidget()
        note_layout = QVBoxLayout(self.note_editor_page)
        note_layout.setContentsMargins(0, 0, 0, 0)
        note_layout.setSpacing(4)

        self.new_note_title_input = QLineEdit()
        self.new_note_title_input.setPlaceholderText("Título da nota")
        self.new_note_editor = QTextEdit()
        self.new_note_editor.setPlaceholderText("Escreva sua nota aqui...")
        self.new_note_editor.setStyleSheet(
            "background-color: #11161F; border: 1px solid #2C3648; border-radius: 6px;"
        )
        self.save_note_button = QPushButton("Salvar nota")
        self.save_note_feedback = QLabel("")
        self.save_note_feedback.setStyleSheet("color: #8FBF7F;")

        note_layout.addWidget(QLabel("Nova anotação"))
        note_layout.addWidget(self.new_note_title_input)
        note_layout.addWidget(self.new_note_editor, 1)
        note_layout.addWidget(self.save_note_button)
        note_layout.addWidget(self.save_note_feedback)

        self.editor_stack.addWidget(self.card_editor_page)
        self.editor_stack.addWidget(self.note_editor_page)
        self.editor_stack.setCurrentWidget(self.note_editor_page)

        editor_layout.addWidget(self.editor_mode_label)
        editor_layout.addWidget(self.editor_stack, 1)

        self.side_splitter.addWidget(viewer_container)
        self.side_splitter.addWidget(editor_container)
        self.side_splitter.setSizes([430, 260])

        right_layout.addWidget(self.side_splitter, 1)
        self.right_panel = right_panel

        self.main_splitter.addWidget(left_panel)
        self.main_splitter.addWidget(right_panel)
        self.main_splitter.setSizes([920, 520])
        self.main_splitter.setStretchFactor(0, 3)
        self.main_splitter.setStretchFactor(1, 2)

        root.addWidget(self.main_splitter, 1)

        self.bottom_actions_bar = QWidget()
        bottom_layout = QHBoxLayout(self.bottom_actions_bar)
        bottom_layout.setContentsMargins(0, 4, 0, 10)
        bottom_layout.setSpacing(0)
        bottom_layout.addStretch(1)

        dock = QWidget()
        dock_layout = QHBoxLayout(dock)
        dock_layout.setContentsMargins(0, 0, 0, 0)
        dock_layout.setSpacing(10)

        self.add_text_card_button = CanvasActionDragButton("add_text_card", self, enable_drag=False)
        self.add_text_card_button.setToolTip("Criar novo card")
        self.add_text_card_button.setFixedSize(46, 46)
        self.add_text_card_button.setIcon(self._build_plus_icon())
        self.add_text_card_button.setIconSize(QSize(22, 22))
        self._apply_round_icon_button_style(self.add_text_card_button, radius=23)

        self.add_image_card_button = CanvasActionDragButton("add_image_card", self, enable_drag=False)
        self.add_image_card_button.setToolTip("Criar card de imagem")
        self.add_image_card_button.setFixedSize(46, 46)
        self.add_image_card_button.setIcon(self._build_image_icon())
        self.add_image_card_button.setIconSize(QSize(22, 22))
        self._apply_round_icon_button_style(self.add_image_card_button, radius=23)

        self.auto_layout_button = CanvasActionDragButton("auto_layout_map", self, enable_drag=False)
        self.auto_layout_button.setToolTip("Organizar mapa automaticamente")
        self.auto_layout_button.setFixedSize(46, 46)
        self.auto_layout_button.setIcon(self._build_auto_layout_icon())
        self.auto_layout_button.setIconSize(QSize(22, 22))
        self._apply_round_icon_button_style(self.auto_layout_button, radius=23)

        dock_layout.addWidget(self.add_text_card_button)
        dock_layout.addWidget(self.add_image_card_button)
        dock_layout.addWidget(self.auto_layout_button)
        bottom_layout.addWidget(dock)
        bottom_layout.addStretch(1)
        root.addWidget(self.bottom_actions_bar, 0)

        self.shortcut_escape = QShortcut(QKeySequence(Qt.Key.Key_Escape), self)
        self.shortcut_escape.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)

        self.shortcut_left = QShortcut(QKeySequence(Qt.Key.Key_Left), self.canvas_view)
        self.shortcut_right = QShortcut(QKeySequence(Qt.Key.Key_Right), self.canvas_view)
        self.shortcut_up = QShortcut(QKeySequence(Qt.Key.Key_Up), self.canvas_view)
        self.shortcut_down = QShortcut(QKeySequence(Qt.Key.Key_Down), self.canvas_view)

        self._activate_note_editor()
        self._set_editor_visible(False)
        self._close_side_panel()

    def _apply_round_icon_button_style(self, button: QPushButton, radius: int = 18):
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        button.setStyleSheet(
            "QPushButton{"
            "background-color:#1F1F1F; color:#D0D0D0; border:1px solid #333842; "
            f"border-radius:{max(8, int(radius))}px;"
            "}"
            "QPushButton:hover{background-color:#2A2A2A; border-color:#535B6B; color:#F3F3F3;}"
            "QPushButton:pressed{background-color:#171717;}"
        )

    def _setup_connections(self):
        self.pomodoro_timer_button.clicked.connect(self._open_pomodoro_menu)
        self.zoom_in_button.clicked.connect(lambda: self.canvas_view.zoom_by(1.12))
        self.zoom_out_button.clicked.connect(lambda: self.canvas_view.zoom_by(0.88))
        self.zoom_reset_button.clicked.connect(self.canvas_view.reset_zoom)
        self.add_text_card_button.clicked.connect(self._create_text_card_isolated)
        self.add_image_card_button.clicked.connect(self._create_image_card_isolated)
        if self.auto_layout_button:
            self.auto_layout_button.clicked.connect(self._auto_organize_current_map)

        self.capture_selection_button.clicked.connect(lambda: self._capture_selection_to_note(show_empty_feedback=True))
        self.note_viewer.customContextMenuRequested.connect(self._on_note_viewer_context_menu)
        self.save_note_button.clicked.connect(self._save_user_note)
        self.card_save_button.clicked.connect(self._save_active_card)
        self.card_pick_image_button.clicked.connect(self._pick_image_for_editor)
        self.shortcut_escape.activated.connect(self._on_escape_pressed)

        self.shortcut_left.activated.connect(lambda: self.canvas_view.pan_by(-self._question_pan_step, 0))
        self.shortcut_right.activated.connect(lambda: self.canvas_view.pan_by(self._question_pan_step, 0))
        self.shortcut_up.activated.connect(lambda: self.canvas_view.pan_by(0, -self._question_pan_step))
        self.shortcut_down.activated.connect(lambda: self.canvas_view.pan_by(0, self._question_pan_step))

    def _build_plus_icon(self) -> QIcon:
        pixmap = QPixmap(24, 24)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setPen(QPen(QColor("#E8EEF9"), 2.2))
        painter.drawLine(12, 5, 12, 19)
        painter.drawLine(5, 12, 19, 12)
        painter.end()
        return QIcon(pixmap)

    def _build_image_icon(self) -> QIcon:
        pixmap = QPixmap(24, 24)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setPen(QPen(QColor("#E8EEF9"), 1.8))
        painter.drawRoundedRect(4, 6, 16, 12, 2, 2)
        painter.drawEllipse(7, 8, 3, 3)
        painter.drawLine(6, 16, 11, 12)
        painter.drawLine(11, 12, 15, 15)
        painter.drawLine(15, 15, 18, 12)
        painter.end()
        return QIcon(pixmap)

    def _build_auto_layout_icon(self) -> QIcon:
        pixmap = QPixmap(24, 24)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        pen = QPen(QColor("#E8EEF9"), 1.7)
        painter.setPen(pen)
        painter.drawRoundedRect(3, 4, 6, 6, 2, 2)
        painter.drawRoundedRect(15, 4, 6, 6, 2, 2)
        painter.drawRoundedRect(9, 14, 6, 6, 2, 2)
        painter.drawLine(9, 7, 15, 7)
        painter.drawLine(18, 10, 12, 14)
        painter.drawLine(6, 10, 12, 14)
        painter.end()
        return QIcon(pixmap)

    @staticmethod
    def _node_size(node: Dict[str, Any]) -> tuple[float, float]:
        try:
            width = max(120.0, float(node.get("width", 220) or 220))
        except Exception:
            width = 220.0
        try:
            height = max(64.0, float(node.get("height", 90) or 90))
        except Exception:
            height = 90.0
        return width, height

    @staticmethod
    def _node_position(node: Dict[str, Any]) -> tuple[float, float]:
        try:
            x = float(node.get("x", 0) or 0)
        except Exception:
            x = 0.0
        try:
            y = float(node.get("y", 0) or 0)
        except Exception:
            y = 0.0
        return x, y

    def _node_rank_label(self, node: Dict[str, Any]) -> str:
        file_ref = str(node.get("file") or "").strip()
        if file_ref:
            return Path(file_ref).stem.lower()
        text = str(node.get("text") or node.get("title") or node.get("caption") or "").strip()
        if text:
            return text.lower()
        return str(node.get("id") or "").strip().lower()

    def _node_signal_text(self, node: Dict[str, Any]) -> str:
        chunks = [
            str(node.get("id") or ""),
            str(node.get("type") or ""),
            str(node.get("file") or ""),
            str(node.get("text") or ""),
            str(node.get("title") or ""),
            str(node.get("caption") or ""),
        ]
        return self._normalize_token(" ".join(chunks))

    def _is_root_like_node(self, node: Dict[str, Any]) -> bool:
        node_id = str(node.get("id") or "").strip().lower()
        if node_id in {"node-livro", "node-disciplina"}:
            return True
        signal = self._node_signal_text(node)
        return "mapa base da obra" in signal or "mapa da disciplina" in signal

    def _is_chapter_like_node(self, node: Dict[str, Any]) -> bool:
        if str(node.get("color") or "").strip() == "5":
            return True
        signal = self._node_signal_text(node)
        return "capitulo" in signal or "chapter" in signal

    def _is_user_note_like_node(self, node: Dict[str, Any]) -> bool:
        signal = self._node_signal_text(node)
        if "02-anotacoes" in signal:
            return True
        if "nota-usuario" in signal or "nota do usuario" in signal or "anotacao" in signal:
            return True
        if "05 - pessoal" in signal or "05-pessoal" in signal:
            return True
        return str(node.get("color") or "").strip() == "6"

    def _resolve_primary_layout_root_id(
        self,
        node_by_id: Dict[str, Dict[str, Any]],
        incoming_by_id: Dict[str, set[str]],
    ) -> str:
        if "node-livro" in node_by_id:
            return "node-livro"
        if "node-disciplina" in node_by_id:
            return "node-disciplina"

        root_candidates = [
            node_id
            for node_id, node in node_by_id.items()
            if self._is_root_like_node(node)
        ]
        if root_candidates:
            root_candidates.sort(
                key=lambda node_id: (
                    self._node_position(node_by_id[node_id])[0],
                    self._node_position(node_by_id[node_id])[1],
                    node_id,
                )
            )
            return root_candidates[0]

        without_parent = [
            node_id
            for node_id in node_by_id
            if not incoming_by_id.get(node_id)
        ]
        if without_parent:
            without_parent.sort(
                key=lambda node_id: (
                    self._node_position(node_by_id[node_id])[0],
                    self._node_position(node_by_id[node_id])[1],
                    node_id,
                )
            )
            return without_parent[0]

        fallback = sorted(
            node_by_id.keys(),
            key=lambda node_id: (
                self._node_position(node_by_id[node_id])[0],
                self._node_position(node_by_id[node_id])[1],
                node_id,
            ),
        )
        return fallback[0] if fallback else ""

    def _nearest_ancestor_in_set(
        self,
        node_id: str,
        incoming_by_id: Dict[str, set[str]],
        candidates: set[str],
    ) -> str:
        start = str(node_id or "").strip()
        if not start or not candidates:
            return ""

        queue = deque(incoming_by_id.get(start, set()))
        visited = {start}
        while queue:
            current = str(queue.popleft() or "").strip()
            if not current or current in visited:
                continue
            if current in candidates:
                return current
            visited.add(current)
            for parent in incoming_by_id.get(current, set()):
                if parent not in visited:
                    queue.append(parent)
        return ""

    def _has_ancestor(
        self,
        node_id: str,
        ancestor_id: str,
        incoming_by_id: Dict[str, set[str]],
    ) -> bool:
        start = str(node_id or "").strip()
        target = str(ancestor_id or "").strip()
        if not start or not target:
            return False
        if start == target:
            return True

        queue = deque(incoming_by_id.get(start, set()))
        visited = {start}
        while queue:
            current = str(queue.popleft() or "").strip()
            if not current or current in visited:
                continue
            if current == target:
                return True
            visited.add(current)
            for parent in incoming_by_id.get(current, set()):
                if parent not in visited:
                    queue.append(parent)
        return False

    def _reorient_edges_for_layout(self, payload: Dict[str, Any], node_by_id: Dict[str, Dict[str, Any]]):
        edges = payload.get("edges")
        if not isinstance(edges, list):
            return
        for edge in edges:
            if not isinstance(edge, dict):
                continue
            from_id = str(edge.get("fromNode") or "").strip()
            to_id = str(edge.get("toNode") or "").strip()
            from_node = node_by_id.get(from_id)
            to_node = node_by_id.get(to_id)
            if not from_node or not to_node:
                continue

            from_x, from_y = self._node_position(from_node)
            to_x, to_y = self._node_position(to_node)
            from_w, from_h = self._node_size(from_node)
            to_w, to_h = self._node_size(to_node)

            from_center = QPointF(from_x + (from_w / 2.0), from_y + (from_h / 2.0))
            to_center = QPointF(to_x + (to_w / 2.0), to_y + (to_h / 2.0))
            dx = float(to_center.x() - from_center.x())
            dy = float(to_center.y() - from_center.y())

            if abs(dx) >= abs(dy):
                if dx >= 0:
                    edge["fromSide"] = "right"
                    edge["toSide"] = "left"
                else:
                    edge["fromSide"] = "left"
                    edge["toSide"] = "right"
            else:
                if dy >= 0:
                    edge["fromSide"] = "bottom"
                    edge["toSide"] = "top"
                else:
                    edge["fromSide"] = "top"
                    edge["toSide"] = "bottom"

    def _auto_organize_current_map(self):
        payload = self.current_canvas_payload
        nodes = payload.get("nodes")
        if not isinstance(nodes, list) or not nodes:
            self.status_label.setText("Não há cards para organizar no mapa atual")
            return

        valid_nodes = [node for node in nodes if isinstance(node, dict) and str(node.get("id") or "").strip()]
        if not valid_nodes:
            self.status_label.setText("Mapa sem nós válidos para organização")
            return

        node_by_id: Dict[str, Dict[str, Any]] = {
            str(node.get("id") or "").strip(): node
            for node in valid_nodes
        }

        edges = payload.get("edges")
        edge_rows = edges if isinstance(edges, list) else []
        outgoing_by_id: Dict[str, set[str]] = {node_id: set() for node_id in node_by_id}
        incoming_by_id: Dict[str, set[str]] = {node_id: set() for node_id in node_by_id}
        for edge in edge_rows:
            if not isinstance(edge, dict):
                continue
            from_id = str(edge.get("fromNode") or "").strip()
            to_id = str(edge.get("toNode") or "").strip()
            if from_id in node_by_id and to_id in node_by_id and from_id != to_id:
                outgoing_by_id.setdefault(from_id, set()).add(to_id)
                incoming_by_id.setdefault(to_id, set()).add(from_id)

        root_id = self._resolve_primary_layout_root_id(node_by_id, incoming_by_id)
        if not root_id:
            self.status_label.setText("Não foi possível identificar o nó raiz do mapa")
            return

        sortable_ids = sorted(
            node_by_id.keys(),
            key=lambda node_id: (
                self._node_position(node_by_id[node_id])[1],
                self._node_position(node_by_id[node_id])[0],
                self._node_rank_label(node_by_id[node_id]),
                node_id,
            ),
        )
        sort_index = {node_id: index for index, node_id in enumerate(sortable_ids)}

        depth_by_id: Dict[str, int] = {root_id: 0}
        bfs_queue = deque([root_id])
        while bfs_queue:
            current = str(bfs_queue.popleft() or "").strip()
            base_depth = int(depth_by_id.get(current, 0))
            for child_id in sorted(outgoing_by_id.get(current, set()), key=lambda item: sort_index.get(item, 10**9)):
                next_depth = base_depth + 1
                previous_depth = depth_by_id.get(child_id)
                if previous_depth is None or next_depth < previous_depth:
                    depth_by_id[child_id] = next_depth
                    bfs_queue.append(child_id)

        def _layout_priority(node_id: str) -> tuple[int, int, str, str]:
            node = node_by_id[node_id]
            node_type = str(node.get("type") or "").strip().lower()
            if self._is_work_anchor_node(node):
                priority = 0
            elif node_type == "file":
                file_ref = str(node.get("file") or "").strip().replace("\\", "/")
                if file_ref.startswith("01-LEITURAS/"):
                    priority = 1
                elif self._is_user_note_like_node(node):
                    priority = 4
                else:
                    priority = 2
            elif node_type == "text":
                signal = self._node_signal_text(node)
                if "descricao" in signal or "descrição" in signal or "contexto" in signal:
                    priority = 5
                else:
                    priority = 3
            elif self._is_user_note_like_node(node):
                priority = 4
            elif node_type == "image":
                priority = 6
            else:
                priority = 1
            return (
                priority,
                sort_index.get(node_id, 10**9),
                self._node_rank_label(node),
                node_id,
            )

        primary_parent_by_id: Dict[str, str] = {}
        children_by_parent: Dict[str, List[str]] = {node_id: [] for node_id in node_by_id}
        loose_ids: List[str] = []

        for node_id in sortable_ids:
            if node_id == root_id:
                continue

            candidate_parents = [
                parent_id
                for parent_id in incoming_by_id.get(node_id, set())
                if parent_id in depth_by_id
            ]
            if not candidate_parents:
                loose_ids.append(node_id)
                continue

            node_depth = depth_by_id.get(node_id)
            ranked_parents = sorted(
                candidate_parents,
                key=lambda parent_id: (
                    0 if node_depth is not None and depth_by_id.get(parent_id, 0) < node_depth else 1,
                    depth_by_id.get(parent_id, 10**9),
                    _layout_priority(parent_id),
                ),
            )
            primary_parent = ranked_parents[0]
            primary_parent_by_id[node_id] = primary_parent
            children_by_parent.setdefault(primary_parent, []).append(node_id)

        for parent_id, child_ids in children_by_parent.items():
            child_ids.sort(key=_layout_priority)

        root_node = node_by_id[root_id]
        root_x, root_y = self._node_position(root_node)
        root_w, root_h = self._node_size(root_node)

        depth_columns: Dict[int, List[str]] = {}
        for node_id, depth in depth_by_id.items():
            depth_columns.setdefault(int(depth), []).append(node_id)
        for depth, column_ids in depth_columns.items():
            if depth == 0:
                continue
            column_ids.sort(
                key=lambda node_id: (
                    sort_index.get(primary_parent_by_id.get(node_id, ""), 10**9),
                    _layout_priority(node_id),
                )
            )

        max_depth = max(depth_columns.keys()) if depth_columns else 0
        column_gap = 190.0
        column_x: Dict[int, float] = {0: root_x}
        prev_width = max(220.0, float(root_w))
        for depth in range(1, max_depth + 1):
            column_x[depth] = column_x[depth - 1] + prev_width + column_gap
            current_ids = depth_columns.get(depth, [])
            prev_width = max(
                220.0,
                max((self._node_size(node_by_id[node_id])[0] for node_id in current_ids), default=220.0),
            )

        loose_x = column_x.get(max_depth, root_x) + prev_width + column_gap

        positions: Dict[str, tuple[float, float]] = {root_id: (root_x, root_y)}
        sibling_gap = 34.0

        subtree_height_cache: Dict[str, float] = {}

        def _subtree_height(node_id: str) -> float:
            cached = subtree_height_cache.get(node_id)
            if cached is not None:
                return cached

            _, own_h = self._node_size(node_by_id[node_id])
            children = children_by_parent.get(node_id, [])
            if not children:
                subtree_height_cache[node_id] = float(own_h)
                return float(own_h)

            children_height = sum(_subtree_height(child_id) for child_id in children)
            children_height += sibling_gap * max(0, len(children) - 1)
            total = max(float(own_h), float(children_height))
            subtree_height_cache[node_id] = total
            return total

        def _place_subtree(node_id: str):
            parent_pos = positions.get(node_id)
            if parent_pos is None:
                return
            parent_x, parent_y = parent_pos
            _, parent_h = self._node_size(node_by_id[node_id])
            child_ids = children_by_parent.get(node_id, [])
            if not child_ids:
                return

            total_children_height = sum(_subtree_height(child_id) for child_id in child_ids)
            total_children_height += sibling_gap * max(0, len(child_ids) - 1)
            parent_center_y = float(parent_y) + (float(parent_h) / 2.0)
            cursor_y = parent_center_y - (total_children_height / 2.0)

            for child_id in child_ids:
                child_depth = int(depth_by_id.get(child_id, 1))
                _, child_h = self._node_size(node_by_id[child_id])
                subtree_h = _subtree_height(child_id)
                child_y = cursor_y + max(0.0, (subtree_h - float(child_h)) / 2.0)
                positions[child_id] = (column_x.get(child_depth, root_x), child_y)
                _place_subtree(child_id)
                cursor_y += subtree_h + sibling_gap

        _place_subtree(root_id)

        loose_ids = sorted(set(loose_ids), key=_layout_priority)
        if loose_ids:
            loose_total = (
                sum(self._node_size(node_by_id[node_id])[1] for node_id in loose_ids)
                + sibling_gap * max(0, len(loose_ids) - 1)
            )
            loose_cursor = (root_y + (root_h / 2.0)) - (loose_total / 2.0)
            for node_id in loose_ids:
                _, card_h = self._node_size(node_by_id[node_id])
                positions[node_id] = (loose_x, loose_cursor)
                loose_cursor += card_h + sibling_gap

        for node_id, (x, y) in positions.items():
            node = node_by_id.get(node_id)
            if not node:
                continue
            node["x"] = round(float(x), 2)
            node["y"] = round(float(y), 2)

        self._reorient_edges_for_layout(payload, node_by_id)
        self._render_canvas(payload, reset_zoom=False)
        self._persist_canvas_payload()
        self.status_label.setText(
            f"Mapa organizado automaticamente: {len(positions)} nós distribuídos por hierarquia"
        )

    def _load_review_settings(self):
        try:
            from core.config.settings import Settings

            model = Settings.from_yaml()
            self.apply_review_settings(model.model_dump().get("review_view", {}))
        except Exception:
            self.apply_review_settings({})

    def apply_review_settings(self, payload: Dict[str, Any] | None):
        data = payload or {}
        self._question_prompt_enabled = bool(data.get("question_prompt_enabled", True))

        try:
            interval = int(data.get("question_interval_minutes", 10) or 10)
        except Exception:
            interval = 10
        self._question_interval_minutes = max(1, min(interval, 180))

        try:
            pan_step = int(data.get("arrow_pan_step", 130) or 130)
        except Exception:
            pan_step = 130
        self._question_pan_step = max(40, min(pan_step, 400))

        if self.review_system and hasattr(self.review_system, "set_question_interval_minutes"):
            try:
                self.review_system.set_question_interval_minutes(self._question_interval_minutes)
            except Exception:
                pass

        self._schedule_next_question_prompt(reset=True)

    def _sanitize_filename(self, value: str) -> str:
        return re.sub(r"[^a-zA-Z0-9._-]+", "-", value).strip("-").lower() or "review"

    def _vault_root(self) -> Optional[Path]:
        manager = self._resolve_reading_manager()
        if not manager:
            return None
        return Path(manager.vault_path)

    def _resolve_book_directory(self, book_id: str, book_title: str) -> Optional[Path]:
        if self.current_book_dir and self.current_book_dir.exists():
            return self.current_book_dir

        vault_root = self._vault_root()
        if not vault_root:
            return None

        reading_root = vault_root / "01-LEITURAS"
        if not reading_root.exists():
            return None

        normalized_title = str(book_title or "").strip().lower()
        for candidate in reading_root.glob("*/*"):
            if not candidate.is_dir():
                continue
            if normalized_title and normalized_title not in candidate.name.lower():
                continue
            return candidate

        if not book_id:
            return None

        for note_path in reading_root.glob("*/*/*.md"):
            if not note_path.is_file():
                continue
            try:
                text = note_path.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue
            if re.search(rf"(?m)^book_id:\s*{re.escape(book_id)}\s*$", text):
                return note_path.parent

        return None

    def _resolve_book_title(self, book_id: str, provided_title: str) -> str:
        title = str(provided_title or "").strip()
        lowered_title = title.lower()
        if title and not (lowered_title.startswith("revisão:") or lowered_title.startswith("revisao:")):
            return title

        manager = self._resolve_reading_manager()
        if manager and book_id:
            try:
                progress = manager.get_reading_progress(book_id) or {}
                progress_title = str(progress.get("title") or "").strip()
                if progress_title:
                    return progress_title
            except Exception:
                pass

        cleaned = re.sub(r"(?i)^revis[ãa]o:\s*", "", title).strip()
        return cleaned or "Obra sem título"

    def _canvas_path_for_book(self, book_title: str) -> Optional[Path]:
        vault_root = self._vault_root()
        if not vault_root:
            return None
        filename = f"{self._sanitize_filename(book_title)}.mapa-mental.canvas"
        return vault_root / self.MINDMAPS_DIR / filename

    def _canvas_path_for_discipline(self, discipline: str) -> Optional[Path]:
        vault_root = self._vault_root()
        if not vault_root:
            return None
        safe = self._sanitize_filename(f"disciplina-{discipline}")
        filename = f"{safe}.mapa-mental.canvas"
        return vault_root / self.MINDMAPS_DIR / filename

    def _resolve_discipline_note_path(self, discipline: str) -> Optional[Path]:
        vault_root = self._vault_root()
        if not vault_root:
            return None
        discipline_dir = vault_root / "05-DISCIPLINAS"
        if not discipline_dir.exists():
            return None

        safe = self._sanitize_filename(discipline)
        direct = discipline_dir / f"{safe}.md"
        if direct.exists():
            return direct

        lowered = discipline.strip().lower()
        for candidate in discipline_dir.glob("*.md"):
            if candidate.stem.lower() == lowered:
                return candidate
        return None

    def _ensure_canvas_exists(self):
        if not self.current_canvas_path:
            return
        if self.current_canvas_path.exists():
            return

        self.current_canvas_path.parent.mkdir(parents=True, exist_ok=True)
        vault_root = self._vault_root()
        if not vault_root:
            return

        if self.current_scope_type == "discipline":
            payload = self._build_discipline_base_canvas(
                vault_root=vault_root,
                discipline=self.current_discipline or self.current_book_title,
                discipline_note=self.current_discipline_note_path,
            )
        else:
            sources = self.mindmap_module.find_base_sources(self.current_book_dir)
            payload = self.mindmap_module.build_base_canvas(
                vault_root=vault_root,
                book_title=self.current_book_title,
                book_note=sources.book_note,
                pretext_note=sources.pretext_note,
            )
        try:
            self.current_canvas_path.write_text(
                self.mindmap_module.dump_canvas_json(payload) + "\n",
                encoding="utf-8",
            )
        except Exception as exc:
            logger.warning("Falha ao criar canvas base: %s", exc)

    def open_review(
        self,
        *,
        book_id: str = "",
        book_title: str = "",
        book_dir: Optional[Path] = None,
        source_event: Optional[Dict[str, Any]] = None,
    ) -> bool:
        normalized_id = str(book_id or "").strip()
        resolved_title = self._resolve_book_title(normalized_id, book_title)

        self.current_book_id = normalized_id
        self.current_book_title = resolved_title
        self.current_book_dir = Path(book_dir) if book_dir else self._resolve_book_directory(normalized_id, resolved_title)
        self.current_scope_type = "book"
        self.current_discipline = ""
        self.current_discipline_note_path = None
        self.current_canvas_path = self._canvas_path_for_book(resolved_title)

        if not self.current_canvas_path:
            self.status_label.setText("Vault não disponível para revisão")
            return False

        self._ensure_canvas_exists()

        self.current_canvas_payload = self._load_sanitized_canvas_payload(self.current_canvas_path)
        self._render_canvas(self.current_canvas_payload)
        self._isolated_spawn_index = 0
        self._opened_node_id = ""
        self.current_source_note_path = None
        self.viewer_title_label.setText("Conteúdo do card")
        self.note_viewer.clear()
        self.new_note_title_input.clear()
        self.new_note_editor.clear()
        self.card_title_input.clear()
        self.card_body_editor.clear()
        self.card_image_path_input.clear()
        self.card_feedback_label.clear()
        self._activate_note_editor()
        self._set_editor_visible(False)
        self._close_side_panel()

        self.book_label.setText(f"Revisão: {self.current_book_title}")
        self.status_label.setText("Mapa mental carregado")

        self._sync_questions_for_current_book()
        self._schedule_next_question_prompt(reset=True)

        if source_event:
            logger.debug("Review workspace aberto com payload: %s", source_event)
        return True

    def open_discipline_review(
        self,
        *,
        discipline: str,
        source_event: Optional[Dict[str, Any]] = None,
    ) -> bool:
        discipline_name = str(discipline or "").strip()
        if not discipline_name:
            self.status_label.setText("Disciplina inválida para revisão")
            return False

        self.current_book_id = ""
        self.current_book_title = discipline_name
        self.current_scope_type = "discipline"
        self.current_discipline = discipline_name
        self.current_discipline_note_path = self._resolve_discipline_note_path(discipline_name)
        self.current_book_dir = self.current_discipline_note_path.parent if self.current_discipline_note_path else None
        self.current_canvas_path = self._canvas_path_for_discipline(discipline_name)

        if not self.current_canvas_path:
            self.status_label.setText("Vault não disponível para revisão por disciplina")
            return False

        self._ensure_canvas_exists()
        self.current_canvas_payload = self._load_sanitized_canvas_payload(self.current_canvas_path)
        self._render_canvas(self.current_canvas_payload)
        self._isolated_spawn_index = 0
        self._opened_node_id = ""
        self.current_source_note_path = None
        self.viewer_title_label.setText("Conteúdo do card")
        self.note_viewer.clear()
        self.new_note_title_input.clear()
        self.new_note_editor.clear()
        self.card_title_input.clear()
        self.card_body_editor.clear()
        self.card_image_path_input.clear()
        self.card_feedback_label.clear()
        self._activate_note_editor()
        self._set_editor_visible(False)
        self._close_side_panel()

        self.book_label.setText(f"Revisão: Disciplina {discipline_name}")
        self.status_label.setText("Mapa mental da disciplina carregado")
        if not self._suppress_pending_work_dialog:
            self._prompt_pending_discipline_works_if_needed(discipline_name)
        if not self._suppress_pending_annotation_dialog:
            self._prompt_pending_discipline_annotations_if_needed(discipline_name)
        self._schedule_next_question_prompt(reset=True)
        if source_event:
            logger.debug("Review workspace de disciplina aberto com payload: %s", source_event)
        return True

    def _load_sanitized_canvas_payload(self, canvas_path: Path) -> Dict[str, Any]:
        payload = self.mindmap_module.load_canvas_payload(canvas_path)
        sanitized = self.mindmap_module.strip_chapter_nodes(payload)
        clean_payload = sanitized.payload
        if clean_payload != payload:
            try:
                canvas_path.write_text(
                    json.dumps(clean_payload, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8",
                )
            except Exception as exc:
                logger.warning("Falha ao remover capítulos do canvas: %s", exc)
        return clean_payload

    def _prompt_pending_discipline_works_if_needed(self, discipline: str) -> None:
        pending = self._collect_pending_discipline_works(discipline)
        if not pending:
            return

        parent_choices = self._discipline_parent_choices_for_pending()
        if not parent_choices:
            parent_choices = [
                {"mode": "root", "target_id": "node-disciplina", "label": "Raiz da disciplina"},
                {"mode": "orphan", "target_id": "", "label": "Criar card órfão"},
            ]

        dialog = PendingDisciplineWorksDialog(
            discipline=discipline,
            pending_works=pending,
            parent_choices=parent_choices,
            parent=self,
        )
        if dialog.exec() != QDialog.DialogCode.Accepted:
            self.status_label.setText(
                f"{len(pending)} obra(s) pendente(s) aguardando vínculo no mapa da disciplina"
            )
            return

        selections = dialog.selections()
        integrated = 0
        for work in pending:
            work_key = str(work.get("work_key") or "").strip()
            if not work_key:
                continue
            selection = selections.get(work_key) or {}
            mode = str(selection.get("mode") or "root").strip().lower()
            target_id = str(selection.get("target_id") or "").strip()
            result = self.integrate_existing_book_into_discipline(
                discipline=discipline,
                book_dir=str(work.get("book_dir") or "").strip(),
                author=str(work.get("author") or "").strip(),
                work=str(work.get("work") or "").strip(),
                parent_node_id=target_id,
                create_orphan=(mode == "orphan"),
            )
            if bool(result.get("ok")):
                integrated += 1

        if integrated:
            self.status_label.setText(
                f"{integrated} nova(s) obra(s) integrada(s) ao mapa da disciplina"
            )

    def _prompt_pending_discipline_annotations_if_needed(self, discipline: str) -> None:
        pending = self._collect_pending_discipline_annotations(discipline)
        if not pending:
            return

        parent_choices = self._annotation_parent_choices_for_pending()
        if not parent_choices:
            parent_choices = [
                {"mode": "root", "target_id": "node-disciplina", "label": "Raiz da disciplina"},
                {"mode": "orphan", "target_id": "", "label": "Manter como card órfão"},
            ]

        dialog = PendingDisciplineAnnotationsDialog(
            discipline=discipline,
            pending_annotations=pending,
            parent_choices=parent_choices,
            parent=self,
        )
        if dialog.exec() != QDialog.DialogCode.Accepted:
            self.status_label.setText(
                f"{len(pending)} anotação(ões) pendente(s) aguardando vínculo no mapa da disciplina"
            )
            return

        selections = dialog.selections()
        integrated = 0
        for annotation in pending:
            annotation_key = str(annotation.get("annotation_key") or "").strip()
            if not annotation_key:
                continue
            selection = selections.get(annotation_key) or {}
            mode = str(selection.get("mode") or "root").strip().lower()
            target_id = str(selection.get("target_id") or "").strip()
            result = self.integrate_existing_annotation_into_discipline(
                discipline=discipline,
                note_path=str(annotation.get("note_path") or "").strip(),
                title=str(annotation.get("title") or "").strip(),
                parent_node_id=target_id,
                create_orphan=(mode == "orphan"),
                mark_selection_resolved=True,
            )
            if bool(result.get("ok")):
                integrated += 1

        if integrated:
            self.status_label.setText(
                f"{integrated} nova(s) anotação(ões) organizada(s) no mapa da disciplina"
            )

    def _collect_pending_discipline_annotations(self, discipline: str) -> List[Dict[str, Any]]:
        if self.current_scope_type != "discipline":
            return []

        linked_annotations = self._linked_annotations_from_discipline_note(discipline)
        if not linked_annotations:
            return []

        nodes = self.current_canvas_payload.get("nodes")
        edges = self.current_canvas_payload.get("edges")
        if not isinstance(nodes, list):
            nodes = []
        if not isinstance(edges, list):
            edges = []

        existing_nodes = self._existing_annotation_nodes_in_canvas(self.current_canvas_payload)
        pending: List[Dict[str, Any]] = []
        for entry in linked_annotations:
            annotation_key = str(entry.get("annotation_key") or "").strip()
            if not annotation_key:
                continue
            existing_node = existing_nodes.get(annotation_key)
            if existing_node is None:
                pending.append(
                    {
                        **entry,
                        "reason": "missing",
                        "reason_label": "Ainda não apareceu no canvas",
                    }
                )
                continue
            if not self._annotation_requires_branch_decision(existing_node, edges):
                continue
            pending.append(
                {
                    **entry,
                    "node_id": str(existing_node.get("id") or "").strip(),
                    "reason": "unresolved",
                    "reason_label": "Ainda sem ramo definido",
                }
            )
        return pending

    def _collect_pending_discipline_works(self, discipline: str) -> List[Dict[str, Any]]:
        if self.current_scope_type != "discipline":
            return []

        linked_books = self._linked_books_from_discipline_note(discipline)
        if not linked_books:
            return []

        existing_keys = self._existing_work_keys_in_canvas(self.current_canvas_payload)
        pending: List[Dict[str, Any]] = []
        for entry in linked_books:
            work_key = str(entry.get("work_key") or "").strip()
            if not work_key or work_key in existing_keys:
                continue
            pending.append(entry)
        return pending

    def _linked_books_from_discipline_note(self, discipline: str) -> List[Dict[str, Any]]:
        vault_root = self._vault_root()
        if not vault_root:
            return []

        note_path = self.current_discipline_note_path or self._resolve_discipline_note_path(discipline)
        if not note_path or not note_path.exists():
            return []

        try:
            content = note_path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            return []

        discovered: List[Dict[str, Any]] = []
        seen: set[str] = set()
        for token in re.findall(r"\[\[([^\]]+)\]\]", content):
            target = token.split("|", 1)[0].strip().replace("\\", "/")
            if not target:
                continue
            resolved = self._resolve_reference_in_vault(target)
            if not resolved or not resolved.exists() or resolved.suffix.lower() != ".md":
                continue
            rel = self.mindmap_module._to_relative_vault_path(resolved, vault_root).replace("\\", "/")
            book_data = self._book_metadata_from_relative_path(rel)
            if not book_data:
                continue
            work_key = str(book_data.get("work_key") or "").strip()
            if not work_key or work_key in seen:
                continue
            seen.add(work_key)
            discovered.append(book_data)
        return discovered

    def _linked_annotations_from_discipline_note(self, discipline: str) -> List[Dict[str, Any]]:
        vault_root = self._vault_root()
        if not vault_root:
            return []

        note_path = self.current_discipline_note_path or self._resolve_discipline_note_path(discipline)
        if not note_path or not note_path.exists():
            return []

        try:
            content = note_path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            return []

        discovered: List[Dict[str, Any]] = []
        seen: set[str] = set()
        for token in re.findall(r"\[\[([^\]]+)\]\]", content):
            target = token.split("|", 1)[0].strip().replace("\\", "/")
            if not target:
                continue
            resolved = self._resolve_reference_in_vault(target)
            if not resolved or not resolved.exists() or resolved.suffix.lower() != ".md":
                continue
            rel = self.mindmap_module._to_relative_vault_path(resolved, vault_root).replace("\\", "/")
            if not self._is_annotation_file_ref(rel):
                continue
            annotation_key = str(rel).strip()
            if not annotation_key or annotation_key in seen:
                continue
            seen.add(annotation_key)
            discovered.append(
                {
                    "annotation_key": annotation_key,
                    "title": resolved.stem,
                    "relative_path": rel,
                    "note_path": str(resolved.resolve(strict=False)),
                }
            )
        return discovered

    def _existing_work_keys_in_canvas(self, payload: Dict[str, Any]) -> set[str]:
        nodes = payload.get("nodes") if isinstance(payload.get("nodes"), list) else []
        keys: set[str] = set()
        for node in nodes:
            if not isinstance(node, dict):
                continue
            work_key = str(node.get("work_key") or "").strip()
            if work_key:
                keys.add(work_key)
                continue
            file_ref = str(node.get("file") or "").strip().replace("\\", "/")
            if not file_ref:
                continue
            meta = self._book_metadata_from_relative_path(file_ref)
            inferred = str(meta.get("work_key") or "").strip() if meta else ""
            if inferred:
                keys.add(inferred)
        return keys

    def _existing_annotation_nodes_in_canvas(self, payload: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        nodes = payload.get("nodes") if isinstance(payload.get("nodes"), list) else []
        annotations: Dict[str, Dict[str, Any]] = {}
        for node in nodes:
            if not isinstance(node, dict):
                continue
            file_ref = str(node.get("file") or "").strip().replace("\\", "/")
            if not self._is_annotation_file_ref(file_ref):
                continue
            annotations[file_ref] = node
        return annotations

    def _annotation_requires_branch_decision(
        self,
        node: Dict[str, Any],
        edges: List[Dict[str, Any]],
    ) -> bool:
        resolved = str(node.get("discipline_annotation_parent_resolved") or "").strip().lower()
        if resolved in {"1", "true", "yes"}:
            return False

        node_id = str(node.get("id") or "").strip()
        if not node_id:
            return True

        incoming: set[str] = set()
        for edge in edges:
            if not isinstance(edge, dict):
                continue
            if str(edge.get("toNode") or "").strip() != node_id:
                continue
            from_node = str(edge.get("fromNode") or "").strip()
            if from_node and from_node != node_id:
                incoming.add(from_node)

        if not incoming:
            return True
        return incoming == {"node-disciplina"}

    def _discipline_parent_choices_for_pending(self) -> List[Dict[str, str]]:
        choices: List[Dict[str, str]] = [
            {"mode": "root", "target_id": "node-disciplina", "label": "Raiz da disciplina"},
        ]

        for anchor in self._discipline_work_anchor_candidates():
            node_id = str(anchor.get("node_id") or "").strip()
            label = str(anchor.get("label") or "").strip()
            if not node_id or not label:
                continue
            choices.append(
                {
                    "mode": "anchor",
                    "target_id": node_id,
                    "label": f"Ligar à obra: {label}",
                }
            )

        choices.append({"mode": "orphan", "target_id": "", "label": "Criar card órfão"})
        return choices

    def _annotation_parent_choices_for_pending(self) -> List[Dict[str, str]]:
        choices: List[Dict[str, str]] = [
            {"mode": "root", "target_id": "node-disciplina", "label": "Raiz da disciplina"},
        ]

        for candidate in self._discipline_annotation_parent_candidates():
            node_id = str(candidate.get("node_id") or "").strip()
            label = str(candidate.get("label") or "").strip()
            if not node_id or not label:
                continue
            choices.append(
                {
                    "mode": "branch",
                    "target_id": node_id,
                    "label": f"Ligar ao nódulo: {label}",
                }
            )

        choices.append({"mode": "orphan", "target_id": "", "label": "Manter como card órfão"})
        return choices

    def _discipline_annotation_parent_candidates(self) -> List[Dict[str, str]]:
        nodes = self.current_canvas_payload.get("nodes")
        if not isinstance(nodes, list):
            return []

        candidates: List[Dict[str, str]] = []
        seen: set[str] = set()
        for node in nodes:
            if not isinstance(node, dict):
                continue
            node_id = str(node.get("id") or "").strip()
            if not node_id or node_id == "node-disciplina":
                continue
            if self._is_chapter_like_node(node) or self._is_annotation_node(node):
                continue
            label = self._annotation_parent_label(node)
            if not label or node_id in seen:
                continue
            seen.add(node_id)
            candidates.append({"node_id": node_id, "label": label})

        candidates.sort(key=lambda item: self._normalize_token(item.get("label") or ""))
        return candidates

    def _discipline_work_anchor_candidates(self) -> List[Dict[str, str]]:
        nodes = self.current_canvas_payload.get("nodes")
        if not isinstance(nodes, list):
            return []

        candidates: Dict[str, Dict[str, str]] = {}
        for node in nodes:
            if not isinstance(node, dict):
                continue
            node_id = str(node.get("id") or "").strip()
            if not node_id or node_id == "node-disciplina":
                continue
            if self._is_chapter_like_node(node):
                continue

            work_key = str(node.get("work_key") or "").strip()
            if work_key:
                label = str(node.get("work_title") or node.get("text") or node.get("title") or "").strip()
                label = self._compact_work_label(label)
                if label:
                    existing = candidates.get(work_key)
                    if not existing or self._is_work_anchor_node(node):
                        candidates[work_key] = {"node_id": node_id, "label": label}
                continue

            file_ref = str(node.get("file") or "").strip().replace("\\", "/")
            if not file_ref:
                continue
            meta = self._book_metadata_from_relative_path(file_ref)
            if not meta:
                continue
            inferred_key = str(meta.get("work_key") or "").strip()
            if not inferred_key or inferred_key in candidates:
                continue
            label = str(meta.get("label") or meta.get("work") or "").strip()
            if label:
                candidates[inferred_key] = {"node_id": node_id, "label": label}

        return sorted(candidates.values(), key=lambda item: self._normalize_token(item.get("label") or ""))

    def _is_work_anchor_node(self, node: Dict[str, Any]) -> bool:
        if str(node.get("discipline_work_anchor") or "").strip().lower() in {"1", "true", "yes"}:
            return True
        work_key = str(node.get("work_key") or "").strip()
        if not work_key:
            return False
        if str(node.get("id") or "").strip().lower() in {"node-livro", "node-disciplina"}:
            return False
        signal = self._node_signal_text(node)
        return "mapa base da obra" in signal or "obra" in signal

    def _compact_work_label(self, value: str) -> str:
        text = str(value or "").strip()
        if not text:
            return ""
        text = re.sub(r"(?i)^mapa base da obra\s*", "", text).strip()
        text = re.sub(r"\s+", " ", text.replace("\n", " ")).strip()
        return text

    def _annotation_parent_label(self, node: Dict[str, Any]) -> str:
        if self._is_work_anchor_node(node):
            label = self._compact_work_label(
                str(node.get("work_title") or node.get("text") or node.get("title") or "")
            )
            if label:
                return f"Obra: {label}"

        node_type = str(node.get("type") or "").strip().lower()
        file_ref = str(node.get("file") or "").strip().replace("\\", "/")
        if file_ref:
            label = Path(file_ref).stem
            if self._book_metadata_from_relative_path(file_ref):
                return f"Nota da obra: {label}"
            return f"Nota: {label}"

        text = str(node.get("title") or node.get("caption") or node.get("text") or "").strip()
        compact = re.sub(r"\s+", " ", text.replace("\n", " ")).strip()
        if compact:
            prefix = "Imagem" if node_type == "image" else "Nódulo"
            return f"{prefix}: {compact[:72]}"
        return f"Nódulo: {str(node.get('id') or '').strip()}"

    def _is_annotation_file_ref(self, file_ref: str) -> bool:
        normalized = str(file_ref or "").strip().replace("\\", "/")
        if not normalized:
            return False
        parts = Path(normalized).parts
        return bool(parts) and parts[0] in {"02-ANOTAÇÕES", "02-ANOTACOES"}

    def _is_annotation_node(self, node: Dict[str, Any]) -> bool:
        note_kind = str(node.get("note_kind") or "").strip().lower()
        if note_kind == "annotation":
            return True
        return self._is_annotation_file_ref(str(node.get("file") or ""))

    def _resolve_reference_in_vault(self, reference: str) -> Optional[Path]:
        vault_root = self._vault_root()
        if not vault_root:
            return None
        target = str(reference or "").strip().replace("\\", "/")
        if not target:
            return None

        candidate = vault_root / target
        if candidate.exists():
            return candidate

        stem_candidate = (vault_root / target).with_suffix(".md")
        if stem_candidate.exists():
            return stem_candidate
        return None

    def _book_metadata_from_relative_path(self, relative_path: str) -> Optional[Dict[str, str]]:
        normalized = str(relative_path or "").strip().replace("\\", "/")
        if not normalized:
            return None
        parts = Path(normalized).parts
        if len(parts) < 4 or parts[0] != "01-LEITURAS":
            return None

        author = str(parts[1]).strip()
        work = str(parts[2]).strip()
        if not author or not work:
            return None

        book_dir = "/".join(parts[:3])
        work_key = self._normalize_token(f"{author}/{work}")
        return {
            "author": author,
            "work": work,
            "book_dir": book_dir,
            "relative_path": normalized,
            "work_key": work_key,
            "label": f"{author}/{work}",
        }

    def _build_discipline_base_canvas(
        self,
        *,
        vault_root: Path,
        discipline: str,
        discipline_note: Optional[Path],
    ) -> Dict[str, Any]:
        root_title = f"Mapa da disciplina\n{discipline}"
        root_w, root_h = self.mindmap_module._card_dimensions_for_title(root_title, is_text=True)
        nodes: List[Dict[str, Any]] = [
            {
                "id": "node-disciplina",
                "type": "text",
                "text": root_title,
                "x": 0,
                "y": 0,
                "width": root_w,
                "height": root_h,
                "color": "4",
            }
        ]
        edges: List[Dict[str, Any]] = []

        linked_files: List[str] = []
        if discipline_note and discipline_note.exists():
            note_rel = self.mindmap_module._to_relative_vault_path(discipline_note, vault_root)
            linked_files.append(note_rel)
            try:
                text = discipline_note.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                text = ""
            for link in re.findall(r"\[\[([^\]]+)\]\]", text):
                target = link.split("|", 1)[0].strip()
                if not target:
                    continue
                candidate = (vault_root / target).with_suffix(".md")
                if candidate.exists():
                    linked_files.append(self.mindmap_module._to_relative_vault_path(candidate, vault_root))
                    continue
                candidate = vault_root / target
                if candidate.exists() and candidate.suffix.lower() == ".md":
                    linked_files.append(self.mindmap_module._to_relative_vault_path(candidate, vault_root))

        unique_files: List[str] = []
        seen: set[str] = set()
        for path in linked_files:
            normalized = str(path).replace("\\", "/").strip()
            if normalized and normalized not in seen:
                seen.add(normalized)
                unique_files.append(normalized)

        base_x = 460
        base_y = -140
        step_y = 128
        for index, rel_path in enumerate(unique_files):
            label = Path(rel_path).stem
            card_w, card_h = self.mindmap_module._card_dimensions_for_title(label)
            node_id = f"node-disciplina-arquivo-{index + 1}"
            node_payload: Dict[str, Any] = {
                "id": node_id,
                "type": "file",
                "file": rel_path,
                "x": base_x,
                "y": base_y + (index * step_y),
                "width": card_w,
                "height": card_h,
                "color": "2" if "01-LEITURAS/" in rel_path else "6",
            }
            if self._is_annotation_file_ref(rel_path):
                node_payload["note_kind"] = "annotation"
            nodes.append(node_payload)
            edges.append(
                {
                    "id": f"edge-disciplina-arquivo-{index + 1}",
                    "fromNode": "node-disciplina",
                    "toNode": node_id,
                    "fromSide": "right",
                    "toSide": "left",
                    "label": "referência",
                    "color": "2",
                }
            )

        return {"nodes": nodes, "edges": edges}

    def ingest_discipline_image(
        self,
        *,
        discipline: str,
        image_path: str,
        description: str = "",
    ) -> Dict[str, Any]:
        if not self.open_discipline_review(discipline=discipline):
            return {"ok": False, "error": "Não foi possível abrir mapa da disciplina."}

        imported = self._import_image_to_assets(Path(image_path))
        if not imported:
            return {"ok": False, "error": "Não foi possível importar imagem para assets."}

        card_w = 280
        card_h = 180
        target = self._next_isolated_spawn_point(card_w, card_h)
        node_id = self._generate_unique_node_id("node-image")
        image_node: Dict[str, Any] = {
            "id": node_id,
            "type": "image",
            "image": imported,
            "caption": str(description or "").strip(),
            "text": str(description or "").strip(),
            "x": round(float(target.x()), 2),
            "y": round(float(target.y()), 2),
            "width": card_w,
            "height": card_h,
            "color": "6",
        }
        item = self._add_node_to_canvas(image_node)
        if not item:
            return {"ok": False, "error": "Falha ao adicionar imagem ao canvas."}

        if str(description or "").strip():
            text_w, text_h = self.mindmap_module._card_dimensions_for_title(str(description)[:60], is_text=True)
            text_id = self._generate_unique_node_id("node-descricao-imagem")
            text_node: Dict[str, Any] = {
                "id": text_id,
                "type": "text",
                "text": str(description).strip(),
                "x": round(float(target.x()) + 330.0, 2),
                "y": round(float(target.y()) + 15.0, 2),
                "width": text_w,
                "height": max(90, text_h),
                "color": "1",
            }
            text_item = self._add_node_to_canvas(text_node)
            if text_item:
                self._create_edge_between(
                    from_node=node_id,
                    to_node=text_id,
                    label="descrição",
                    color_id="1",
                )

        anchor_id = "node-disciplina"
        if anchor_id in self._node_items:
            self._create_edge_between(
                from_node=anchor_id,
                to_node=node_id,
                label="imagem contextual",
                color_id="6",
            )
        self._persist_canvas_payload()
        self.status_label.setText("Imagem adicionada ao mapa mental da disciplina")
        return {
            "ok": True,
            "canvas_path": str(self.current_canvas_path) if self.current_canvas_path else "",
            "image_ref": imported,
            "node_id": node_id,
        }

    def integrate_existing_book_into_discipline(
        self,
        *,
        discipline: str,
        book_dir: str,
        author: str = "",
        work: str = "",
        parent_node_id: str = "",
        create_orphan: bool = False,
    ) -> Dict[str, Any]:
        previous_suppress = self._suppress_pending_work_dialog
        previous_annotation_suppress = self._suppress_pending_annotation_dialog
        self._suppress_pending_work_dialog = True
        self._suppress_pending_annotation_dialog = True
        try:
            if not self.open_discipline_review(discipline=discipline):
                return {"ok": False, "error": "Não foi possível abrir o mapa da disciplina."}

            vault_root = self._vault_root()
            if not vault_root:
                return {"ok": False, "error": "Vault indisponível para integração do livro."}

            raw_dir = Path(str(book_dir or "").strip())
            if not str(raw_dir):
                return {"ok": False, "error": "Diretório do livro inválido."}
            book_abs = raw_dir if raw_dir.is_absolute() else (vault_root / raw_dir)
            book_abs = book_abs.resolve(strict=False)
            if not book_abs.exists() or not book_abs.is_dir():
                return {"ok": False, "error": f"Diretório do livro não encontrado: {book_abs}"}

            work_title = str(work or book_abs.name).strip() or book_abs.name
            author_name = str(author or book_abs.parent.name).strip() or "Sem autor"
            work_key = self._normalize_token(f"{author_name}/{work_title}")

            nodes = self.current_canvas_payload.get("nodes")
            edges = self.current_canvas_payload.get("edges")
            if not isinstance(nodes, list):
                nodes = []
                self.current_canvas_payload["nodes"] = nodes
            if not isinstance(edges, list):
                edges = []
                self.current_canvas_payload["edges"] = edges

            anchor_id = "node-disciplina"
            if anchor_id not in {
                str(node.get("id") or "").strip()
                for node in nodes
                if isinstance(node, dict)
            }:
                root_title = f"Mapa da disciplina\n{discipline}"
                root_w, root_h = self.mindmap_module._card_dimensions_for_title(root_title, is_text=True)
                nodes.insert(
                    0,
                    {
                        "id": anchor_id,
                        "type": "text",
                        "text": root_title,
                        "x": 0,
                        "y": 0,
                        "width": root_w,
                        "height": root_h,
                        "color": "4",
                    },
                )

            target_parent_id = str(parent_node_id or "").strip()
            if not create_orphan and not target_parent_id:
                target_parent_id = anchor_id
            if create_orphan:
                target_parent_id = ""

            existing_file_nodes: Dict[str, str] = {}
            work_anchor_id = self._find_work_anchor_node_id(nodes, work_key)
            for node in nodes:
                if not isinstance(node, dict):
                    continue
                if str(node.get("type") or "").strip().lower() != "file":
                    continue
                node_id = str(node.get("id") or "").strip()
                ref = str(node.get("file") or "").strip().replace("\\", "/")
                if node_id and ref:
                    existing_file_nodes[ref] = node_id

            canvas_merge = self._import_existing_book_canvas_into_discipline(
                vault_root=vault_root,
                work_title=work_title,
                author_name=author_name,
                work_key=work_key,
                book_abs=book_abs,
                nodes=nodes,
                edges=edges,
                existing_file_nodes=existing_file_nodes,
            )

            if not work_anchor_id:
                work_anchor_id = str(canvas_merge.get("imported_root_id") or "").strip()
            if not work_anchor_id:
                work_anchor_id = self._ensure_discipline_work_anchor_node(
                    nodes=nodes,
                    author_name=author_name,
                    work_title=work_title,
                    work_key=work_key,
                )
            self._tag_work_anchor_node(
                nodes=nodes,
                node_id=work_anchor_id,
                author_name=author_name,
                work_title=work_title,
                work_key=work_key,
                book_dir=book_abs,
                vault_root=vault_root,
            )

            anchor_node = self._find_node_payload(nodes, work_anchor_id)
            anchor_x, anchor_y = self._node_position(anchor_node or {})
            step_y = 104.0

            added_note_nodes = 0
            added_note_edges = 0
            note_offset = 0
            primary_book_note = find_primary_book_note(book_abs, title=work_title)
            for note_abs in self._list_book_markdown_files(book_abs):
                rel = self.mindmap_module._to_relative_vault_path(note_abs, vault_root).replace("\\", "/")
                existing_id = existing_file_nodes.get(rel)
                if existing_id:
                    if not self._has_edge_payload(edges, work_anchor_id, existing_id):
                        edges.append(
                            {
                                "id": self._generate_unique_edge_id(),
                                "fromNode": work_anchor_id,
                                "toNode": existing_id,
                                "fromSide": "right",
                                "toSide": "left",
                                "label": "material da obra",
                                "color": "2",
                            }
                        )
                        added_note_edges += 1
                    continue

                node_id = self._generate_unique_node_id(f"node-livro-nota-{self._sanitize_filename(note_abs.stem)}")
                card_w, card_h = self.mindmap_module._card_dimensions_for_title(note_abs.stem)
                nodes.append(
                    {
                        "id": node_id,
                        "type": "file",
                        "file": rel,
                        "x": round(anchor_x + 420.0, 2),
                        "y": round(anchor_y - 140.0 + (note_offset * step_y), 2),
                        "width": card_w,
                        "height": card_h,
                        "color": "2",
                        "work_key": work_key,
                        "work_title": work_title,
                        "author_name": author_name,
                    }
                )
                existing_file_nodes[rel] = node_id
                added_note_nodes += 1
                note_offset += 1

                if not self._has_edge_payload(edges, work_anchor_id, node_id):
                    edges.append(
                        {
                            "id": self._generate_unique_edge_id(),
                            "fromNode": work_anchor_id,
                            "toNode": node_id,
                            "fromSide": "right",
                            "toSide": "left",
                            "label": "material da obra",
                            "color": "2",
                        }
                    )
                    added_note_edges += 1

            if target_parent_id and target_parent_id != work_anchor_id and not self._has_edge_payload(edges, target_parent_id, work_anchor_id):
                edge_label = f"obra: {author_name}/{work_title}"
                edge_color = "2" if target_parent_id == anchor_id else "6"
                edges.append(
                    {
                        "id": self._generate_unique_edge_id(),
                        "fromNode": target_parent_id,
                        "toNode": work_anchor_id,
                        "fromSide": "right",
                        "toSide": "left",
                        "label": edge_label,
                        "color": edge_color,
                    }
                )

            discipline_update = self._append_links_to_discipline_note(
                discipline=discipline,
                linked_paths=[str(primary_book_note)] if primary_book_note else [],
            )

            self.current_canvas_payload = {"nodes": nodes, "edges": edges}
            self._render_canvas(self.current_canvas_payload, reset_zoom=False)
            self._persist_canvas_payload()
            self.status_label.setText(f"Livro {author_name}/{work_title} integrado à disciplina")

            return {
                "ok": True,
                "work_anchor_id": work_anchor_id,
                "added_note_nodes": added_note_nodes,
                "added_note_edges": added_note_edges,
                "imported_canvas_nodes": int(canvas_merge.get("added_nodes", 0) or 0),
                "imported_canvas_edges": int(canvas_merge.get("added_edges", 0) or 0),
                "discipline_links_added": int(discipline_update.get("added_links", 0) or 0),
                "discipline_note_path": discipline_update.get("note_path", ""),
                "book_dir": str(book_abs),
            }
        finally:
            self._suppress_pending_work_dialog = previous_suppress
            self._suppress_pending_annotation_dialog = previous_annotation_suppress

    def queue_existing_book_for_discipline(
        self,
        *,
        discipline: str,
        book_dir: str,
        author: str = "",
        work: str = "",
    ) -> Dict[str, Any]:
        if not self.open_discipline_review(discipline=discipline):
            return {"ok": False, "error": "Não foi possível abrir o mapa da disciplina."}

        vault_root = self._vault_root()
        if not vault_root:
            return {"ok": False, "error": "Vault indisponível para vincular o livro."}

        raw_dir = Path(str(book_dir or "").strip())
        if not str(raw_dir):
            return {"ok": False, "error": "Diretório do livro inválido."}
        book_abs = raw_dir if raw_dir.is_absolute() else (vault_root / raw_dir)
        book_abs = book_abs.resolve(strict=False)
        if not book_abs.exists() or not book_abs.is_dir():
            return {"ok": False, "error": f"Diretório do livro não encontrado: {book_abs}"}

        work_title = str(work or book_abs.name).strip() or book_abs.name
        author_name = str(author or book_abs.parent.name).strip() or "Sem autor"
        work_key = self._normalize_token(f"{author_name}/{work_title}")

        existing_keys = self._existing_work_keys_in_canvas(self.current_canvas_payload)
        primary_book_note = find_primary_book_note(book_abs, title=work_title)
        if not primary_book_note:
            return {
                "ok": False,
                "error": "Não foi possível localizar a nota principal da obra para registrá-la na disciplina.",
            }

        discipline_update = self._append_links_to_discipline_note(
            discipline=discipline,
            linked_paths=[str(primary_book_note)],
        )

        if work_key in existing_keys:
            self.status_label.setText(f"Livro {author_name}/{work_title} já está presente no mapa da disciplina")
            return {
                "ok": True,
                "already_present": True,
                "dialog_shown": False,
                "discipline_links_added": int(discipline_update.get("added_links", 0) or 0),
                "discipline_note_path": discipline_update.get("note_path", ""),
                "book_dir": str(book_abs),
            }

        pending_before = len(self._collect_pending_discipline_works(discipline))
        self._prompt_pending_discipline_works_if_needed(discipline)
        pending_after = len(self._collect_pending_discipline_works(discipline))

        return {
            "ok": True,
            "already_present": False,
            "dialog_shown": pending_before > 0 or pending_after >= 0,
            "discipline_links_added": int(discipline_update.get("added_links", 0) or 0),
            "discipline_note_path": discipline_update.get("note_path", ""),
            "book_dir": str(book_abs),
        }

    def integrate_existing_annotation_into_discipline(
        self,
        *,
        discipline: str,
        note_path: str,
        title: str = "",
        parent_node_id: str = "",
        create_orphan: bool = False,
        mark_selection_resolved: bool = True,
    ) -> Dict[str, Any]:
        previous_work_suppress = self._suppress_pending_work_dialog
        previous_annotation_suppress = self._suppress_pending_annotation_dialog
        self._suppress_pending_work_dialog = True
        self._suppress_pending_annotation_dialog = True
        try:
            if not self.open_discipline_review(discipline=discipline):
                return {"ok": False, "error": "Não foi possível abrir o mapa da disciplina."}

            vault_root = self._vault_root()
            if not vault_root:
                return {"ok": False, "error": "Vault indisponível para vincular a anotação."}

            raw_path = Path(str(note_path or "").strip())
            if not str(raw_path):
                return {"ok": False, "error": "Caminho da anotação inválido."}

            note_abs = raw_path if raw_path.is_absolute() else (vault_root / raw_path)
            note_abs = note_abs.resolve(strict=False)
            if not note_abs.exists() or not note_abs.is_file() or note_abs.suffix.lower() != ".md":
                return {"ok": False, "error": f"Anotação não encontrada: {note_abs}"}

            try:
                relative = note_abs.relative_to(vault_root)
            except Exception:
                return {"ok": False, "error": "A anotação precisa estar dentro do vault."}

            if not relative.parts or relative.parts[0] not in {"02-ANOTAÇÕES", "02-ANOTACOES"}:
                return {"ok": False, "error": "A anotação precisa estar em 02-ANOTAÇÕES."}

            rel = self.mindmap_module._to_relative_vault_path(note_abs, vault_root).replace("\\", "/")
            note_title = str(title or note_abs.stem).strip() or note_abs.stem

            nodes = self.current_canvas_payload.get("nodes")
            edges = self.current_canvas_payload.get("edges")
            if not isinstance(nodes, list):
                nodes = []
                self.current_canvas_payload["nodes"] = nodes
            if not isinstance(edges, list):
                edges = []
                self.current_canvas_payload["edges"] = edges

            anchor_id = "node-disciplina"
            if anchor_id not in {
                str(node.get("id") or "").strip()
                for node in nodes
                if isinstance(node, dict)
            }:
                root_title = f"Mapa da disciplina\n{discipline}"
                root_w, root_h = self.mindmap_module._card_dimensions_for_title(root_title, is_text=True)
                nodes.insert(
                    0,
                    {
                        "id": anchor_id,
                        "type": "text",
                        "text": root_title,
                        "x": 0,
                        "y": 0,
                        "width": root_w,
                        "height": root_h,
                        "color": "4",
                    },
                )

            target_parent_id = str(parent_node_id or "").strip()
            if not create_orphan and not target_parent_id:
                target_parent_id = anchor_id
            if create_orphan:
                target_parent_id = ""

            discipline_update = self._append_annotation_links_to_discipline_note(
                discipline=discipline,
                linked_paths=[str(note_abs)],
            )

            existing_nodes = self._existing_annotation_nodes_in_canvas({"nodes": nodes, "edges": edges})
            existing_node = existing_nodes.get(rel)
            if existing_node is not None:
                node_id = str(existing_node.get("id") or "").strip()
                changed = self._apply_annotation_parent_selection(
                    nodes=nodes,
                    edges=edges,
                    node_id=node_id,
                    parent_node_id=target_parent_id,
                    create_orphan=create_orphan,
                    mark_resolved=mark_selection_resolved,
                )
                if changed:
                    self.current_canvas_payload = {"nodes": nodes, "edges": edges}
                    self._render_canvas(self.current_canvas_payload, reset_zoom=False)
                    self._persist_canvas_payload()

                self.status_label.setText(f"Anotação {note_title} atualizada no mapa da disciplina")
                return {
                    "ok": True,
                    "already_present": True,
                    "discipline_links_added": int(discipline_update.get("added_links", 0) or 0),
                    "discipline_note_path": discipline_update.get("note_path", ""),
                    "annotation_path": str(note_abs),
                    "node_id": node_id,
                    "edge_updated": changed,
                }

            card_w, card_h = self.mindmap_module._card_dimensions_for_title(note_title)
            spawn = self._next_isolated_spawn_point(card_w, card_h)
            node_id = self._generate_unique_node_id(
                f"node-disciplina-anotacao-{self._sanitize_filename(note_abs.stem)}"
            )
            node_payload: Dict[str, Any] = {
                "id": node_id,
                "type": "file",
                "file": rel,
                "x": round(float(spawn.x()), 2),
                "y": round(float(spawn.y()), 2),
                "width": card_w,
                "height": card_h,
                "color": "6",
                "note_kind": "annotation",
            }
            if mark_selection_resolved:
                node_payload["discipline_annotation_parent_resolved"] = True
                node_payload["discipline_annotation_parent_mode"] = (
                    "orphan"
                    if create_orphan
                    else ("root" if target_parent_id == anchor_id else "node")
                )
                node_payload["discipline_annotation_parent_id"] = target_parent_id
            nodes.append(node_payload)

            if target_parent_id:
                edges.append(
                    {
                        "id": self._generate_unique_edge_id(),
                        "fromNode": target_parent_id,
                        "toNode": node_id,
                        "fromSide": "right",
                        "toSide": "left",
                        "label": "anotação",
                        "color": "6",
                    }
                )

            self.current_canvas_payload = {"nodes": nodes, "edges": edges}
            self._render_canvas(self.current_canvas_payload, reset_zoom=False)
            self._persist_canvas_payload()
            self.status_label.setText(f"Anotação {note_title} integrada à disciplina")

            return {
                "ok": True,
                "already_present": False,
                "discipline_links_added": int(discipline_update.get("added_links", 0) or 0),
                "discipline_note_path": discipline_update.get("note_path", ""),
                "annotation_path": str(note_abs),
                "node_id": node_id,
            }
        finally:
            self._suppress_pending_work_dialog = previous_work_suppress
            self._suppress_pending_annotation_dialog = previous_annotation_suppress

    def queue_existing_annotation_for_discipline(
        self,
        *,
        discipline: str,
        note_path: str,
        title: str = "",
    ) -> Dict[str, Any]:
        previous_annotation_suppress = self._suppress_pending_annotation_dialog
        self._suppress_pending_annotation_dialog = True
        try:
            if not self.open_discipline_review(discipline=discipline):
                return {"ok": False, "error": "Não foi possível abrir o mapa da disciplina."}
        finally:
            self._suppress_pending_annotation_dialog = previous_annotation_suppress

        vault_root = self._vault_root()
        if not vault_root:
            return {"ok": False, "error": "Vault indisponível para vincular a anotação."}

        raw_path = Path(str(note_path or "").strip())
        if not str(raw_path):
            return {"ok": False, "error": "Caminho da anotação inválido."}

        note_abs = raw_path if raw_path.is_absolute() else (vault_root / raw_path)
        note_abs = note_abs.resolve(strict=False)
        if not note_abs.exists() or not note_abs.is_file() or note_abs.suffix.lower() != ".md":
            return {"ok": False, "error": f"Anotação não encontrada: {note_abs}"}

        try:
            relative = note_abs.relative_to(vault_root)
        except Exception:
            return {"ok": False, "error": "A anotação precisa estar dentro do vault."}

        if not relative.parts or relative.parts[0] not in {"02-ANOTAÇÕES", "02-ANOTACOES"}:
            return {"ok": False, "error": "A anotação precisa estar em 02-ANOTAÇÕES."}

        rel = self.mindmap_module._to_relative_vault_path(note_abs, vault_root).replace("\\", "/")
        existing_annotations = self._existing_annotation_nodes_in_canvas(self.current_canvas_payload)
        existing_node = existing_annotations.get(rel)

        discipline_update = self._append_annotation_links_to_discipline_note(
            discipline=discipline,
            linked_paths=[str(note_abs)],
        )
        pending_before = self._collect_pending_discipline_annotations(discipline)
        annotation_pending_before = any(
            str(entry.get("annotation_key") or "").strip() == rel
            for entry in pending_before
        )
        self._prompt_pending_discipline_annotations_if_needed(discipline)

        return {
            "ok": True,
            "already_present": existing_node is not None and not annotation_pending_before,
            "dialog_shown": bool(pending_before),
            "discipline_links_added": int(discipline_update.get("added_links", 0) or 0),
            "discipline_note_path": discipline_update.get("note_path", ""),
            "annotation_path": str(note_abs),
        }

    def _apply_annotation_parent_selection(
        self,
        *,
        nodes: List[Dict[str, Any]],
        edges: List[Dict[str, Any]],
        node_id: str,
        parent_node_id: str,
        create_orphan: bool,
        mark_resolved: bool,
    ) -> bool:
        node = self._find_node_payload(nodes, node_id)
        if not node:
            return False

        changed = False
        if str(node.get("note_kind") or "").strip().lower() != "annotation":
            node["note_kind"] = "annotation"
            changed = True
        if str(node.get("color") or "").strip() != "6":
            node["color"] = "6"
            changed = True

        if mark_resolved:
            mode = "orphan" if create_orphan else ("root" if parent_node_id == "node-disciplina" else "node")
            if str(node.get("discipline_annotation_parent_mode") or "").strip() != mode:
                node["discipline_annotation_parent_mode"] = mode
                changed = True
            if str(node.get("discipline_annotation_parent_id") or "").strip() != str(parent_node_id or "").strip():
                node["discipline_annotation_parent_id"] = str(parent_node_id or "").strip()
                changed = True
            resolved = str(node.get("discipline_annotation_parent_resolved") or "").strip().lower()
            if resolved not in {"1", "true", "yes"}:
                node["discipline_annotation_parent_resolved"] = True
                changed = True

        filtered_edges: List[Dict[str, Any]] = []
        existing_target_edge = False
        for edge in edges:
            if not isinstance(edge, dict):
                filtered_edges.append(edge)
                continue
            if str(edge.get("toNode") or "").strip() != node_id:
                filtered_edges.append(edge)
                continue
            if str(edge.get("label") or "").strip().lower() != "anotação":
                filtered_edges.append(edge)
                continue

            from_node = str(edge.get("fromNode") or "").strip()
            if not create_orphan and from_node == str(parent_node_id or "").strip():
                existing_target_edge = True
                filtered_edges.append(edge)
                continue
            changed = True

        if len(filtered_edges) != len(edges):
            edges[:] = filtered_edges

        if not create_orphan and parent_node_id and not existing_target_edge:
            edges.append(
                {
                    "id": self._generate_unique_edge_id(),
                    "fromNode": parent_node_id,
                    "toNode": node_id,
                    "fromSide": "right",
                    "toSide": "left",
                    "label": "anotação",
                    "color": "6",
                }
            )
            changed = True

        return changed

    def _list_book_markdown_files(self, book_dir: Path) -> List[Path]:
        files = [path for path in book_dir.rglob("*.md") if path.is_file()]
        files.sort(key=lambda p: (len(p.relative_to(book_dir).parts), p.name.lower()))
        return files

    def _find_node_payload(self, nodes: List[Dict[str, Any]], node_id: str) -> Optional[Dict[str, Any]]:
        target = str(node_id or "").strip()
        if not target:
            return None
        for node in nodes:
            if isinstance(node, dict) and str(node.get("id") or "").strip() == target:
                return node
        return None

    def _find_work_anchor_node_id(self, nodes: List[Dict[str, Any]], work_key: str) -> str:
        target = str(work_key or "").strip()
        if not target:
            return ""

        fallback = ""
        for node in nodes:
            if not isinstance(node, dict):
                continue
            if str(node.get("work_key") or "").strip() != target:
                continue
            node_id = str(node.get("id") or "").strip()
            if not node_id:
                continue
            if self._is_work_anchor_node(node):
                return node_id
            if not fallback:
                fallback = node_id
        return fallback

    def _ensure_discipline_work_anchor_node(
        self,
        *,
        nodes: List[Dict[str, Any]],
        author_name: str,
        work_title: str,
        work_key: str,
    ) -> str:
        existing = self._find_work_anchor_node_id(nodes, work_key)
        if existing:
            return existing

        card_w, card_h = self.mindmap_module._card_dimensions_for_title(
            f"Obra\n{work_title}",
            is_text=True,
        )
        target = self._next_isolated_spawn_point(card_w, card_h)
        node_id = self._generate_unique_node_id("node-obra")
        nodes.append(
            {
                "id": node_id,
                "type": "text",
                "text": f"Obra\n{work_title}",
                "x": round(float(target.x()), 2),
                "y": round(float(target.y()), 2),
                "width": card_w,
                "height": card_h,
                "color": "4",
                "discipline_work_anchor": True,
                "work_key": work_key,
                "work_title": work_title,
                "author_name": author_name,
            }
        )
        return node_id

    def _tag_work_anchor_node(
        self,
        *,
        nodes: List[Dict[str, Any]],
        node_id: str,
        author_name: str,
        work_title: str,
        work_key: str,
        book_dir: Path,
        vault_root: Path,
    ) -> None:
        node = self._find_node_payload(nodes, node_id)
        if not node:
            return
        node["discipline_work_anchor"] = True
        node["work_key"] = work_key
        node["work_title"] = work_title
        node["author_name"] = author_name
        try:
            node["book_dir"] = self.mindmap_module._to_relative_vault_path(book_dir, vault_root)
        except Exception:
            node["book_dir"] = str(book_dir)

    def _import_existing_book_canvas_into_discipline(
        self,
        *,
        vault_root: Path,
        work_title: str,
        author_name: str,
        work_key: str,
        book_abs: Path,
        nodes: List[Dict[str, Any]],
        edges: List[Dict[str, Any]],
        existing_file_nodes: Dict[str, str],
    ) -> Dict[str, Any]:
        canvas_path = self._find_canvas_for_existing_book(vault_root=vault_root, work_title=work_title, book_abs=book_abs)
        if not canvas_path or not canvas_path.exists():
            return {"added_nodes": 0, "added_edges": 0, "canvas_ref": "", "imported_root_id": ""}

        imported = self.mindmap_module.load_canvas_payload(canvas_path)
        import_nodes = imported.get("nodes") if isinstance(imported.get("nodes"), list) else []
        import_edges = imported.get("edges") if isinstance(imported.get("edges"), list) else []
        if not import_nodes:
            return {"added_nodes": 0, "added_edges": 0, "canvas_ref": "", "imported_root_id": ""}

        right_edge = 0.0
        for node in nodes:
            if not isinstance(node, dict):
                continue
            try:
                node_right = float(node.get("x", 0) or 0) + float(node.get("width", 220) or 220)
            except Exception:
                node_right = 0.0
            right_edge = max(right_edge, node_right)

        xs: List[float] = []
        ys: List[float] = []
        for node in import_nodes:
            if not isinstance(node, dict):
                continue
            try:
                xs.append(float(node.get("x", 0) or 0))
                ys.append(float(node.get("y", 0) or 0))
            except Exception:
                continue
        min_x = min(xs) if xs else 0.0
        min_y = min(ys) if ys else 0.0
        offset_x = right_edge + 360.0
        offset_y = -120.0

        added_nodes = 0
        added_edges = 0
        id_map: Dict[str, str] = {}
        imported_root_id = ""

        for raw in import_nodes:
            if not isinstance(raw, dict):
                continue
            old_id = str(raw.get("id") or "").strip()
            if not old_id:
                continue

            node_type = str(raw.get("type") or "").strip().lower()
            if node_type == "file":
                file_ref = str(raw.get("file") or "").strip().replace("\\", "/")
                existing_id = existing_file_nodes.get(file_ref)
                if file_ref and existing_id:
                    id_map[old_id] = existing_id
                    if not imported_root_id and old_id == "node-livro":
                        imported_root_id = existing_id
                    continue

            new_node = dict(raw)
            new_id = self._generate_unique_node_id(f"node-import-{self._sanitize_filename(work_title)}")
            new_node["id"] = new_id

            try:
                source_x = float(raw.get("x", 0) or 0)
            except Exception:
                source_x = 0.0
            try:
                source_y = float(raw.get("y", 0) or 0)
            except Exception:
                source_y = 0.0
            new_node["x"] = round((source_x - min_x) + offset_x, 2)
            new_node["y"] = round((source_y - min_y) + offset_y, 2)
            new_node["work_key"] = work_key
            new_node["work_title"] = work_title
            new_node["author_name"] = author_name

            nodes.append(new_node)
            id_map[old_id] = new_id
            added_nodes += 1

            if node_type == "file":
                file_ref = str(new_node.get("file") or "").strip().replace("\\", "/")
                if file_ref:
                    existing_file_nodes[file_ref] = new_id

            if not imported_root_id:
                text_norm = self._normalize_token(str(new_node.get("text") or ""))
                if old_id == "node-livro" or "mapa base da obra" in text_norm:
                    imported_root_id = new_id

        if not imported_root_id and id_map:
            imported_root_id = next(iter(id_map.values()))

        if imported_root_id:
            self._tag_work_anchor_node(
                nodes=nodes,
                node_id=imported_root_id,
                author_name=author_name,
                work_title=work_title,
                work_key=work_key,
                book_dir=book_abs,
                vault_root=vault_root,
            )

        for raw_edge in import_edges:
            if not isinstance(raw_edge, dict):
                continue
            from_old = str(raw_edge.get("fromNode") or "").strip()
            to_old = str(raw_edge.get("toNode") or "").strip()
            from_new = id_map.get(from_old, "")
            to_new = id_map.get(to_old, "")
            if not from_new or not to_new or from_new == to_new:
                continue

            from_side = str(raw_edge.get("fromSide") or "right").strip().lower() or "right"
            to_side = str(raw_edge.get("toSide") or "left").strip().lower() or "left"
            if self._has_edge_payload(edges, from_new, to_new, from_side, to_side):
                continue

            edges.append(
                {
                    "id": self._generate_unique_edge_id(),
                    "fromNode": from_new,
                    "toNode": to_new,
                    "fromSide": from_side,
                    "toSide": to_side,
                    "label": str(raw_edge.get("label") or "").strip(),
                    "color": str(raw_edge.get("color") or "2"),
                }
            )
            added_edges += 1

        return {
            "added_nodes": added_nodes,
            "added_edges": added_edges,
            "canvas_ref": self.mindmap_module._to_relative_vault_path(canvas_path, vault_root),
            "imported_root_id": imported_root_id,
        }

    def _find_canvas_for_existing_book(self, *, vault_root: Path, work_title: str, book_abs: Path) -> Optional[Path]:
        direct = self._canvas_path_for_book(work_title)
        if direct and direct.exists():
            return direct

        from_dir_name = self._canvas_path_for_book(book_abs.name)
        if from_dir_name and from_dir_name.exists():
            return from_dir_name

        maps_dir = vault_root / self.MINDMAPS_DIR
        if not maps_dir.exists():
            return None

        target = self._normalize_token(work_title)
        best: Optional[Path] = None
        best_score: Optional[int] = None
        for candidate in sorted(maps_dir.glob("*.canvas")):
            stem_norm = self._normalize_token(candidate.stem)
            if not target:
                continue
            if target not in stem_norm and stem_norm not in target:
                continue
            score = abs(len(stem_norm) - len(target))
            if best is None or best_score is None or score < best_score:
                best = candidate
                best_score = score
        return best

    @staticmethod
    def _has_edge_payload(
        edges: List[Dict[str, Any]],
        from_node: str,
        to_node: str,
        from_side: str = "",
        to_side: str = "",
    ) -> bool:
        from_id = str(from_node or "").strip()
        to_id = str(to_node or "").strip()
        side_from = str(from_side or "").strip().lower()
        side_to = str(to_side or "").strip().lower()

        for edge in edges:
            if not isinstance(edge, dict):
                continue
            if str(edge.get("fromNode") or "").strip() != from_id:
                continue
            if str(edge.get("toNode") or "").strip() != to_id:
                continue
            if side_from and str(edge.get("fromSide") or "").strip().lower() != side_from:
                continue
            if side_to and str(edge.get("toSide") or "").strip().lower() != side_to:
                continue
            return True
        return False

    def _append_links_to_discipline_note(self, *, discipline: str, linked_paths: List[str]) -> Dict[str, Any]:
        vault_root = self._vault_root()
        if not vault_root:
            return {"added_links": 0, "note_path": ""}
        note_path = self.current_discipline_note_path or self._resolve_discipline_note_path(discipline)
        try:
            result = append_book_note_links(
                vault_root,
                discipline,
                linked_paths,
                note_path=note_path,
            )
        except Exception as exc:
            logger.warning("Falha ao atualizar nota de disciplina com novos links: %s", exc)
            return {"added_links": 0, "note_path": str(note_path or "")}

        resolved_note_path = Path(str(result.get("note_path") or "")).resolve(strict=False) if result.get("note_path") else note_path
        if resolved_note_path is not None:
            self.current_discipline_note_path = resolved_note_path
        return {
            "added_links": int(result.get("added_links", 0) or 0),
            "note_path": str(resolved_note_path or ""),
        }

    def _append_annotation_links_to_discipline_note(self, *, discipline: str, linked_paths: List[str]) -> Dict[str, Any]:
        vault_root = self._vault_root()
        if not vault_root:
            return {"added_links": 0, "note_path": ""}
        note_path = self.current_discipline_note_path or self._resolve_discipline_note_path(discipline)
        try:
            result = append_annotation_note_links(
                vault_root,
                discipline,
                linked_paths,
                note_path=note_path,
            )
        except Exception as exc:
            logger.warning("Falha ao atualizar nota de disciplina com links de anotação: %s", exc)
            return {"added_links": 0, "note_path": str(note_path or "")}

        resolved_note_path = Path(str(result.get("note_path") or "")).resolve(strict=False) if result.get("note_path") else note_path
        if resolved_note_path is not None:
            self.current_discipline_note_path = resolved_note_path
        return {
            "added_links": int(result.get("added_links", 0) or 0),
            "note_path": str(resolved_note_path or ""),
        }

    def _next_isolated_spawn_point(self, card_width: int, card_height: int) -> QPointF:
        """Retorna posição de criação em coluna isolada à direita do mapa atual."""
        if self._node_items:
            right_edge = max(
                float(item.pos().x()) + float(item.rect().width())
                for item in self._node_items.values()
            )
            top_edge = min(float(item.pos().y()) for item in self._node_items.values())
            base_x = right_edge + 240.0
            base_y = top_edge - 10.0
        else:
            base_x = 380.0
            base_y = -120.0

        row = self._isolated_spawn_index % 6
        col = self._isolated_spawn_index // 6
        self._isolated_spawn_index += 1

        x = base_x + (col * (card_width + 42.0))
        y = base_y + (row * (card_height + 30.0))
        return QPointF(x, y)

    def _color_for_id(self, color_id: str) -> QColor:
        raw = str(color_id or "").strip()
        if raw in self.COLOR_PALETTE:
            return QColor(self.COLOR_PALETTE[raw][1])

        parsed = QColor(raw)
        if parsed.isValid():
            return parsed

        if raw.isdigit() and raw in self.COLOR_PALETTE:
            return QColor(self.COLOR_PALETTE[raw][1])

        return QColor("#46506A")

    def _edge_color_for_id(self, color_id: str) -> QColor:
        base = self._color_for_id(color_id)
        return base.lighter(120)

    def _normalize_token(self, value: str) -> str:
        return (
            str(value or "")
            .strip()
            .lower()
            .replace("á", "a")
            .replace("à", "a")
            .replace("â", "a")
            .replace("ã", "a")
            .replace("é", "e")
            .replace("ê", "e")
            .replace("í", "i")
            .replace("ó", "o")
            .replace("ô", "o")
            .replace("õ", "o")
            .replace("ú", "u")
            .replace("ç", "c")
        )

    def _infer_default_color_for_node(self, node: Dict[str, Any]) -> str:
        node_type = str(node.get("type") or "").strip().lower()
        if node_type == "text":
            return "4"
        if node_type == "image":
            return "6"

        file_ref = self._normalize_token(str(node.get("file") or ""))
        node_id = self._normalize_token(str(node.get("id") or ""))
        label_text = self._normalize_token(str(node.get("text") or ""))
        signal = " ".join([file_ref, node_id, label_text]).strip()

        if "03-revisao" in signal or "resumo" in signal:
            return "1"
        if "02-anotacoes" in signal or "nota-usuario" in signal:
            return "6"
        if "pre-texto" in signal or "pre texto" in signal or "pretexto" in signal:
            return "3"
        if "capitulo" in signal:
            return "5"
        return "2"

    def _on_node_position_changed(self, item: MindmapNodeItem):
        node_id = str(item.node_data.get("id") or "").strip()
        if not node_id:
            return
        self._update_edges_for_node(node_id)
        self._update_scene_bounds()
        self.persist_move_timer.start()

    def _on_node_size_changed(self, item: MindmapNodeItem):
        node_id = str(item.node_data.get("id") or "").strip()
        if not node_id:
            return
        item.node_data["width"] = int(item.rect().width())
        item.node_data["height"] = int(item.rect().height())
        self._update_edges_for_node(node_id)
        self._update_scene_bounds()
        self.persist_move_timer.start()

    def _on_connector_drag_started(self, item: MindmapNodeItem, side: str, scene_pos: QPointF):
        self._edge_drag_source_item = item
        self._edge_drag_source_side = str(side or "right").strip().lower()

        if self._edge_drag_preview is None:
            self._edge_drag_preview = QGraphicsPathItem()
            self._edge_drag_preview.setPen(QPen(QColor("#A5B1C8"), 1.4, Qt.PenStyle.DashLine))
            self._edge_drag_preview.setZValue(3)
            self.scene.addItem(self._edge_drag_preview)
        self._update_edge_drag_preview(scene_pos)

    def _on_connector_drag_moved(self, scene_pos: QPointF):
        self._update_edge_drag_preview(scene_pos)

    def _on_connector_drag_finished(self, scene_pos: QPointF):
        try:
            self._finalize_edge_drag(scene_pos)
        finally:
            self._clear_edge_drag_preview()
            self._edge_drag_source_item = None
            self._edge_drag_source_side = "right"

    def _update_edge_drag_preview(self, scene_pos: QPointF):
        source = self._edge_drag_source_item
        if not source or self._edge_drag_preview is None:
            return

        start = source.connector_scene_pos(self._edge_drag_source_side)
        end = QPointF(scene_pos)
        horizontal_delta = abs(end.x() - start.x())
        control_dx = max(54.0, horizontal_delta * 0.42)
        if end.x() >= start.x():
            c1 = QPointF(start.x() + control_dx, start.y())
            c2 = QPointF(end.x() - control_dx, end.y())
        else:
            c1 = QPointF(start.x() - control_dx, start.y())
            c2 = QPointF(end.x() + control_dx, end.y())

        path = QPainterPath(start)
        path.cubicTo(c1, c2, end)
        self._edge_drag_preview.setPath(path)

    def _clear_edge_drag_preview(self):
        if self._edge_drag_preview is None:
            return
        try:
            self.scene.removeItem(self._edge_drag_preview)
        except Exception:
            pass
        self._edge_drag_preview = None

    def _find_node_item_at(self, scene_pos: QPointF) -> Optional[MindmapNodeItem]:
        for obj in self.scene.items(scene_pos):
            item: Optional[QGraphicsItem] = obj
            while item is not None:
                if isinstance(item, MindmapNodeItem):
                    return item
                item = item.parentItem()
        return None

    def _finalize_edge_drag(self, scene_pos: QPointF):
        source = self._edge_drag_source_item
        if source is None:
            return

        target = self._find_node_item_at(scene_pos)
        if target is None or target is source:
            return

        from_id = str(source.node_data.get("id") or "").strip()
        to_id = str(target.node_data.get("id") or "").strip()
        if not from_id or not to_id:
            return

        to_side = target.closest_side_for_scene_pos(scene_pos)
        from_side = str(self._edge_drag_source_side or "right")

        edges = self.current_canvas_payload.get("edges")
        if not isinstance(edges, list):
            edges = []
            self.current_canvas_payload["edges"] = edges

        for edge in edges:
            if not isinstance(edge, dict):
                continue
            if str(edge.get("fromNode") or "").strip() != from_id:
                continue
            if str(edge.get("toNode") or "").strip() != to_id:
                continue
            if str(edge.get("fromSide") or "right").strip().lower() != from_side:
                continue
            if str(edge.get("toSide") or "left").strip().lower() != to_side:
                continue
            return

        edge_payload = {
            "id": self._generate_unique_edge_id(),
            "fromNode": from_id,
            "toNode": to_id,
            "fromSide": from_side,
            "toSide": to_side,
            "color": str(source.node_data.get("color") or "6"),
        }
        edges.append(edge_payload)

        edge_item = MindmapEdgeItem(
            from_item=source,
            to_item=target,
            color=self._edge_color_for_id(str(edge_payload.get("color") or "")),
            from_side=from_side,
            to_side=to_side,
            label="",
        )
        self.scene.addItem(edge_item)
        self._edge_items.append(edge_item)
        self._edges_by_node.setdefault(from_id, []).append(edge_item)
        self._edges_by_node.setdefault(to_id, []).append(edge_item)

        self._persist_canvas_payload()
        self.status_label.setText("Conexão criada")

    def _create_edge_between(
        self,
        *,
        from_node: str,
        to_node: str,
        color_id: str = "6",
        label: str = "",
        from_side: str = "right",
        to_side: str = "left",
    ) -> bool:
        from_id = str(from_node or "").strip()
        to_id = str(to_node or "").strip()
        if not from_id or not to_id or from_id == to_id:
            return False
        source_item = self._node_items.get(from_id)
        target_item = self._node_items.get(to_id)
        if not source_item or not target_item:
            return False

        edges = self.current_canvas_payload.get("edges")
        if not isinstance(edges, list):
            edges = []
            self.current_canvas_payload["edges"] = edges

        for edge in edges:
            if not isinstance(edge, dict):
                continue
            if (
                str(edge.get("fromNode") or "").strip() == from_id
                and str(edge.get("toNode") or "").strip() == to_id
                and str(edge.get("fromSide") or "right").strip().lower() == from_side
                and str(edge.get("toSide") or "left").strip().lower() == to_side
            ):
                return False

        edge_payload = {
            "id": self._generate_unique_edge_id(),
            "fromNode": from_id,
            "toNode": to_id,
            "fromSide": from_side,
            "toSide": to_side,
            "label": str(label or "").strip(),
            "color": str(color_id or "6"),
        }
        edges.append(edge_payload)

        edge_item = MindmapEdgeItem(
            from_item=source_item,
            to_item=target_item,
            color=self._edge_color_for_id(str(edge_payload.get("color") or "")),
            from_side=from_side,
            to_side=to_side,
            label=str(label or "").strip(),
        )
        self.scene.addItem(edge_item)
        self._edge_items.append(edge_item)
        self._edges_by_node.setdefault(from_id, []).append(edge_item)
        self._edges_by_node.setdefault(to_id, []).append(edge_item)
        return True

    def _update_edges_for_node(self, node_id: str):
        for edge_item in self._edges_by_node.get(str(node_id or "").strip(), []):
            edge_item.update_path()

    def _update_scene_bounds(self):
        try:
            bounds = self.scene.itemsBoundingRect()
        except Exception:
            return
        margin = 220
        self.scene.setSceneRect(bounds.adjusted(-margin, -margin, margin, margin))

    def _render_canvas(self, payload: Dict[str, Any], reset_zoom: bool = True):
        self.scene.clear()
        self._node_items.clear()
        self._edge_items.clear()
        self._edges_by_node.clear()
        self._clear_edge_drag_preview()
        self._edge_drag_source_item = None
        applied_default_colors = False

        nodes = payload.get("nodes") if isinstance(payload.get("nodes"), list) else []
        edges = payload.get("edges") if isinstance(payload.get("edges"), list) else []

        for raw_node in nodes:
            if not isinstance(raw_node, dict):
                continue
            node_id = str(raw_node.get("id") or "").strip()
            if not node_id:
                continue
            if not str(raw_node.get("color") or "").strip():
                raw_node["color"] = self._infer_default_color_for_node(raw_node)
                applied_default_colors = True

            item = MindmapNodeItem(
                node_data=raw_node,
                color_lookup=self._color_for_id,
                on_left_click=self._on_node_left_click,
                on_right_click=self._on_node_right_click,
                on_position_changed=self._on_node_position_changed,
                on_size_changed=self._on_node_size_changed,
                on_connector_drag_started=self._on_connector_drag_started,
                on_connector_drag_moved=self._on_connector_drag_moved,
                on_connector_drag_finished=self._on_connector_drag_finished,
                image_path_resolver=self._resolve_image_path_for_node,
            )
            self.scene.addItem(item)
            self._node_items[node_id] = item

        for raw_edge in edges:
            if not isinstance(raw_edge, dict):
                continue
            from_id = str(raw_edge.get("fromNode") or "").strip()
            to_id = str(raw_edge.get("toNode") or "").strip()
            if not from_id or not to_id:
                continue
            from_item = self._node_items.get(from_id)
            to_item = self._node_items.get(to_id)
            if not from_item or not to_item:
                continue

            edge_item = MindmapEdgeItem(
                from_item=from_item,
                to_item=to_item,
                color=self._edge_color_for_id(str(raw_edge.get("color") or "")),
                from_side=str(raw_edge.get("fromSide") or "right"),
                to_side=str(raw_edge.get("toSide") or "left"),
                label=str(raw_edge.get("label") or "").strip(),
            )
            self.scene.addItem(edge_item)
            self._edge_items.append(edge_item)
            self._edges_by_node.setdefault(from_id, []).append(edge_item)
            self._edges_by_node.setdefault(to_id, []).append(edge_item)

        self._update_scene_bounds()
        if reset_zoom:
            self.canvas_view.reset_zoom()
        if applied_default_colors:
            self._persist_canvas_payload()

    def _resolve_node_file_path(self, file_ref: str) -> Optional[Path]:
        reference = str(file_ref or "").strip().replace("\\", "/")
        if not reference:
            return None

        vault_root = self._vault_root()
        if not vault_root:
            return None

        candidate = vault_root / reference
        if candidate.exists():
            return candidate

        if not Path(reference).suffix:
            for suffix in (".md", ".canvas"):
                candidate = vault_root / f"{reference}{suffix}"
                if candidate.exists():
                    return candidate

        for folder in (self.USER_NOTES_DIR, self.REVIEW_DIR, self.MINDMAPS_DIR, "05 - Pessoal"):
            base = vault_root / folder
            if not base.exists():
                continue
            named = base / Path(reference).name
            if named.exists():
                return named
            stemmed = base / f"{Path(reference).stem}.md"
            if stemmed.exists():
                return stemmed

        return None

    def _resolve_image_path_for_node(self, node: Dict[str, Any]) -> Optional[Path]:
        image_ref = str(node.get("image") or "").strip().replace("\\", "/")
        if not image_ref:
            return None

        candidate = Path(image_ref)
        if candidate.is_absolute() and candidate.exists():
            return candidate

        vault_root = self._vault_root()
        if not vault_root:
            return None
        resolved = vault_root / image_ref
        if resolved.exists():
            return resolved
        return None

    def _normalize_vault_reference(self, path: Path) -> str:
        vault_root = self._vault_root()
        if not vault_root:
            return str(path).replace("\\", "/")
        try:
            relative = path.relative_to(vault_root)
            return str(relative).replace("\\", "/")
        except Exception:
            return str(path).replace("\\", "/")

    def _generate_unique_node_id(self, prefix: str = "node-card") -> str:
        nodes = self.current_canvas_payload.get("nodes")
        if not isinstance(nodes, list):
            nodes = []
            self.current_canvas_payload["nodes"] = nodes
        existing = {
            str(node.get("id") or "").strip()
            for node in nodes
            if isinstance(node, dict)
        }
        if prefix not in existing:
            return prefix
        index = 2
        while True:
            candidate = f"{prefix}-{index}"
            if candidate not in existing:
                return candidate
            index += 1

    def _generate_unique_edge_id(self, prefix: str = "edge") -> str:
        edges = self.current_canvas_payload.get("edges")
        if not isinstance(edges, list):
            edges = []
            self.current_canvas_payload["edges"] = edges
        existing = {
            str(edge.get("id") or "").strip()
            for edge in edges
            if isinstance(edge, dict)
        }
        if prefix not in existing:
            return prefix
        index = 2
        while True:
            candidate = f"{prefix}-{index}"
            if candidate not in existing:
                return candidate
            index += 1

    def _review_assets_dir(self) -> Optional[Path]:
        vault_root = self._vault_root()
        if not vault_root:
            return None
        assets = vault_root / self.REVIEW_DIR / "assets"
        assets.mkdir(parents=True, exist_ok=True)
        return assets

    def _import_image_to_assets(self, source_path: Path) -> Optional[str]:
        source = Path(source_path)
        if not source.exists() or not source.is_file():
            return None

        vault_root = self._vault_root()
        if vault_root:
            try:
                return str(source.relative_to(vault_root)).replace("\\", "/")
            except Exception:
                pass

        assets_dir = self._review_assets_dir()
        if not assets_dir:
            return None

        stem = self._sanitize_filename(source.stem)
        suffix = source.suffix.lower() or ".png"
        target = assets_dir / f"{stem}{suffix}"
        index = 2
        while target.exists():
            target = assets_dir / f"{stem}-{index}{suffix}"
            index += 1

        try:
            shutil.copy2(source, target)
        except Exception:
            return None
        return self._normalize_vault_reference(target)

    def _add_node_to_canvas(self, node_data: Dict[str, Any]) -> Optional[MindmapNodeItem]:
        nodes = self.current_canvas_payload.get("nodes")
        if not isinstance(nodes, list):
            nodes = []
            self.current_canvas_payload["nodes"] = nodes
        nodes.append(node_data)

        item = MindmapNodeItem(
            node_data=node_data,
            color_lookup=self._color_for_id,
            on_left_click=self._on_node_left_click,
            on_right_click=self._on_node_right_click,
            on_position_changed=self._on_node_position_changed,
            on_size_changed=self._on_node_size_changed,
            on_connector_drag_started=self._on_connector_drag_started,
            on_connector_drag_moved=self._on_connector_drag_moved,
            on_connector_drag_finished=self._on_connector_drag_finished,
            image_path_resolver=self._resolve_image_path_for_node,
        )
        self.scene.addItem(item)
        node_id = str(node_data.get("id") or "").strip()
        if node_id:
            self._node_items[node_id] = item

        self._update_scene_bounds()
        self._persist_canvas_payload()
        return item

    def _handle_canvas_drop_action(self, action_key: str, scene_pos: QPointF, payload: Optional[str]):
        if not self.current_canvas_path:
            self.status_label.setText("Abra uma revisão antes de criar cards")
            return

        action = str(action_key or "").strip().lower()
        if action == "add_text_card":
            self._create_text_card_at(scene_pos)
            return
        if action == "add_image_card":
            self._create_image_card_at(scene_pos, None)
            return
        if action == "image_from_file":
            self._create_image_card_at(scene_pos, payload)

    def _create_text_card_isolated(self):
        self._create_text_card_at(None)

    def _create_image_card_isolated(self):
        self._create_image_card_at(None, None)

    def _create_text_card_at(self, scene_pos: Optional[QPointF] = None):
        card_w = 220
        card_h = 112
        target = scene_pos if scene_pos is not None else self._next_isolated_spawn_point(card_w, card_h)
        node_id = self._generate_unique_node_id("node-card")
        node_data: Dict[str, Any] = {
            "id": node_id,
            "type": "text",
            "text": "Novo card",
            "x": round(float(target.x()), 2),
            "y": round(float(target.y()), 2),
            "width": card_w,
            "height": card_h,
            "color": "6",
        }

        item = self._add_node_to_canvas(node_data)
        if not item:
            return
        self._open_card_editor_for_item(item, mode="text")
        self.status_label.setText("Novo card criado")

    def _create_image_card_at(self, scene_pos: Optional[QPointF], source_path: Optional[str]):
        image_ref = ""
        if source_path:
            imported = self._import_image_to_assets(Path(source_path))
            image_ref = imported or ""

        if not image_ref:
            selected, _ = QFileDialog.getOpenFileName(
                self,
                "Selecionar imagem",
                "",
                "Imagens (*.png *.jpg *.jpeg *.bmp *.gif *.webp);;Todos os arquivos (*)",
            )
            if not selected:
                return
            imported = self._import_image_to_assets(Path(selected))
            if not imported:
                QMessageBox.warning(self, "Imagem", "Não foi possível importar a imagem.")
                return
            image_ref = imported

        card_w = 280
        card_h = 180
        target = scene_pos if scene_pos is not None else self._next_isolated_spawn_point(card_w, card_h)
        node_id = self._generate_unique_node_id("node-image")
        node_data: Dict[str, Any] = {
            "id": node_id,
            "type": "image",
            "image": image_ref,
            "caption": "",
            "x": round(float(target.x()), 2),
            "y": round(float(target.y()), 2),
            "width": card_w,
            "height": card_h,
            "color": "6",
        }

        item = self._add_node_to_canvas(node_data)
        if not item:
            return
        self._open_card_editor_for_item(item, mode="image")
        self.status_label.setText("Card de imagem criado")

    def _is_side_panel_visible(self) -> bool:
        sizes = self.main_splitter.sizes()
        return len(sizes) >= 2 and int(sizes[1]) > 32

    def _open_side_panel(self):
        sizes = self.main_splitter.sizes()
        total = sum(int(s) for s in sizes)
        if total <= 0:
            total = max(int(self.width()), 1200)
        right = max(360, min(680, int(total * 0.36)))
        left = max(420, total - right)
        self.main_splitter.setSizes([left, right])

    def _close_side_panel(self):
        sizes = self.main_splitter.sizes()
        total = sum(int(s) for s in sizes)
        if total <= 0:
            total = max(int(self.width()), 1200)
        self.main_splitter.setSizes([total, 0])
        self._set_editor_visible(False)
        self._editing_card_node_id = ""

    def _set_editor_visible(self, visible: bool):
        total = sum(int(s) for s in self.side_splitter.sizes())
        if total <= 0:
            total = 680
        if visible:
            top = max(220, int(total * 0.62))
            self.side_splitter.setSizes([top, total - top])
        else:
            self.side_splitter.setSizes([total, 0])

    def _activate_note_editor(self):
        self.editor_mode_label.setText("Nova anotação")
        self.editor_stack.setCurrentWidget(self.note_editor_page)
        self._editing_card_node_id = ""

    def _activate_card_editor(self, mode: str):
        normalized = str(mode or "text").strip().lower()
        self._editing_card_mode = "image" if normalized == "image" else "text"
        self.editor_mode_label.setText("Editor de card")
        self.editor_stack.setCurrentWidget(self.card_editor_page)

        is_image = self._editing_card_mode == "image"
        self.card_body_label.setVisible(not is_image)
        self.card_body_editor.setVisible(not is_image)
        self.card_image_row.setVisible(is_image)

        if is_image:
            self.card_title_input.setPlaceholderText("Legenda (opcional)")
            self.card_save_button.setText("Salvar card de imagem")
        else:
            self.card_title_input.setPlaceholderText("Título do card")
            self.card_save_button.setText("Salvar card")
        self.card_feedback_label.clear()

    def _pick_image_for_editor(self):
        selected, _ = QFileDialog.getOpenFileName(
            self,
            "Selecionar imagem",
            "",
            "Imagens (*.png *.jpg *.jpeg *.bmp *.gif *.webp);;Todos os arquivos (*)",
        )
        if not selected:
            return
        imported = self._import_image_to_assets(Path(selected))
        if not imported:
            QMessageBox.warning(self, "Imagem", "Não foi possível importar a imagem.")
            return
        self.card_image_path_input.setText(imported)

    def _open_card_editor_for_item(self, item: MindmapNodeItem, mode: Optional[str] = None):
        node = item.node_data
        node_id = str(node.get("id") or "").strip()
        if not node_id:
            return

        node_type = str(mode or node.get("type") or "text").strip().lower()
        self._editing_card_node_id = node_id
        self._activate_card_editor(node_type)
        self._open_side_panel()
        self._set_editor_visible(True)
        self._opened_node_id = node_id

        if self._editing_card_mode == "image":
            self.card_title_input.setText(str(node.get("caption") or "").strip())
            self.card_image_path_input.setText(str(node.get("image") or "").strip())
            self.card_body_editor.clear()
            self.card_image_path_input.setFocus()
        else:
            full_text = str(node.get("text") or "").strip()
            title = str(node.get("title") or "").strip()
            body = full_text
            if title and full_text.startswith(title):
                remainder = full_text[len(title):].lstrip("\n")
                body = remainder
            self.card_title_input.setText(title)
            self.card_body_editor.setPlainText(body)
            self.card_image_path_input.clear()
            self.card_body_editor.setFocus()

        self.card_feedback_label.setText("Editando card")

    def _save_active_card(self):
        node_id = str(self._editing_card_node_id or "").strip()
        if not node_id:
            QMessageBox.information(self, "Card", "Selecione um card para editar.")
            return

        item = self._node_items.get(node_id)
        if not item:
            return

        if self._editing_card_mode == "image":
            image_ref = self.card_image_path_input.text().strip()
            if not image_ref:
                QMessageBox.information(self, "Imagem", "Selecione uma imagem para o card.")
                return

            path = Path(image_ref)
            if path.exists() and path.is_file():
                imported = self._import_image_to_assets(path)
                if imported:
                    image_ref = imported

            item.node_data["type"] = "image"
            item.node_data["image"] = image_ref
            item.node_data["caption"] = self.card_title_input.text().strip()
            item.node_data["width"] = max(240, int(item.rect().width()))
            item.node_data["height"] = max(160, int(item.rect().height()))
            item.refresh_style()
            self.card_feedback_label.setText("Card de imagem atualizado")
            self.status_label.setText("Card de imagem salvo")
        else:
            title = self.card_title_input.text().strip()
            body = self.card_body_editor.toPlainText().strip()
            if not title and not body:
                QMessageBox.information(self, "Card", "Informe título ou conteúdo para o card.")
                return

            combined = title
            if body:
                combined = f"{title}\n{body}".strip() if title else body

            item.node_data["type"] = "text"
            item.node_data.pop("image", None)
            item.node_data.pop("caption", None)
            item.node_data["title"] = title
            item.node_data["text"] = combined
            item.refresh_style()
            self.card_feedback_label.setText("Card atualizado")
            self.status_label.setText("Card salvo")

        self._persist_canvas_payload()

    def _selected_note_text(self) -> str:
        cursor = self.note_viewer.textCursor()
        return cursor.selectedText().replace("\u2029", "\n").strip()

    def _on_note_viewer_context_menu(self, pos):
        menu = self.note_viewer.createStandardContextMenu()
        selected = self._selected_note_text()
        create_note_action = None
        if selected:
            menu.addSeparator()
            create_note_action = menu.addAction("Criar anotação com seleção")
        chosen = menu.exec(self.note_viewer.viewport().mapToGlobal(pos))
        if create_note_action and chosen == create_note_action:
            self._capture_selection_to_note(show_empty_feedback=False)

    def _on_node_left_click(self, item: MindmapNodeItem):
        node = item.node_data
        node_id = str(node.get("id") or "").strip()
        if node_id and node_id == self._opened_node_id and self._is_side_panel_visible():
            self._opened_node_id = ""
            self.current_source_note_path = None
            self.viewer_title_label.setText("Conteúdo do card")
            self.note_viewer.clear()
            self._close_side_panel()
            self.status_label.setText("Painel de nota ocultado")
            return

        self._opened_node_id = node_id
        self._open_side_panel()
        self._set_editor_visible(False)

        node_type = str(node.get("type") or "").strip().lower()

        if node_type == "file":
            file_ref = str(node.get("file") or "").strip()
            file_path = self._resolve_node_file_path(file_ref)
            if not file_path:
                self.viewer_title_label.setText(f"Arquivo não encontrado: {file_ref}")
                self.note_viewer.setPlainText("Não foi possível localizar a nota associada a este card.")
                self.current_source_note_path = None
                return

            self.current_source_note_path = file_path if file_path.suffix.lower() == ".md" else None
            self.viewer_title_label.setText(file_path.name)

            try:
                content = file_path.read_text(encoding="utf-8", errors="ignore")
            except Exception as exc:
                self.note_viewer.setPlainText(f"Falha ao abrir o arquivo:\n{exc}")
                return

            self.note_viewer.setPlainText(content)
            self.status_label.setText(f"Card aberto: {file_path.name}")
            return

        if node_type == "image":
            self.current_source_note_path = None
            caption = str(node.get("caption") or "").strip()
            self.viewer_title_label.setText(caption or str(node.get("id") or "Card de imagem"))
            image_path = self._resolve_image_path_for_node(node)
            if image_path and image_path.exists():
                image_uri = image_path.resolve().as_uri()
                html = (
                    "<div style='padding: 4px;'>"
                    f"<img src='{image_uri}' style='max-width: 100%; height: auto;'/>"
                    "</div>"
                )
                self.note_viewer.setHtml(html)
            else:
                self.note_viewer.setPlainText("Imagem não encontrada para este card.")
            self.status_label.setText("Card de imagem aberto")
            return

        text = str(node.get("text") or "").strip() or "Card textual"
        self.current_source_note_path = None
        label = str(node.get("title") or "").strip() or str(node.get("id") or "Card")
        self.viewer_title_label.setText(label)
        self.note_viewer.setPlainText(text)
        self.status_label.setText("Card textual aberto")

    def _on_node_right_click(self, item: MindmapNodeItem, global_pos):
        menu = QMenu(self)

        edit_action = menu.addAction("Editar card")
        delete_action = menu.addAction("Excluir card")
        menu.addSeparator()

        color_menu = menu.addMenu("Cor do card")
        actions_by_id: Dict[QAction, str] = {}
        current_color = str(item.node_data.get("color") or self._infer_default_color_for_node(item.node_data))

        for color_id, (label, color_value) in self.COLOR_PALETTE.items():
            action = color_menu.addAction(label)
            action.setCheckable(True)
            action.setChecked(color_id == current_color)
            action.setIcon(self._color_icon(color_value))
            actions_by_id[action] = color_id

        menu.addSeparator()
        favorite_action = menu.addAction("Destacar como favorito")
        favorite_action.setCheckable(True)
        favorite_action.setChecked(item.is_favorite())

        selected = menu.exec(global_pos)
        if not selected:
            return

        if selected == edit_action:
            self._open_card_editor_for_item(item)
            return

        if selected == delete_action:
            reply = QMessageBox.question(
                self,
                "Excluir card",
                "Deseja excluir este card e suas conexões?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if reply == QMessageBox.StandardButton.Yes:
                self._delete_card_item(item)
            return

        if selected in actions_by_id:
            chosen_color = actions_by_id[selected]
            item.node_data["color"] = chosen_color
            item.refresh_style()
            self._persist_canvas_payload()
            self.status_label.setText("Cor do card atualizada")
            return

        if selected == favorite_action:
            item.node_data["favorite"] = bool(favorite_action.isChecked())
            item.refresh_style()
            self._persist_canvas_payload()
            self.status_label.setText("Destaque do card atualizado")

    def _color_icon(self, color: QColor):
        from PyQt6.QtGui import QPixmap

        pixmap = QPixmap(12, 12)
        pixmap.fill(color)
        return QIcon(pixmap)

    def _delete_card_item(self, item: MindmapNodeItem):
        node_id = str(item.node_data.get("id") or "").strip()
        if not node_id:
            return

        nodes = self.current_canvas_payload.get("nodes")
        if isinstance(nodes, list):
            self.current_canvas_payload["nodes"] = [
                node for node in nodes
                if not (
                    isinstance(node, dict)
                    and str(node.get("id") or "").strip() == node_id
                )
            ]

        edges = self.current_canvas_payload.get("edges")
        if isinstance(edges, list):
            self.current_canvas_payload["edges"] = [
                edge for edge in edges
                if not (
                    isinstance(edge, dict)
                    and (
                        str(edge.get("fromNode") or "").strip() == node_id
                        or str(edge.get("toNode") or "").strip() == node_id
                    )
                )
            ]

        self._render_canvas(self.current_canvas_payload, reset_zoom=False)
        self._persist_canvas_payload()

        if self._opened_node_id == node_id:
            self._opened_node_id = ""
            self.note_viewer.clear()
            self.viewer_title_label.setText("Conteúdo do card")
            self._close_side_panel()

        self.status_label.setText("Card excluído")

    def _persist_canvas_payload(self):
        if not self.current_canvas_path:
            return

        nodes = self.current_canvas_payload.get("nodes") if isinstance(self.current_canvas_payload.get("nodes"), list) else []
        for node in nodes:
            if not isinstance(node, dict):
                continue
            node_id = str(node.get("id") or "").strip()
            if not node_id:
                continue
            item = self._node_items.get(node_id)
            if not item:
                continue
            pos = item.pos()
            node["x"] = round(float(pos.x()), 2)
            node["y"] = round(float(pos.y()), 2)
            node["width"] = int(item.rect().width())
            node["height"] = int(item.rect().height())

        try:
            self.current_canvas_path.write_text(
                json.dumps(self.current_canvas_payload, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
        except Exception as exc:
            logger.warning("Falha ao persistir canvas de revisão: %s", exc)

    def _capture_selection_to_note(self, show_empty_feedback: bool = True) -> bool:
        selected = self._selected_note_text()
        if not selected:
            if show_empty_feedback:
                QMessageBox.information(self, "Seleção", "Selecione um trecho da nota para criar anotação.")
            return False

        self._open_side_panel()
        self._set_editor_visible(True)
        self._activate_note_editor()

        current = self.new_note_editor.toPlainText().strip()
        block = f"> {selected}\n\n"
        if current:
            self.new_note_editor.setPlainText(f"{current}\n\n{block}")
        else:
            self.new_note_editor.setPlainText(block)

        if not self.new_note_title_input.text().strip():
            self.new_note_title_input.setText(f"Nota de revisão - {datetime.now().strftime('%H%M')}")

        self.save_note_feedback.setText("Trecho enviado para o editor")
        self.new_note_editor.setFocus()
        return True

    def _save_user_note(self):
        vault_root = self._vault_root()
        if not vault_root:
            QMessageBox.warning(self, "Vault", "Vault não disponível para salvar a nota.")
            return

        title = self.new_note_title_input.text().strip()
        if not title:
            title = f"nota-revisao-{datetime.now().strftime('%Y%m%d-%H%M%S')}"

        body = self.new_note_editor.toPlainText().strip()
        if not body:
            QMessageBox.information(self, "Nota vazia", "Escreva algum conteúdo antes de salvar.")
            return

        notes_dir = vault_root / self.USER_NOTES_DIR
        notes_dir.mkdir(parents=True, exist_ok=True)

        stem = self._sanitize_obsidian_title(title)
        note_path = notes_dir / f"{stem}.md"
        counter = 2
        while note_path.exists():
            note_path = notes_dir / f"{stem} ({counter}).md"
            counter += 1

        metadata_lines = [
            f"# {title}",
            "",
            f"- Data: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            f"- Livro: {self.current_book_title}",
            f"- Book ID: {self.current_book_id or '-'}",
        ]

        if self.current_source_note_path:
            metadata_lines.append(f"- Origem: [[{self.current_source_note_path.stem}]]")

        content = "\n".join(metadata_lines + ["", "## Anotação", body.strip(), ""])

        try:
            note_path.write_text(content, encoding="utf-8")
        except Exception as exc:
            QMessageBox.warning(self, "Erro ao salvar", f"Não foi possível salvar a nota:\n{exc}")
            return

        self._append_link_to_source_note(note_path)

        self.save_note_feedback.setText(f"Nota salva: {note_path.name}")
        self.status_label.setText("Nota criada na revisão")
        self.new_note_title_input.clear()
        self.new_note_editor.clear()

    def _sanitize_obsidian_title(self, title: str) -> str:
        cleaned = title.strip().replace("\n", " ")
        cleaned = re.sub(r"[\\/:*?\"<>|]+", "-", cleaned)
        cleaned = re.sub(r"\s+", " ", cleaned).strip(". ").strip()
        return cleaned or f"nota-{datetime.now().strftime('%Y%m%d-%H%M%S')}"

    def _append_link_to_source_note(self, note_path: Path):
        if not self.current_source_note_path or not self.current_source_note_path.exists():
            return

        vault_root = self._vault_root()
        if not vault_root:
            return

        try:
            relative = note_path.relative_to(vault_root).with_suffix("")
        except Exception:
            return

        link_line = f"- [[{str(relative).replace('\\\\', '/')}|{note_path.stem}]]"
        target = self.current_source_note_path

        try:
            text = target.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            return

        if link_line in text:
            return

        section_header = f"## {NerdIcons.LINK} Notas da Revisão"
        header_pattern = re.compile(rf"(?m)^##\s+(?:{re.escape(LEGACY_LINK_ICON)}|{re.escape(NerdIcons.LINK)})\s+Notas da Revisão\s*$")
        header_match = header_pattern.search(text)
        if header_match is None:
            updated = text.rstrip() + f"\n\n{section_header}\n{link_line}\n"
            target.write_text(updated, encoding="utf-8")
            return

        existing_header = header_match.group(0)
        updated = text.replace(existing_header, f"{existing_header}\n{link_line}", 1)
        target.write_text(updated, encoding="utf-8")

    def _open_pomodoro_menu(self):
        menu = QMenu(self)
        start_action = menu.addAction("Iniciar")
        pause_action = menu.addAction("Pausar")
        config_action = menu.addAction("Configurar")

        pos = self.pomodoro_timer_button.mapToGlobal(self.pomodoro_timer_button.rect().bottomLeft())
        selected = menu.exec(pos)

        if selected == start_action:
            self._start_pomodoro()
        elif selected == pause_action:
            self._pause_pomodoro()
        elif selected == config_action:
            self._open_pomodoro_config_dialog()

    def _start_pomodoro(self):
        if not self.pomodoro:
            self.status_label.setText("Pomodoro indisponível")
            return
        if self.pomodoro.is_running and self.pomodoro.is_paused:
            self.pomodoro.resume()
        elif not self.pomodoro.is_running:
            self.pomodoro.start(session_type="work", discipline="revisao")
        self._tick_ui()

    def _pause_pomodoro(self):
        if not self.pomodoro:
            return
        self.pomodoro.pause()
        self._tick_ui()

    def _open_pomodoro_config_dialog(self):
        if not self.pomodoro:
            return
        dialog = PomodoroConfigDialog(self.pomodoro, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            values = dialog.get_values()
            self.pomodoro.configure(
                work_minutes=values["work_minutes"],
                break_minutes=values["break_minutes"],
                long_break_minutes=values["long_break_minutes"],
                sessions_before_long_break=values["sessions_before_long_break"],
            )
            self._tick_ui()

    def _format_mmss(self, total_seconds: int) -> str:
        minutes, seconds = divmod(max(int(total_seconds), 0), 60)
        return f"{minutes:02d}:{seconds:02d}"

    def _tick_ui(self):
        if not self.pomodoro:
            self.pomodoro_timer_button.setText("--:--")
            return

        if not self.pomodoro.is_running or not self.pomodoro.start_time:
            self.pomodoro_timer_button.setText(self._format_mmss(self.pomodoro._get_duration_for_type("work")))
            return

        now = time.time()
        elapsed = now - self.pomodoro.start_time - self.pomodoro.elapsed_paused
        total = self.pomodoro._get_duration_for_type(self.pomodoro.current_session_type)
        remaining = max(total - elapsed, 0)

        prefix = "⏸ " if self.pomodoro.is_paused else ""
        self.pomodoro_timer_button.setText(f"{prefix}{self._format_mmss(int(remaining))}")

    def _schedule_next_question_prompt(self, reset: bool = False):
        if reset or self._next_question_prompt_at is None:
            self._next_question_prompt_at = datetime.now() + timedelta(minutes=self._question_interval_minutes)

    def _sync_questions_for_current_book(self):
        if not self.review_system or not self.current_book_id:
            return

        if hasattr(self.review_system, "sync_manual_questions_from_review_dir"):
            vault_root = self._vault_root()
            if not vault_root:
                return
            try:
                self.review_system.sync_manual_questions_from_review_dir(
                    book_id=self.current_book_id,
                    review_dir=vault_root / self.REVIEW_DIR,
                    book_title=self.current_book_title,
                )
            except Exception as exc:
                logger.debug("Falha ao sincronizar perguntas manuais na review view: %s", exc)

    def _check_question_prompt(self):
        if not self._is_active:
            return
        if not self._question_prompt_enabled:
            return
        if not self.review_system or not self.current_book_id:
            return

        now = datetime.now()
        if self._next_question_prompt_at is None:
            self._schedule_next_question_prompt(reset=True)
            return
        if now < self._next_question_prompt_at:
            return

        self._schedule_next_question_prompt(reset=True)

        picker = getattr(self.review_system, "pick_weighted_question", None)
        if not callable(picker):
            return

        try:
            question_obj = picker(book_id=self.current_book_id, now=now)
        except Exception as exc:
            logger.debug("Falha ao buscar pergunta periódica: %s", exc)
            return

        if not question_obj:
            return

        qid = getattr(question_obj, "id", "")
        question_text = getattr(question_obj, "question", "")
        answer_text = getattr(question_obj, "answer", "")
        chapter_label = getattr(question_obj, "chapter_title", "") or getattr(question_obj, "chapter_key", "")
        difficulty = int(getattr(question_obj, "difficulty", 3) or 3)

        marker = getattr(self.review_system, "mark_question_presented", None)
        if callable(marker) and qid:
            try:
                marker(qid, shown_at=now)
            except Exception:
                pass

        dialog = ReviewQuestionDialog(
            question=question_text,
            answer=answer_text,
            chapter_label=chapter_label,
            difficulty=difficulty,
            parent=self,
        )
        dialog.exec()

        if dialog.answer_revealed:
            marker_answer = getattr(self.review_system, "mark_question_answer_viewed", None)
            if callable(marker_answer) and qid:
                try:
                    marker_answer(qid, viewed=True)
                except Exception:
                    pass

    def _on_escape_pressed(self):
        self._set_fullscreen_mode(False)
        self.navigate_to.emit("dashboard")

    def _set_fullscreen_mode(self, enabled: bool):
        window = self.window()
        if window is None:
            return

        if enabled:
            if self._fullscreen_active:
                return
            self._window_was_fullscreen = bool(getattr(window, "isFullScreen", lambda: False)())
            self._window_was_maximized = bool(getattr(window, "isMaximized", lambda: False)())
            if hasattr(window, "showFullScreen"):
                window.showFullScreen()
            self._fullscreen_active = True
            return

        if not self._fullscreen_active:
            return

        if self._window_was_fullscreen and hasattr(window, "showFullScreen"):
            window.showFullScreen()
        elif self._window_was_maximized and hasattr(window, "showMaximized"):
            window.showMaximized()
        elif hasattr(window, "showNormal"):
            window.showNormal()

        self._fullscreen_active = False

    def on_view_activated(self):
        self._is_active = True
        self._set_fullscreen_mode(True)
        self.canvas_view.setFocus()
        self._tick_ui()
        self._schedule_next_question_prompt(reset=False)

    def on_view_deactivated(self, _next_view: str = ""):
        self._is_active = False
        self._set_fullscreen_mode(False)

    def cleanup(self):
        if hasattr(self, "ui_timer"):
            self.ui_timer.stop()
        if hasattr(self, "question_timer"):
            self.question_timer.stop()
