"""
Workspace de revisão com mapa mental interativo.
"""
from __future__ import annotations

import json
import logging
import re
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Optional

from PyQt6.QtCore import QPoint, QPointF, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import (
    QAction,
    QColor,
    QIcon,
    QKeySequence,
    QPainter,
    QPainterPath,
    QPen,
    QShortcut,
)
from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
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
    QMenu,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTextEdit,
    QVBoxLayout,
    QWidget,
    QSpinBox,
)

from core.modules.mindmap_review_module import MindmapReviewModule
from core.modules.pomodoro_timer import PomodoroTimer
from core.modules.review_system import ReviewSystem

logger = logging.getLogger("GLaDOS.UI.ReviewWorkspaceView")


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


class MindmapCanvasView(QGraphicsView):
    """View gráfica com zoom por scroll e pan por arrasto."""

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

    def wheelEvent(self, event):
        if event.angleDelta().y() > 0:
            self.zoom_by(1.12)
        else:
            self.zoom_by(0.88)

    def zoom_by(self, factor: float):
        current = self.transform().m11()
        target = current * factor
        if target < 0.25 or target > 4.0:
            return
        self.scale(factor, factor)
        self._zoom_factor = target

    def reset_zoom(self):
        self.resetTransform()
        self._zoom_factor = 1.0

    def pan_by(self, dx: int, dy: int):
        hbar = self.horizontalScrollBar()
        vbar = self.verticalScrollBar()
        hbar.setValue(hbar.value() + int(dx))
        vbar.setValue(vbar.value() + int(dy))


