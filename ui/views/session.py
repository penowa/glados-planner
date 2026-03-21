"""
View de sessão de leitura com Pomodoro e assistente LLM.
"""
from __future__ import annotations

import html as html_lib
import logging
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, Optional
from urllib.request import Request, urlopen

from PyQt6.QtCore import QEasingCurve, QPoint, QPropertyAnimation, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QKeySequence, QShortcut, QTextBlockFormat, QTextCharFormat, QTextCursor
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QMenu,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QProgressBar,
    QSpinBox,
    QScrollArea,
    QTabWidget,
    QTextEdit,
    QTreeWidget,
    QTreeWidgetItem,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from core.modules.mindmap_review_module import (
    MindmapReviewModule,
)
from core.modules.pomodoro_timer import PomodoroTimer
from core.modules.review_system import ReviewSystem

try:
    from bs4 import BeautifulSoup  # type: ignore
except Exception:
    BeautifulSoup = None

logger = logging.getLogger("GLaDOS.UI.SessionView")


class PomodoroConfigDialog(QDialog):
    """Diálogo de configuração do Pomodoro."""

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


class ReviewGenerationDialog(QDialog):
    """Configura geração de revisão com seleção de contexto."""

    def __init__(
        self,
        chapter_name: str,
        default_difficulty: int,
        default_notes: list[Dict[str, str]],
        base_context_chars: int,
        max_context_chars: int,
        search_callback: Callable[[str], list[Dict[str, str]]],
        parent=None,
    ):
        super().__init__(parent)
        self.setWindowTitle("Configurar geração de revisão")
        self.setModal(True)
        self.resize(860, 640)

        self._search_callback = search_callback
        self._base_context_chars = max(0, int(base_context_chars))
        self._max_context_chars = max(1200, int(max_context_chars))
        self._note_keys: set[str] = set()

        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        intro = QLabel(
            f"Capítulo: {chapter_name}\n"
            "Ajuste a revisão, confira o contexto e adicione notas extras antes de gerar."
        )
        intro.setWordWrap(True)
        layout.addWidget(intro)

        form = QFormLayout()
        self.difficulty_combo = QComboBox()
        self.difficulty_combo.addItem("1 - Muito fácil", 1)
        self.difficulty_combo.addItem("2 - Fácil", 2)
        self.difficulty_combo.addItem("3 - Médio", 3)
        self.difficulty_combo.addItem("4 - Difícil", 4)
        self.difficulty_combo.addItem("5 - Muito difícil", 5)
        self.difficulty_combo.setCurrentIndex(max(0, min(int(default_difficulty) - 1, 4)))

        form.addRow("Material:", QLabel("Resumo de revisão"))
        form.addRow("Dificuldade do capítulo:", self.difficulty_combo)
        layout.addLayout(form)

        meter_row = QHBoxLayout()
        self.context_meter_label = QLabel("Contexto estimado: 0 chars")
        self.context_meter_bar = QProgressBar()
        self.context_meter_bar.setRange(0, 100)
        self.context_meter_bar.setValue(0)
        meter_row.addWidget(self.context_meter_label, 1)
        meter_row.addWidget(self.context_meter_bar, 1)
        layout.addLayout(meter_row)

        capacity_tokens = int(self._max_context_chars / 4)
        self.context_capacity_label = QLabel(
            f"Janela estimada da LLM: ~{self._max_context_chars} chars (~{capacity_tokens} tokens)."
        )
        layout.addWidget(self.context_capacity_label)

        self.context_tree = QTreeWidget()
        self.context_tree.setHeaderLabels(["Notas usadas como contexto"])
        self.context_tree.setRootIsDecorated(False)
        self.context_tree.setAlternatingRowColors(True)
        self.context_tree.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.context_tree.itemChanged.connect(self._on_context_item_changed)
        layout.addWidget(self.context_tree, 2)

        search_row = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Pesquisar notas no vault...")
        self.search_input.returnPressed.connect(self._search_notes)
        self.search_button = QPushButton("Buscar")
        self.search_button.clicked.connect(self._search_notes)
        search_row.addWidget(self.search_input, 1)
        search_row.addWidget(self.search_button)
        layout.addLayout(search_row)

        self.search_results = QListWidget()
        self.search_results.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        layout.addWidget(self.search_results, 1)

        add_row = QHBoxLayout()
        self.search_status_label = QLabel("Notas relacionadas sugeridas carregadas.")
        self.add_selected_button = QPushButton("Adicionar seleção ao contexto")
        self.add_selected_button.clicked.connect(self._add_selected_search_results)
        add_row.addWidget(self.search_status_label, 1)
        add_row.addWidget(self.add_selected_button)
        layout.addLayout(add_row)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        for note in default_notes:
            self._add_context_note(note, checked=True)
        self._update_context_meter()

    def _note_key(self, note: Dict[str, str]) -> str:
        path = (note.get("path") or "").strip()
        if path:
            return path
        return f"title::{(note.get('title') or '').strip().lower()}"

    def _add_context_note(self, note: Dict[str, str], checked: bool):
        key = self._note_key(note)
        if key in self._note_keys:
            return
        self._note_keys.add(key)

        title = (note.get("title") or "Sem título").strip()
        source = (note.get("source") or "Selecionada").strip()
        display_path = (note.get("display_path") or note.get("path") or "").strip()
        text = f"{title} [{source}]"
        if display_path:
            text = f"{text} — {display_path}"

        item = QTreeWidgetItem([text])
        item.setData(0, Qt.ItemDataRole.UserRole, note)
        item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
        item.setCheckState(0, Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked)
        snippet = (note.get("content") or "").strip()
        if snippet:
            item.setToolTip(0, snippet[:500])
        self.context_tree.addTopLevelItem(item)

    def _search_notes(self):
        query = self.search_input.text().strip()
        if not query:
            self.search_status_label.setText("Digite um termo para buscar notas.")
            return

        try:
            results = self._search_callback(query)
        except Exception as exc:
            self.search_results.clear()
            self.search_status_label.setText(f"Erro na busca: {exc}")
            return

        self.search_results.clear()
        for note in results:
            title = (note.get("title") or "Sem título").strip()
            display_path = (note.get("display_path") or note.get("path") or "").strip()
            item = QListWidgetItem(f"{title} — {display_path}" if display_path else title)
            item.setData(Qt.ItemDataRole.UserRole, note)
            snippet = (note.get("content") or "").strip()
            if snippet:
                item.setToolTip(snippet[:500])
            self.search_results.addItem(item)

        self.search_status_label.setText(
            f"{self.search_results.count()} nota(s) encontrada(s). Selecione e adicione ao contexto."
        )

    def _add_selected_search_results(self):
        selected_items = self.search_results.selectedItems()
        if not selected_items:
            self.search_status_label.setText("Selecione pelo menos uma nota da busca.")
            return

        added = 0
        for item in selected_items:
            note = item.data(Qt.ItemDataRole.UserRole) or {}
            before = len(self._note_keys)
            self._add_context_note(note, checked=True)
            if len(self._note_keys) > before:
                added += 1

        self._update_context_meter()
        self.search_status_label.setText(f"{added} nota(s) adicionada(s) ao contexto.")

    def _on_context_item_changed(self, _item: QTreeWidgetItem, _column: int):
        self._update_context_meter()

    def _selected_notes(self) -> list[Dict[str, str]]:
        selected: list[Dict[str, str]] = []
        for idx in range(self.context_tree.topLevelItemCount()):
            item = self.context_tree.topLevelItem(idx)
            if item.checkState(0) != Qt.CheckState.Checked:
                continue
            note = item.data(0, Qt.ItemDataRole.UserRole) or {}
            if isinstance(note, dict):
                selected.append(note)
        return selected

    def _update_context_meter(self):
        selected = self._selected_notes()
        dynamic_chars = 0
        for note in selected:
            estimate = int(note.get("estimated_chars") or 0)
            if estimate <= 0:
                estimate = len((note.get("title") or "")) + len((note.get("content") or "")) + 48
            dynamic_chars += estimate

        used_chars = self._base_context_chars + dynamic_chars
        used_tokens = int(used_chars / 4)
        capacity_tokens = int(self._max_context_chars / 4)
        ratio = int((used_chars / max(self._max_context_chars, 1)) * 100)
        bounded_ratio = max(0, min(100, ratio))

        self.context_meter_bar.setValue(bounded_ratio)
        self.context_meter_label.setText(
            f"Contexto estimado: {used_chars}/{self._max_context_chars} chars "
            f"(~{used_tokens}/{capacity_tokens} tokens)"
        )

        if ratio >= 95:
            self.context_meter_bar.setStyleSheet("QProgressBar::chunk { background-color: #B03030; }")
        elif ratio >= 80:
            self.context_meter_bar.setStyleSheet("QProgressBar::chunk { background-color: #B8882A; }")
        else:
            self.context_meter_bar.setStyleSheet("")

    def get_values(self) -> Dict[str, Any]:
        difficulty = int(self.difficulty_combo.currentData() or 3)
        return {
            "chapter_difficulty": max(1, min(difficulty, 5)),
            "selected_notes": self._selected_notes(),
        }


