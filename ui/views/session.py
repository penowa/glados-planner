"""
View de sessão de leitura com Pomodoro e chat LLM.
"""
from __future__ import annotations

import logging
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QMenu,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from core.modules.pomodoro_timer import PomodoroTimer

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


class SessionView(QWidget):
    """Tela de sessão com leitura em dupla página, Pomodoro e chat LLM."""

    navigate_to = pyqtSignal(str)

    def __init__(self, controllers: Optional[Dict[str, Any]] = None, parent=None):
        super().__init__(parent)
        self.controllers = controllers or {}
        self.reading_controller = self.controllers.get("reading")
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

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        header = QHBoxLayout()
        header.setContentsMargins(6, 4, 6, 2)
        header.setSpacing(4)
        self.title_label = QLabel("Sessão de leitura")  # mantido para estado interno
        self.progress_label = QLabel("Página 1 de ?")   # mantido para estado interno
        self.source_label = QLabel("Fonte: nota não carregada")  # mantido para estado interno

        # Pomodoro minimalista no header
        self.pomodoro_timer_label = QLabel("25:00")
        self.pomodoro_timer_label.setObjectName("session_pomodoro_timer")
        self.pomodoro_timer_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
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
        root.addLayout(header)

        reading_panel = QFrame()
        reading_panel.setObjectName("session_reading_panel")
        reading_layout = QVBoxLayout(reading_panel)
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
            page.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
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

        nav = QHBoxLayout()
        nav.setContentsMargins(0, 0, 0, 0)
        nav.setSpacing(4)
        self.prev_pages_button = QPushButton("◀ Páginas anteriores")
        self.next_pages_button = QPushButton("Próximas páginas ▶")
        self.page_pair_label = QLabel("1-2")
        self.page_pair_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        nav.addWidget(self.prev_pages_button)
        nav.addWidget(self.page_pair_label, 1)
        nav.addWidget(self.next_pages_button)
        reading_layout.addLayout(nav)

        self.assistant_tabs = QTabWidget()
        self.assistant_tabs.setObjectName("session_assistant_tabs")
        self.assistant_tabs.setVisible(False)
        self.assistant_hide_button = QPushButton("Ocultar")
        self.assistant_hide_button.setObjectName("secondary_button")
        self.assistant_hide_button.setFixedHeight(22)
        self.assistant_tabs.setCornerWidget(self.assistant_hide_button, Qt.Corner.TopRightCorner)

        self.chat_panel = QFrame()
        self.chat_panel.setObjectName("session_chat_panel")
        chat_layout = QVBoxLayout(self.chat_panel)
        chat_layout.setContentsMargins(8, 8, 8, 8)
        chat_layout.setSpacing(6)

        self.chat_history = QTextEdit()
        self.chat_history.setReadOnly(True)
        self.chat_input = QLineEdit()
        self.chat_input.setPlaceholderText("Pergunte algo sobre a leitura...")
        self.chat_send_button = QPushButton("Enviar")
        self.chat_status_label = QLabel("LLM pronta")

        input_row = QHBoxLayout()
        input_row.addWidget(self.chat_input, 1)
        input_row.addWidget(self.chat_send_button)

        chat_layout.addWidget(self.chat_history, 1)
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
        self.note_save_button = QPushButton("Salvar")
        note_header.addWidget(self.note_title_input, 1)
        note_header.addWidget(self.note_save_button)

        self.note_editor = QTextEdit()
        self.note_editor.setPlaceholderText("Escreva sua anotação aqui...")
        self.note_editor.setStyleSheet(
            "background-color: #FFFFFF; color: #111111; "
            "font-family: Georgia, 'Times New Roman', serif;"
        )

        note_layout.addLayout(note_header)
        note_layout.addWidget(self.note_editor, 1)

        self.assistant_tabs.addTab(self.chat_panel, "Chat")
        self.assistant_tabs.addTab(self.note_panel, "Anotação")
        reading_layout.addWidget(self.assistant_tabs)

        root.addWidget(reading_panel, 1)

        # Menu único com os controles não relacionados à navegação de páginas.
        self.controls_menu = QMenu(self)
        self.action_back_dashboard = self.controls_menu.addAction("Voltar para Dashboard")
        self.action_end_session = self.controls_menu.addAction("Encerrar Sessão")
        self.controls_menu.addSeparator()
        self.action_pomodoro_start = self.controls_menu.addAction("Pomodoro: Iniciar")
        self.action_pomodoro_pause = self.controls_menu.addAction("Pomodoro: Pausar")
        self.action_pomodoro_config = self.controls_menu.addAction("Pomodoro: Configurar")
        self.controls_menu.addSeparator()
        self.action_chat_init = self.controls_menu.addAction("LLM: Inicializar Chat")
        self.action_chat_toggle = self.controls_menu.addAction("LLM: Mostrar Chat")
        self.action_chat_toggle.setCheckable(True)

    def _setup_connections(self):
        self.note_button.clicked.connect(self._open_note_tab)
        self.controls_menu_button.clicked.connect(self._open_controls_menu)
        self.action_back_dashboard.triggered.connect(self._on_back_clicked)
        self.action_end_session.triggered.connect(self._on_end_session_clicked)
        self.action_pomodoro_start.triggered.connect(self._start_pomodoro)
        self.action_pomodoro_pause.triggered.connect(self._pause_pomodoro)
        self.action_pomodoro_config.triggered.connect(self._open_pomodoro_config_dialog)
        self.action_chat_init.triggered.connect(self._initialize_context_chat)
        self.action_chat_toggle.toggled.connect(self._toggle_chat)

        self.prev_pages_button.clicked.connect(self._go_prev_pages)
        self.next_pages_button.clicked.connect(self._go_next_pages)
        self.chat_send_button.clicked.connect(self._send_chat_message)
        self.chat_input.returnPressed.connect(self._send_chat_message)
        self.note_save_button.clicked.connect(self._save_note_from_tab)
        self.assistant_hide_button.clicked.connect(self._hide_assistant_panels)

        if self.glados_controller:
            self.glados_controller.response_ready.connect(self._on_llm_response)
            self.glados_controller.processing_started.connect(self._on_llm_processing_started)
            self.glados_controller.processing_completed.connect(self._on_llm_processing_completed)
            self.glados_controller.error_occurred.connect(self._on_llm_error)

    def on_view_activated(self):
        self._session_closed = False
        self.refresh_reading_context()
        self._tick_ui()

    def start_ad_hoc_reading(self, book_dir: Path):
        """Inicia leitura avulsa a partir de um diretório de livro do vault."""
        self._manual_book_dir = Path(book_dir)
        self._manual_book_id = None
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

        self.left_page_title.setText(f"Página {left}")
        self.right_page_title.setText(f"Página {right}")
        self.left_page_text.setPlainText(self._build_page_content(left))
        self.right_page_text.setPlainText(self._build_page_content(right))

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

    def _build_page_content(self, page_number: int) -> str:
        if self.total_pages > 0 and page_number > self.total_pages:
            return "Fim do livro."

        if self.page_contents:
            content = self.page_contents.get(page_number)
            if content is not None:
                return content
            return "[Página não encontrada na nota do livro]"

        return "[Conteúdo do livro indisponível]"

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

    def _toggle_chat(self, checked: bool):
        self.assistant_tabs.setVisible(checked)
        if checked:
            self.assistant_tabs.setCurrentWidget(self.chat_panel)
        self.action_chat_toggle.setText("LLM: Ocultar Chat" if checked else "LLM: Mostrar Chat")
        if self.action_chat_toggle.isChecked() != checked:
            self.action_chat_toggle.setChecked(checked)

    def _hide_assistant_panels(self):
        self._toggle_chat(False)

    def _open_controls_menu(self):
        pos = self.controls_menu_button.mapToGlobal(self.controls_menu_button.rect().bottomLeft())
        self.controls_menu.exec(pos)

    def _send_chat_message(self):
        question = self.chat_input.text().strip()
        if not question:
            return

        self.chat_history.append(f"Você: {question}")
        self.chat_input.clear()

        if not self.glados_controller:
            self.chat_history.append("GLaDOS: Controller indisponível.")
            return

        self.glados_controller.ask_glados(question, True, "Helio")

    def _initialize_context_chat(self):
        if not self.glados_controller:
            self.chat_history.append("GLaDOS: Controller indisponível.")
            return

        context = self._build_chapter_context()
        if not context:
            self.chat_history.append("GLaDOS: Não encontrei contexto de capítulos para iniciar.")
            return

        self._toggle_chat(True)
        self.chat_history.append("Sistema: Contexto de leitura enviado para GLaDOS.")
        prompt = (
            "Contextualize-se para me apoiar nesta sessão de leitura.\n\n"
            f"{context}\n\n"
            "Responda com um resumo curto do contexto e 3 pontos de atenção para esta sessão."
        )
        self.glados_controller.ask_glados(prompt, True, "Helio")

    def _on_llm_response(self, payload: Dict[str, Any]):
        text = payload.get("text", "")
        if text:
            self.chat_history.append(f"GLaDOS: {text}")
            if self._pending_note_request:
                self._handle_pending_note_response(text, self._pending_note_request)
                self._pending_note_request = None
        self.chat_status_label.setText("LLM pronta")

    def _handle_pending_note_response(self, llm_text: str, request: Dict[str, Any]):
        req_type = request.get("type", "legacy")
        if req_type == "draft":
            self.note_editor.setPlainText(self._compose_note_draft(llm_text))
            return
        self._create_llm_note_from_response(llm_text, request)

    def _on_llm_processing_started(self, _task_type: str, message: str):
        self.chat_status_label.setText(message)

    def _on_llm_processing_completed(self, _task_type: str):
        self.chat_status_label.setText("LLM pronta")

    def _on_llm_error(self, error_type: str, error_message: str, _context: str):
        self.chat_history.append(f"GLaDOS [{error_type}]: {error_message}")
        self.chat_status_label.setText("Erro na LLM")
        self._pending_note_request = None

    def _show_notes_menu(self):
        menu = QMenu(self)
        action_summary = menu.addAction("Gerar resumo da sessão (LLM)")
        action_questions = menu.addAction("Gerar perguntas da sessão (LLM)")
        menu.addSeparator()
        action_tpl_reading = menu.addAction("Nova nota com template: Reading")
        action_tpl_concept = menu.addAction("Nova nota com template: Concept")
        action_tpl_conversation = menu.addAction("Nova nota com template: Conversation")

        selected = menu.exec(self.controls_menu_button.mapToGlobal(self.controls_menu_button.rect().bottomLeft()))
        if selected == action_summary:
            self._request_llm_generated_note("resumo")
        elif selected == action_questions:
            self._request_llm_generated_note("perguntas")
        elif selected == action_tpl_reading:
            self._create_template_note("reading_note.md", "reading_template")
        elif selected == action_tpl_concept:
            self._create_template_note("concept_note.md", "concept_template")
        elif selected == action_tpl_conversation:
            self._create_template_note("conversation.md", "conversation_template")

    def _open_note_tab(self):
        self.action_chat_toggle.setChecked(True)
        self.assistant_tabs.setVisible(True)
        self.assistant_tabs.setCurrentWidget(self.note_panel)

        if not self.note_title_input.text().strip():
            self.note_title_input.setText(f"Anotação - {self.current_book_title}")

        self.note_editor.setPlainText("Gerando template com contexto da sessão...")
        self._request_note_draft_from_llm()

    def _request_note_draft_from_llm(self):
        context = self._build_chapter_context()
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
        self.glados_controller.ask_glados(prompt, True, "Helio")

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
        content = self.note_editor.toPlainText().strip()

        if not title:
            QMessageBox.warning(self, "Título obrigatório", "Defina um título para salvar a anotação.")
            return
        if not content:
            QMessageBox.warning(self, "Conteúdo vazio", "Adicione conteúdo antes de salvar.")
            return

        note_path = self._write_note_to_personal_with_title(content, title)
        if not note_path:
            QMessageBox.warning(self, "Erro ao salvar", "Não foi possível criar a anotação no vault.")
            return

        if self._selected_excerpt_for_note:
            self._link_excerpt_to_note(note_path.stem, self._selected_excerpt_for_note)
            self._selected_excerpt_for_note = ""
            self._selected_excerpt_chapter_path = None

        self.chat_history.append(f"Sistema: Nota salva em {note_path.name}")
        QMessageBox.information(self, "Anotação salva", f"Nota criada em 05 - Pessoal/{note_path.name}")

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
        self._selected_excerpt_chapter_path = self.current_chapter_path
        self.note_title_input.setText(excerpt_title)
        self._open_note_tab()

    def _normalize_excerpt_title(self, selected_text: str, max_len: int = 80) -> str:
        text = re.sub(r"\s+", " ", selected_text.replace("\u2029", " ")).strip()
        return text[:max_len].strip()

    def _request_llm_generated_note(self, mode: str):
        if not self.glados_controller:
            QMessageBox.warning(self, "LLM indisponível", "Não foi possível acessar o controller da LLM.")
            return

        context = self._build_chapter_context()
        if not context:
            QMessageBox.warning(self, "Contexto indisponível", "Não foi possível montar contexto de capítulos.")
            return

        if mode == "resumo":
            instruction = (
                "Gere um resumo estruturado da sessão atual com: síntese, conceitos-chave, "
                "3 insights e 2 conexões com capítulos anteriores."
            )
        else:
            instruction = (
                "Gere perguntas de estudo da sessão atual: 8 perguntas (4 compreensão, 2 crítica, 2 aplicação) "
                "e um gabarito curto."
            )

        self._pending_note_request = {"mode": mode}
        prompt = f"{instruction}\n\n{context}"
        self.chat_history.append(f"Sistema: Solicitação de nota ({mode}) enviada para GLaDOS.")
        self.glados_controller.ask_glados(prompt, True, "Helio")

    def _build_chapter_context(self) -> str:
        if not self.current_chapter_path:
            return ""

        current_idx = -1
        for idx, chapter in enumerate(self.chapter_notes):
            if chapter["path"] == self.current_chapter_path:
                current_idx = idx
                break
        if current_idx < 0:
            return ""

        current_text = self.current_chapter_path.read_text(encoding="utf-8", errors="ignore")
        previous = self.chapter_notes[:current_idx]

        lines = []
        lines.append(f"Livro: {self.current_book_title}")
        lines.append(f"Página atual de leitura: {self.current_page}")
        lines.append("")
        lines.append(f"Capítulo atual: {self.current_chapter_path.name}")
        lines.append(self._truncate_text(current_text, 14000))
        lines.append("")
        lines.append("Capítulos anteriores:")

        if not previous:
            lines.append("- Nenhum capítulo anterior.")
        else:
            for item in previous:
                chapter_text = item["path"].read_text(encoding="utf-8", errors="ignore")
                snippet = self._truncate_text(chapter_text, 1800)
                lines.append(f"- {item['path'].name} (páginas {item['start_page']}-{item['end_page']})")
                lines.append(snippet)
                lines.append("")

        return "\n".join(lines)

    def _truncate_text(self, text: str, max_len: int) -> str:
        clean = text.strip()
        if len(clean) <= max_len:
            return clean
        return clean[:max_len] + "\n...[truncado]..."

    def _create_llm_note_from_response(self, llm_text: str, request: Dict[str, Any]):
        mode = request.get("mode", "resumo")
        title_mode = "Resumo de Sessão" if mode == "resumo" else "Perguntas de Sessão"
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

        note_path = self._write_note_to_personal("\n".join(content), f"llm-{mode}")
        if note_path:
            self._append_note_link_to_current_chapter(note_path)
            self.chat_history.append(f"Sistema: Nota criada em {note_path.name}")

    def _create_template_note(self, template_name: str, note_type: str):
        template_path = Path("src/cli/interactive/screens/glados_templates") / template_name
        if not template_path.exists():
            QMessageBox.warning(self, "Template não encontrado", f"Template ausente: {template_name}")
            return

        raw = template_path.read_text(encoding="utf-8", errors="ignore")
        title = f"{note_type} - {self.current_book_title}"
        rendered = self._render_template(raw, title)

        note_path = self._write_note_to_personal(rendered, note_type)
        if note_path:
            self._append_note_link_to_current_chapter(note_path)
            self.chat_history.append(f"Sistema: Nota de template criada em {note_path.name}")

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

    def _write_note_to_personal(self, content: str, slug: str) -> Optional[Path]:
        if not self.reading_controller or not getattr(self.reading_controller, "reading_manager", None):
            return None

        vault_path = Path(self.reading_controller.reading_manager.vault_path)
        personal_dir = vault_path / "05 - Pessoal"
        personal_dir.mkdir(parents=True, exist_ok=True)

        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        safe_book = self._sanitize_filename(self.current_book_title)[:60]
        filename = f"{stamp}-{slug}-{safe_book}.md"
        note_path = personal_dir / filename
        note_path.write_text(content, encoding="utf-8")
        return note_path

    def _write_note_to_personal_with_title(self, content: str, title: str) -> Optional[Path]:
        if not self.reading_controller or not getattr(self.reading_controller, "reading_manager", None):
            return None

        vault_path = Path(self.reading_controller.reading_manager.vault_path)
        personal_dir = vault_path / "05 - Pessoal"
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

    def _link_excerpt_to_note(self, note_stem: str, selected_text: str):
        target_path = self._selected_excerpt_chapter_path or self.current_chapter_path or self.book_source_path
        if not target_path or not target_path.exists():
            return

        excerpt = selected_text.replace("\u2029", "\n").strip()
        if not excerpt:
            return

        wikilink = f"[[05 - Pessoal/{note_stem}|{excerpt}]]"
        text = target_path.read_text(encoding="utf-8", errors="ignore")

        if wikilink in text:
            return

        if excerpt in text:
            updated = text.replace(excerpt, wikilink, 1)
        else:
            updated = text.rstrip() + f"\n\n- {wikilink}\n"
        target_path.write_text(updated, encoding="utf-8")

    def _append_note_link_to_current_chapter(self, note_path: Path):
        if not self.current_chapter_path or not self.current_chapter_path.exists():
            return

        relative_note = f"05 - Pessoal/{note_path.stem}"
        link_line = f"- [[{relative_note}|{note_path.stem}]]"
        text = self.current_chapter_path.read_text(encoding="utf-8", errors="ignore")
        if link_line in text:
            return

        section_header = "## 🔗 Notas da Sessão"
        header_pattern = re.compile(r"(?m)^##\s+🔗\s+Notas da Sessão\s*$")
        header_match = header_pattern.search(text)

        if not header_match:
            updated = text.rstrip() + f"\n\n{section_header}\n{link_line}\n"
            self.current_chapter_path.write_text(updated, encoding="utf-8")
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
        self.current_chapter_path.write_text(updated, encoding="utf-8")

    def _sanitize_filename(self, value: str) -> str:
        return re.sub(r"[^a-zA-Z0-9._-]+", "-", value).strip("-").lower() or "nota"

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
            return

        if not self.pomodoro.is_running or not self.pomodoro.start_time:
            total_seconds = self.pomodoro._get_duration_for_type("work")
            self.pomodoro_timer_label.setText(self._format_mmss(total_seconds))
            return

        now = time.time()
        elapsed = now - self.pomodoro.start_time - self.pomodoro.elapsed_paused
        total_seconds = self.pomodoro._get_duration_for_type(self.pomodoro.current_session_type)
        remaining = max(int(total_seconds - elapsed), 0)

        self.pomodoro_timer_label.setText(self._format_mmss(remaining))

    def _format_mmss(self, seconds: int) -> str:
        minutes, sec = divmod(max(seconds, 0), 60)
        return f"{minutes:02d}:{sec:02d}"

    def _on_back_clicked(self):
        self._finalize_session()
        self.navigate_to.emit("dashboard")

    def _on_end_session_clicked(self):
        self._finalize_session()
        self.navigate_to.emit("dashboard")

    def _sync_progress_realtime(self):
        if self._session_closed:
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
        self._finalize_session()

        if self.ui_timer.isActive():
            self.ui_timer.stop()

        if self.glados_controller:
            try:
                self.glados_controller.response_ready.disconnect(self._on_llm_response)
                self.glados_controller.processing_started.disconnect(self._on_llm_processing_started)
                self.glados_controller.processing_completed.disconnect(self._on_llm_processing_completed)
                self.glados_controller.error_occurred.disconnect(self._on_llm_error)
            except Exception:
                pass