class MindmapNodeItem(QGraphicsRectItem):
    """Item de card para nós do canvas."""

    def __init__(
        self,
        node_data: Dict[str, Any],
        color_lookup,
        on_left_click,
        on_right_click,
        on_position_changed,
    ):
        width = max(120, int(float(node_data.get("width", 220) or 220)))
        height = max(64, int(float(node_data.get("height", 90) or 90)))
        super().__init__(0, 0, width, height)
        self.node_data = node_data
        self._color_lookup = color_lookup
        self._on_left_click = on_left_click
        self._on_right_click = on_right_click
        self._on_position_changed = on_position_changed

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

        self._hovered = False
        self._press_scene_pos: Optional[QPointF] = None
        self.refresh_style()

    def _label_text(self) -> str:
        node_type = str(self.node_data.get("type") or "").strip().lower()
        if node_type == "file":
            file_ref = str(self.node_data.get("file") or "").strip()
            if file_ref:
                return Path(file_ref).stem
            return "Arquivo"
        text = str(self.node_data.get("text") or "").strip()
        if not text:
            return str(self.node_data.get("id") or "Nó")
        return text

    def is_favorite(self) -> bool:
        return bool(self.node_data.get("favorite", False))

    def refresh_style(self):
        color_id = str(self.node_data.get("color") or "0")
        fill = self._color_lookup(color_id)

        if self.is_favorite():
            self._pen = QPen(QColor("#FFD54F"), 2.8)
        else:
            self._pen = QPen(fill.darker(150), 1.4)

        self._brush = fill
        self.favorite_badge.setVisible(self.is_favorite())
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
            self._press_scene_pos = event.scenePos()
        self.setSelected(True)
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
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

    def hoverLeaveEvent(self, event):
        self._hovered = False
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
        self.current_canvas_path: Optional[Path] = None
        self.current_canvas_payload: Dict[str, Any] = {"nodes": [], "edges": []}
        self.current_source_note_path: Optional[Path] = None
        self._node_items: Dict[str, MindmapNodeItem] = {}
        self._edge_items: list[MindmapEdgeItem] = []
        self._edges_by_node: Dict[str, list[MindmapEdgeItem]] = {}
        self._opened_node_id: str = ""

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

        self.zoom_out_button = QPushButton("-")
        self.zoom_reset_button = QPushButton("100%")
        self.zoom_in_button = QPushButton("+")
        for button in (self.zoom_out_button, self.zoom_reset_button, self.zoom_in_button):
            button.setFixedWidth(44)
            button.setObjectName("secondary_button")

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

        editor_layout.addWidget(QLabel("Nova anotação"))
        editor_layout.addWidget(self.new_note_title_input)
        editor_layout.addWidget(self.new_note_editor, 1)
        editor_layout.addWidget(self.save_note_button)
        editor_layout.addWidget(self.save_note_feedback)

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

        self.shortcut_escape = QShortcut(QKeySequence(Qt.Key.Key_Escape), self)
        self.shortcut_escape.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)

        self.shortcut_left = QShortcut(QKeySequence(Qt.Key.Key_Left), self.canvas_view)
        self.shortcut_right = QShortcut(QKeySequence(Qt.Key.Key_Right), self.canvas_view)
        self.shortcut_up = QShortcut(QKeySequence(Qt.Key.Key_Up), self.canvas_view)
        self.shortcut_down = QShortcut(QKeySequence(Qt.Key.Key_Down), self.canvas_view)

        self._set_editor_visible(False)
        self._close_side_panel()

    def _setup_connections(self):
        self.pomodoro_timer_button.clicked.connect(self._open_pomodoro_menu)
        self.zoom_in_button.clicked.connect(lambda: self.canvas_view.zoom_by(1.12))
        self.zoom_out_button.clicked.connect(lambda: self.canvas_view.zoom_by(0.88))
        self.zoom_reset_button.clicked.connect(self.canvas_view.reset_zoom)

        self.capture_selection_button.clicked.connect(lambda: self._capture_selection_to_note(show_empty_feedback=True))
        self.note_viewer.customContextMenuRequested.connect(self._on_note_viewer_context_menu)
        self.save_note_button.clicked.connect(self._save_user_note)
        self.shortcut_escape.activated.connect(self._on_escape_pressed)

        self.shortcut_left.activated.connect(lambda: self.canvas_view.pan_by(-self._question_pan_step, 0))
        self.shortcut_right.activated.connect(lambda: self.canvas_view.pan_by(self._question_pan_step, 0))
        self.shortcut_up.activated.connect(lambda: self.canvas_view.pan_by(0, -self._question_pan_step))
        self.shortcut_down.activated.connect(lambda: self.canvas_view.pan_by(0, self._question_pan_step))

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

    def _ensure_canvas_exists(self):
        if not self.current_canvas_path:
            return
        if self.current_canvas_path.exists():
            return

        self.current_canvas_path.parent.mkdir(parents=True, exist_ok=True)
        vault_root = self._vault_root()
        if not vault_root:
            return

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
        self.current_canvas_path = self._canvas_path_for_book(resolved_title)

        if not self.current_canvas_path:
            self.status_label.setText("Vault não disponível para revisão")
            return False

        self._ensure_canvas_exists()

        self.current_canvas_payload = self.mindmap_module.load_canvas_payload(self.current_canvas_path)
        self._render_canvas(self.current_canvas_payload)
        self._opened_node_id = ""
        self.current_source_note_path = None
        self.viewer_title_label.setText("Conteúdo do card")
        self.note_viewer.clear()
        self.new_note_title_input.clear()
        self.new_note_editor.clear()
        self._set_editor_visible(False)
        self._close_side_panel()

        self.book_label.setText(f"Revisão: {self.current_book_title}")
        self.status_label.setText("Mapa mental carregado")

        self._sync_questions_for_current_book()
        self._schedule_next_question_prompt(reset=True)

        if source_event:
            logger.debug("Review workspace aberto com payload: %s", source_event)
        return True

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

    def _render_canvas(self, payload: Dict[str, Any]):
        self.scene.clear()
        self._node_items.clear()
        self._edge_items.clear()
        self._edges_by_node.clear()
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

    def _set_editor_visible(self, visible: bool):
        total = sum(int(s) for s in self.side_splitter.sizes())
        if total <= 0:
            total = 680
        if visible:
            top = max(220, int(total * 0.62))
            self.side_splitter.setSizes([top, total - top])
        else:
            self.side_splitter.setSizes([total, 0])

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

        text = str(node.get("text") or "").strip() or "Card textual"
        self.current_source_note_path = None
        self.viewer_title_label.setText(str(node.get("id") or "Card"))
        self.note_viewer.setPlainText(text)
        self.status_label.setText("Card textual aberto")

    def _on_node_right_click(self, item: MindmapNodeItem, global_pos):
        menu = QMenu(self)

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

        section_header = "## 🔗 Notas da Revisão"
        if section_header not in text:
            updated = text.rstrip() + f"\n\n{section_header}\n{link_line}\n"
            target.write_text(updated, encoding="utf-8")
            return

        updated = text.replace(section_header, f"{section_header}\n{link_line}", 1)
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