class ManualQuestionsDialog(QDialog):
    """Diálogo para criação manual de perguntas e respostas."""

    def __init__(self, chapter_name: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Criar perguntas manualmente")
        self.setModal(True)
        self.resize(760, 560)
        self._rows: list[Dict[str, Any]] = []

        layout = QVBoxLayout(self)
        intro = QLabel(
            f"Capítulo: {chapter_name}\n"
            "Adicione pares de pergunta e resposta. Você pode criar quantos quiser."
        )
        intro.setWordWrap(True)
        layout.addWidget(intro)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll_content = QWidget()
        self.rows_layout = QVBoxLayout(self.scroll_content)
        self.rows_layout.setContentsMargins(0, 0, 0, 0)
        self.rows_layout.setSpacing(8)
        self.scroll.setWidget(self.scroll_content)
        layout.addWidget(self.scroll, 1)

        add_row = QHBoxLayout()
        self.add_button = QPushButton("Adicionar pergunta")
        self.add_button.clicked.connect(lambda: self._add_row())
        add_row.addWidget(self.add_button)
        add_row.addStretch(1)
        layout.addLayout(add_row)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self._add_row()

    def _add_row(self, question: str = "", answer: str = ""):
        card = QFrame()
        card.setObjectName("manual_question_card")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(8, 8, 8, 8)
        card_layout.setSpacing(6)

        header = QHBoxLayout()
        index_label = QLabel(f"Item {len(self._rows) + 1}")
        remove_btn = QPushButton("Remover")
        remove_btn.setFixedWidth(90)
        header.addWidget(index_label)
        header.addStretch(1)
        header.addWidget(remove_btn)
        card_layout.addLayout(header)

        q_input = QLineEdit()
        q_input.setPlaceholderText("Pergunta")
        q_input.setText(question)
        card_layout.addWidget(q_input)

        a_input = QLineEdit()
        a_input.setPlaceholderText("Resposta")
        a_input.setText(answer)
        card_layout.addWidget(a_input)

        row = {
            "card": card,
            "index_label": index_label,
            "question_input": q_input,
            "answer_input": a_input,
            "remove_button": remove_btn,
        }
        remove_btn.clicked.connect(lambda _checked=False, r=row: self._remove_row(r))
        self._rows.append(row)
        self.rows_layout.addWidget(card)
        self._refresh_labels()

    def _remove_row(self, row: Dict[str, Any]):
        if len(self._rows) <= 1:
            return
        self._rows.remove(row)
        row["card"].setParent(None)
        row["card"].deleteLater()
        self._refresh_labels()

    def _refresh_labels(self):
        for idx, row in enumerate(self._rows, start=1):
            row["index_label"].setText(f"Item {idx}")

    def get_values(self) -> list[Dict[str, str]]:
        values: list[Dict[str, str]] = []
        for row in self._rows:
            question = row["question_input"].text().strip()
            answer = row["answer_input"].text().strip()
            if not question or not answer:
                continue
            values.append({"question": question, "answer": answer})
        return values


class SessionView(QWidget):
    """Tela de sessão com leitura em dupla página, Pomodoro e assistente LLM."""

    navigate_to = pyqtSignal(str)
    USER_NOTES_DIR = "02-ANOTAÇÕES"
    REVIEW_DIR = "03-REVISÃO"
    MINDMAPS_DIR = "04-MAPAS MENTAIS"

    def __init__(self, controllers: Optional[Dict[str, Any]] = None, parent=None):
        super().__init__(parent)
        self.controllers = controllers or {}
        self.reading_controller = self.controllers.get("reading")
        self.agenda_controller = self.controllers.get("agenda")
        self.glados_controller = self.controllers.get("glados")

        self.current_book_id: Optional[str] = None
        self.current_book_title = "Sessão de leitura"
        self.current_page = 1
        self.total_pages = 0
        self.left_page = 1
        self.session_start_page = 1
        self.max_page_reached = 1
        self._last_synced_page = 0
        self._session_closed = False
        self.page_contents: Dict[int, str] = {}
        self.page_chapter_map: Dict[int, Path] = {}
        self.chapter_notes: list[Dict[str, Any]] = []
        self.book_source_path: Optional[Path] = None
        self.current_chapter_path: Optional[Path] = None
        self._pending_note_request: Optional[Dict[str, Any]] = None
        self._manual_book_dir: Optional[Path] = None
        self._manual_book_id: Optional[str] = None
        self._selected_excerpt_for_note: str = ""
        self._selected_excerpt_chapter_path: Optional[Path] = None
        self._excerpt_note_capture_mode = False
        self._fullscreen_mode = False
        self._window_was_fullscreen = False
        self._window_was_maximized = False
        self._assistant_visible_before_fullscreen = False
        self._assistant_expanded_in_fullscreen = False
        self._assistant_should_hide_after_animation = False
        self._pomodoro_overlay_visible = False
        self._review_generation_active = False
        self._review_queue: list[Dict[str, Any]] = []
        self._review_current_task_index = 0
        self._review_context_payload = ""
        self._review_inflight_task: Optional[Dict[str, Any]] = None
        self._review_waiting_cache_clear = False
        self._review_llm_inflight = False
        self._review_started_monotonic: Optional[float] = None
        self._review_retry_max_attempts = 2
        self._review_chapter_difficulty = 3
        self._review_context_note_selection: list[Dict[str, str]] = []
        self._review_backend_metadata: Dict[str, Any] = {}
        self._review_summary_saved_in_run = False
        self._temporary_read_only_session = False
        self._temporary_news_article: Dict[str, Any] = {}
        self._search_matches: list[Dict[str, int]] = []
        self._search_term = ""
        self._search_current_index = -1
        self._search_match_color = QColor("#FFE08A")
        self._search_active_match_color = QColor("#FFB347")
        self.mindmap_review_module = MindmapReviewModule()
        self.review_system = self._resolve_review_system()

        self.pomodoro = self._create_pomodoro()
        self.ui_timer = QTimer(self)
        self.ui_timer.timeout.connect(self._tick_ui)
        self.ui_timer.start(1000)

        self._setup_ui()
        self._setup_connections()
        self.refresh_reading_context()

    def _create_pomodoro(self) -> Optional[PomodoroTimer]:
        try:
            if self.reading_controller and getattr(self.reading_controller, "reading_manager", None):
                vault_path = str(self.reading_controller.reading_manager.vault_path)
                return PomodoroTimer(vault_path)
        except Exception as exc:
            logger.warning("Falha ao inicializar Pomodoro com reading_manager: %s", exc)
        return None

    def _resolve_review_system(self) -> Optional[ReviewSystem]:
        try:
            if self.agenda_controller and getattr(self.agenda_controller, "agenda_manager", None):
                manager = self.agenda_controller.agenda_manager
                if getattr(manager, "review_system", None):
                    return manager.review_system
        except Exception:
            pass

        if not self.reading_controller or not getattr(self.reading_controller, "reading_manager", None):
            return None

        try:
            return ReviewSystem(str(self.reading_controller.reading_manager.vault_path))
        except Exception as exc:
            logger.warning("Falha ao resolver ReviewSystem na SessionView: %s", exc)
            return None

    def _current_chapter_key_for_review(self) -> str:
        chapter_path = self._resolve_active_chapter_path()
        if chapter_path and chapter_path.exists():
            return chapter_path.stem
        chapter_number = self._current_chapter_number()
        if chapter_number > 0:
            return f"capitulo-{chapter_number:02d}"
        return "capitulo-geral"

    def _current_chapter_title_for_review(self) -> str:
        chapter_path = self._resolve_active_chapter_path()
        if chapter_path and chapter_path.exists():
            return chapter_path.stem
        chapter_number = self._current_chapter_number()
        if chapter_number > 0:
            return f"Capítulo {chapter_number}"
        return "Capítulo atual"

    def _register_chapter_difficulty(self, source_note_path: Optional[Path] = None):
        if not self.review_system or not hasattr(self.review_system, "upsert_chapter_difficulty"):
            return

        book_id = str(self.current_book_id or self._manual_book_id or "").strip()
        if not book_id:
            return

        try:
            self.review_system.upsert_chapter_difficulty(
                book_id=book_id,
                chapter_key=self._current_chapter_key_for_review(),
                chapter_title=self._current_chapter_title_for_review(),
                difficulty=int(self._review_chapter_difficulty or 3),
                source_path=str(source_note_path) if source_note_path else "",
            )
        except Exception as exc:
            logger.debug("Falha ao registrar dificuldade do capítulo: %s", exc)

    def _register_manual_questions_with_review_system(
        self,
        entries: list[Dict[str, str]],
        note_path: Optional[Path] = None,
    ):
        if not entries:
            return
        if not self.review_system or not hasattr(self.review_system, "register_manual_questions"):
            return

        book_id = str(self.current_book_id or self._manual_book_id or "").strip()
        if not book_id:
            return

        try:
            self.review_system.register_manual_questions(
                book_id=book_id,
                chapter_key=self._current_chapter_key_for_review(),
                chapter_title=self._current_chapter_title_for_review(),
                difficulty=int(self._review_chapter_difficulty or 3),
                source_path=str(note_path) if note_path else "",
                questions=entries,
                tags=["manual", "session"],
            )
        except Exception as exc:
            logger.debug("Falha ao registrar perguntas manuais: %s", exc)

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        self.header_widget = QWidget()
        header = QHBoxLayout(self.header_widget)
        header.setContentsMargins(6, 4, 6, 2)
        header.setSpacing(4)
        self.title_label = QLabel("Sessão de leitura")  # mantido para estado interno
        self.progress_label = QLabel("Página 1 de ?")   # mantido para estado interno
        self.source_label = QLabel("Fonte: nota não carregada")  # mantido para estado interno

        # Pomodoro minimalista no header
        self.pomodoro_timer_label = QPushButton("25:00")
        self.pomodoro_timer_label.setObjectName("session_pomodoro_timer")
        self.pomodoro_timer_label.setCursor(Qt.CursorShape.PointingHandCursor)
        self.pomodoro_timer_label.setToolTip("Clique para iniciar/pausar Pomodoro")
        self.pomodoro_timer_label.setFixedHeight(32)
        self.pomodoro_timer_label.setFixedWidth(110)
        self.pomodoro_timer_label.setStyleSheet(
            "color: #FFFFFF; background-color: #232733; "
            "border: 1px solid #4A5263; border-radius: 6px; "
            "font-weight: 700; padding: 2px 6px;"
        )

        self.note_button = QPushButton("📝")
        self.note_button.setObjectName("secondary_button")
        self.note_button.setFixedSize(24, 24)
        self.note_button.setToolTip("Anotações")
        self.note_button.setStyleSheet("font-size: 12px; padding: 0px; margin: 0px; margin-top: -2px;")

        self.controls_menu_button = QPushButton("☰")
        self.controls_menu_button.setObjectName("secondary_button")
        self.controls_menu_button.setFixedSize(24, 24)
        self.controls_menu_button.setToolTip("Controles da sessão")
        self.controls_menu_button.setStyleSheet(
            "font-size: 12px; padding: 0px; margin: 0px; margin-top: -2px;"
        )

        header.addWidget(self.note_button)
        header.addStretch()
        header.addWidget(self.pomodoro_timer_label, alignment=Qt.AlignmentFlag.AlignHCenter)
        header.addStretch()
        header.addWidget(self.controls_menu_button)
        root.addWidget(self.header_widget)

        self.reading_panel = QFrame()
        self.reading_panel.setObjectName("session_reading_panel")
        reading_layout = QVBoxLayout(self.reading_panel)
        reading_layout.setContentsMargins(2, 1, 2, 1)
        reading_layout.setSpacing(2)

        pages_grid = QGridLayout()
        pages_grid.setContentsMargins(0, 0, 0, 0)
        pages_grid.setHorizontalSpacing(4)
        pages_grid.setVerticalSpacing(1)

        self.left_page_title = QLabel("Página 1")
        self.right_page_title = QLabel("Página 2")
        self.left_page_text = QTextEdit()
        self.right_page_text = QTextEdit()
        for page in (self.left_page_text, self.right_page_text):
            page.setReadOnly(True)
            page.setObjectName("session_page_text")
            page.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)
            page.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            page.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            page.setStyleSheet(
                "background-color: #FFFFFF; color: #111111; "
                "font-family: Georgia, 'Times New Roman', serif;"
            )
            page.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            page.customContextMenuRequested.connect(
                lambda pos, editor=page: self._show_page_context_menu(editor, pos)
            )

        pages_grid.addWidget(self.left_page_title, 0, 0)
        pages_grid.addWidget(self.right_page_title, 0, 1)
        pages_grid.addWidget(self.left_page_text, 1, 0)
        pages_grid.addWidget(self.right_page_text, 1, 1)
        reading_layout.addLayout(pages_grid)

        self.fullscreen_button = QPushButton("⛶")
        self.fullscreen_button.setToolTip("Modo fullscreen (ESC para sair)")
        self.fullscreen_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.fullscreen_button.setFixedSize(36, 36)
        self.fullscreen_button.setStyleSheet(
            "QPushButton {"
            "background-color: rgba(35, 39, 51, 0.9); color: #FFFFFF; "
            "border: 1px solid #4A5263; border-radius: 18px; font-size: 17px;"
            "}"
            "QPushButton:hover { background-color: rgba(53, 60, 77, 0.95); }"
        )
        self.fullscreen_button.setParent(self.left_page_text.viewport())
        self.fullscreen_button.raise_()

        self.nav_widget = QWidget()
        nav = QHBoxLayout(self.nav_widget)
        nav.setContentsMargins(0, 0, 0, 0)
        nav.setSpacing(4)
        self.prev_pages_button = QPushButton("◀ Páginas anteriores")
        self.next_pages_button = QPushButton("Próximas páginas ▶")
        self.page_pair_label = QLabel("1-2")
        self.page_pair_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        nav.addWidget(self.prev_pages_button)
        nav.addWidget(self.page_pair_label, 1)
        nav.addWidget(self.next_pages_button)
        reading_layout.addWidget(self.nav_widget)

        self.search_bar = QFrame()
        self.search_bar.setObjectName("session_search_bar")
        search_layout = QHBoxLayout(self.search_bar)
        search_layout.setContentsMargins(0, 0, 0, 0)
        search_layout.setSpacing(6)
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Pesquisar em toda a obra (Ctrl+F)...")
        self.search_prev_button = QPushButton("◀ Anterior")
        self.search_next_button = QPushButton("Próxima ▶")
        self.search_counter_label = QLabel("0/0")
        self.search_close_button = QPushButton("Fechar")
        self.search_prev_button.setEnabled(False)
        self.search_next_button.setEnabled(False)
        search_layout.addWidget(self.search_input, 1)
        search_layout.addWidget(self.search_prev_button)
        search_layout.addWidget(self.search_next_button)
        search_layout.addWidget(self.search_counter_label)
        search_layout.addWidget(self.search_close_button)
        self.search_bar.setVisible(False)
        reading_layout.addWidget(self.search_bar)

        self.assistant_tabs = QTabWidget()
        self.assistant_tabs.setObjectName("session_assistant_tabs")
        self.assistant_tabs.setVisible(False)
        self.assistant_hide_button = QToolButton()
        self.assistant_hide_button.setText("Ocultar")
        self.assistant_hide_button.setObjectName("session_tab_corner_button")
        self.assistant_hide_button.setAutoRaise(True)
        self.assistant_hide_button.setFixedHeight(22)
        self.assistant_hide_button.setStyleSheet(
            "QToolButton#session_tab_corner_button {"
            "padding: 2px 8px; border: 1px solid #4A5263; border-bottom: none; "
            "border-top-left-radius: 4px; border-top-right-radius: 4px;"
            "}"
        )
        self.assistant_tabs.setCornerWidget(self.assistant_hide_button, Qt.Corner.TopRightCorner)

        self.chat_panel = QFrame()
        self.chat_panel.setObjectName("session_chat_panel")
        chat_layout = QVBoxLayout(self.chat_panel)
        chat_layout.setContentsMargins(8, 8, 8, 8)
        chat_layout.setSpacing(6)

        self.chat_history = QTextEdit()
        self.chat_history.setReadOnly(True)
        self.chat_preset_combo = QComboBox()
        self.chat_preset_combo.addItems(["Rápido", "Balanceado", "Qualidade"])
        self.chat_preset_combo.setCurrentText("Balanceado")
        self.chat_preset_combo.setFixedWidth(130)
        self.chat_summary_button = QPushButton("Resumo + anotações")
        self.chat_mindmap_button = QPushButton("Mapa mental")
        self.chat_mindmap_button.setToolTip("Criar/atualizar mapa mental da obra")
        self.chat_mark_review_button = QPushButton("Marcar para revisão")
        self.chat_status_label = QLabel("LLM pronta")
        self.review_step_label = QLabel("Revisão: inativa")
        self.review_overall_progress = QProgressBar()
        self.review_overall_progress.setRange(0, 100)
        self.review_overall_progress.setValue(0)
        self.review_item_progress = QProgressBar()
        self.review_item_progress.setRange(0, 100)
        self.review_item_progress.setValue(0)
        self.review_step_label.setVisible(False)
        self.review_overall_progress.setVisible(False)
        self.review_item_progress.setVisible(False)

        input_row = QHBoxLayout()
        input_row.addStretch(1)
        input_row.addWidget(self.chat_preset_combo)
        input_row.addWidget(self.chat_mindmap_button)
        input_row.addWidget(self.chat_mark_review_button)

        chat_layout.addWidget(self.chat_history, 1)
        chat_layout.addWidget(self.review_step_label)
        chat_layout.addWidget(self.review_overall_progress)
        chat_layout.addWidget(self.review_item_progress)
        chat_layout.addLayout(input_row)
        chat_layout.addWidget(self.chat_status_label)

        self.note_panel = QFrame()
        self.note_panel.setObjectName("session_note_panel")
        note_layout = QVBoxLayout(self.note_panel)
        note_layout.setContentsMargins(8, 8, 8, 8)
        note_layout.setSpacing(6)

        note_header = QHBoxLayout()
        self.note_title_input = QLineEdit()
        self.note_title_input.setPlaceholderText("Título da nota")
        note_header.addWidget(self.chat_summary_button)
        self.note_save_button = QPushButton("Salvar")
        note_header.addWidget(self.note_title_input, 1)
        note_header.addWidget(self.note_save_button)

        self.note_capture_hint = QLabel("")
        self.note_capture_hint.setWordWrap(True)
        self.note_capture_hint.setVisible(False)

        self.note_editor = QTextEdit()
        self.note_editor.setPlaceholderText("Escreva sua anotação aqui...")
        self.note_editor.setStyleSheet(
            "background-color: #FFFFFF; color: #111111; "
            "font-family: Georgia, 'Times New Roman', serif;"
        )

        note_layout.addLayout(note_header)
        note_layout.addWidget(self.note_capture_hint)
        note_layout.addWidget(self.note_editor, 1)

        self.assistant_tabs.addTab(self.note_panel, "Anotação")
        reading_layout.addWidget(self.assistant_tabs)

        root.addWidget(self.reading_panel, 1)

        # Menu único com os controles não relacionados à navegação de páginas.
        self.controls_menu = QMenu(self)
        self.action_back_dashboard = self.controls_menu.addAction("Voltar para Dashboard")
        self.action_end_session = self.controls_menu.addAction("Encerrar Sessão")
        self.controls_menu.addSeparator()
        self.action_pomodoro_start = self.controls_menu.addAction("Pomodoro: Iniciar")
        self.action_pomodoro_pause = self.controls_menu.addAction("Pomodoro: Pausar")
        self.action_pomodoro_config = self.controls_menu.addAction("Pomodoro: Configurar")

        self.pomodoro_overlay = QFrame(self.reading_panel)
        self.pomodoro_overlay.setStyleSheet("background-color: rgba(10, 12, 18, 160);")
        self.pomodoro_overlay.hide()
        self.pomodoro_overlay.mousePressEvent = self._on_pomodoro_overlay_mouse_press

        self.pomodoro_overlay_card = QFrame(self.pomodoro_overlay)
        self.pomodoro_overlay_card.setStyleSheet(
            "background-color: #202430; border: 1px solid #4A5263; border-radius: 10px;"
        )
        overlay_row = QHBoxLayout(self.pomodoro_overlay_card)
        overlay_row.setContentsMargins(12, 10, 12, 10)
        overlay_row.setSpacing(8)
        self.pomodoro_overlay_toggle_button = QPushButton("▶")
        self.pomodoro_overlay_toggle_button.setFixedWidth(48)
        self.pomodoro_overlay_timer_label = QLabel("25:00")
        self.pomodoro_overlay_timer_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.pomodoro_overlay_timer_label.setStyleSheet("font-size: 18px; font-weight: 700; color: #E8ECF5;")
        self.pomodoro_overlay_config_button = QPushButton("Configurações")
        overlay_row.addWidget(self.pomodoro_overlay_toggle_button)
        overlay_row.addWidget(self.pomodoro_overlay_timer_label, 1)
        overlay_row.addWidget(self.pomodoro_overlay_config_button)

        self.pomodoro_overlay_animation = QPropertyAnimation(self.pomodoro_overlay_card, b"pos", self)
        self.pomodoro_overlay_animation.setDuration(220)
        self.pomodoro_overlay_animation.setEasingCurve(QEasingCurve.Type.OutCubic)

        self.assistant_slide_animation = QPropertyAnimation(self.assistant_tabs, b"maximumHeight", self)
        self.assistant_slide_animation.setDuration(230)
        self.assistant_slide_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.assistant_slide_animation.finished.connect(self._on_assistant_slide_finished)

        self.review_done_toast = QFrame(self.reading_panel)
        self.review_done_toast.setStyleSheet(
            "background-color: rgba(27, 32, 41, 235); border: 1px solid #4A5263; border-radius: 8px;"
        )
        toast_layout = QHBoxLayout(self.review_done_toast)
        toast_layout.setContentsMargins(10, 6, 10, 6)
        toast_layout.setSpacing(6)
        self.review_done_toast_label = QLabel("Materiais de revisão prontos")
        self.review_done_toast_label.setStyleSheet("color: #E8ECF5; font-weight: 600;")
        toast_layout.addWidget(self.review_done_toast_label)
        self.review_done_toast.hide()

        self.shortcut_left = QShortcut(QKeySequence(Qt.Key.Key_Left), self)
        self.shortcut_right = QShortcut(QKeySequence(Qt.Key.Key_Right), self)
        self.shortcut_up = QShortcut(QKeySequence(Qt.Key.Key_Up), self)
        self.shortcut_down = QShortcut(QKeySequence(Qt.Key.Key_Down), self)
        self.shortcut_esc = QShortcut(QKeySequence(Qt.Key.Key_Escape), self)
        self.shortcut_find = QShortcut(QKeySequence.StandardKey.Find, self)
        self.shortcut_find_ctrl = QShortcut(QKeySequence("Ctrl+F"), self)
        for shortcut in (
            self.shortcut_left,
            self.shortcut_right,
            self.shortcut_up,
            self.shortcut_down,
            self.shortcut_esc,
            self.shortcut_find,
            self.shortcut_find_ctrl,
        ):
            shortcut.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)

    def _setup_connections(self):
        self.note_button.clicked.connect(self._open_note_tab)
        self.fullscreen_button.clicked.connect(self._toggle_fullscreen_mode)
        self.pomodoro_timer_label.clicked.connect(self._toggle_pomodoro_from_timer)
        self.controls_menu_button.clicked.connect(self._open_controls_menu)
        self.action_back_dashboard.triggered.connect(self._on_back_clicked)
        self.action_end_session.triggered.connect(self._on_end_session_clicked)
        self.action_pomodoro_start.triggered.connect(self._start_pomodoro)
        self.action_pomodoro_pause.triggered.connect(self._pause_pomodoro)
        self.action_pomodoro_config.triggered.connect(self._open_pomodoro_config_dialog)

        self.prev_pages_button.clicked.connect(self._go_prev_pages)
        self.next_pages_button.clicked.connect(self._go_next_pages)
        self.chat_summary_button.clicked.connect(self._request_summary_with_annotations)
        self.chat_mindmap_button.clicked.connect(self._handle_mindmap_button_clicked)
        self.chat_mark_review_button.clicked.connect(self._start_review_generation)
        self.chat_preset_combo.currentTextChanged.connect(self._apply_chat_preset)
        self.note_save_button.clicked.connect(self._save_note_from_tab)
        self.assistant_hide_button.clicked.connect(self._hide_assistant_panels)
        self.pomodoro_overlay_toggle_button.clicked.connect(self._toggle_pomodoro_from_timer)
        self.pomodoro_overlay_config_button.clicked.connect(self._open_pomodoro_config_dialog)
        self.search_input.textChanged.connect(self._on_search_term_changed)
        self.search_input.returnPressed.connect(self._go_to_next_search_match)
        self.search_prev_button.clicked.connect(self._go_to_prev_search_match)
        self.search_next_button.clicked.connect(self._go_to_next_search_match)
        self.search_close_button.clicked.connect(self._hide_search_bar)

        self.shortcut_left.activated.connect(self._on_fullscreen_left)
        self.shortcut_right.activated.connect(self._on_fullscreen_right)
        self.shortcut_up.activated.connect(self._on_fullscreen_up)
        self.shortcut_down.activated.connect(self._on_fullscreen_down)
        self.shortcut_esc.activated.connect(self._on_fullscreen_escape)
        self.shortcut_find.activated.connect(self._open_search_bar)
        self.shortcut_find_ctrl.activated.connect(self._open_search_bar)

        if self.glados_controller:
            self.glados_controller.response_ready.connect(self._on_llm_response)
            self.glados_controller.processing_started.connect(self._on_llm_processing_started)
            self.glados_controller.processing_progress.connect(self._on_llm_processing_progress)
            self.glados_controller.processing_completed.connect(self._on_llm_processing_completed)
            self.glados_controller.error_occurred.connect(self._on_llm_error)

    def on_view_activated(self):
        self._session_closed = False
        if not self._temporary_read_only_session:
            self.refresh_reading_context()
        else:
            self._refresh_pages()
            self._apply_session_mode_ui()
        self._tick_ui()
        self._position_fullscreen_button()
        self._sync_fullscreen_overlays_geometry()
        self._set_fullscreen_mode(True)

    def start_ad_hoc_reading(self, book_dir: Path):
        """Inicia leitura avulsa a partir de um diretório de livro do vault."""
        self._manual_book_dir = Path(book_dir)
        self._manual_book_id = None
        self._temporary_read_only_session = False
        self._temporary_news_article = {}
        self._session_closed = False

        if not self.reading_controller or not getattr(self.reading_controller, "reading_manager", None):
            self.refresh_reading_context()
            return

        manager = self.reading_controller.reading_manager
        title = self._manual_book_dir.name
        author = self._manual_book_dir.parent.name if self._manual_book_dir.parent else "Desconhecido"

        matched_book_id = None
        for bid, info in manager.readings.items():
            if info.title.strip().lower() == title.strip().lower():
                matched_book_id = bid
                break

        if not matched_book_id:
            total_pages = self._estimate_total_pages_in_dir(self._manual_book_dir)
            matched_book_id = manager.add_book(
                title=title,
                author=author,
                total_pages=max(total_pages, 1)
            )

        self._manual_book_id = str(matched_book_id)
        if hasattr(self.reading_controller, "start_reading_session"):
            try:
                self.reading_controller.start_reading_session(self._manual_book_id, 10)
            except Exception:
                pass

        self.refresh_reading_context()

    def start_news_reading(self, article: Dict[str, Any]):
        """Inicia uma sessao temporaria de leitura de noticia (sem persistencia)."""
        payload = dict(article or {})
        title = str(payload.get("title") or "Notícia").strip() or "Notícia"
        subtitle = str(payload.get("subtitle") or "").strip()
        summary = str(payload.get("summary") or "").strip()
        source = str(payload.get("source") or payload.get("feed_url") or "").strip()
        published = str(payload.get("published") or "").strip()
        original_url = str(payload.get("url") or "").strip()

        summary_plain = self._strip_html_to_text(summary)
        full_article_text = self._fetch_news_article_text(original_url) if original_url else ""
        blocks: list[str] = [title]
        if subtitle:
            blocks.extend(["", subtitle])
        if source or published:
            meta_line = " | ".join(part for part in (source, published) if part)
            if meta_line:
                blocks.extend(["", f"Fonte: {meta_line}"])
        if original_url:
            blocks.extend(["", f"Link: {original_url}"])
        if full_article_text:
            blocks.extend(["", full_article_text])
        elif summary_plain:
            blocks.extend(
                [
                    "",
                    summary_plain,
                    "",
                    "Observação: conteúdo completo indisponível no momento; exibindo resumo do feed.",
                ]
            )
        else:
            blocks.extend(["", "Conteúdo indisponível."])

        full_text = "\n".join(blocks).strip()
        page_contents = self._split_text_into_pages(full_text, chars_per_page=self._news_chars_per_page())

        self._temporary_read_only_session = True
        self._temporary_news_article = payload
        self._session_closed = False
        self.current_book_id = None
        self._manual_book_id = None
        self._manual_book_dir = None
        self.current_book_title = title
        self.current_page = 1
        self.session_start_page = 1
        self.max_page_reached = 1
        self._last_synced_page = 0
        self.page_contents = page_contents
        self.page_chapter_map = {}
        self.chapter_notes = []
        self.book_source_path = None
        self.current_chapter_path = None
        self.left_page = 1
        self.total_pages = max(page_contents.keys()) if page_contents else 1
        self._refresh_pages()
        self._apply_session_mode_ui()

    def _split_text_into_pages(self, text: str, chars_per_page: int = 2600) -> Dict[int, str]:
        clean = str(text or "").strip()
        if not clean:
            return {1: "Sem conteúdo disponível."}

        page_limit = max(800, int(chars_per_page))
        raw_paragraphs = [part.strip() for part in re.split(r"\n\s*\n", clean) if part.strip()]
        if not raw_paragraphs:
            raw_paragraphs = [clean]

        paragraphs: list[str] = []
        for paragraph in raw_paragraphs:
            working = paragraph.strip()
            while len(working) > page_limit:
                split_at = working.rfind(" ", 0, page_limit + 1)
                if split_at < max(120, int(page_limit * 0.5)):
                    split_at = page_limit
                chunk = working[:split_at].strip()
                if chunk:
                    paragraphs.append(chunk)
                working = working[split_at:].strip()
            if working:
                paragraphs.append(working)

        pages: Dict[int, str] = {}
        current_parts: list[str] = []
        current_len = 0
        page_number = 1

        for paragraph in paragraphs:
            projected = current_len + len(paragraph) + (2 if current_parts else 0)
            if current_parts and projected > page_limit:
                pages[page_number] = "\n\n".join(current_parts).strip()
                page_number += 1
                current_parts = [paragraph]
                current_len = len(paragraph)
                continue
            current_parts.append(paragraph)
            current_len = projected

        if current_parts:
            pages[page_number] = "\n\n".join(current_parts).strip()

        if not pages:
            pages[1] = clean
        return pages

    def _news_chars_per_page(self) -> int:
        viewport = self.left_page_text.viewport() if hasattr(self, "left_page_text") else None
        if viewport is not None and viewport.width() > 320 and viewport.height() > 280:
            w = max(420, int(viewport.width()))
            h = max(360, int(viewport.height()))
            estimated = int((w * h) / 130)
            return max(1800, min(4600, estimated))
        return 2600

    def _strip_html_to_text(self, value: str) -> str:
        raw = str(value or "")
        if not raw:
            return ""
        without_tags = re.sub(r"<[^>]+>", " ", raw)
        unescaped = html_lib.unescape(without_tags)
        normalized = re.sub(r"\s+", " ", unescaped).strip()
        return normalized

    def _fetch_news_article_text(self, url: str, max_chars: int = 26000) -> str:
        target = str(url or "").strip()
        if not target:
            return ""

        html_text = ""
        try:
            request = Request(
                target,
                headers={
                    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/123.0 Safari/537.36",
                    "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
                },
            )
            with urlopen(request, timeout=12) as response:
                raw_bytes = response.read(3 * 1024 * 1024)
                content_type = str(response.headers.get("content-type", "") or "")
            charset_match = re.search(r"charset=([a-zA-Z0-9._-]+)", content_type, flags=re.IGNORECASE)
            charset = str(charset_match.group(1) or "").strip() if charset_match else ""
            html_text = raw_bytes.decode(charset or "utf-8", errors="ignore")
        except Exception as exc:
            logger.info("Nao foi possivel baixar conteudo completo da noticia '%s': %s", target, exc)
            return ""

        extracted = self._extract_news_text_from_html(html_text, max_chars=max_chars)
        if extracted:
            return extracted
        return ""

    def _extract_news_text_from_html(self, html_text: str, max_chars: int = 26000) -> str:
        raw = str(html_text or "").strip()
        if not raw:
            return ""

        if BeautifulSoup is None:
            fallback = self._strip_html_to_text(raw)
            if len(fallback) > max_chars:
                return fallback[:max_chars].rsplit(" ", 1)[0].strip() + "..."
            return fallback

        try:
            soup = BeautifulSoup(raw, "lxml")
        except Exception:
            try:
                soup = BeautifulSoup(raw, "html.parser")
            except Exception:
                return ""

        for tag in soup.find_all(
            [
                "script",
                "style",
                "noscript",
                "svg",
                "canvas",
                "iframe",
                "form",
                "button",
                "input",
                "header",
                "footer",
                "nav",
                "aside",
            ]
        ):
            try:
                tag.decompose()
            except Exception:
                continue

        containers = []
        article_tag = soup.find("article")
        if article_tag is not None:
            containers.append(article_tag)
        main_tag = soup.find("main")
        if main_tag is not None and main_tag not in containers:
            containers.append(main_tag)
        body_tag = soup.body
        if not containers and body_tag is not None:
            containers.append(body_tag)
        if not containers:
            containers.append(soup)

        parts: list[str] = []
        seen: set[str] = set()
        collected_chars = 0
        for container in containers:
            for node in container.find_all(["h1", "h2", "h3", "p", "li", "blockquote"]):
                text = re.sub(r"\s+", " ", node.get_text(" ", strip=True)).strip()
                if not text:
                    continue
                if node.name in {"p", "li", "blockquote"} and len(text) < 30:
                    continue
                lowered = text.lower()
                if lowered in {
                    "recommended stories",
                    "related stories",
                    "read more",
                    "advertisement",
                }:
                    continue
                if re.match(r"^list\s+\d+\s+of\s+\d+", lowered):
                    continue
                key = text.lower()
                if key in seen:
                    continue
                seen.add(key)
                parts.append(text)
                collected_chars += len(text) + 2
                if collected_chars >= max_chars:
                    break
            if collected_chars >= max_chars:
                break

        if not parts:
            plain = re.sub(r"\s+", " ", soup.get_text(" ", strip=True)).strip()
            if len(plain) > max_chars:
                return plain[:max_chars].rsplit(" ", 1)[0].strip() + "..."
            return plain

        joined = "\n\n".join(parts).strip()
        if len(joined) > max_chars:
            return joined[:max_chars].rsplit(" ", 1)[0].strip() + "..."
        return joined

    def _apply_session_mode_ui(self):
        is_temporary = bool(self._temporary_read_only_session)

        if self.note_button is not None:
            self.note_button.setEnabled(not is_temporary)
            self.note_button.setToolTip(
                "Anotações" if not is_temporary else "Anotações desativadas na leitura de notícia"
            )
        if self.chat_summary_button is not None:
            self.chat_summary_button.setEnabled(not is_temporary)
        if self.chat_mindmap_button is not None:
            self.chat_mindmap_button.setEnabled(not is_temporary)
        if self.chat_mark_review_button is not None:
            self.chat_mark_review_button.setEnabled(not is_temporary)
        if self.chat_preset_combo is not None:
            self.chat_preset_combo.setEnabled(not is_temporary)
        if self.note_save_button is not None:
            self.note_save_button.setEnabled(not is_temporary)
        if self.note_title_input is not None:
            self.note_title_input.setEnabled(not is_temporary)
        if self.note_editor is not None:
            self.note_editor.setReadOnly(is_temporary)

        if self.assistant_tabs is not None and is_temporary:
            self.assistant_tabs.setVisible(False)
            self.assistant_tabs.setMaximumHeight(0)
            self._assistant_expanded_in_fullscreen = False

        if is_temporary:
            self.action_back_dashboard.setText("Voltar para chats")
            self.action_end_session.setText("Fechar notícia")
            source = str(
                self._temporary_news_article.get("source")
                or self._temporary_news_article.get("feed_url")
                or ""
            ).strip()
            if source:
                self.source_label.setText(f"Fonte: {source}")
        else:
            self.action_back_dashboard.setText("Voltar para Dashboard")
            self.action_end_session.setText("Encerrar Sessão")

    def refresh_reading_context(self):
        book_id = self._manual_book_id or self._resolve_book_id()
        progress = self._get_progress(book_id) if book_id else {}

        if progress:
            self.current_book_id = progress.get("book_id") or progress.get("id") or book_id
            self.current_book_title = progress.get("title", "Sessão de leitura")
            current_page, total_pages = self._parse_progress(progress.get("progress", "1/0"))
            self.current_page = max(current_page, 1)
            self.session_start_page = self.current_page
            self.max_page_reached = self.current_page
            self._last_synced_page = self.current_page
            self.total_pages = max(total_pages, 0)
            self._load_book_pages(progress)
            self.current_chapter_path = self.page_chapter_map.get(self.current_page)
        else:
            self.current_book_id = None
            self.current_book_title = "Sessão de leitura"
            self.current_page = 1
            self.session_start_page = 1
            self.max_page_reached = 1
            self._last_synced_page = 0
            self.total_pages = 0
            self.page_contents = {}
            self.page_chapter_map = {}
            self.chapter_notes = []
            self.book_source_path = None
            self.current_chapter_path = None

        self.left_page = self._left_page_from_current(self.current_page)
        self._refresh_pages()
        self._apply_session_mode_ui()

    def _resolve_book_id(self) -> Optional[str]:
        if self.reading_controller:
            try:
                current_session = self.reading_controller.get_current_session()
                if current_session and current_session.get("book_id"):
                    return current_session["book_id"]
            except Exception:
                pass

            try:
                all_progress = self.reading_controller.reading_manager.get_reading_progress()
                if isinstance(all_progress, dict):
                    for bid, info in all_progress.items():
                        current_page, total_pages = self._parse_progress(info.get("progress", "0/0"))
                        if total_pages == 0 or current_page < total_pages:
                            return bid
            except Exception:
                pass

        return None

    def _get_progress(self, book_id: str) -> Dict[str, Any]:
        if not self.reading_controller or not book_id:
            return {}
        try:
            return self.reading_controller.reading_manager.get_reading_progress(book_id) or {}
        except Exception as exc:
            logger.warning("Falha ao carregar progresso do livro %s: %s", book_id, exc)
            return {}

    def _parse_progress(self, progress_str: str) -> tuple[int, int]:
        try:
            parts = progress_str.split("/")
            return int(parts[0]), int(parts[1])
        except Exception:
            return 1, 0

    def _left_page_from_current(self, current_page: int) -> int:
        if current_page <= 1:
            return 1
        return current_page if current_page % 2 == 1 else current_page - 1

    def _refresh_pages(self):
        left = max(self.left_page, 1)
        right = left + 1

        left_text = self._sanitize_page_display_text(self._build_page_content(left))
        right_text = self._sanitize_page_display_text(self._build_page_content(right))
        self.left_page_title.setText(f"Página {left}")
        self.right_page_title.setText(f"Página {right}")
        self.left_page_text.setPlainText(left_text)
        self.right_page_text.setPlainText(right_text)
        if self._temporary_read_only_session:
            self._apply_news_readability_format(self.left_page_text, left)
            self._apply_news_readability_format(self.right_page_text, right)

        self.page_pair_label.setText(f"{left}-{right}")
        total_text = "?" if self.total_pages <= 0 else str(self.total_pages)
        self.progress_label.setText(f"Página atual: {self.current_page} de {total_text}")
        self.title_label.setText(self.current_book_title)
        if self.book_source_path:
            self.source_label.setText(f"Fonte: {self.book_source_path.name}")
        else:
            self.source_label.setText("Fonte: nota não encontrada")

        self.prev_pages_button.setEnabled(left > 1)
        if self.total_pages > 0:
            self.next_pages_button.setEnabled(right < self.total_pages)
        else:
            self.next_pages_button.setEnabled(True)
        self._apply_search_highlights()
        self._position_fullscreen_button()

    def _apply_news_readability_format(self, editor: QTextEdit, page_number: int):
        doc = editor.document()
        if doc is None:
            return

        base_char_fmt = QTextCharFormat()
        base_char_fmt.setFont(QFont("Georgia", 12))
        base_char_fmt.setForeground(QColor("#171717"))

        base_block_fmt = QTextBlockFormat()
        base_block_fmt.setLineHeight(145, QTextBlockFormat.LineHeightTypes.ProportionalHeight.value)
        base_block_fmt.setAlignment(Qt.AlignmentFlag.AlignJustify)

        cursor = QTextCursor(doc)
        cursor.select(QTextCursor.SelectionType.Document)
        cursor.mergeCharFormat(base_char_fmt)

        block = doc.begin()
        while block.isValid():
            block_cursor = QTextCursor(block)
            block_cursor.select(QTextCursor.SelectionType.BlockUnderCursor)
            block_cursor.mergeBlockFormat(base_block_fmt)
            block = block.next()

        title_block = None
        subtitle_block = None
        if page_number == 1:
            probe = doc.begin()
            while probe.isValid():
                text = str(probe.text() or "").strip()
                if text:
                    title_block = probe
                    break
                probe = probe.next()

            if title_block is not None:
                probe = title_block.next()
                while probe.isValid():
                    text = str(probe.text() or "").strip()
                    if not text:
                        probe = probe.next()
                        continue
                    if text.lower().startswith("fonte:") or text.lower().startswith("link:"):
                        probe = probe.next()
                        continue
                    subtitle_block = probe
                    break

        if title_block is not None:
            title_char_fmt = QTextCharFormat()
            title_char_fmt.setFont(QFont("Georgia", 20, QFont.Weight.Bold))
            title_char_fmt.setForeground(QColor("#101010"))
            title_cursor = QTextCursor(title_block)
            title_cursor.select(QTextCursor.SelectionType.BlockUnderCursor)
            title_cursor.mergeCharFormat(title_char_fmt)

            title_block_fmt = QTextBlockFormat()
            title_block_fmt.setAlignment(Qt.AlignmentFlag.AlignLeft)
            title_block_fmt.setLineHeight(120, QTextBlockFormat.LineHeightTypes.ProportionalHeight.value)
            title_cursor.mergeBlockFormat(title_block_fmt)

        if subtitle_block is not None:
            subtitle_char_fmt = QTextCharFormat()
            subtitle_char_fmt.setFont(QFont("Georgia", 14, QFont.Weight.Medium))
            subtitle_char_fmt.setFontItalic(True)
            subtitle_char_fmt.setForeground(QColor("#2E3946"))
            subtitle_cursor = QTextCursor(subtitle_block)
            subtitle_cursor.select(QTextCursor.SelectionType.BlockUnderCursor)
            subtitle_cursor.mergeCharFormat(subtitle_char_fmt)

            subtitle_block_fmt = QTextBlockFormat()
            subtitle_block_fmt.setAlignment(Qt.AlignmentFlag.AlignLeft)
            subtitle_block_fmt.setLineHeight(132, QTextBlockFormat.LineHeightTypes.ProportionalHeight.value)
            subtitle_cursor.mergeBlockFormat(subtitle_block_fmt)

        probe = doc.begin()
        while probe.isValid():
            text = str(probe.text() or "").strip()
            lowered = text.lower()
            if lowered.startswith("fonte:") or lowered.startswith("link:") or lowered.startswith("observação:"):
                meta_char_fmt = QTextCharFormat()
                meta_char_fmt.setFont(QFont("Georgia", 10, QFont.Weight.Medium))
                meta_char_fmt.setForeground(QColor("#4A5563"))
                meta_cursor = QTextCursor(probe)
                meta_cursor.select(QTextCursor.SelectionType.BlockUnderCursor)
                meta_cursor.mergeCharFormat(meta_char_fmt)
                meta_block_fmt = QTextBlockFormat()
                meta_block_fmt.setAlignment(Qt.AlignmentFlag.AlignLeft)
                meta_block_fmt.setLineHeight(126, QTextBlockFormat.LineHeightTypes.ProportionalHeight.value)
                meta_cursor.mergeBlockFormat(meta_block_fmt)
            probe = probe.next()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._position_fullscreen_button()
        self._sync_fullscreen_overlays_geometry()

    def keyPressEvent(self, event):
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier and event.key() == Qt.Key.Key_F:
            self._open_search_bar()
            event.accept()
            return
        super().keyPressEvent(event)

    def _position_fullscreen_button(self):
        viewport = self.left_page_text.viewport()
        if not viewport:
            return
        margin = 10
        x = margin
        y = max(margin, viewport.height() - self.fullscreen_button.height() - margin)
        self.fullscreen_button.move(x, y)
        self.fullscreen_button.raise_()

    def _sync_fullscreen_overlays_geometry(self):
        if not hasattr(self, "reading_panel"):
            return
        panel_rect = self.reading_panel.rect()
        self.pomodoro_overlay.setGeometry(panel_rect)

        card_width = min(560, max(320, panel_rect.width() - 100))
        card_height = 64
        x = max(8, (panel_rect.width() - card_width) // 2)
        if self.pomodoro_overlay_card.width() != card_width or self.pomodoro_overlay_card.height() != card_height:
            self.pomodoro_overlay_card.resize(card_width, card_height)
        if not self._pomodoro_overlay_visible:
            self.pomodoro_overlay_card.move(x, -card_height)
        else:
            self.pomodoro_overlay_card.move(x, 16)

        if self.review_done_toast.isVisible():
            self._position_review_done_toast()

    def _position_review_done_toast(self):
        panel_rect = self.reading_panel.rect()
        self.review_done_toast.adjustSize()
        margin = 16
        x = max(margin, panel_rect.width() - self.review_done_toast.width() - margin)
        y = max(margin, panel_rect.height() - self.review_done_toast.height() - margin)
        self.review_done_toast.move(x, y)
        self.review_done_toast.raise_()

    def _build_page_content(self, page_number: int) -> str:
        if self.total_pages > 0 and page_number > self.total_pages:
            return "Fim do livro."

        if self.page_contents:
            content = self.page_contents.get(page_number)
            if content is not None:
                return content
            return "[Página não encontrada na nota do livro]"

        return "[Conteúdo do livro indisponível]"

    def _sanitize_page_display_text(self, text: str) -> str:
        # Mantém só o rótulo do link na sessão para evitar poluição visual com caminho.
        clean = text or ""
        clean = re.sub(r"\[([^\]]+)\]\(\s*<[^>]+>\s*\)", r"[\1]", clean)
        clean = re.sub(r"\[([^\]]+)\]\(\s*[^)]+\s*\)", r"[\1]", clean)
        return clean

    def _load_book_pages(self, progress: Dict[str, Any]):
        self.page_contents = {}
        self.page_chapter_map = {}
        self.chapter_notes = []
        self.book_source_path = None
        self.current_chapter_path = None

        self._index_chapter_notes(progress)
        if self.current_page in self.page_chapter_map:
            self.current_chapter_path = self.page_chapter_map[self.current_page]

        note_path = self._find_primary_book_note(progress)
        if note_path:
            sections = self._extract_page_sections(note_path.read_text(encoding="utf-8", errors="ignore"))
            if sections:
                self.page_contents = sections
                self.book_source_path = note_path
                self.total_pages = max(self.total_pages, max(sections.keys()))
                return

        # Fallback: agrega páginas a partir das notas de capítulo.
        for chapter_file in self._collect_book_markdown_files(progress):
            try:
                text = chapter_file.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue
            sections = self._extract_page_sections(text)
            if not sections:
                continue
            for page_no, page_text in sections.items():
                self.page_contents[page_no] = page_text

        if self.page_contents:
            self.book_source_path = self._find_book_directory(progress)
            self.total_pages = max(self.total_pages, max(self.page_contents.keys()))

    def _index_chapter_notes(self, progress: Dict[str, Any]):
        for md_file in self._collect_book_markdown_files(progress):
            name_lower = md_file.name.lower()
            if "capitulo" not in name_lower and "capítulo" not in name_lower:
                continue
            try:
                text = md_file.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue

            pages = self._extract_page_sections(text)
            if not pages:
                continue

            page_numbers = sorted(pages.keys())
            start_page = page_numbers[0]
            end_page = page_numbers[-1]
            chapter_number = self._extract_chapter_number(md_file, text)

            self.chapter_notes.append(
                {
                    "path": md_file,
                    "number": chapter_number,
                    "start_page": start_page,
                    "end_page": end_page,
                }
            )
            for p in page_numbers:
                self.page_chapter_map[p] = md_file

        self.chapter_notes.sort(key=lambda item: item["start_page"])

    def _extract_chapter_number(self, file_path: Path, text: str) -> int:
        match = re.search(r"(?m)^chapter(?:_number)?:\s*(\d+)\s*$", text)
        if match:
            return int(match.group(1))

        match = re.search(r"capitulo[-_ ]?(\d+)", file_path.name.lower())
        if match:
            return int(match.group(1))

        match = re.search(r"capítulo[-_ ]?(\d+)", file_path.name.lower())
        if match:
            return int(match.group(1))

        return 0

    def _find_primary_book_note(self, progress: Dict[str, Any]) -> Optional[Path]:
        files = self._collect_book_markdown_files(progress)
        best: Optional[Path] = None
        best_score = -1

        progress_book_id = str(progress.get("book_id") or progress.get("id") or "").strip()
        title = str(progress.get("title") or "").strip()

        for file_path in files:
            try:
                content = file_path.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue

            page_count = len(re.findall(r"(?m)^---\s*Página\s+\d+\s*---\s*$", content))
            if page_count <= 0:
                continue

            score = page_count
            name_lower = file_path.name.lower()

            if file_path.name.startswith("📖 "):
                score += 400
            if "completo" in name_lower:
                score += 300
            if "capitulo" in name_lower or "capítulo" in name_lower:
                score -= 200
            if progress_book_id and re.search(rf"(?m)^book_id:\s*{re.escape(progress_book_id)}\s*$", content):
                score += 500
            if title and title.lower() in content.lower():
                score += 40

            if score > best_score:
                best_score = score
                best = file_path

        return best

    def _collect_book_markdown_files(self, progress: Dict[str, Any]) -> list[Path]:
        book_dir = self._find_book_directory(progress)
        if not book_dir or not book_dir.exists():
            return []
        return sorted([p for p in book_dir.glob("*.md") if p.is_file()])

    def _find_book_directory(self, progress: Dict[str, Any]) -> Optional[Path]:
        if not self.reading_controller or not getattr(self.reading_controller, "reading_manager", None):
            return None

        reading_manager = self.reading_controller.reading_manager
        if self._manual_book_dir and self._manual_book_dir.exists():
            return self._manual_book_dir

        vault_root = Path(reading_manager.vault_path) / "01-LEITURAS"
        if not vault_root.exists():
            return None

        progress_book_id = str(progress.get("book_id") or progress.get("id") or "").strip()
        title = self._normalize_key(str(progress.get("title") or ""))
        author = ""

        try:
            if progress_book_id and progress_book_id in reading_manager.readings:
                author = reading_manager.readings[progress_book_id].author
        except Exception:
            author = ""

        target_author = self._normalize_key(author)

        for path in vault_root.glob("*/*"):
            if not path.is_dir():
                continue

            if title and title not in self._normalize_key(path.name):
                continue

            if target_author:
                parent_author = self._normalize_key(path.parent.name)
                if target_author not in parent_author and parent_author not in target_author:
                    continue

            return path

        # Fallback por book_id no frontmatter.
        if progress_book_id:
            for md_file in vault_root.glob("*/*/*.md"):
                if not md_file.is_file():
                    continue
                try:
                    text = md_file.read_text(encoding="utf-8", errors="ignore")
                except Exception:
                    continue
                if re.search(rf"(?m)^book_id:\s*{re.escape(progress_book_id)}\s*$", text):
                    return md_file.parent

        return None

    def _estimate_total_pages_in_dir(self, book_dir: Path) -> int:
        max_page = 0
        for md_file in book_dir.glob("*.md"):
            try:
                text = md_file.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue
            for page_str in re.findall(r"(?m)^---\s*Página\s+(\d+)\s*---\s*$", text):
                try:
                    max_page = max(max_page, int(page_str))
                except Exception:
                    continue
        return max_page

    def _extract_page_sections(self, text: str) -> Dict[int, str]:
        pattern = re.compile(r"(?m)^---\s*Página\s+(\d+)\s*---\s*$")
        matches = list(pattern.finditer(text))
        if not matches:
            return {}

        pages: Dict[int, str] = {}
        for idx, match in enumerate(matches):
            page_number = int(match.group(1))
            start = match.end()
            end = matches[idx + 1].start() if idx + 1 < len(matches) else len(text)
            page_text = text[start:end]
            page_text = page_text.lstrip("\n").rstrip()
            pages[page_number] = page_text

        return pages

    def _normalize_key(self, value: str) -> str:
        value = value.lower().strip()
        value = re.sub(r"\s+", " ", value)
        return value

    def _go_prev_pages(self):
        if self.left_page > 1:
            self.left_page = max(1, self.left_page - 2)
            self.current_page = self.left_page
            self.current_chapter_path = self.page_chapter_map.get(self.current_page)
            self._refresh_pages()
            self._sync_progress_realtime()

    def _go_next_pages(self):
        next_left = self.left_page + 2
        if self.total_pages > 0 and next_left > self.total_pages:
            return
        self.left_page = next_left
        self.current_page = self.left_page
        self.max_page_reached = max(self.max_page_reached, self.left_page)
        self.current_chapter_path = self.page_chapter_map.get(self.current_page)
        self._refresh_pages()
        self._sync_progress_realtime()

    def _on_fullscreen_left(self):
        if not self._fullscreen_mode:
            return
        self._go_prev_pages()

    def _on_fullscreen_right(self):
        if not self._fullscreen_mode:
            return
        self._go_next_pages()

    def _on_fullscreen_up(self):
        if not self._fullscreen_mode:
            return
        self._toggle_fullscreen_assistant_panel()

    def _on_fullscreen_down(self):
        if not self._fullscreen_mode:
            return
        self._open_pomodoro_dropdown()

    def _on_fullscreen_escape(self):
        if not self._fullscreen_mode:
            return
        self._set_fullscreen_mode(False)

    def _toggle_fullscreen_mode(self):
        self._set_fullscreen_mode(not self._fullscreen_mode)

    def _open_search_bar(self):
        self.search_bar.setVisible(True)
        self.search_input.setFocus()
        self.search_input.selectAll()

    def _hide_search_bar(self):
        self.search_bar.setVisible(False)
        self.search_input.clear()
        self._search_term = ""
        self._search_matches = []
        self._search_current_index = -1
        self._apply_search_highlights()

    def _on_search_term_changed(self, text: str):
        term = (text or "").strip()
        self._search_term = term
        self._search_matches = self._build_search_matches(term)
        self._search_current_index = -1
        if self._search_matches:
            self._search_current_index = self._preferred_search_index()
        self._update_search_controls()
        self._apply_search_highlights()

    def _build_search_matches(self, term: str) -> list[Dict[str, int]]:
        if len(term) < 2:
            return []

        pattern = re.compile(re.escape(term), re.IGNORECASE)
        matches: list[Dict[str, int]] = []
        for page_number in self._iter_searchable_pages():
            text = self._sanitize_page_display_text(self._build_page_content(page_number))
            if not text or (text.startswith("[") and text.endswith("]")):
                continue
            for match in pattern.finditer(text):
                matches.append(
                    {
                        "page": int(page_number),
                        "start": int(match.start()),
                        "end": int(match.end()),
                    }
                )
        return matches

    def _iter_searchable_pages(self) -> list[int]:
        if self.page_contents:
            return sorted(int(page) for page in self.page_contents.keys())
        if self.total_pages > 0:
            return list(range(1, int(self.total_pages) + 1))
        return [max(1, self.left_page), max(1, self.left_page) + 1]

    def _preferred_search_index(self) -> int:
        if not self._search_matches:
            return -1
        for idx, match in enumerate(self._search_matches):
            page = int(match.get("page", 0))
            if page < self.current_page:
                continue
            return idx
        return 0

    def _go_to_next_search_match(self):
        if not self._search_matches:
            return
        next_index = 0 if self._search_current_index < 0 else (self._search_current_index + 1) % len(self._search_matches)
        self._go_to_search_index(next_index)

    def _go_to_prev_search_match(self):
        if not self._search_matches:
            return
        prev_index = len(self._search_matches) - 1 if self._search_current_index < 0 else (self._search_current_index - 1) % len(self._search_matches)
        self._go_to_search_index(prev_index)

    def _go_to_search_index(self, index: int):
        if not self._search_matches:
            return
        bounded = max(0, min(index, len(self._search_matches) - 1))
        self._search_current_index = bounded
        match = self._search_matches[bounded]
        target_page = int(match.get("page", self.current_page))
        target_left = self._left_page_from_current(target_page)
        if target_left != self.left_page:
            self.left_page = target_left
            self.current_page = target_page
            self.current_chapter_path = self.page_chapter_map.get(self.current_page)
            self.max_page_reached = max(self.max_page_reached, self.current_page)
            self._refresh_pages()
            self._sync_progress_realtime()
        else:
            self.current_page = target_page
            self.current_chapter_path = self.page_chapter_map.get(self.current_page)
            self._apply_search_highlights()
        self._focus_current_search_match()
        self._update_search_controls()

    def _focus_current_search_match(self):
        current = self._current_search_match()
        if not current:
            return
        page = int(current["page"])
        editor = self.left_page_text if page == self.left_page else self.right_page_text
        cursor = editor.textCursor()
        cursor.setPosition(int(current["start"]))
        cursor.setPosition(int(current["end"]), QTextCursor.MoveMode.KeepAnchor)
        editor.setTextCursor(cursor)
        editor.ensureCursorVisible()

    def _current_search_match(self) -> Optional[Dict[str, int]]:
        if self._search_current_index < 0 or self._search_current_index >= len(self._search_matches):
            return None
        return self._search_matches[self._search_current_index]

    def _apply_search_highlights(self):
        self._apply_search_highlight_to_editor(self.left_page_text, self.left_page)
        self._apply_search_highlight_to_editor(self.right_page_text, self.left_page + 1)
        self._update_search_controls()

    def _apply_search_highlight_to_editor(self, editor: QTextEdit, page_number: int):
        if not self._search_matches:
            editor.setExtraSelections([])
            return

        selections: list[QTextEdit.ExtraSelection] = []
        current = self._current_search_match()
        for match in self._search_matches:
            if int(match.get("page", -1)) != int(page_number):
                continue
            selection = QTextEdit.ExtraSelection()
            cursor = editor.textCursor()
            cursor.setPosition(int(match["start"]))
            cursor.setPosition(int(match["end"]), QTextCursor.MoveMode.KeepAnchor)
            selection.cursor = cursor
            char_format = QTextCharFormat()
            is_active = bool(
                current
                and int(current.get("page", -1)) == int(match["page"])
                and int(current.get("start", -1)) == int(match["start"])
                and int(current.get("end", -1)) == int(match["end"])
            )
            char_format.setBackground(self._search_active_match_color if is_active else self._search_match_color)
            char_format.setForeground(QColor("#111111"))
            selection.format = char_format
            selections.append(selection)
        editor.setExtraSelections(selections)

    def _update_search_controls(self):
        total = len(self._search_matches)
        current = self._search_current_index + 1 if self._search_current_index >= 0 and total else 0
        self.search_counter_label.setText(f"{current}/{total}")
        enabled = total > 0
        self.search_prev_button.setEnabled(enabled)
        self.search_next_button.setEnabled(enabled)

    def _set_fullscreen_mode(self, enabled: bool):
        main_window = self.window()
        if enabled and self._fullscreen_mode:
            return
        if not enabled and not self._fullscreen_mode:
            return

        if enabled:
            self._assistant_visible_before_fullscreen = self.assistant_tabs.isVisible()
            self._window_was_fullscreen = bool(getattr(main_window, "isFullScreen", lambda: False)())
            self._window_was_maximized = bool(getattr(main_window, "isMaximized", lambda: False)())
            self._fullscreen_mode = True
            self.header_widget.setVisible(False)
            self.nav_widget.setVisible(False)
            self._assistant_expanded_in_fullscreen = False
            self.assistant_tabs.setMaximumHeight(0)
            self.assistant_tabs.setVisible(False)
            self.fullscreen_button.setText("🡽")
            self.fullscreen_button.setToolTip("Sair do fullscreen (ESC)")
            self._toggle_main_window_chrome(hidden=True)
            if hasattr(main_window, "showFullScreen") and not self._window_was_fullscreen:
                main_window.showFullScreen()
        else:
            self._hide_fullscreen_pomodoro_overlay(immediate=True)
            self._set_fullscreen_assistant_visible(False, animate=False)
            self._fullscreen_mode = False
            self.header_widget.setVisible(True)
            self.nav_widget.setVisible(True)
            self.assistant_tabs.setMaximumHeight(16777215)
            self.fullscreen_button.setText("⛶")
            self.fullscreen_button.setToolTip("Modo fullscreen (ESC para sair)")
            self._toggle_main_window_chrome(hidden=False)
            if self._assistant_visible_before_fullscreen:
                self.assistant_tabs.setVisible(True)
            if not self._window_was_fullscreen:
                if self._window_was_maximized and hasattr(main_window, "showMaximized"):
                    main_window.showMaximized()
                elif hasattr(main_window, "showNormal"):
                    main_window.showNormal()
            self._window_was_fullscreen = False
            self._window_was_maximized = False

        self._position_fullscreen_button()
        self._sync_fullscreen_overlays_geometry()

    def _toggle_main_window_chrome(self, hidden: bool):
        main_window = self.window()
        if hasattr(main_window, "title_bar"):
            main_window.title_bar.setVisible(not hidden)
        separator = main_window.findChild(QFrame, "title_separator") if hasattr(main_window, "findChild") else None
        if separator:
            separator.setVisible(not hidden)
        if hasattr(main_window, "statusBar") and main_window.statusBar():
            main_window.statusBar().setVisible(not hidden)

    def _open_pomodoro_dropdown(self):
        self._hide_review_done_toast()
        if not self._fullscreen_mode:
            return
        if self._pomodoro_overlay_visible:
            self._hide_fullscreen_pomodoro_overlay()
            return
        self._show_fullscreen_pomodoro_overlay()

    def _show_fullscreen_pomodoro_overlay(self):
        self._pomodoro_overlay_visible = True
        self.pomodoro_overlay.show()
        self.pomodoro_overlay.raise_()
        self._sync_fullscreen_overlays_geometry()

        start_pos = self.pomodoro_overlay_card.pos()
        end_pos = QPoint(start_pos.x(), 16)
        self.pomodoro_overlay_animation.stop()
        self.pomodoro_overlay_animation.setStartValue(start_pos)
        self.pomodoro_overlay_animation.setEndValue(end_pos)
        self.pomodoro_overlay_animation.start()

    def _hide_fullscreen_pomodoro_overlay(self, immediate: bool = False):
        if not self._pomodoro_overlay_visible and not self.pomodoro_overlay.isVisible():
            return
        self._pomodoro_overlay_visible = False
        self.pomodoro_overlay_animation.stop()

        if immediate:
            self.pomodoro_overlay.hide()
            self._sync_fullscreen_overlays_geometry()
            return

        start_pos = self.pomodoro_overlay_card.pos()
        end_pos = QPoint(start_pos.x(), -self.pomodoro_overlay_card.height())
        self.pomodoro_overlay_animation.setStartValue(start_pos)
        self.pomodoro_overlay_animation.setEndValue(end_pos)
        self.pomodoro_overlay_animation.start()
        QTimer.singleShot(self.pomodoro_overlay_animation.duration(), self.pomodoro_overlay.hide)

    def _on_pomodoro_overlay_mouse_press(self, event):
        if self.pomodoro_overlay_card.geometry().contains(event.pos()):
            event.ignore()
            return
        self._hide_fullscreen_pomodoro_overlay()
        event.accept()

    def _toggle_fullscreen_assistant_panel(self):
        self._hide_review_done_toast()
        if not self._fullscreen_mode:
            return
        self._set_fullscreen_assistant_visible(not self._assistant_expanded_in_fullscreen, animate=True)

    def _set_fullscreen_assistant_visible(self, visible: bool, animate: bool = True):
        if not self._fullscreen_mode:
            self.assistant_tabs.setVisible(visible)
            return

        target_height = 0 if not visible else self._assistant_target_height()
        self._assistant_expanded_in_fullscreen = visible
        if visible:
            self.assistant_tabs.setVisible(True)

        self.assistant_slide_animation.stop()
        self._assistant_should_hide_after_animation = not visible
        if animate:
            self.assistant_slide_animation.setStartValue(self.assistant_tabs.maximumHeight())
            self.assistant_slide_animation.setEndValue(target_height)
            self.assistant_slide_animation.start()
        else:
            self.assistant_tabs.setMaximumHeight(target_height)
            if not visible:
                self.assistant_tabs.setVisible(False)
            self._assistant_should_hide_after_animation = False

    def _assistant_target_height(self) -> int:
        panel_height = max(0, self.reading_panel.height())
        return max(180, min(420, int(panel_height * 0.38)))

    def _on_assistant_slide_finished(self):
        if self._assistant_should_hide_after_animation and self.assistant_tabs.maximumHeight() <= 0:
            self.assistant_tabs.setVisible(False)
        self._assistant_should_hide_after_animation = False

    def _hide_assistant_panels(self):
        if self._fullscreen_mode:
            self._set_fullscreen_assistant_visible(False, animate=True)
            return
        self.assistant_tabs.setVisible(False)

    def _toggle_pomodoro_from_timer(self):
        if not self.pomodoro:
            self.chat_status_label.setText("Pomodoro indisponível")
            return
        if self.pomodoro.is_running and not self.pomodoro.is_paused:
            self._pause_pomodoro()
        else:
            self._start_pomodoro()

    def _open_controls_menu(self):
        self._hide_review_done_toast()
        pos = self.controls_menu_button.mapToGlobal(self.controls_menu_button.rect().bottomLeft())
        self.controls_menu.exec(pos)

    def _apply_chat_preset(self, preset_label: str):
        if not self.glados_controller:
            return
        self.glados_controller.set_generation_preset(preset_label)

    def _set_chat_locked(self, locked: bool):
        self.chat_summary_button.setEnabled(not locked)
        self.chat_mindmap_button.setEnabled(not locked)
        self.chat_mark_review_button.setEnabled(not locked)
        self.chat_preset_combo.setEnabled(not locked)

    def _handle_mindmap_button_clicked(self):
        if self._review_generation_active:
            QMessageBox.information(self, "Processamento em andamento", "Aguarde a geração atual terminar.")
            return

        canvas_path = self._review_target_path("mapa-mental-canva", self.MINDMAPS_DIR)
        if not canvas_path:
            QMessageBox.warning(self, "Vault indisponível", "Não foi possível localizar o diretório do vault.")
            return

        if not canvas_path.exists():
            self._create_base_mindmap_canvas(canvas_path, ask_confirmation=True, show_feedback=True)
            return

        self._start_mindmap_incremental_generation(
            canvas_path,
            ask_confirmation=True,
            show_feedback=True,
        )

    def _create_base_mindmap_canvas(
        self,
        canvas_path: Path,
        ask_confirmation: bool = True,
        show_feedback: bool = True,
    ) -> bool:
        if not self.reading_controller or not getattr(self.reading_controller, "reading_manager", None):
            if show_feedback:
                QMessageBox.warning(self, "Sessão sem livro", "Não foi possível identificar o livro atual.")
            return False

        progress = self._get_progress(self.current_book_id) if self.current_book_id else {}
        book_dir = self._find_book_directory(progress)
        preferred_book_note = self._find_primary_book_note(progress) if progress else None
        sources = self.mindmap_review_module.find_base_sources(
            book_dir=book_dir,
            preferred_book_note=preferred_book_note,
        )

        info_note_status = "OK" if sources.book_note else "FALTANDO"
        pretext_status = "OK" if sources.pretext_note else "FALTANDO"
        details = [
            "Ainda não existe canvas base para esta obra.",
            "",
            f"Destino: {self._display_relative_path(canvas_path)}",
            "",
            "Arquivos para criação do canvas base:",
            f"- Nota principal do livro: {info_note_status}",
            f"- Nota de pré-texto: {pretext_status}",
            "",
            "Deseja criar o canvas base agora?",
        ]
        if sources.book_note:
            details.extend(["  arquivo nota do livro:", f"  {self._display_relative_path(sources.book_note)}"])
        if sources.pretext_note:
            details.extend(["  arquivo pré-texto:", f"  {self._display_relative_path(sources.pretext_note)}"])

        if ask_confirmation:
            confirm = QMessageBox.question(
                self,
                "Canvas base não encontrado",
                "\n".join(details),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes,
            )
            if confirm != QMessageBox.StandardButton.Yes:
                return False

        if not sources.book_note and not sources.pretext_note:
            if show_feedback:
                QMessageBox.warning(
                    self,
                    "Arquivos ausentes",
                    "Não encontrei nota do livro nem nota de pré-texto para criar o canvas base.",
                )
            return False

        vault_root = Path(self.reading_controller.reading_manager.vault_path)
        canvas_payload = self.mindmap_review_module.build_base_canvas(
            vault_root=vault_root,
            book_title=self.current_book_title,
            book_note=sources.book_note,
            pretext_note=sources.pretext_note,
        )
        filename = self._build_review_filename("mapa-mental-canva", self.MINDMAPS_DIR)
        note_path = self._write_note_to_personal(
            self.mindmap_review_module.dump_canvas_json(canvas_payload) + "\n",
            "mapa-mental-base",
            target_dir=self.MINDMAPS_DIR,
            filename_override=filename,
            overwrite_existing=True,
        )
        if not note_path:
            if show_feedback:
                QMessageBox.warning(
                    self,
                    "Erro ao criar canvas",
                    "Não foi possível salvar o canvas base no diretório de mapas mentais.",
                )
            return False

        self.chat_history.append(f"Sistema: canvas base criado em {note_path.name}.")
        if show_feedback:
            QMessageBox.information(
                self,
                "Canvas base criado",
                f"Canvas salvo em {self.MINDMAPS_DIR}/{note_path.name}.",
            )
        return True

    def _start_mindmap_incremental_generation(
        self,
        canvas_path: Path,
        ask_confirmation: bool = True,
        show_feedback: bool = True,
    ) -> bool:
        active_chapter_path = self._resolve_active_chapter_path()
        user_notes = self._collect_chapter_user_notes(active_chapter_path, max_items=4, max_chars=320)
        summary_path, _summary_text = self._load_summary_note_for_current_chapter(max_chars=900)

        chapter_exists = bool(active_chapter_path and active_chapter_path.exists())
        user_notes_exists = bool(user_notes)
        summary_exists = bool(summary_path and summary_path.exists())
        missing_items: list[str] = []
        status_lines = [
            "Arquivos usados para adicionar conteúdo ao mapa mental:",
            f"- Capítulo atual: {'OK' if chapter_exists else 'FALTANDO'}",
            f"- Notas do usuário do capítulo: {'OK' if user_notes_exists else 'FALTANDO'}",
            f"- Resumo LLM do capítulo: {'OK' if summary_exists else 'FALTANDO'}",
        ]
        if chapter_exists and active_chapter_path:
            status_lines.append(f"  arquivo capítulo: {self._display_relative_path(active_chapter_path)}")
        else:
            missing_items.append("capítulo atual")
        if user_notes_exists:
            status_lines.append(f"  notas encontradas: {len(user_notes)}")
        else:
            missing_items.append("notas do usuário")
        if summary_exists and summary_path:
            status_lines.append(f"  arquivo resumo: {self._display_relative_path(summary_path)}")
        else:
            missing_items.append("resumo LLM")
        status_lines.append("")
        if missing_items:
            status_lines.append("Faltando: " + ", ".join(missing_items) + ".")
            status_lines.append("")
        status_lines.append("Deseja continuar com a atualização do mapa mental?")

        if ask_confirmation:
            confirm = QMessageBox.question(
                self,
                "Atualizar mapa mental da obra",
                "\n".join(status_lines),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes,
            )
            if confirm != QMessageBox.StandardButton.Yes:
                return False

        if not chapter_exists and not user_notes_exists and not summary_exists:
            if show_feedback:
                QMessageBox.warning(
                    self,
                    "Sem conteúdo novo",
                    "Nenhum dos arquivos necessários foi encontrado para atualizar o mapa mental.",
                )
            return False

        self.chat_status_label.setText("Atualizando mapa mental localmente...")
        self.chat_history.append("Sistema: atualização de mapa mental iniciada (modo local, sem LLM).")

        if not self.reading_controller or not getattr(self.reading_controller, "reading_manager", None):
            if show_feedback:
                QMessageBox.warning(self, "Vault indisponível", "Não foi possível localizar o diretório do vault.")
            self.chat_status_label.setText("Falha ao atualizar mapa mental")
            return False

        vault_root = Path(self.reading_controller.reading_manager.vault_path)
        existing_payload = self.mindmap_review_module.load_canvas_payload(canvas_path)
        merge_result = self.mindmap_review_module.merge_incremental_canvas(
            payload=existing_payload,
            vault_root=vault_root,
            book_title=self.current_book_title,
            chapter_path=active_chapter_path if chapter_exists else None,
            user_notes=user_notes,
            summary_path=summary_path if summary_exists else None,
        )
        serialized = self.mindmap_review_module.dump_canvas_json(merge_result.payload) + "\n"
        saved_path = self._write_note_to_personal(
            serialized,
            "mapa-mental-incremental",
            target_dir=self.MINDMAPS_DIR,
            filename_override=canvas_path.name,
            overwrite_existing=True,
        )
        if not saved_path:
            if show_feedback:
                QMessageBox.warning(
                    self,
                    "Erro ao atualizar canvas",
                    "Não foi possível salvar a atualização local do mapa mental.",
                )
            self.chat_status_label.setText("Falha ao atualizar mapa mental")
            return False

        self.chat_history.append(
            "Sistema: mapa mental atualizado localmente "
            f"(+{merge_result.added_nodes} nó(s), +{merge_result.added_edges} conexão(ões))."
        )
        self.chat_status_label.setText("Mapa mental atualizado")
        return True

    def _auto_update_mindmap(self, reason: str):
        if self._review_generation_active:
            self.chat_history.append(
                f"Sistema: atualização automática do mapa mental adiada ({reason}) porque a revisão está ativa."
            )
            return

        canvas_path = self._review_target_path("mapa-mental-canva", self.MINDMAPS_DIR)
        if not canvas_path:
            return

        if not canvas_path.exists():
            created = self._create_base_mindmap_canvas(
                canvas_path,
                ask_confirmation=False,
                show_feedback=False,
            )
            if not created:
                return

        self._start_mindmap_incremental_generation(
            canvas_path,
            ask_confirmation=False,
            show_feedback=False,
        )

    def _collect_chapter_user_notes(
        self,
        chapter_path: Optional[Path],
        max_items: int = 6,
        max_chars: int = 320,
    ) -> list[Dict[str, str]]:
        if not chapter_path or not chapter_path.exists():
            return []

        chapter_text = chapter_path.read_text(encoding="utf-8", errors="ignore")
        links = re.findall(r"\[\[([^\]\|#]+)(?:\|[^\]]+)?(?:#[^\]]+)?\]\]", chapter_text)
        if not links:
            return []

        user_notes: list[Dict[str, str]] = []
        seen = set()
        for target in links:
            note_path = self._resolve_wikilink_to_path(target.strip())
            if not note_path or not note_path.exists() or not note_path.is_file():
                continue
            display_path = self._display_relative_path(note_path)
            if not display_path.startswith(f"{self.USER_NOTES_DIR}/") and display_path != self.USER_NOTES_DIR:
                continue
            key = str(note_path).lower()
            if key in seen:
                continue
            seen.add(key)
            try:
                content = note_path.read_text(encoding="utf-8", errors="ignore").strip()
            except Exception:
                continue
            snippet = self._truncate_text(content, max_chars)
            user_notes.append(
                {
                    "title": note_path.stem,
                    "path": str(note_path),
                    "display_path": display_path,
                    "content": snippet,
                }
            )
            if len(user_notes) >= max_items:
                break
        return user_notes

    def _load_summary_note_for_current_chapter(self, max_chars: int = 900) -> tuple[Optional[Path], str]:
        summary_path = self._review_target_path("resumo", self.REVIEW_DIR)
        if not summary_path or not summary_path.exists():
            return None, ""
        try:
            content = summary_path.read_text(encoding="utf-8", errors="ignore").strip()
        except Exception:
            return None, ""
        if not content:
            return summary_path, ""
        material = content
        marker = "## Material"
        marker_idx = content.find(marker)
        if marker_idx >= 0:
            material = content[marker_idx + len(marker) :].strip()
        return summary_path, self._truncate_text(material, max_chars)

    def _start_review_generation(self):
        if self._review_generation_active:
            return
        if not self.glados_controller:
            self.chat_history.append("Sistema: LLM indisponível para gerar revisão.")
            return

        self._hide_review_done_toast()
        review_plan = self._open_review_generation_dialog()
        if not review_plan:
            return

        self._review_chapter_difficulty = int(review_plan.get("chapter_difficulty", 3))
        self._review_context_note_selection = list(review_plan.get("selected_notes", []))
        review_context = self._build_review_generation_context(
            selected_note_entries=self._review_context_note_selection,
            chapter_difficulty=self._review_chapter_difficulty,
        )
        if not review_context:
            self.chat_history.append("Sistema: Contexto insuficiente para revisão.")
            return

        selected_preset = self.chat_preset_combo.currentText()
        self._apply_chat_preset(selected_preset)
        self._review_backend_metadata = {
            "workflow": "review_generation",
            "book_title": self.current_book_title,
            "chapter_path": str(self.current_chapter_path) if self.current_chapter_path else "",
            "chapter_difficulty": self._review_chapter_difficulty,
            "selected_context_count": len(self._review_context_note_selection),
            "selected_context_paths": [
                n.get("path", "")
                for n in self._review_context_note_selection
                if isinstance(n, dict) and n.get("path")
            ],
            "estimated_context_chars": len(review_context),
        }
        self._review_context_payload = review_context
        self._review_queue = [
            {"slug": "resumo", "title": "Resumo", "instruction": self._review_instruction_summary()},
        ]
        self.chat_status_label.setText("Revisão em processamento...")
        self.chat_history.append(
            f"Sistema: revisão iniciada com preset '{selected_preset}' (material: resumo)."
        )
        self._review_current_task_index = 0
        self._review_inflight_task = None
        self._review_waiting_cache_clear = False
        self._review_llm_inflight = False
        self._review_started_monotonic = time.monotonic()
        self._review_summary_saved_in_run = False
        self._review_generation_active = True
        self._set_chat_locked(True)
        self.review_step_label.setVisible(True)
        self.review_overall_progress.setVisible(True)
        self.review_item_progress.setVisible(True)
        self.review_overall_progress.setValue(0)
        self.review_item_progress.setValue(0)
        self._run_next_review_task()

    def _run_next_review_task(self):
        if not self._review_generation_active:
            return

        if self._review_current_task_index >= len(self._review_queue):
            self._finish_review_generation()
            return

        task = self._review_queue[self._review_current_task_index]
        if "retry_count" not in task:
            task["retry_count"] = 0
        self._review_inflight_task = task
        self.review_step_label.setText(
            f"Processando {self._review_current_task_index + 1}/{len(self._review_queue)}: {task['title']}"
        )
        overall = int((self._review_current_task_index / max(len(self._review_queue), 1)) * 100)
        self.review_overall_progress.setValue(overall)
        self.review_item_progress.setRange(0, 100)
        self.review_item_progress.setValue(5)
        self._review_waiting_cache_clear = True
        self._review_llm_inflight = False
        self.chat_status_label.setText("Limpando cache para próximo item...")
        self.glados_controller.update_memory("clear_responses")

    def _start_review_llm_task(self):
        task = self._review_inflight_task
        if not self._review_generation_active or not task:
            return
        self._review_waiting_cache_clear = False
        self._review_llm_inflight = True
        self.review_item_progress.setRange(0, 100)
        self.review_item_progress.setValue(30)
        self._tune_generation_for_review_task(task)

        prompt = self._build_review_prompt(task)
        # Sem contexto semântico adicional para não estourar n_ctx.
        self.glados_controller.ask_glados(
            prompt,
            False,
            "Helio",
            request_metadata=self._build_review_task_backend_metadata(task),
        )

    def _tune_generation_for_review_task(self, task: Dict[str, Any]):
        backend = getattr(self.glados_controller, "backend", None) if self.glados_controller else None
        if not backend or not hasattr(backend, "set_generation_params"):
            return
        slug = str(task.get("slug") or "")
        try:
            if slug == "resumo":
                backend.set_generation_params(
                    temperature=0.34,
                    top_p=0.90,
                    repeat_penalty=1.12,
                    max_tokens=260,
                )
        except Exception:
            pass

    def _build_review_task_backend_metadata(self, task: Dict[str, Any]) -> Dict[str, Any]:
        payload = dict(self._review_backend_metadata or {})
        payload.update(
            {
                "task_slug": task.get("slug", ""),
                "task_title": task.get("title", ""),
                "retry_count": int(task.get("retry_count", 0)),
                "timestamp": datetime.now().isoformat(),
            }
        )
        return payload

    def _open_review_generation_dialog(self) -> Optional[Dict[str, Any]]:
        chapter_context = self._build_chapter_context(
            max_current_chars=700,
            max_prev_chapters=1,
            max_prev_chars=240,
        )
        if not chapter_context:
            self.chat_history.append(
                "Sistema: não foi possível montar contexto do capítulo atual para revisão."
            )
            self.chat_status_label.setText("Sem contexto de capítulo para revisão")
            return None

        active_chapter_path = self._resolve_active_chapter_path()
        chapter_name = active_chapter_path.name if active_chapter_path else "Capítulo atual"
        related_notes = self._load_related_note_entries_for_current_chapter(max_items=8, max_chars=320)
        max_context_chars = self._estimate_llm_context_capacity_chars()

        dialog = ReviewGenerationDialog(
            chapter_name=chapter_name,
            default_difficulty=self._review_chapter_difficulty,
            default_notes=related_notes,
            base_context_chars=len(chapter_context),
            max_context_chars=max_context_chars,
            search_callback=self._search_notes_for_review_dialog,
            parent=self,
        )
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return None
        return dialog.get_values()

    def _resolve_active_chapter_path(self) -> Optional[Path]:
        if self.current_chapter_path and self.current_chapter_path.exists():
            return self.current_chapter_path

        candidates = [
            self.page_chapter_map.get(self.current_page),
            self.page_chapter_map.get(self.left_page),
            self.page_chapter_map.get(max(1, self.current_page - 1)),
            self.page_chapter_map.get(self.current_page + 1),
        ]
        for candidate in candidates:
            if candidate and candidate.exists():
                return candidate

        for item in self.chapter_notes:
            start_page = int(item.get("start_page") or 0)
            end_page = int(item.get("end_page") or 0)
            if start_page <= self.current_page <= end_page:
                path = item.get("path")
                if path and Path(path).exists():
                    return Path(path)

        return None

    def _estimate_llm_context_capacity_chars(self) -> int:
        n_ctx = 2048
        try:
            backend = getattr(self.glados_controller, "backend", None)
            model = getattr(backend, "model", None)
            config = getattr(model, "config", None)
            if config and getattr(config, "n_ctx", None):
                n_ctx = int(config.n_ctx)
        except Exception:
            n_ctx = 2048
        return max(2048, int(n_ctx * 4))

    def _search_notes_for_review_dialog(self, query: str, limit: int = 35) -> list[Dict[str, str]]:
        vault_root = self._get_vault_root()
        if not vault_root or not vault_root.exists():
            return []

        term = (query or "").strip().lower()
        if len(term) < 2:
            return []

        md_files = [p for p in vault_root.rglob("*.md") if p.is_file()]
        title_matches: list[tuple[int, Path]] = []
        content_candidates: list[Path] = []
        for file_path in md_files:
            try:
                relative = str(file_path.relative_to(vault_root)).replace("\\", "/")
            except Exception:
                relative = file_path.name
            rel_lower = relative.lower()
            title_lower = file_path.stem.lower()

            score = 0
            if term in title_lower:
                score += 8
            if term in rel_lower:
                score += 4

            if score > 0:
                title_matches.append((score, file_path))
            else:
                content_candidates.append(file_path)

        title_matches.sort(key=lambda item: (-item[0], str(item[1]).lower()))
        selected_paths = [path for _, path in title_matches[:limit]]

        if len(selected_paths) < limit:
            for file_path in content_candidates:
                try:
                    text = file_path.read_text(encoding="utf-8", errors="ignore")
                except Exception:
                    continue
                idx = text.lower().find(term)
                if idx < 0:
                    continue
                selected_paths.append(file_path)
                if len(selected_paths) >= limit:
                    break

        results: list[Dict[str, str]] = []
        seen = set()
        for file_path in selected_paths:
            key = str(file_path)
            if key in seen:
                continue
            seen.add(key)
            try:
                text = file_path.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                text = ""
            snippet = self._build_search_snippet(text, term, max_chars=260)
            display_path = ""
            try:
                display_path = str(file_path.relative_to(vault_root)).replace("\\", "/")
            except Exception:
                display_path = file_path.name
            results.append(
                {
                    "path": str(file_path),
                    "display_path": display_path,
                    "title": file_path.stem,
                    "content": snippet,
                    "source": "Busca manual",
                    "estimated_chars": len(snippet) + 80,
                }
            )
        return results[:limit]

    def _build_search_snippet(self, text: str, term: str, max_chars: int = 260) -> str:
        clean = (text or "").strip()
        if not clean:
            return ""
        idx = clean.lower().find(term.lower())
        if idx < 0:
            return self._truncate_text(clean, max_chars)
        start = max(0, idx - int(max_chars * 0.35))
        end = min(len(clean), idx + int(max_chars * 0.65))
        snippet = clean[start:end].replace("\n", " ").strip()
        if start > 0:
            snippet = "..." + snippet
        if end < len(clean):
            snippet = snippet + "..."
        return self._truncate_text(snippet, max_chars)

    def _get_vault_root(self) -> Optional[Path]:
        if not self.reading_controller or not getattr(self.reading_controller, "reading_manager", None):
            return None
        return Path(self.reading_controller.reading_manager.vault_path)

    def _safe_prompt_char_budget(self, reserve_tokens: int = 760) -> int:
        n_ctx_tokens = 2048
        try:
            backend = getattr(self.glados_controller, "backend", None)
            model = getattr(backend, "model", None)
            config = getattr(model, "config", None)
            if config and getattr(config, "n_ctx", None):
                n_ctx_tokens = int(config.n_ctx)
        except Exception:
            n_ctx_tokens = 2048

        available_tokens = max(420, n_ctx_tokens - max(200, reserve_tokens))
        estimated_chars = int(available_tokens * 3.0)
        return max(1200, min(estimated_chars, 5200))

    def _is_gpu_only_runtime(self) -> bool:
        try:
            backend = getattr(self.glados_controller, "backend", None)
            if not backend:
                return False
            mode = str(getattr(backend, "runtime_info", {}).get("device_mode", "") or "").lower()
            if mode:
                return mode == "gpu_only"
            model = getattr(backend, "model", None)
            config = getattr(model, "config", None)
            return str(getattr(config, "device_mode", "") or "").lower() == "gpu_only"
        except Exception:
            return False

    def _compact_context_payload(self, max_chars: int) -> str:
        payload = (self._review_context_payload or "").strip()
        if not payload:
            return ""
        return self._truncate_text(payload, max(500, max_chars))

    def _build_review_prompt(self, task: Dict[str, Any]) -> str:
        hard_limit = self._safe_prompt_char_budget(reserve_tokens=760)
        context_budget = max(700, hard_limit - 1050)
        compact_context = self._compact_context_payload(context_budget)
        base_lines = [
            f"{task['instruction']}",
            "",
            f"Contexto consolidado:\n{compact_context}",
            "",
        ]

        base_lines.append("Responda apenas com o material solicitado, em markdown limpo.")
        return self._trim_prompt_for_context_window("\n".join(base_lines), hard_limit_chars=hard_limit)

    def _build_review_repair_prompt(self, task: Dict[str, Any], raw_text: str, reason: str) -> str:
        slug = task.get("slug", "")
        retry_count = int(task.get("retry_count", 0))
        retry_limit = int(task.get("retry_limit") or self._review_retry_max_attempts)
        compact_mode = "context window" in reason.lower() or "janela de contexto" in reason.lower()
        hard_limit = self._safe_prompt_char_budget(reserve_tokens=860 if compact_mode else 760)
        compact_context = self._compact_context_payload(750 if compact_mode else max(800, hard_limit - 1200))
        compact_raw = self._truncate_text((raw_text or "").strip(), 700 if compact_mode else 1000)
        header = [
            f"Correção de formato (tentativa {retry_count}/{retry_limit}) para '{task.get('title', 'item')}'.",
            f"Falha detectada: {reason}",
            "",
        ]

        if slug == "flashcards":
            body = [
                "Reescreva para o formato EXATO abaixo, com 12 blocos válidos:",
                "### Flashcard N",
                "Frente: ...",
                "Verso: ...",
                "Não inclua texto antes/depois dos 12 blocos.",
                "Evite cartões triviais de metadado (título/autor/página/capítulo) e não use placeholders genéricos.",
                "",
                f"Contexto consolidado:\n{compact_context}",
                "",
                f"Resposta inválida anterior:\n{compact_raw}",
            ]
            return self._trim_prompt_for_context_window("\n".join(header + body), hard_limit_chars=hard_limit)

        if slug == "resumo":
            body = [
                "Reescreva no formato EXATO abaixo, sem texto extra e sem raciocínio interno:",
                "## Síntese",
                "<texto>",
                "## Conceitos-chave",
                "- item",
                "## Ligações entre capítulos",
                "<texto>",
                "## Pontos de dúvida",
                "- item",
                "",
                f"Contexto consolidado:\n{compact_context}",
                "",
                f"Resposta inválida anterior:\n{compact_raw}",
            ]
            return self._trim_prompt_for_context_window("\n".join(header + body), hard_limit_chars=hard_limit)

        body = [
            "Reescreva somente no formato solicitado inicialmente.",
            "Sem comentários extras.",
            "",
            f"Resposta inválida anterior:\n{compact_raw}",
        ]
        return self._trim_prompt_for_context_window("\n".join(header + body), hard_limit_chars=hard_limit)

    def _retry_review_task_with_format_repair(self, task: Dict[str, Any], raw_text: str, reason: str) -> bool:
        retry_count = int(task.get("retry_count", 0))
        retry_limit = self._review_retry_max_attempts
        if retry_count >= retry_limit:
            return False

        task["retry_count"] = retry_count + 1
        task["retry_limit"] = retry_limit
        self._review_waiting_cache_clear = False
        self._review_llm_inflight = True
        self.review_item_progress.setRange(0, 100)
        self.review_item_progress.setValue(max(self.review_item_progress.value(), 45))
        self.chat_status_label.setText("Corrigindo formato do item...")

        repair_prompt = self._build_review_repair_prompt(task, raw_text, reason)
        self.chat_history.append(
            f"Sistema: tentando corrigir formato de '{task.get('title', 'item')}' ({task['retry_count']}/{retry_limit})."
        )
        self.glados_controller.ask_glados(
            repair_prompt,
            False,
            "Helio",
            request_metadata=self._build_review_task_backend_metadata(task),
        )
        return True

    def _finish_review_generation(
        self,
        clear_context: bool = True,
    ):
        elapsed_seconds = 0.0
        if self._review_started_monotonic is not None:
            elapsed_seconds = max(0.0, time.monotonic() - self._review_started_monotonic)

        self._review_generation_active = False
        self._review_inflight_task = None
        self._review_waiting_cache_clear = False
        self._review_llm_inflight = False
        self._set_chat_locked(False)
        self.review_step_label.setText("Etapa concluída.")
        self.review_overall_progress.setRange(0, 100)
        self.review_item_progress.setRange(0, 100)
        self.review_overall_progress.setValue(100)
        self.review_item_progress.setValue(100)
        self.chat_status_label.setText("LLM pronta")

        self.chat_history.append("Sistema: materiais de revisão concluídos.")
        self.chat_history.append(
            f"Sistema: tempo total de processamento: {self._format_processing_duration(elapsed_seconds)}."
        )

        if self._review_summary_saved_in_run:
            should_create_questions = QMessageBox.question(
                self,
                "Resumo concluído",
                "Resumo salvo com sucesso.\nDeseja criar perguntas manuais agora?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes,
            )
            if should_create_questions == QMessageBox.StandardButton.Yes:
                self._open_manual_questions_dialog()

        self._review_started_monotonic = None
        self._review_context_payload = "" if clear_context else self._review_context_payload
        self._review_backend_metadata = {}
        self._review_queue = []
        self._review_summary_saved_in_run = False
        if self._fullscreen_mode:
            self._show_review_done_toast()

    def _open_manual_questions_dialog(self):
        chapter_path = self._resolve_active_chapter_path()
        chapter_name = chapter_path.name if chapter_path else "Capítulo atual"
        dialog = ManualQuestionsDialog(chapter_name, self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        entries = dialog.get_values()
        if not entries:
            QMessageBox.information(
                self,
                "Sem conteúdo",
                "Nenhuma pergunta/resposta válida foi informada.",
            )
            return

        note_path = self._save_manual_questions_to_vault(entries)
        if note_path:
            self._append_note_link_to_current_chapter(note_path)
            self._register_manual_questions_with_review_system(entries, note_path)
            self.chat_history.append(f"Sistema: perguntas manuais salvas em {note_path.name}")
            self._auto_update_mindmap("novo material de perguntas manuais")
            QMessageBox.information(
                self,
                "Perguntas salvas",
                f"Perguntas manuais salvas em {self.REVIEW_DIR}/{note_path.name}",
            )
        else:
            QMessageBox.warning(
                self,
                "Erro ao salvar",
                "Não foi possível salvar as perguntas manuais no vault.",
            )

    def _save_manual_questions_to_vault(self, entries: list[Dict[str, str]]) -> Optional[Path]:
        chapter_title = self._current_chapter_title_for_review()
        lines = [
            f"# Revisão - Perguntas manuais - {self.current_book_title}",
            "",
            f"- Data: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            f"- Livro: {self.current_book_title}",
            f"- Capítulo: {chapter_title}",
            f"- Dificuldade do capítulo (1-5): {int(self._review_chapter_difficulty or 3)}",
            f"- Página atual: {self.current_page}",
            "- Tipo: Perguntas manuais",
            "",
            "## Material",
            "",
        ]
        valid_entries = 0
        for idx, item in enumerate(entries, start=1):
            question = item.get("question", "").strip()
            answer = item.get("answer", "").strip()
            if not question or not answer:
                continue
            valid_entries += 1
            lines.extend(
                [
                    f"### Pergunta {idx}",
                    f"Pergunta: {question}",
                    f"Resposta: {answer}",
                    "",
                ]
            )

        if valid_entries <= 0:
            return None

        filename = self._build_review_filename("perguntas-manual", self.REVIEW_DIR)
        return self._write_note_to_personal(
            "\n".join(lines).strip() + "\n",
            "revisao-perguntas-manual",
            target_dir=self.REVIEW_DIR,
            filename_override=filename,
        )

    def _abort_review_generation(self, reason: str):
        elapsed_seconds = 0.0
        if self._review_started_monotonic is not None:
            elapsed_seconds = max(0.0, time.monotonic() - self._review_started_monotonic)

        self._review_generation_active = False
        self._review_inflight_task = None
        self._review_waiting_cache_clear = False
        self._review_llm_inflight = False
        self._review_started_monotonic = None
        self._review_context_payload = ""
        self._review_backend_metadata = {}
        self._set_chat_locked(False)
        self.review_step_label.setText("Revisão interrompida.")
        self.review_overall_progress.setRange(0, 100)
        self.review_item_progress.setRange(0, 100)
        self.review_item_progress.setValue(0)
        self.chat_status_label.setText("Revisão interrompida")
        self.chat_history.append(f"Sistema: revisão interrompida ({reason}).")
        self.chat_history.append(
            f"Sistema: tempo total de processamento: {self._format_processing_duration(elapsed_seconds)}."
        )

    def _format_processing_duration(self, elapsed_seconds: float) -> str:
        total_seconds = max(0, int(round(elapsed_seconds)))
        minutes, seconds = divmod(total_seconds, 60)
        hours, minutes = divmod(minutes, 60)
        if hours > 0:
            return f"{hours}h {minutes:02d}m {seconds:02d}s"
        if minutes > 0:
            return f"{minutes}m {seconds:02d}s"
        return f"{seconds}s"

    def _show_review_done_toast(self):
        self.review_done_toast_label.setText("Materiais de revisão prontos")
        self.review_done_toast.show()
        self._position_review_done_toast()

    def _clear_llm_cache_after_material(self, material_label: str):
        if not self.glados_controller:
            return
        try:
            self.glados_controller.update_memory("clear_all")
            self.chat_history.append(
                f"Sistema: cache da LLM limpo após gerar {material_label}."
            )
        except Exception as exc:
            self.chat_history.append(
                f"Sistema: falha ao limpar cache da LLM após gerar {material_label}: {exc}"
            )

    def _hide_review_done_toast(self):
        if self.review_done_toast.isVisible():
            self.review_done_toast.hide()

    def _on_llm_response(self, payload: Dict[str, Any]):
        text = payload.get("text", "")
        if self._review_generation_active:
            self._handle_review_generation_response(text)
            return
        if text:
            self.chat_history.append(f"GLaDOS: {text}")
            if self._pending_note_request:
                self._handle_pending_note_response(text, self._pending_note_request)
                self._pending_note_request = None
        self.chat_status_label.setText("LLM pronta")

    def _handle_review_generation_response(self, text: str):
        task = self._review_inflight_task
        if not task:
            return

        if self._is_backend_unavailable_response(text):
            self._abort_review_generation("LLM indisponível no backend atual (gpu_only)")
            return

        if self._is_llm_failure_response(text):
            if self._retry_review_task_with_format_repair(
                task,
                text,
                "LLM retornou erro/falha de geração",
            ):
                return
            self.chat_history.append(f"Sistema: resposta inválida para '{task['title']}', item pulado.")
            self.review_item_progress.setRange(0, 100)
            self.review_item_progress.setValue(0)
            self._review_current_task_index += 1
            self._review_inflight_task = None
            self._review_llm_inflight = False
            overall = int((self._review_current_task_index / max(len(self._review_queue), 1)) * 100)
            self.review_overall_progress.setValue(overall)
            QTimer.singleShot(120, self._run_next_review_task)
            return

        self.review_item_progress.setRange(0, 100)
        self.review_item_progress.setValue(100)
        target_dir = self.MINDMAPS_DIR if "mapa-mental" in task["slug"] else self.REVIEW_DIR
        filename = self._build_review_filename(task["slug"], target_dir)
        note_path: Optional[Path]
        if task["slug"] == "resumo":
            normalized_summary, reason = self._normalize_summary_response(text)
            if not normalized_summary:
                if self._retry_review_task_with_format_repair(task, text, reason):
                    return
                self.chat_history.append(
                    f"Sistema: resumo rejeitado ({reason}). Material não foi salvo no vault."
                )
                self.review_item_progress.setValue(0)
                self._review_current_task_index += 1
                self._review_inflight_task = None
                self._review_llm_inflight = False
                overall = int((self._review_current_task_index / max(len(self._review_queue), 1)) * 100)
                self.review_overall_progress.setValue(overall)
                QTimer.singleShot(120, self._run_next_review_task)
                return

            safe_title = f"Revisão - {task['title']} - {self.current_book_title}"
            chapter_title = self._current_chapter_title_for_review()
            note_content = [
                f"# {safe_title}",
                "",
                f"- Data: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                f"- Livro: {self.current_book_title}",
                f"- Capítulo: {chapter_title}",
                f"- Dificuldade do capítulo (1-5): {int(self._review_chapter_difficulty or 3)}",
                f"- Página atual: {self.current_page}",
                f"- Tipo: {task['title']}",
                "",
                "## Material",
                normalized_summary.strip(),
                "",
            ]
            note_path = self._write_note_to_personal(
                "\n".join(note_content),
                f"revisao-{task['slug']}",
                target_dir=target_dir,
                filename_override=filename,
            )
        elif task["slug"] == "flashcards":
            normalized_flashcards, reason = self._normalize_flashcards_response(text)
            if not normalized_flashcards:
                if self._retry_review_task_with_format_repair(task, text, reason):
                    return
                self.chat_history.append(
                    f"Sistema: flashcards rejeitados ({reason}). Material não foi salvo no vault."
                )
                self.review_item_progress.setValue(0)
                self._review_current_task_index += 1
                self._review_inflight_task = None
                self._review_llm_inflight = False
                overall = int((self._review_current_task_index / max(len(self._review_queue), 1)) * 100)
                self.review_overall_progress.setValue(overall)
                QTimer.singleShot(120, self._run_next_review_task)
                return

            safe_title = f"Revisão - {task['title']} - {self.current_book_title}"
            note_content = [
                f"# {safe_title}",
                "",
                f"- Data: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                f"- Livro: {self.current_book_title}",
                f"- Página atual: {self.current_page}",
                f"- Tipo: {task['title']}",
                "",
                "## Material",
                normalized_flashcards.strip(),
                "",
            ]
            note_path = self._write_note_to_personal(
                "\n".join(note_content),
                f"revisao-{task['slug']}",
                target_dir=target_dir,
                filename_override=filename,
            )
        else:
            safe_title = f"Revisão - {task['title']} - {self.current_book_title}"
            note_content = [
                f"# {safe_title}",
                "",
                f"- Data: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                f"- Livro: {self.current_book_title}",
                f"- Página atual: {self.current_page}",
                f"- Tipo: {task['title']}",
                "",
                "## Material",
                text.strip(),
                "",
            ]
            note_path = self._write_note_to_personal(
                "\n".join(note_content),
                f"revisao-{task['slug']}",
                target_dir=target_dir,
                filename_override=filename,
            )
        if note_path:
            self._append_note_link_to_current_chapter(note_path)
            self.chat_history.append(f"Sistema: {task['title']} salvo em {note_path.name}")
            self._auto_update_mindmap(f"novo material de revisão: {task['title']}")
            if task["slug"] == "resumo":
                self._review_summary_saved_in_run = True
                self._register_chapter_difficulty(note_path)
                self._clear_llm_cache_after_material(task["title"])
        else:
            self.chat_history.append(f"Sistema: falha ao salvar material de {task['title']}.")

        self._review_current_task_index += 1
        self._review_inflight_task = None
        self._review_llm_inflight = False
        overall = int((self._review_current_task_index / max(len(self._review_queue), 1)) * 100)
        self.review_overall_progress.setValue(overall)
        QTimer.singleShot(120, self._run_next_review_task)

    def _handle_pending_note_response(self, llm_text: str, request: Dict[str, Any]):
        req_type = request.get("type", "legacy")
        if req_type == "draft":
            if self._is_llm_failure_response(llm_text):
                excerpt = self._selected_excerpt_for_note.strip()
                self.note_editor.setPlainText(self._fallback_note_template(excerpt))
                self.chat_status_label.setText("Template local aplicado (LLM sem contexto)")
                return
            self.note_editor.setPlainText(self._compose_note_draft(llm_text))
            return
        if self._is_llm_failure_response(llm_text):
            self.chat_history.append("Sistema: LLM não retornou conteúdo útil para esta geração.")
            return
        self._create_llm_note_from_response(llm_text, request)

    def _on_llm_processing_started(self, task_type: str, message: str):
        self.chat_status_label.setText(message)
        if self._review_generation_active and task_type == "llm_generate":
            self.review_item_progress.setRange(0, 100)
            self.review_item_progress.setValue(max(self.review_item_progress.value(), 40))

    def _on_llm_processing_progress(self, percent: int, _message: str):
        if not self._review_generation_active or not self._review_llm_inflight:
            return
        bounded = max(0, min(percent, 100))
        mapped = 30 + int(bounded * 0.65)  # 30..95
        self.review_item_progress.setRange(0, 100)
        self.review_item_progress.setValue(mapped)

    def _on_llm_processing_completed(self, task_type: str):
        if self._review_generation_active and task_type == "memory_update" and self._review_waiting_cache_clear:
            self.review_item_progress.setRange(0, 100)
            self.review_item_progress.setValue(20)
            self.chat_status_label.setText("Cache limpo. Gerando item...")
            QTimer.singleShot(80, self._start_review_llm_task)
            return
        if not self._review_generation_active:
            self.chat_status_label.setText("LLM pronta")

    def _on_llm_error(self, error_type: str, error_message: str, _context: str):
        self.chat_history.append(f"GLaDOS [{error_type}]: {error_message}")
        self.chat_status_label.setText("Erro na LLM")
        if self._review_generation_active:
            if self._is_backend_unavailable_response(error_message):
                self._abort_review_generation("LLM indisponível no backend atual (gpu_only)")
                self._pending_note_request = None
                return

            task = self._review_inflight_task
            message_lower = (error_message or "").lower()
            if task and (
                "context window" in message_lower
                or "requested tokens" in message_lower
                or "exceed" in message_lower
            ):
                if self._retry_review_task_with_format_repair(
                    task,
                    "",
                    "janela de contexto excedida; gere resposta mais curta e estritamente no formato exigido",
                ):
                    return

            current_title = (
                self._review_inflight_task["title"] if self._review_inflight_task else "item atual"
            )
            self.chat_history.append(f"Sistema: erro em '{current_title}', avançando para o próximo item.")
            self.review_item_progress.setRange(0, 100)
            self.review_item_progress.setValue(0)
            self._review_waiting_cache_clear = False
            self._review_llm_inflight = False
            self._review_current_task_index += 1
            self._review_inflight_task = None
            if self._review_current_task_index >= len(self._review_queue):
                self._finish_review_generation()
            else:
                QTimer.singleShot(150, self._run_next_review_task)
        self._pending_note_request = None

    def _show_notes_menu(self):
        menu = QMenu(self)
        action_summary = menu.addAction("Gerar resumo + anotações (LLM)")
        menu.addSeparator()
        action_tpl_reading = menu.addAction("Nova nota com template: Reading")
        action_tpl_concept = menu.addAction("Nova nota com template: Concept")
        action_tpl_conversation = menu.addAction("Nova nota com template: Conversation")

        selected = menu.exec(self.controls_menu_button.mapToGlobal(self.controls_menu_button.rect().bottomLeft()))
        if selected == action_summary:
            self._request_summary_with_annotations()
        elif selected == action_tpl_reading:
            self._create_template_note("reading_note.md", "reading_template")
        elif selected == action_tpl_concept:
            self._create_template_note("concept_note.md", "concept_template")
        elif selected == action_tpl_conversation:
            self._create_template_note("conversation.md", "conversation_template")

    def _set_excerpt_note_capture_mode(self, enabled: bool):
        self._excerpt_note_capture_mode = enabled
        self.note_title_input.setVisible(not enabled)
        if enabled:
            excerpt = self._selected_excerpt_for_note.strip()
            excerpt_preview = self._truncate_text(excerpt, max_len=180) if excerpt else ""
            self.note_capture_hint.setText(
                "Anotação rápida do trecho selecionado.\n"
                f"Trecho: {excerpt_preview}"
            )
            self.note_capture_hint.setVisible(True)
            self.note_editor.setPlaceholderText("Escreva apenas sua anotação sobre o trecho...")
        else:
            self.note_capture_hint.setVisible(False)
            self.note_editor.setPlaceholderText("Escreva sua anotação aqui...")

    def _open_note_tab(self, excerpt_capture_mode: bool = False):
        if self._fullscreen_mode:
            self._set_fullscreen_assistant_visible(True, animate=True)
        else:
            self.assistant_tabs.setVisible(True)
        self.assistant_tabs.setCurrentWidget(self.note_panel)
        self._set_excerpt_note_capture_mode(excerpt_capture_mode)

        if not self.note_title_input.text().strip():
            self.note_title_input.setText(f"Anotação - {self.current_book_title}")

        if excerpt_capture_mode:
            self.note_editor.clear()
            self.note_editor.setFocus()
            self.chat_status_label.setText("Capturando anotação do trecho selecionado")
            return

        self.note_editor.setPlainText("Gerando template com contexto da sessão...")
        self._request_note_draft_from_llm()

    def _request_note_draft_from_llm(self):
        if self._review_generation_active:
            self.note_editor.setPlainText("Aguarde: revisão em processamento.")
            return
        context = self._build_chapter_context(
            max_current_chars=900,
            max_prev_chapters=1,
            max_prev_chars=280,
        )
        excerpt = self._selected_excerpt_for_note.strip()

        if not self.glados_controller:
            self.note_editor.setPlainText(self._fallback_note_template(excerpt))
            self.chat_status_label.setText("LLM indisponível")
            return

        instruction = (
            "Retorne SOMENTE uma lista curta de links wiki de notas relacionadas ao capítulo atual. "
            "Formato obrigatório: uma linha por item, iniciando com '- [[...]]'. "
            "Não inclua prompts, explicações, citações longas, nem trecho integral do capítulo."
        )
        if excerpt:
            instruction += f"\nTrecho foco para busca semântica: {excerpt}"

        self._pending_note_request = {"type": "draft"}
        prompt = f"{instruction}\n\n{context}"
        self.chat_status_label.setText("Gerando template de anotação...")
        prompt = self._trim_prompt_for_context_window(prompt, hard_limit_chars=1350)
        self.glados_controller.ask_glados(prompt, False, "Helio")

    def _fallback_note_template(self, excerpt: str) -> str:
        return self._build_note_document(related_links=[], excerpt=excerpt)

    def _compose_note_draft(self, llm_text: str) -> str:
        links = self._extract_wikilinks(llm_text)
        excerpt = self._selected_excerpt_for_note.strip()
        return self._build_note_document(related_links=links, excerpt=excerpt)

    def _build_note_document(self, related_links: list[str], excerpt: str) -> str:
        title = self.note_title_input.text().strip() or f"Anotação - {self.current_book_title}"
        source_name = "não identificado"
        if self.current_chapter_path:
            source_name = self.current_chapter_path.stem
        elif self.book_source_path:
            source_name = self.book_source_path.stem

        lines = [
            f"# {title}",
            "",
            "## Cabeçalho",
            f"- Data: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            f"- Livro: {self.current_book_title}",
            f"- Página da sessão: {self.current_page}",
            f"- Origem: [[{source_name}]]",
        ]
        if excerpt:
            lines.append(f"- Trecho selecionado: {excerpt}")

        lines.extend(["", "## Notas Relacionadas"])
        if related_links:
            lines.extend([f"- {item}" for item in related_links])
        else:
            lines.append("- ")

        lines.extend(
            [
                "",
                "## Minha anotação",
                "",
                "## Ações / revisão",
                "- ",
                "",
            ]
        )
        return "\n".join(lines)

    def _extract_wikilinks(self, text: str) -> list[str]:
        found = re.findall(r"\[\[[^\]]+\]\]", text or "")
        normalized: list[str] = []
        seen = set()
        for link in found:
            item = link.strip()
            if item and item not in seen:
                seen.add(item)
                normalized.append(item)
        return normalized[:10]

    def _save_note_from_tab(self):
        title = self.note_title_input.text().strip()
        user_content = self.note_editor.toPlainText().strip()

        if not title:
            QMessageBox.warning(self, "Título obrigatório", "Defina um título para salvar a anotação.")
            return
        if not user_content:
            QMessageBox.warning(self, "Conteúdo vazio", "Adicione conteúdo antes de salvar.")
            return

        content = user_content
        if self._excerpt_note_capture_mode:
            content = self._build_excerpt_note_document(user_content)

        note_path = self._write_note_to_personal_with_title(content, title)
        if not note_path:
            QMessageBox.warning(self, "Erro ao salvar", "Não foi possível criar a anotação no vault.")
            return

        if self._selected_excerpt_for_note:
            self._link_excerpt_to_note(note_path, self._selected_excerpt_for_note)
            self._append_note_link_to_current_chapter(
                note_path,
                chapter_path=self._selected_excerpt_chapter_path,
            )
            self._selected_excerpt_for_note = ""
            self._selected_excerpt_chapter_path = None
        self._set_excerpt_note_capture_mode(False)

        self.chat_history.append(f"Sistema: Nota salva em {note_path.name}")
        self._auto_update_mindmap("nova anotação manual")
        QMessageBox.information(
            self,
            "Anotação salva",
            f"Nota criada em {self.USER_NOTES_DIR}/{note_path.name}",
        )

    def _show_page_context_menu(self, editor: QTextEdit, pos):
        menu = editor.createStandardContextMenu()
        selected_text = editor.textCursor().selectedText().replace("\u2029", "\n").strip()
        if selected_text:
            menu.addSeparator()
            create_note_action = menu.addAction("Criar nota do trecho")
            create_note_action.triggered.connect(
                lambda: self._create_note_from_excerpt(selected_text)
            )
        menu.exec(editor.mapToGlobal(pos))

    def _create_note_from_excerpt(self, selected_text: str):
        excerpt_title = self._normalize_excerpt_title(selected_text)
        if not excerpt_title:
            QMessageBox.warning(self, "Trecho inválido", "Selecione um trecho válido para criar a nota.")
            return

        self._selected_excerpt_for_note = selected_text.strip()
        self._selected_excerpt_chapter_path = self._resolve_active_chapter_path()
        self.note_title_input.setText(excerpt_title)
        self._open_note_tab(excerpt_capture_mode=True)

    def _normalize_excerpt_title(self, selected_text: str, max_len: int = 80) -> str:
        text = re.sub(r"\s+", " ", selected_text.replace("\u2029", " ")).strip()
        return text[:max_len].strip()

    def _request_summary_with_annotations(self):
        self._request_llm_generated_note("resumo", include_annotations=True)

    def _request_llm_generated_note(self, mode: str, include_annotations: bool = False):
        if self._review_generation_active:
            QMessageBox.information(self, "Revisão em andamento", "Aguarde a revisão terminar.")
            return
        if not self.glados_controller:
            QMessageBox.warning(self, "LLM indisponível", "Não foi possível acessar o controller da LLM.")
            return

        context = self._build_chapter_context(
            max_current_chars=1200,
            max_prev_chapters=2,
            max_prev_chars=500,
        )
        if not context:
            QMessageBox.warning(self, "Contexto indisponível", "Não foi possível montar contexto de capítulos.")
            return

        instruction = (
            "Gere um resumo estruturado da sessão atual com: síntese, conceitos-chave, "
            "3 insights e 2 conexões com capítulos anteriores."
        )
        annotation_context = ""
        if mode == "resumo" and include_annotations:
            annotation_context = self._build_annotation_context_for_summary(max_items=8, max_chars=360)
            if annotation_context:
                instruction += (
                    "\nIntegre explicitamente as anotações do usuário, destacando onde elas reforçam, "
                    "completam ou corrigem a leitura do capítulo."
                )

        self._pending_note_request = {"mode": mode}
        prompt_parts = [instruction, context]
        if annotation_context:
            prompt_parts.append(annotation_context)
        prompt = "\n\n".join(part for part in prompt_parts if part)
        self.chat_history.append(f"Sistema: Solicitação de nota ({mode}) enviada para GLaDOS.")
        self._apply_chat_preset(self.chat_preset_combo.currentText())
        prompt = self._trim_prompt_for_context_window(prompt, hard_limit_chars=1600)
        self.glados_controller.ask_glados(prompt, False, "Helio")

    def _build_annotation_context_for_summary(self, max_items: int = 8, max_chars: int = 360) -> str:
        related_entries = self._load_related_note_entries_for_current_chapter(
            max_items=max_items,
            max_chars=max_chars,
        )
        if not related_entries:
            return ""

        lines = ["Anotações do usuário para integrar ao resumo:"]
        for note in related_entries:
            title = (note.get("title") or "Anotação").strip()
            content = (note.get("content") or "").strip()
            if not content:
                continue
            lines.append(f"- {title}:")
            lines.append(content)
        if len(lines) <= 1:
            return ""
        return "\n".join(lines)

    def _build_chapter_context(
        self,
        max_current_chars: int = 14000,
        max_prev_chapters: int = 50,
        max_prev_chars: int = 1800,
    ) -> str:
        chapter_path = self._resolve_active_chapter_path()

        current_idx = -1
        for idx, chapter in enumerate(self.chapter_notes):
            if chapter.get("path") == chapter_path:
                current_idx = idx
                break

        if chapter_path and chapter_path.exists():
            current_text = chapter_path.read_text(encoding="utf-8", errors="ignore")
        else:
            current_text = self._build_page_content(self.current_page)
            if current_text.startswith("[") and current_text.endswith("]"):
                return ""
            chapter_path = self.book_source_path if self.book_source_path and self.book_source_path.exists() else None

        previous: list[Dict[str, Any]] = []
        if current_idx >= 0:
            previous = self.chapter_notes[:current_idx]
            if max_prev_chapters >= 0:
                previous = previous[-max_prev_chapters:] if max_prev_chapters else []

        lines = []
        lines.append(f"Livro: {self.current_book_title}")
        lines.append(f"Página atual de leitura: {self.current_page}")
        lines.append("")
        chapter_name = chapter_path.name if chapter_path else f"Página {self.current_page}"
        lines.append(f"Capítulo atual: {chapter_name}")
        lines.append(self._truncate_text(current_text, max_current_chars))
        lines.append("")
        lines.append("Capítulos anteriores:")

        if not previous:
            lines.append("- Nenhum capítulo anterior.")
        else:
            for item in previous:
                chapter_text = item["path"].read_text(encoding="utf-8", errors="ignore")
                snippet = self._truncate_text(chapter_text, max_prev_chars)
                lines.append(f"- {item['path'].name} (páginas {item['start_page']}-{item['end_page']})")
                lines.append(snippet)
                lines.append("")

        return "\n".join(lines)

    def _build_review_generation_context(
        self,
        selected_note_entries: Optional[list[Dict[str, str]]] = None,
        chapter_difficulty: Optional[int] = None,
    ) -> str:
        chapter_context = self._build_chapter_context(
            max_current_chars=700,
            max_prev_chapters=1,
            max_prev_chars=420,
        )
        if not chapter_context:
            return ""

        effective_difficulty = max(1, min(int(chapter_difficulty or self._review_chapter_difficulty), 5))
        previous_chapter_excerpt = self._load_previous_chapter_excerpt(max_chars=650)
        previous_summary = self._load_previous_chapter_review_summary(max_chars=520)
        related_entries = (
            selected_note_entries
            if selected_note_entries is not None
            else self._load_related_note_entries_for_current_chapter(max_items=4, max_chars=320)
        )
        lines = [
            chapter_context,
            "",
            f"Dificuldade percebida do capítulo (escala 1-5): {effective_difficulty}",
            "",
            "Capítulo imediatamente anterior (trecho):",
            previous_chapter_excerpt or "- Não encontrado.",
            "",
            "Resumo de revisão do capítulo anterior:",
            previous_summary or "- Não encontrado.",
            "",
            "Notas relacionadas ao capítulo atual:",
        ]
        if not related_entries:
            lines.append("- Nenhuma nota relacionada encontrada.")
        else:
            for note in related_entries:
                title = note.get("title", "Nota sem título")
                source = note.get("source", "")
                source_text = f" [{source}]" if source else ""
                lines.append(f"- {title}{source_text}")
                lines.append(note.get("content", ""))
                lines.append("")
        return "\n".join(lines)

    def _load_previous_chapter_excerpt(self, max_chars: int = 650) -> str:
        chapter_path = self._resolve_active_chapter_path()
        if not chapter_path:
            return ""
        current_idx = -1
        for idx, chapter in enumerate(self.chapter_notes):
            if chapter.get("path") == chapter_path:
                current_idx = idx
                break
        if current_idx <= 0:
            return ""
        prev_info = self.chapter_notes[current_idx - 1]
        prev_path = prev_info.get("path")
        if not prev_path or not prev_path.exists():
            return ""
        try:
            prev_text = prev_path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            return ""
        return self._truncate_text(prev_text, max_chars)

    def _load_previous_chapter_review_summary(self, max_chars: int = 520) -> str:
        if not self.reading_controller or not getattr(self.reading_controller, "reading_manager", None):
            return ""
        current_chapter = self._current_chapter_number()
        if current_chapter <= 1:
            return ""
        prev_chapter = current_chapter - 1
        safe_book = self._sanitize_filename(self.current_book_title)
        filename = f"{safe_book}.{prev_chapter:02d}_resumo.md"
        vault_path = Path(self.reading_controller.reading_manager.vault_path)
        summary_path = vault_path / self.REVIEW_DIR / filename
        if not summary_path.exists():
            return ""
        try:
            content = summary_path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            return ""
        return self._truncate_text(content.strip(), max_chars)

    def _load_related_notes_for_current_chapter(self) -> list[Dict[str, str]]:
        entries = self._load_related_note_entries_for_current_chapter(max_items=2, max_chars=320)
        return [{"title": item["title"], "content": item["content"]} for item in entries]

    def _load_related_note_entries_for_current_chapter(
        self,
        max_items: int = 6,
        max_chars: int = 320,
    ) -> list[Dict[str, str]]:
        chapter_path = self._resolve_active_chapter_path()
        if not chapter_path or not chapter_path.exists():
            return []

        chapter_text = chapter_path.read_text(encoding="utf-8", errors="ignore")
        links = re.findall(r"\[\[([^\]\|#]+)(?:\|[^\]]+)?(?:#[^\]]+)?\]\]", chapter_text)
        if not links:
            return []

        related: list[Dict[str, str]] = []
        seen = set()
        for raw_target in links:
            target = raw_target.strip()
            if not target or target in seen:
                continue
            seen.add(target)
            note_path = self._resolve_wikilink_to_path(target)
            if not note_path or not note_path.exists() or not note_path.is_file():
                continue
            try:
                content = note_path.read_text(encoding="utf-8", errors="ignore").strip()
            except Exception:
                continue
            display_path = note_path.name
            vault_root = self._get_vault_root()
            if vault_root:
                try:
                    display_path = str(note_path.relative_to(vault_root)).replace("\\", "/")
                except Exception:
                    display_path = note_path.name
            truncated = self._truncate_text(content, max_chars)
            related.append(
                {
                    "title": note_path.stem,
                    "path": str(note_path),
                    "display_path": display_path,
                    "content": truncated,
                    "source": "Relacionado",
                    "estimated_chars": len(truncated) + 80,
                }
            )
            if len(related) >= max_items:
                break
        return related

    def _resolve_wikilink_to_path(self, wikilink_target: str) -> Optional[Path]:
        if not self.reading_controller or not getattr(self.reading_controller, "reading_manager", None):
            return None
        vault_root = Path(self.reading_controller.reading_manager.vault_path)
        normalized = wikilink_target.strip().replace("\\", "/")
        if not normalized:
            return None
        if normalized.endswith(".md") or normalized.endswith(".canvas"):
            relative_candidates = [normalized]
        else:
            relative_candidates = [f"{normalized}.md", f"{normalized}.canvas"]

        for relative in relative_candidates:
            candidate = vault_root / relative
            if candidate.exists():
                return candidate

            fallback_paths = [
                vault_root / self.USER_NOTES_DIR / relative,
                vault_root / self.USER_NOTES_DIR / Path(relative).name,
                vault_root / self.REVIEW_DIR / relative,
                vault_root / self.REVIEW_DIR / Path(relative).name,
                vault_root / self.MINDMAPS_DIR / relative,
                vault_root / self.MINDMAPS_DIR / Path(relative).name,
                vault_root / "05 - Pessoal" / relative,  # retrocompatibilidade
                vault_root / "05 - Pessoal" / Path(relative).name,
            ]
            for path in fallback_paths:
                if path.exists():
                    return path
        return None

    def _review_instruction_summary(self) -> str:
        return (
            "Gere um resumo de revisão com EXATAMENTE 4 seções, sem texto extra e sem raciocínio interno. "
            "Formato obrigatório:\n"
            "## Síntese\n"
            "<texto>\n"
            "## Conceitos-chave\n"
            "- item 1\n"
            "- item 2\n"
            "## Ligações entre capítulos\n"
            "<texto>\n"
            "## Pontos de dúvida\n"
            "- dúvida 1\n"
            "- dúvida 2\n"
            "Máximo de 350 palavras."
        )

    def _review_instruction_flashcards(self) -> str:
        return (
            "Gere EXATAMENTE 12 flashcards em markdown, sem texto extra antes/depois, no formato: "
            "### Flashcard N\\nFrente: ...\\nVerso: ...\\n. "
            "Misture definição, aplicação e comparação. Não inclua blocos de código. "
            "Evite perguntas de metadado (título, autor, número de capítulo, número de página)."
        )

    def _truncate_text(self, text: str, max_len: int) -> str:
        clean = text.strip()
        if len(clean) <= max_len:
            return clean
        return clean[:max_len] + "\n...[truncado]..."

    def _trim_prompt_for_context_window(self, prompt: str, hard_limit_chars: int = 1600) -> str:
        text = (prompt or "").strip()
        if len(text) <= hard_limit_chars:
            return text
        head_budget = int(hard_limit_chars * 0.72)
        tail_budget = max(120, hard_limit_chars - head_budget - 40)
        return text[:head_budget].rstrip() + "\n...[contexto reduzido]...\n" + text[-tail_budget:].lstrip()

    def _create_llm_note_from_response(self, llm_text: str, request: Dict[str, Any]):
        if self._is_llm_failure_response(llm_text):
            self.chat_history.append("Sistema: geração ignorada por resposta de erro da LLM.")
            return
        mode = "resumo"
        title_mode = "Resumo de Sessão"
        title = f"{title_mode} - {self.current_book_title}"

        content = [
            f"# {title}",
            "",
            f"- Data: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            f"- Livro: {self.current_book_title}",
            f"- Página: {self.current_page}",
            "",
            "## Conteúdo gerado pela LLM",
            llm_text,
            "",
        ]

        filename = self._build_review_filename(mode, self.REVIEW_DIR)
        note_path = self._write_note_to_personal(
            "\n".join(content),
            f"llm-{mode}",
            target_dir=self.REVIEW_DIR,
            filename_override=filename,
        )
        if note_path:
            self._append_note_link_to_current_chapter(note_path)
            self.chat_history.append(f"Sistema: Nota criada em {note_path.name}")
            self._auto_update_mindmap("novo resumo LLM")
            self._clear_llm_cache_after_material("Resumo")

    def _create_template_note(self, template_name: str, note_type: str):
        template_path = Path("src/cli/interactive/screens/glados_templates") / template_name
        if not template_path.exists():
            QMessageBox.warning(self, "Template não encontrado", f"Template ausente: {template_name}")
            return

        raw = template_path.read_text(encoding="utf-8", errors="ignore")
        title = f"{note_type} - {self.current_book_title}"
        rendered = self._render_template(raw, title)

        note_path = self._write_note_to_personal(
            rendered,
            note_type,
            target_dir=self.USER_NOTES_DIR,
        )
        if note_path:
            self._append_note_link_to_current_chapter(note_path)
            self.chat_history.append(f"Sistema: Nota de template criada em {note_path.name}")
            self._auto_update_mindmap("nova nota de template")

    def _render_template(self, template_text: str, title: str) -> str:
        replacements = {
            "{{title}}": title,
            "{{date}}": datetime.now().strftime("%Y-%m-%d"),
            "{{timestamp}}": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "{{context}}": f"Leitura em {self.current_book_title}, página {self.current_page}",
            "{{question}}": "",
            "{{response}}": "",
            "{{summary}}": "",
            "{{insights}}": "",
            "{{tags}}": "leitura",
            "{{duration}}": "",
            "{{message_count}}": "",
            "{{token_count}}": "",
            "{{avg_tokens}}": "",
            "{{source_count}}": "",
            "{{generated_tags}}": "",
        }

        rendered = template_text
        for src, dst in replacements.items():
            rendered = rendered.replace(src, dst)

        rendered_lines = []
        for line in rendered.splitlines():
            if "{%" in line or "%}" in line:
                continue
            rendered_lines.append(line)
        return "\n".join(rendered_lines).strip() + "\n"

    def _write_note_to_personal(
        self,
        content: str,
        slug: str,
        target_dir: str = "",
        filename_override: str = "",
        overwrite_existing: bool = False,
    ) -> Optional[Path]:
        if not self.reading_controller or not getattr(self.reading_controller, "reading_manager", None):
            return None

        vault_path = Path(self.reading_controller.reading_manager.vault_path)
        selected_dir = target_dir or self.USER_NOTES_DIR
        personal_dir = vault_path / selected_dir
        personal_dir.mkdir(parents=True, exist_ok=True)

        if filename_override:
            filename = filename_override
        else:
            stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            safe_book = self._sanitize_filename(self.current_book_title)[:60]
            filename = f"{stamp}-{slug}-{safe_book}.md"
        note_path = personal_dir / filename
        if not overwrite_existing:
            suffix = 2
            while note_path.exists():
                note_path = personal_dir / f"{note_path.stem} ({suffix}){note_path.suffix}"
                suffix += 1
        note_path.write_text(content, encoding="utf-8")
        return note_path

    def _write_note_to_personal_with_title(self, content: str, title: str) -> Optional[Path]:
        if not self.reading_controller or not getattr(self.reading_controller, "reading_manager", None):
            return None

        vault_path = Path(self.reading_controller.reading_manager.vault_path)
        personal_dir = vault_path / self.USER_NOTES_DIR
        personal_dir.mkdir(parents=True, exist_ok=True)

        note_stem = self._sanitize_obsidian_title(title)
        if not note_stem:
            note_stem = f"anotacao-{datetime.now().strftime('%Y%m%d-%H%M%S')}"

        note_path = personal_dir / f"{note_stem}.md"
        suffix = 2
        while note_path.exists():
            note_path = personal_dir / f"{note_stem} ({suffix}).md"
            suffix += 1

        note_path.write_text(content.strip() + "\n", encoding="utf-8")
        return note_path

    def _sanitize_obsidian_title(self, title: str) -> str:
        cleaned = title.strip().replace("\n", " ")
        cleaned = re.sub(r'[\\/:*?"<>|]+', "-", cleaned)
        cleaned = re.sub(r"\s+", " ", cleaned).strip(". ").strip()
        return cleaned

    def _build_excerpt_note_document(self, user_note: str) -> str:
        title = self.note_title_input.text().strip() or "Anotação de trecho"
        excerpt = self._selected_excerpt_for_note.replace("\u2029", "\n").strip()
        chapter_path = self._selected_excerpt_chapter_path or self._resolve_active_chapter_path()
        chapter_link = f"[[{chapter_path.stem}]]" if chapter_path and chapter_path.is_file() else "-"
        book_link = (
            f"[[{self.book_source_path.stem}]]"
            if self.book_source_path and self.book_source_path.is_file()
            else self.current_book_title
        )
        lines = [
            f"# {title}",
            "",
            "## Trecho selecionado",
            excerpt or "-",
            "",
            "## Minha anotação",
            user_note.strip(),
            "",
            "## Referências",
            f"- Livro completo: {book_link}",
            f"- Capítulo em foco: {chapter_link}",
            "",
        ]
        return "\n".join(lines)

    def _link_excerpt_to_note(self, note_path: Path, selected_text: str):
        excerpt = selected_text.replace("\u2029", "\n").strip()
        if not excerpt:
            return

        markdown_note_path = self._relative_note_markdown_path_from_abs(note_path)
        if not markdown_note_path:
            return

        excerpt_label = re.sub(r"\s+", " ", excerpt).replace("]", r"\]")
        markdown_link = f"[{excerpt_label}](<{markdown_note_path}>)"
        target_paths: list[Path] = []
        for candidate in (
            self.book_source_path,
            self._selected_excerpt_chapter_path,
            self.current_chapter_path,
        ):
            if not candidate or not candidate.exists() or not candidate.is_file():
                continue
            if candidate not in target_paths:
                target_paths.append(candidate)

        for target_path in target_paths:
            text = target_path.read_text(encoding="utf-8", errors="ignore")
            if markdown_link in text:
                continue
            if excerpt in text:
                updated = text.replace(excerpt, markdown_link, 1)
            else:
                updated = text.rstrip() + f"\n\n- {markdown_link}\n"
            target_path.write_text(updated, encoding="utf-8")

    def _append_note_link_to_current_chapter(self, note_path: Path, chapter_path: Optional[Path] = None):
        target_chapter_path = chapter_path or self.current_chapter_path
        if not target_chapter_path or not target_chapter_path.exists():
            return

        relative_note = self._relative_note_path_from_abs(note_path)
        if not relative_note:
            return
        link_line = f"- [[{relative_note}|{note_path.stem}]]"
        text = target_chapter_path.read_text(encoding="utf-8", errors="ignore")
        if link_line in text:
            return

        section_header = "## 🔗 Notas da Sessão"
        header_pattern = re.compile(r"(?m)^##\s+🔗\s+Notas da Sessão\s*$")
        header_match = header_pattern.search(text)

        if not header_match:
            updated = text.rstrip() + f"\n\n{section_header}\n{link_line}\n"
            target_chapter_path.write_text(updated, encoding="utf-8")
            return

        section_start = header_match.end()
        next_header_pattern = re.compile(r"(?m)^##\s+.+$")
        next_header_match = next_header_pattern.search(text, section_start)
        section_end = next_header_match.start() if next_header_match else len(text)

        section_body = text[section_start:section_end]
        existing_links = re.findall(r"(?m)^\s*-\s*\[\[.*\]\]\s*$", section_body)
        normalized_existing = [ln.strip() for ln in existing_links]
        if link_line in normalized_existing:
            return

        lines = [ln for ln in normalized_existing if ln]
        lines.append(link_line)
        lines = sorted(set(lines), key=str.lower)

        new_section_body = "\n" + "\n".join(lines) + "\n"
        updated = text[:section_start] + new_section_body + text[section_end:]
        target_chapter_path.write_text(updated, encoding="utf-8")

    def _relative_note_path_from_abs(self, note_path: Path) -> Optional[str]:
        if not self.reading_controller or not getattr(self.reading_controller, "reading_manager", None):
            return None
        vault_path = Path(self.reading_controller.reading_manager.vault_path)
        try:
            relative = note_path.relative_to(vault_path)
        except Exception:
            return None
        return str(relative.with_suffix("")).replace("\\", "/")

    def _relative_note_markdown_path_from_abs(self, note_path: Path) -> Optional[str]:
        if not self.reading_controller or not getattr(self.reading_controller, "reading_manager", None):
            return None
        vault_path = Path(self.reading_controller.reading_manager.vault_path)
        try:
            relative = note_path.relative_to(vault_path)
        except Exception:
            return None
        return str(relative).replace("\\", "/")

    def _display_relative_path(self, file_path: Optional[Path]) -> str:
        if not file_path:
            return ""
        if not self.reading_controller or not getattr(self.reading_controller, "reading_manager", None):
            return file_path.name
        vault_path = Path(self.reading_controller.reading_manager.vault_path)
        try:
            relative = file_path.relative_to(vault_path)
            return str(relative).replace("\\", "/")
        except Exception:
            return file_path.name

    def _sanitize_filename(self, value: str) -> str:
        return re.sub(r"[^a-zA-Z0-9._-]+", "-", value).strip("-").lower() or "nota"

    def _is_backend_unavailable_response(self, text: str) -> bool:
        clean = (text or "").strip().lower()
        if not clean:
            return False
        return (
            "llm indispon" in clean
            or "gpu_only estrito" in clean
            or "modo gpu_only" in clean
            or "gpu_only" in clean
            or "backend gpu" in clean and "indispon" in clean
        )

    def _is_llm_failure_response(self, text: str) -> bool:
        clean = (text or "").strip().lower()
        if not clean:
            return True
        return (
            "não consegui processar totalmente a pergunta" in clean
            or "requested tokens" in clean
            or "exceed context window" in clean
            or "erro na geração" in clean
            or self._is_backend_unavailable_response(clean)
        )

    def _current_chapter_number(self) -> int:
        if not self.current_chapter_path:
            return 0
        for item in self.chapter_notes:
            if item.get("path") == self.current_chapter_path:
                try:
                    return int(item.get("number") or 0)
                except Exception:
                    return 0
        return self._extract_chapter_number(self.current_chapter_path, "")

    def _build_review_filename(self, mode_slug: str, target_dir: str) -> str:
        book = self._sanitize_filename(self.current_book_title)
        if mode_slug == "mapa-mental-canva" or target_dir == self.MINDMAPS_DIR:
            return f"{book}.mapa-mental.canvas"

        chapter = self._current_chapter_number()
        chapter_part = f"{chapter:02d}" if chapter > 0 else "00"
        mode_map = {
            "resumo": "resumo",
            "flashcards": "flashcard",
            "perguntas-manual": "perguntas",
        }
        mode_part = mode_map.get(mode_slug, self._sanitize_filename(mode_slug))
        return f"{book}.{chapter_part}_{mode_part}.md"

    def _review_target_path(self, mode_slug: str, target_dir: str) -> Optional[Path]:
        if not self.reading_controller or not getattr(self.reading_controller, "reading_manager", None):
            return None
        vault_path = Path(self.reading_controller.reading_manager.vault_path)
        filename = self._build_review_filename(mode_slug, target_dir)
        return vault_path / target_dir / filename

    def _strip_llm_meta_text(self, text: str) -> str:
        clean = (text or "").strip()
        if not clean:
            return ""

        clean = re.sub(r"```(?:json|markdown|md|text)?", "", clean, flags=re.IGNORECASE).replace("```", "")
        lines: list[str] = []
        meta_pattern = re.compile(
            r"^\s*(okay[, ]|i need to|let me|vou |preciso |racioc[ií]nio|chain of thought|thought:|analysis:)",
            flags=re.IGNORECASE,
        )
        for raw_line in clean.splitlines():
            line = raw_line.rstrip()
            if meta_pattern.match(line):
                continue
            lines.append(line)
        return "\n".join(lines).strip()

    def _ensure_bullet_list(self, text: str) -> str:
        raw_lines = [ln.strip() for ln in (text or "").splitlines() if ln.strip()]
        if not raw_lines:
            return "- Não identificado."
        if any(ln.startswith("- ") for ln in raw_lines):
            return "\n".join(raw_lines)
        parts = [p.strip(" -•\t") for p in re.split(r"[;\n•]+", " ".join(raw_lines)) if p.strip(" -•\t")]
        if not parts:
            return "- Não identificado."
        return "\n".join(f"- {part}" for part in parts[:6])

    def _normalize_summary_response(self, text: str) -> tuple[Optional[str], str]:
        clean = self._strip_llm_meta_text(text)
        if not clean:
            return None, "resposta vazia"

        sections: Dict[str, list[str]] = {
            "sintese": [],
            "conceitos": [],
            "ligacoes": [],
            "duvidas": [],
        }
        current_key: Optional[str] = None
        heading_pattern = re.compile(
            r"^\s*(?:#+\s*)?(?:\*\*)?\s*"
            r"(s[ií]ntese|conceitos?[- ]?chave|liga(?:ç|c)[õo]es?\s+entre\s+cap[ií]tulos|pontos?\s+de\s+d[úu]vida)"
            r"\s*:?\s*(?:\*\*)?\s*(.*)$",
            flags=re.IGNORECASE,
        )

        for raw_line in clean.splitlines():
            line = raw_line.strip()
            if not line:
                continue
            match = heading_pattern.match(line)
            if match:
                heading = match.group(1).lower()
                tail = match.group(2).strip()
                if "sint" in heading or "sínt" in heading:
                    current_key = "sintese"
                elif "conceit" in heading:
                    current_key = "conceitos"
                elif "liga" in heading:
                    current_key = "ligacoes"
                else:
                    current_key = "duvidas"
                if tail:
                    sections[current_key].append(tail)
                continue
            if current_key is not None:
                sections[current_key].append(line)

        has_any = any(sections[key] for key in sections)
        if not has_any:
            sections["sintese"].append(clean)

        sintese = "\n".join(sections["sintese"]).strip() or "Não identificado."
        conceitos = self._ensure_bullet_list("\n".join(sections["conceitos"]))
        ligacoes = "\n".join(sections["ligacoes"]).strip() or "Não identificado."
        duvidas = self._ensure_bullet_list("\n".join(sections["duvidas"]))

        normalized = (
            "## Síntese\n"
            f"{sintese}\n\n"
            "## Conceitos-chave\n"
            f"{conceitos}\n\n"
            "## Ligações entre capítulos\n"
            f"{ligacoes}\n\n"
            "## Pontos de dúvida\n"
            f"{duvidas}\n"
        )
        return normalized, ""

    def _fallback_review_terms(self, limit: int = 14) -> list[str]:
        source = (self._review_context_payload or "").strip()
        terms: list[str] = []
        seen: set[str] = set()

        for term in re.findall(r"\*\*([^*]{3,80})\*\*", source):
            normalized = " ".join(term.strip().split())
            key = normalized.lower()
            if len(normalized) < 4 or key in seen:
                continue
            seen.add(key)
            terms.append(normalized)
            if len(terms) >= limit:
                return terms

        for term in re.findall(r"(?m)^#+\s+(.+)$", source):
            normalized = " ".join(term.strip().split())
            key = normalized.lower()
            if len(normalized) < 4 or key in seen:
                continue
            seen.add(key)
            terms.append(normalized)
            if len(terms) >= limit:
                return terms

        if not terms:
            terms = [
                f"Conceito central do capítulo ({self.current_book_title})",
                "Relação entre teoria e aplicação",
                "Tensão crítica do argumento principal",
                "Exemplo prático discutido no capítulo",
            ]
        return terms[:limit]

    def _normalize_flashcards_response(self, text: str) -> tuple[Optional[str], str]:
        clean = self._strip_llm_meta_text(text)
        if not clean:
            return None, "resposta vazia"

        clean = re.sub(r"\*\*\s*Frente\s*:\s*\*\*", "Frente:", clean, flags=re.IGNORECASE)
        clean = re.sub(r"\*\*\s*Verso\s*:\s*\*\*", "Verso:", clean, flags=re.IGNORECASE)
        clean = clean.replace("**Frente:**", "Frente:").replace("**Verso:**", "Verso:")

        pair_pattern = re.compile(
            r"(?is)Frente:\s*(.+?)\s*Verso:\s*(.+?)(?=(?:\n\s*###\s*Flashcard|\n\s*Frente:|\Z))"
        )
        pairs = pair_pattern.findall(clean)

        if len(pairs) < 12:
            line_pairs = re.findall(
                r"(?im)^(?!frente:|verso:)([^:\n]{4,90})\s*:\s*([^:\n].{12,})$",
                clean,
            )
            for front, back in line_pairs:
                pairs.append((front, back))

        if len(pairs) < 12:
            return None, "não foi possível extrair 12 pares 'Frente/Verso'"

        blocks: list[str] = []
        card_count = 0
        quality_count = 0
        for idx, (front, back) in enumerate(pairs[:12], start=1):
            front_line = " ".join(front.strip().split())
            back_line = " ".join(back.strip().split())
            if not front_line or not back_line:
                continue
            card_count += 1
            if self._is_flashcard_content_acceptable(front_line, back_line):
                quality_count += 1
            blocks.extend(
                [
                    f"### Flashcard {idx}",
                    f"Frente: {front_line}",
                    f"Verso: {back_line}",
                    "",
                ]
            )

        if card_count < 12:
            return None, "conteúdo insuficiente após normalização de flashcards"
        if quality_count < 10:
            return None, "flashcards com baixa qualidade (metadado/trivial/genérico)"
        return "\n".join(blocks).strip() + "\n", ""

    def _is_flashcard_content_acceptable(self, front: str, back: str) -> bool:
        if len(front.strip()) < 18 or len(back.strip()) < 35:
            return False

        front_norm = self._normalize_pt_text(front)
        back_norm = self._normalize_pt_text(back)
        generic_patterns = [
            "qual e o titulo do livro",
            "quem e o autor",
            "qual capitulo",
            "em qual pagina",
            "explique o conceito",
            "no contexto deste capitulo",
        ]
        if any(pattern in front_norm for pattern in generic_patterns):
            return False
        if "no contexto deste capitulo" in back_norm:
            return False
        if re.search(r"\b(livro|autor|capitulo|pagina|paginas)\b", front_norm) and len(front_norm) < 55:
            return False
        return True

    def _normalize_pt_text(self, text: str) -> str:
        normalized = (text or "").strip().lower()
        normalized = normalized.replace("ç", "c")
        normalized = normalized.replace("ã", "a").replace("â", "a").replace("á", "a")
        normalized = normalized.replace("é", "e").replace("ê", "e")
        normalized = normalized.replace("í", "i")
        normalized = normalized.replace("ó", "o").replace("ô", "o").replace("õ", "o")
        normalized = normalized.replace("ú", "u")
        return normalized

    def _start_pomodoro(self):
        if not self.pomodoro:
            self.chat_status_label.setText("Pomodoro indisponível")
            return
        if self.pomodoro.is_running and self.pomodoro.is_paused:
            self.pomodoro.resume()
        elif not self.pomodoro.is_running:
            self.pomodoro.start(session_type="work", discipline="leitura")
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

    def _tick_ui(self):
        self._sync_progress_realtime()

        if not self.pomodoro:
            self.pomodoro_timer_label.setText("--:--")
            self.pomodoro_overlay_timer_label.setText("--:--")
            self.pomodoro_overlay_toggle_button.setText("▶")
            return

        if not self.pomodoro.is_running or not self.pomodoro.start_time:
            total_seconds = self.pomodoro._get_duration_for_type("work")
            timer_text = self._format_mmss(total_seconds)
            self.pomodoro_timer_label.setText(timer_text)
            self.pomodoro_overlay_timer_label.setText(timer_text)
            self.pomodoro_overlay_toggle_button.setText("▶")
            return

        now = time.time()
        elapsed = now - self.pomodoro.start_time - self.pomodoro.elapsed_paused
        total_seconds = self.pomodoro._get_duration_for_type(self.pomodoro.current_session_type)
        remaining = max(int(total_seconds - elapsed), 0)

        timer_text = self._format_mmss(remaining)
        self.pomodoro_timer_label.setText(timer_text)
        self.pomodoro_overlay_timer_label.setText(timer_text)
        self.pomodoro_overlay_toggle_button.setText("▶" if self.pomodoro.is_paused else "⏸")

    def _format_mmss(self, seconds: int) -> str:
        minutes, sec = divmod(max(seconds, 0), 60)
        return f"{minutes:02d}:{sec:02d}"

    def _on_back_clicked(self):
        self._set_fullscreen_mode(False)
        self._finalize_session()
        if self._temporary_read_only_session:
            self._temporary_read_only_session = False
            self._temporary_news_article = {}
            self.navigate_to.emit("discipline_chat")
            return
        self.navigate_to.emit("dashboard")

    def _on_end_session_clicked(self):
        self._set_fullscreen_mode(False)
        self._finalize_session()
        if self._temporary_read_only_session:
            self._temporary_read_only_session = False
            self._temporary_news_article = {}
            self.navigate_to.emit("discipline_chat")
            return
        self.navigate_to.emit("dashboard")

    def _sync_progress_realtime(self):
        if self._session_closed:
            return
        if self._temporary_read_only_session:
            return
        page_to_sync = self.current_page
        if self.total_pages > 0:
            page_to_sync = min(page_to_sync, self.total_pages)
        if page_to_sync <= 0 or page_to_sync == self._last_synced_page:
            return
        self._save_progress_absolute(page_to_sync, notes="sync sessão")

    def _compute_resume_page(self) -> int:
        resume = self.current_page
        if self.total_pages > 0:
            resume = min(max(1, resume), self.total_pages)
        return max(1, resume)

    def _finalize_session(self):
        if self._session_closed:
            return
        self._session_closed = True
        if self._temporary_read_only_session:
            return

        self._auto_update_mindmap("encerramento da sessão")

        resume_page = self._compute_resume_page()
        self._save_progress_absolute(
            resume_page,
            notes=f"Fim de sessão. Retomar da página {resume_page}."
        )

        if self.reading_controller:
            try:
                current_session = self.reading_controller.get_current_session()
            except Exception:
                current_session = {}

            if current_session:
                try:
                    self.reading_controller.end_reading_session(
                        0,
                        f"Fim de sessão. Próxima página: {resume_page}."
                    )
                except Exception as exc:
                    logger.warning("Falha ao encerrar sessão no ReadingController: %s", exc)

    def _save_progress_absolute(self, page: int, notes: str = ""):
        if self._temporary_read_only_session:
            return
        if not self.reading_controller:
            return
        manager = getattr(self.reading_controller, "reading_manager", None)
        if not manager or not self.current_book_id:
            return
        try:
            if manager.update_progress(str(self.current_book_id), int(page), notes):
                self._last_synced_page = int(page)
        except Exception as exc:
            logger.warning("Falha ao sincronizar progresso (%s): %s", page, exc)

    def cleanup(self):
        self._set_fullscreen_mode(False)
        self._finalize_session()

        if self.ui_timer.isActive():
            self.ui_timer.stop()

        if self.glados_controller:
            try:
                self.glados_controller.response_ready.disconnect(self._on_llm_response)
                self.glados_controller.processing_started.disconnect(self._on_llm_processing_started)
                self.glados_controller.processing_progress.disconnect(self._on_llm_processing_progress)
                self.glados_controller.processing_completed.disconnect(self._on_llm_processing_completed)
                self.glados_controller.error_occurred.disconnect(self._on_llm_error)
            except Exception:
                pass
