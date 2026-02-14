"""
View de sessão de leitura com Pomodoro e chat LLM.
"""
from __future__ import annotations

import logging
import time
from typing import Any, Dict, Optional

from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtWidgets import (
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QProgressBar,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from core.modules.pomodoro_timer import PomodoroTimer

logger = logging.getLogger("GLaDOS.UI.SessionView")


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
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(14)

        header = QHBoxLayout()
        self.title_label = QLabel("Sessão de leitura")
        self.title_label.setObjectName("session_title")

        self.progress_label = QLabel("Página 1 de ?")
        self.progress_label.setObjectName("session_progress_label")

        self.back_button = QPushButton("Voltar para Dashboard")
        self.back_button.setObjectName("secondary_button")
        self.back_button.setFixedHeight(36)

        header.addWidget(self.title_label, 1)
        header.addWidget(self.progress_label)
        header.addWidget(self.back_button)
        root.addLayout(header)

        body = QHBoxLayout()
        body.setSpacing(14)

        reading_panel = QFrame()
        reading_panel.setObjectName("session_reading_panel")
        reading_layout = QVBoxLayout(reading_panel)
        reading_layout.setContentsMargins(12, 12, 12, 12)
        reading_layout.setSpacing(10)

        pages_grid = QGridLayout()
        pages_grid.setHorizontalSpacing(10)
        pages_grid.setVerticalSpacing(6)

        self.left_page_title = QLabel("Página 1")
        self.right_page_title = QLabel("Página 2")
        self.left_page_text = QTextEdit()
        self.right_page_text = QTextEdit()
        for page in (self.left_page_text, self.right_page_text):
            page.setReadOnly(True)
            page.setObjectName("session_page_text")

        pages_grid.addWidget(self.left_page_title, 0, 0)
        pages_grid.addWidget(self.right_page_title, 0, 1)
        pages_grid.addWidget(self.left_page_text, 1, 0)
        pages_grid.addWidget(self.right_page_text, 1, 1)
        reading_layout.addLayout(pages_grid)

        nav = QHBoxLayout()
        self.prev_pages_button = QPushButton("◀ Páginas anteriores")
        self.next_pages_button = QPushButton("Próximas páginas ▶")
        self.page_pair_label = QLabel("1-2")
        self.page_pair_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        nav.addWidget(self.prev_pages_button)
        nav.addWidget(self.page_pair_label, 1)
        nav.addWidget(self.next_pages_button)
        reading_layout.addLayout(nav)

        self.chat_toggle_button = QPushButton("Mostrar Chat LLM")
        self.chat_toggle_button.setCheckable(True)
        self.chat_toggle_button.setObjectName("secondary_button")
        reading_layout.addWidget(self.chat_toggle_button, alignment=Qt.AlignmentFlag.AlignLeft)

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
        self.chat_panel.setVisible(False)
        reading_layout.addWidget(self.chat_panel, 1)

        body.addWidget(reading_panel, 3)

        pomodoro_panel = QFrame()
        pomodoro_panel.setObjectName("session_pomodoro_panel")
        pomodoro_layout = QVBoxLayout(pomodoro_panel)
        pomodoro_layout.setContentsMargins(12, 12, 12, 12)
        pomodoro_layout.setSpacing(8)

        pomodoro_title = QLabel("Pomodoro")
        pomodoro_title.setObjectName("session_side_title")
        self.pomodoro_timer_label = QLabel("25:00")
        self.pomodoro_timer_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.pomodoro_timer_label.setObjectName("session_pomodoro_timer")

        self.pomodoro_progress = QProgressBar()
        self.pomodoro_progress.setRange(0, 100)
        self.pomodoro_progress.setValue(0)

        self.pomodoro_mode = QComboBox()
        self.pomodoro_mode.addItem("Foco (25m)", "work")
        self.pomodoro_mode.addItem("Pausa curta (5m)", "short_break")
        self.pomodoro_mode.addItem("Pausa longa (15m)", "long_break")

        self.pomodoro_start = QPushButton("Iniciar")
        self.pomodoro_pause = QPushButton("Pausar")
        self.pomodoro_resume = QPushButton("Retomar")
        self.pomodoro_stop = QPushButton("Parar")
        self.pomodoro_state_label = QLabel("Parado")

        controls = QGridLayout()
        controls.addWidget(self.pomodoro_start, 0, 0)
        controls.addWidget(self.pomodoro_pause, 0, 1)
        controls.addWidget(self.pomodoro_resume, 1, 0)
        controls.addWidget(self.pomodoro_stop, 1, 1)

        pomodoro_layout.addWidget(pomodoro_title)
        pomodoro_layout.addWidget(self.pomodoro_timer_label)
        pomodoro_layout.addWidget(self.pomodoro_progress)
        pomodoro_layout.addWidget(self.pomodoro_mode)
        pomodoro_layout.addLayout(controls)
        pomodoro_layout.addWidget(self.pomodoro_state_label)
        pomodoro_layout.addStretch()

        body.addWidget(pomodoro_panel, 1)
        root.addLayout(body, 1)

    def _setup_connections(self):
        self.back_button.clicked.connect(lambda: self.navigate_to.emit("dashboard"))
        self.prev_pages_button.clicked.connect(self._go_prev_pages)
        self.next_pages_button.clicked.connect(self._go_next_pages)
        self.chat_toggle_button.toggled.connect(self._toggle_chat)
        self.chat_send_button.clicked.connect(self._send_chat_message)
        self.chat_input.returnPressed.connect(self._send_chat_message)

        self.pomodoro_start.clicked.connect(self._start_pomodoro)
        self.pomodoro_pause.clicked.connect(self._pause_pomodoro)
        self.pomodoro_resume.clicked.connect(self._resume_pomodoro)
        self.pomodoro_stop.clicked.connect(self._stop_pomodoro)

        if self.glados_controller:
            self.glados_controller.response_ready.connect(self._on_llm_response)
            self.glados_controller.processing_started.connect(self._on_llm_processing_started)
            self.glados_controller.processing_completed.connect(self._on_llm_processing_completed)
            self.glados_controller.error_occurred.connect(self._on_llm_error)

    def on_view_activated(self):
        self.refresh_reading_context()
        self._tick_ui()

    def refresh_reading_context(self):
        book_id = self._resolve_book_id()
        progress = self._get_progress(book_id) if book_id else {}

        if progress:
            self.current_book_id = progress.get("book_id") or progress.get("id") or book_id
            self.current_book_title = progress.get("title", "Sessão de leitura")
            current_page, total_pages = self._parse_progress(progress.get("progress", "1/0"))
            self.current_page = max(current_page, 1)
            self.total_pages = max(total_pages, 0)
        else:
            self.current_book_id = None
            self.current_book_title = "Sessão de leitura"
            self.current_page = 1
            self.total_pages = 0

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

        self.prev_pages_button.setEnabled(left > 1)
        if self.total_pages > 0:
            self.next_pages_button.setEnabled(right < self.total_pages)
        else:
            self.next_pages_button.setEnabled(True)

    def _build_page_content(self, page_number: int) -> str:
        if self.total_pages > 0 and page_number > self.total_pages:
            return "Fim do livro."

        lines = [
            f"{self.current_book_title}",
            "",
            f"Página {page_number}",
            "",
            "Visualização de leitura inicial.",
            "Conteúdo textual completo do livro será integrado na próxima etapa.",
        ]

        if page_number == self.current_page:
            lines.extend(["", "Você parou nesta região na última sessão."])

        return "\n".join(lines)

    def _go_prev_pages(self):
        if self.left_page > 1:
            self.left_page = max(1, self.left_page - 2)
            self._refresh_pages()

    def _go_next_pages(self):
        next_left = self.left_page + 2
        if self.total_pages > 0 and next_left > self.total_pages:
            return
        self.left_page = next_left
        self._refresh_pages()

    def _toggle_chat(self, checked: bool):
        self.chat_panel.setVisible(checked)
        self.chat_toggle_button.setText("Ocultar Chat LLM" if checked else "Mostrar Chat LLM")

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

    def _on_llm_response(self, payload: Dict[str, Any]):
        text = payload.get("text", "")
        if text:
            self.chat_history.append(f"GLaDOS: {text}")
        self.chat_status_label.setText("LLM pronta")

    def _on_llm_processing_started(self, _task_type: str, message: str):
        self.chat_status_label.setText(message)

    def _on_llm_processing_completed(self, _task_type: str):
        self.chat_status_label.setText("LLM pronta")

    def _on_llm_error(self, error_type: str, error_message: str, _context: str):
        self.chat_history.append(f"GLaDOS [{error_type}]: {error_message}")
        self.chat_status_label.setText("Erro na LLM")

    def _start_pomodoro(self):
        if not self.pomodoro:
            self.pomodoro_state_label.setText("Pomodoro indisponível")
            return
        session_type = self.pomodoro_mode.currentData()
        started = self.pomodoro.start(session_type=session_type, discipline="leitura")
        self.pomodoro_state_label.setText("Rodando" if started else "Já em execução")
        self._tick_ui()

    def _pause_pomodoro(self):
        if not self.pomodoro:
            return
        self.pomodoro_state_label.setText("Pausado" if self.pomodoro.pause() else self.pomodoro_state_label.text())
        self._tick_ui()

    def _resume_pomodoro(self):
        if not self.pomodoro:
            return
        self.pomodoro_state_label.setText("Rodando" if self.pomodoro.resume() else self.pomodoro_state_label.text())
        self._tick_ui()

    def _stop_pomodoro(self):
        if not self.pomodoro:
            return
        self.pomodoro.stop(save_stats=True)
        self.pomodoro_state_label.setText("Parado")
        self._tick_ui()

    def _tick_ui(self):
        if not self.pomodoro:
            self.pomodoro_timer_label.setText("--:--")
            self.pomodoro_progress.setValue(0)
            return

        if not self.pomodoro.is_running or not self.pomodoro.start_time:
            total_seconds = self.pomodoro._get_duration_for_type(self.pomodoro_mode.currentData())
            self.pomodoro_timer_label.setText(self._format_mmss(total_seconds))
            self.pomodoro_progress.setValue(0)
            if self.pomodoro_state_label.text() not in ("Pomodoro indisponível", "Parado"):
                self.pomodoro_state_label.setText("Parado")
            return

        now = time.time()
        elapsed = now - self.pomodoro.start_time - self.pomodoro.elapsed_paused
        total_seconds = self.pomodoro._get_duration_for_type(self.pomodoro.current_session_type)
        remaining = max(int(total_seconds - elapsed), 0)
        progress = int(min(100, (elapsed / total_seconds) * 100)) if total_seconds > 0 else 0

        self.pomodoro_timer_label.setText(self._format_mmss(remaining))
        self.pomodoro_progress.setValue(progress)
        self.pomodoro_state_label.setText("Pausado" if self.pomodoro.is_paused else "Rodando")

    def _format_mmss(self, seconds: int) -> str:
        minutes, sec = divmod(max(seconds, 0), 60)
        return f"{minutes:02d}:{sec:02d}"

    def cleanup(self):
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
