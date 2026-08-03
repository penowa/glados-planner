"""DynamicEventCard: shows imminent event (class/reading) or weekly summary.

Minimal, safe implementation matching requested API and signals.
"""
from datetime import datetime, timedelta, date
import logging
import random
import re
from pathlib import Path

from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QRectF, QPropertyAnimation, QEvent
from PyQt6.QtGui import QPixmap, QPainter, QPen, QColor, QFont
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QStackedWidget, QScrollArea, QGridLayout, QSizePolicy, QFrame,
    QMenu, QGraphicsOpacityEffect, QScrollBar, QTextBrowser, QLineEdit, QApplication,
)

from ui.utils.nerd_icons import NerdIcons, nerd_font
from ui.utils.config_manager import ConfigManager

from ui.utils import book_helpers

logger = logging.getLogger("GLaDOS.UI.DynamicEventCard")
AULAS_AUTHOR = "Aulas"

try:
    from core.config.settings import settings as core_settings
except Exception:
    core_settings = None


class LeituraProgressRing(QWidget):
    """Anel circular de progresso para a página de leitura."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._progress = 0.0
        self.setMinimumSize(160, 160)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self._label = "0/0"
        self._subtitle = "Páginas"

    def set_progress(self, fraction: float, label: str = "0/0", subtitle: str = "Páginas"):
        self._progress = max(0.0, min(1.0, float(fraction)))
        self._label = label
        self._subtitle = subtitle
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        side = min(self.width(), self.height())
        margin = 12
        diameter = max(80, side - margin * 2)
        x = (self.width() - diameter) / 2
        y = (self.height() - diameter) / 2
        rect = QRectF(x, y, diameter, diameter)

        track_pen = QPen(QColor("#3F4B5C"), 14)
        track_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(track_pen)
        painter.drawArc(rect, 0, 360 * 16)

        if self._progress > 0:
            progress_pen = QPen(QColor("#72B0F0"), 14)
            progress_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            painter.setPen(progress_pen)
            span = int(360 * 16 * self._progress)
            painter.drawArc(rect, 90 * 16, -span)

        painter.setPen(QColor("#E8EDF5"))
        font = QFont()
        font.setBold(True)
        font.setPointSize(12)
        painter.setFont(font)
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, self._label)

        subtitle_rect = QRectF(x, y + diameter * 0.62, diameter, diameter * 0.3)
        font.setBold(False)
        font.setPointSize(9)
        painter.setFont(font)
        painter.drawText(subtitle_rect, Qt.AlignmentFlag.AlignCenter, self._subtitle)

        painter.end()


class WeeklySessionBars(QWidget):
    """Gráfico de barras simples para páginas planejadas ao livro na semana."""

    WEEKDAY_LABELS = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]

    def __init__(self, parent=None):
        super().__init__(parent)
        self._counts = [0] * 7
        self.setMinimumHeight(180)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def set_counts(self, counts: list[int]):
        self._counts = [max(0, int(value)) for value in (counts or [])[:7]]
        while len(self._counts) < 7:
            self._counts.append(0)
        self.update()

    def _bar_color(self, count: int) -> QColor:
        if count > 41:
            return QColor("#E25A5A")
        if count >= 21:
            return QColor("#E0C14A")
        if count >= 10:
            return QColor("#5EBF7A")
        return QColor("#4B5565")

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = self.rect().adjusted(8, 8, -8, -8)
        title_font = QFont()
        title_font.setBold(True)
        title_font.setPointSize(10)
        painter.setFont(title_font)
        painter.setPen(QColor("#DDE6F5"))
        painter.drawText(rect.adjusted(0, 0, 0, -rect.height() + 16), Qt.AlignmentFlag.AlignLeft, "Páginas planejadas por dia")

        chart_top = rect.top() + 24
        chart_bottom = rect.bottom() - 48
        chart_height = max(1, chart_bottom - chart_top)
        chart_width = rect.width()
        slot_width = chart_width / 7.0
        max_pages = max(max(self._counts), 41.0)

        label_font = QFont()
        label_font.setPointSize(8)
        painter.setFont(label_font)

        for index, pages in enumerate(self._counts):
            slot_left = rect.left() + index * slot_width
            bar_area_width = slot_width * 0.56
            bar_left = slot_left + (slot_width - bar_area_width) / 2
            bar_height = 0 if pages <= 0 else int((pages / max_pages) * (chart_height - 22))
            bar_height = max(10 if pages > 0 else 0, bar_height)
            bar_rect = QRectF(bar_left, chart_bottom - bar_height, bar_area_width, bar_height)

            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(self._bar_color(pages))
            painter.drawRoundedRect(bar_rect, 4, 4)

            painter.setPen(QColor("#DDE6F5"))
            painter.drawText(
                QRectF(slot_left, chart_bottom + 2, slot_width, 14),
                Qt.AlignmentFlag.AlignCenter,
                self.WEEKDAY_LABELS[index],
            )
            painter.setPen(QColor("#C4D0E0"))
            painter.drawText(
                QRectF(slot_left, chart_top - 2, slot_width, 14),
                Qt.AlignmentFlag.AlignCenter,
                f"{pages:d}" if pages > 0 else "0",
            )

        legend_y = rect.bottom() - 22
        legend_items = [
            ("10-20", "#5EBF7A"),
            ("21-40", "#E0C14A"),
            ("41+", "#E25A5A"),
        ]
        legend_font = QFont()
        legend_font.setPointSize(8)
        painter.setFont(legend_font)
        legend_width = rect.width() / len(legend_items)
        for index, (label, color) in enumerate(legend_items):
            left = rect.left() + index * legend_width
            swatch = QRectF(left + 12, legend_y, 10, 10)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(color))
            painter.drawRoundedRect(swatch, 2, 2)
            painter.setPen(QColor("#C4D0E0"))
            painter.drawText(
                QRectF(left + 26, legend_y - 2, legend_width - 30, 14),
                Qt.AlignmentFlag.AlignLeft,
                label,
            )

        painter.end()


class DynamicEventCard(QWidget):
    navigate_to = pyqtSignal(str)
    open_session = pyqtSignal(dict)
    open_class_notes = pyqtSignal(dict)
    open_discipline_chat = pyqtSignal(str)

    def __init__(
        self,
        agenda_backend=None,
        reading_controller=None,
        book_controller=None,
        daily_checkin_controller=None,
        vault_controller=None,
        parent=None,
    ):
        super().__init__(parent)

        self.agenda_backend = agenda_backend
        self.reading_controller = reading_controller
        self.book_controller = book_controller
        self.daily_checkin_controller = daily_checkin_controller
        self.vault_controller = vault_controller
        self.config_manager = ConfigManager.instance()

        self._current_state = "base"  # base | aula | intervalo | leitura
        self._current_event = None
        self._is_updating = False
        self._leitura_pomodoro_profiles = []
        self._selected_leitura_pomodoro_profile_id = ""
        self._assistant_name_override = ""
        self._user_name_override = ""
        self._intervalo_library_mode = "livros"
        self._intervalo_books_cache: list[dict] = []
        self._intervalo_visible_slots = 6
        self._intervalo_scroll_offset = 0
        self._intervalo_all_books: list[dict] = []
        self._intervalo_chat_messages: list[dict] = []
        self._intervalo_chat_full_text = ""
        self._intervalo_chat_index = 0
        self._intervalo_chat_active = False
        self._intervalo_input_buffer = ""
        self._intervalo_chat_cursor_visible = True
        self._intervalo_assistant_reply_index = 0
        self._intervalo_pending_assistant_message: dict | None = None
        self._intervalo_quote_data: dict | None = None
        self._base_rendered = False
        self._intervalo_chat_started_at: datetime | None = None

        self._build_ui()
        self._connect_signals()
        self._intervalo_chat_timer = QTimer(self)
        self._intervalo_chat_timer.setInterval(120)
        self._intervalo_chat_timer.timeout.connect(self._advance_intervalo_chat_typing)
        self._intervalo_cursor_timer = QTimer(self)
        self._intervalo_cursor_timer.setInterval(500)
        self._intervalo_cursor_timer.timeout.connect(self._toggle_intervalo_chat_cursor)
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._update_state)
        self._timer.start(30000)  # 30 seconds

        # Initial update
        self._update_state()

    def _build_ui(self):
        self.setObjectName("dynamic_event_card")
        self.setMinimumHeight(400)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        self.setStyleSheet("background: transparent;")

        self.stack = QStackedWidget()
        self.stack.setStyleSheet("background: transparent;")

        # Base page now hosts the interval state
        self.base_page = QWidget()
        self.base_page.setStyleSheet("background: transparent;")
        b_layout = QVBoxLayout(self.base_page)
        b_layout.setContentsMargins(12, 12, 12, 12)
        b_layout.setSpacing(0)

        self.intervalo_terminal_frame = QFrame()
        self.intervalo_terminal_frame.setObjectName("intervalo_terminal_frame")
        self.intervalo_terminal_frame.setStyleSheet(
            "QFrame#intervalo_terminal_frame { background: transparent; border: 1px solid rgba(42, 52, 64, 0.75); border-radius: 18px; }"
        )
        terminal_layout = QVBoxLayout(self.intervalo_terminal_frame)
        terminal_layout.setContentsMargins(16, 14, 16, 14)
        terminal_layout.setSpacing(0)

        self.intervalo_text_panel = QWidget()
        right_layout = QVBoxLayout(self.intervalo_text_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(4)

        self.intervalo_chat_view = QTextBrowser()
        self.intervalo_chat_view.setFrameShape(QFrame.Shape.NoFrame)
        self.intervalo_chat_view.setStyleSheet(
            "QTextBrowser { background: transparent; border: none; color: #D7DCE6; padding: 0; }"
        )
        self.intervalo_chat_view.setFont(nerd_font(10))
        self.intervalo_chat_view.setMinimumHeight(280)
        self.intervalo_chat_view.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.intervalo_chat_view.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.intervalo_chat_view.setOpenExternalLinks(False)
        self.intervalo_chat_view.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        right_layout.addWidget(self.intervalo_chat_view, 1)

        self.intervalo_input_line = QLineEdit()
        self.intervalo_input_line.setPlaceholderText("Digite sua mensagem...")
        self.intervalo_input_line.setFixedHeight(34)
        self.intervalo_input_line.setStyleSheet(
            "QLineEdit { background: #121828; border: 1px solid #31415C; border-radius: 12px; color: #D7DCE6; padding: 8px 10px; }"
        )
        self.intervalo_input_line.returnPressed.connect(self._on_intervalo_input_submitted)
        self.intervalo_input_line.setVisible(False)
        self.intervalo_input_line.setEnabled(False)
        right_layout.addWidget(self.intervalo_input_line, 0)

        terminal_layout.addWidget(self.intervalo_text_panel, 1)
        b_layout.addWidget(self.intervalo_terminal_frame, 1)

        # Aula page
        self.aula_page = QWidget()
        a_layout = QVBoxLayout(self.aula_page)
        a_layout.setContentsMargins(12, 12, 12, 12)
        self.aula_header = QLabel("🧑‍🏫 Aula")
        self.aula_header.setFont(nerd_font(11, weight=600))
        a_layout.addWidget(self.aula_header)

        self.aula_books_area = QScrollArea()
        self.aula_books_area.setWidgetResizable(True)
        self.aula_books_widget = QWidget()
        self.aula_books_layout = QGridLayout(self.aula_books_widget)
        self.aula_books_layout.setSpacing(8)
        self.aula_books_area.setWidget(self.aula_books_widget)
        a_layout.addWidget(self.aula_books_area)

        # Action buttons
        a_buttons = QHBoxLayout()
        self.a_open_notes_btn = QPushButton("Anotações da aula")
        self.a_open_chat_btn = QPushButton("Chat da disciplina")
        a_buttons.addWidget(self.a_open_notes_btn)
        a_buttons.addWidget(self.a_open_chat_btn)
        a_layout.addLayout(a_buttons)

        # Leitura page
        self.leitura_page = QWidget()
        l_layout = QVBoxLayout(self.leitura_page)
        l_layout.setContentsMargins(12, 12, 12, 12)
        l_layout.setSpacing(12)

        self.leitura_main_row = QWidget()
        main_row_layout = QHBoxLayout(self.leitura_main_row)
        main_row_layout.setContentsMargins(0, 0, 0, 0)
        main_row_layout.setSpacing(16)

        cover_frame = QFrame()
        cover_frame.setObjectName("leitura_cover_frame")
        cover_frame.setStyleSheet(
            "QFrame#leitura_cover_frame { border: 1px solid #5B5B5B; border-radius: 6px; padding: 12px; }"
        )
        cover_layout = QVBoxLayout(cover_frame)
        cover_layout.setContentsMargins(0, 0, 0, 0)
        cover_layout.setSpacing(8)
        self.leitura_cover = QLabel()
        self.leitura_cover.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Minimum)
        self.leitura_cover.setMaximumSize(180, 220)
        self.leitura_cover.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.leitura_book_title = QLabel("Título do livro")
        self.leitura_book_title.setWordWrap(True)
        self.leitura_book_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.leitura_book_title.setFont(nerd_font(11, weight=600))
        cover_layout.addWidget(self.leitura_cover, alignment=Qt.AlignmentFlag.AlignCenter)
        cover_layout.addWidget(self.leitura_book_title)

        details_widget = QWidget()
        details_layout = QVBoxLayout(details_widget)
        details_layout.setContentsMargins(0, 0, 0, 0)
        details_layout.setSpacing(8)

        self.leitura_properties_label = QLabel("Propriedades do livro")
        self.leitura_properties_label.setTextFormat(Qt.TextFormat.RichText)
        self.leitura_properties_label.setWordWrap(True)
        self.leitura_properties_label.setText('Carregando propriedades...')
        details_layout.addWidget(self.leitura_properties_label)

        self.leitura_weekly_sessions_chart = WeeklySessionBars()
        self.leitura_weekly_sessions_chart_opacity = QGraphicsOpacityEffect(self.leitura_weekly_sessions_chart)
        self.leitura_weekly_sessions_chart.setGraphicsEffect(self.leitura_weekly_sessions_chart_opacity)
        self.leitura_weekly_sessions_chart_fade = QPropertyAnimation(
            self.leitura_weekly_sessions_chart_opacity, b"opacity", self
        )
        self.leitura_weekly_sessions_chart_fade.setDuration(260)
        self.leitura_weekly_sessions_chart_fade.setStartValue(0.0)
        self.leitura_weekly_sessions_chart_fade.setEndValue(1.0)
        details_layout.addWidget(self.leitura_weekly_sessions_chart)

        self.leitura_start_btn = QPushButton("Iniciar Sessão Agendada")
        self.leitura_start_btn.setObjectName("leitura_start_btn")
        self.leitura_start_btn.setFixedHeight(40)
        self.leitura_start_btn.setStyleSheet(
            "QPushButton#leitura_start_btn { font-weight: 700; }"
        )
        details_layout.addStretch()
        details_layout.addWidget(self.leitura_start_btn)

        progress_panel = QFrame()
        progress_panel.setObjectName("leitura_progress_panel")
        progress_panel.setStyleSheet(
            "QFrame#leitura_progress_panel { border: 1px solid #5B5B5B; border-radius: 8px; padding: 12px; }"
        )
        progress_layout = QVBoxLayout(progress_panel)
        progress_layout.setContentsMargins(0, 0, 0, 0)
        progress_layout.setSpacing(10)

        self.leitura_progress_ring = LeituraProgressRing()
        self.leitura_progress_status = QLabel("Progresso de leitura")
        self.leitura_progress_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.leitura_progress_status.setStyleSheet("color: #C7D2E0; font-size: 12px;")
        self.leitura_progress_summary_label = QLabel("—")
        self.leitura_progress_summary_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.leitura_progress_summary_label.setStyleSheet("font-weight: 600; font-size: 12px;")

        self.leitura_pomodoro_chip_row = QWidget()
        chip_layout = QHBoxLayout(self.leitura_pomodoro_chip_row)
        chip_layout.setContentsMargins(0, 0, 0, 0)
        chip_layout.setSpacing(8)
        self.leitura_pomodoro_session_chip = QLabel("Sessão 25m")
        self.leitura_pomodoro_interval_chip = QLabel("Intervalo 5m")
        self.leitura_pomodoro_cycles_chip = QLabel("Ciclos 4")
        for chip in (
            self.leitura_pomodoro_session_chip,
            self.leitura_pomodoro_interval_chip,
            self.leitura_pomodoro_cycles_chip,
        ):
            chip.setStyleSheet(
                "background-color: #2B3342; border-radius: 12px; padding: 8px 12px; color: #D7E0F2; font-size: 11px;"
            )
            chip.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
            chip.setAlignment(Qt.AlignmentFlag.AlignCenter)
            chip_layout.addWidget(chip)

        progress_layout.addWidget(self.leitura_progress_ring, alignment=Qt.AlignmentFlag.AlignCenter)
        progress_layout.addWidget(self.leitura_progress_status)
        progress_layout.addWidget(self.leitura_progress_summary_label)
        progress_layout.addWidget(self.leitura_pomodoro_chip_row)

        self.leitura_pomodoro_profile_button = QPushButton("Selecionar perfil")
        self.leitura_pomodoro_profile_button.setObjectName("library_chip_button")
        self.leitura_pomodoro_profile_button.setFixedHeight(34)
        self.leitura_pomodoro_profile_button.setToolTip(
            "Escolha um perfil Pomodoro com base na duração da sessão de leitura"
        )
        progress_layout.addWidget(self.leitura_pomodoro_profile_button)

        self.leitura_session_pages_label = QLabel("Páginas desta sessão: —")
        self.leitura_session_pages_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.leitura_session_pages_label.setStyleSheet("color: #C4D0E0; font-size: 11px;")
        progress_layout.addWidget(self.leitura_session_pages_label)
        progress_layout.addStretch(1)

        main_row_layout.addWidget(cover_frame, 0)
        main_row_layout.addWidget(details_widget, 1)
        main_row_layout.addWidget(progress_panel, 0)
        l_layout.addWidget(self.leitura_main_row)

        self.stack.addWidget(self.base_page)
        self.stack.addWidget(self.aula_page)
        self.stack.addWidget(self.leitura_page)

        layout.addWidget(self.stack)

    def _connect_signals(self):
        if self.agenda_backend and hasattr(self.agenda_backend, 'agenda_updated'):
            try:
                self.agenda_backend.agenda_updated.connect(lambda *a: self._update_state())
            except Exception:
                pass
        if self.daily_checkin_controller and hasattr(self.daily_checkin_controller, 'checkin_completed'):
            try:
                self.daily_checkin_controller.checkin_completed.connect(lambda *a: self._update_state())
            except Exception:
                pass
        if self.reading_controller and hasattr(self.reading_controller, 'stats_updated'):
            try:
                self.reading_controller.stats_updated.connect(lambda *a: self._update_state())
            except Exception:
                pass

        self.a_open_notes_btn.clicked.connect(self._emit_open_notes)
        self.a_open_chat_btn.clicked.connect(self._emit_open_chat)
        self.leitura_start_btn.clicked.connect(self._emit_open_session)
        self.leitura_pomodoro_profile_button.clicked.connect(self._show_leitura_pomodoro_profiles_menu)
        self._set_intervalo_library_mode(self._intervalo_library_mode)

    def _update_state(self):
        # prevent re-entrant updates triggered by signals during data access
        if getattr(self, '_is_updating', False):
            return
        self._is_updating = True
        now = datetime.now()
        window_end = now + timedelta(minutes=15)
        ongoing = []
        upcoming = []

        try:
            # Try to get today's events
            for day_offset in (0, 1):
                d = (date.today() + timedelta(days=day_offset)).strftime("%Y-%m-%d")
                if self.agenda_backend and hasattr(self.agenda_backend, 'get_day_events'):
                    events = self.agenda_backend.get_day_events(d) or []
                elif self.agenda_backend and hasattr(self.agenda_backend, 'agenda_manager') and hasattr(self.agenda_backend.agenda_manager, 'get_day_events'):
                    events = self.agenda_backend.agenda_manager.get_day_events(d) or []
                else:
                    events = []

                for ev in events:
                    if ev.get('completed', False):
                        continue
                    try:
                        start = ev.get('start')
                        if not start:
                            continue
                        ev_start = datetime.fromisoformat(start.replace('Z', '+00:00'))
                        end = ev.get('end')
                        ev_end = None
                        if end:
                            try:
                                ev_end = datetime.fromisoformat(end.replace('Z', '+00:00'))
                            except Exception:
                                ev_end = None

                        if ev_end and ev_start <= now <= ev_end:
                            ongoing.append((ev_start, ev))
                            continue

                        if ev_start >= now and ev_start <= window_end:
                            upcoming.append((ev_start, ev))
                    except Exception:
                        continue
        except Exception:
            # Log error but avoid deep recursion in logging handlers
            logger.error("Erro ao buscar eventos para DynamicEventCard", exc_info=True)
        finally:
            self._is_updating = False

        chosen = None
        if ongoing:
            ongoing.sort(key=lambda t: t[0])
            chosen = ongoing[0][1]
        elif upcoming:
            upcoming.sort(key=lambda t: t[0])
            chosen = upcoming[0][1]

        new_state = 'base'
        if chosen:
            etype = self._normalized_event_type(chosen)
            if etype == 'aula':
                new_state = 'aula'
            elif etype == 'intervalo':
                new_state = 'intervalo'
            elif etype == 'leitura':
                new_state = 'leitura'

        if new_state == self._current_state and chosen == self._current_event:
            if new_state == "base" and not self._base_rendered:
                self._render_base()
            if new_state == "intervalo":
                self._refresh_intervalo_library_content()
            return

        self._current_state = new_state
        self._current_event = chosen

        if new_state == 'base':
            self._render_base()
            self.stack.setCurrentWidget(self.base_page)
        elif new_state == 'aula':
            self._render_aula(chosen)
            self.stack.setCurrentWidget(self.aula_page)
        elif new_state == 'intervalo':
            self._render_intervalo(chosen)
            self.stack.setCurrentWidget(self.base_page)
        elif new_state == 'leitura':
            self._render_leitura(chosen)
            self.stack.setCurrentWidget(self.leitura_page)

    def _render_base(self):
        self._base_rendered = True
        self._render_intervalo(self._current_event)
        if hasattr(self, "intervalo_input_line"):
            self.intervalo_input_line.setVisible(False)
            self.intervalo_input_line.setEnabled(False)

    def _progress_value(self, progress, key: str, default=None):
        if isinstance(progress, dict):
            return progress.get(key, default)
        return getattr(progress, key, default)

    def _parse_datetime_value(self, value) -> datetime | None:
        if not value:
            return None
        try:
            text = str(value).strip()
            if not text:
                return None
            return datetime.fromisoformat(text.replace('Z', '+00:00'))
        except Exception:
            return None

    def _normalized_event_type(self, event: dict | None) -> str:
        if not isinstance(event, dict):
            return ""

        metadata = event.get("metadata") if isinstance(event.get("metadata"), dict) else {}
        candidates = [
            event.get("type"),
            event.get("event_type"),
            event.get("state"),
            event.get("subtype"),
            metadata.get("type"),
            metadata.get("event_type"),
            metadata.get("state"),
            metadata.get("subtype"),
        ]

        normalized = ""
        for raw_value in candidates:
            normalized = str(raw_value or "").strip().lower()
            if normalized:
                break

        if not normalized:
            return ""

        aliases = {
            "aula": "aula",
            "aulas": "aula",
            "class": "aula",
            "lecture": "aula",
            "leitura": "leitura",
            "reading": "leitura",
            "intervalo": "intervalo",
            "interval": "intervalo",
            "pausa": "intervalo",
            "pause": "intervalo",
            "break": "intervalo",
            "interlude": "intervalo",
        }
        return aliases.get(normalized, normalized)

    def _assistant_display_name(self) -> str:
        if self._assistant_name_override.strip():
            return self._assistant_name_override.strip()
        try:
            if core_settings and getattr(core_settings, "llm", None) and getattr(core_settings.llm, "glados", None):
                configured = str(core_settings.llm.glados.glados_name or "").strip()
                if configured:
                    return configured
        except Exception:
            pass
        return "GLaDOS"

    def _user_display_name(self) -> str:
        if self._user_name_override.strip():
            return self._user_name_override.strip()
        try:
            if core_settings and getattr(core_settings, "llm", None) and getattr(core_settings.llm, "glados", None):
                configured = str(core_settings.llm.glados.user_name or "").strip()
                if configured:
                    return configured
        except Exception:
            pass
        return "Usuário"

    def eventFilter(self, watched, event):
        if self._current_state == "intervalo" and event.type() == QEvent.Type.KeyPress:
            if self._handle_intervalo_keypress(event):
                return True
        return super().eventFilter(watched, event)

    def update_identity(self, user_name: str | None = None, assistant_name: str | None = None):
        if user_name is not None:
            normalized_user = str(user_name).strip()
            if normalized_user:
                self._user_name_override = normalized_user
        if assistant_name is not None:
            normalized = str(assistant_name).strip()
            if normalized:
                self._assistant_name_override = normalized
        if self._current_state == "intervalo":
            self._render_intervalo(self._current_event)

    def _set_intervalo_library_mode(self, mode: str):
        normalized = "aulas" if str(mode).strip().lower() == "aulas" else "livros"
        self._intervalo_library_mode = normalized
        for current_mode, button in getattr(self, "intervalo_mode_buttons", {}).items():
            button.setChecked(current_mode == normalized)
            button.setProperty("activeFilter", "true" if current_mode == normalized else "false")
            button.style().unpolish(button)
            button.style().polish(button)
            button.update()
        self._refresh_intervalo_library_content()

    def _intervalo_book_sort_key(self, item: dict):
        last_read = item.get("last_read") or item.get("last_activity") or item.get("registered_at")
        ts = last_read.timestamp() if isinstance(last_read, datetime) else 0.0
        return (ts, str(item.get("title", "")).lower())

    def _books_roots(self) -> list[Path]:
        roots: list[Path] = []
        seen: set[Path] = set()
        vault_paths: list[Path] = []

        if self.reading_controller and getattr(self.reading_controller, "reading_manager", None):
            vault_paths.append(Path(self.reading_controller.reading_manager.vault_path))
        if self.book_controller and getattr(self.book_controller, "vault_manager", None):
            vault_paths.append(Path(self.book_controller.vault_manager.vault_path))
        if core_settings:
            settings_vault = str(getattr(getattr(core_settings, "paths", None), "vault", "") or "").strip()
            if settings_vault:
                vault_paths.append(Path(settings_vault).expanduser())
        vault_paths.append(Path.home() / "Documentos" / "Obsidian" / "Planner")
        vault_paths.append(Path.home() / "Documents" / "Obsidian" / "Planner")
        vault_paths.append(Path.home() / "Obsidian" / "Planner")

        unique_vault_paths: list[Path] = []
        seen_vaults: set[Path] = set()
        for vault_path in vault_paths:
            resolved = Path(vault_path).expanduser().resolve(strict=False)
            if resolved not in seen_vaults:
                seen_vaults.add(resolved)
                unique_vault_paths.append(resolved)

        for vault_path in unique_vault_paths:
            for folder_name in ("01-LEITURAS", "01- LEITURAS"):
                candidate = (vault_path / folder_name).resolve(strict=False)
                if candidate.exists() and candidate.is_dir() and candidate not in seen:
                    seen.add(candidate)
                    roots.append(candidate)
        return roots

    def _vault_root(self) -> Path | None:
        roots = self._books_roots()
        return roots[0].parent if roots else None

    def _find_concepts_note_path(self, book_dir: Path) -> Path | None:
        if not book_dir or not book_dir.exists() or not book_dir.is_dir():
            return None

        candidates = [
            book_dir / "Anotações.md",
            book_dir / "🧠 Conceitos-Chave.md",
            book_dir / "Conceitos-Chave.md",
            book_dir / "🧠 Conceitos-Chave.MD",
            book_dir / "Conceitos-Chave.MD",
        ]
        for candidate in candidates:
            if candidate.exists() and candidate.is_file():
                return candidate

        for candidate in book_dir.glob("*Anotações*.md"):
            if candidate.is_file():
                return candidate
        for candidate in book_dir.glob("*Conceitos-Chave*.md"):
            if candidate.is_file():
                return candidate

        return None

    def _extract_quotes_from_concepts_note(self, note_path: Path) -> list[dict]:
        if not note_path or not note_path.exists() or not note_path.is_file():
            return []

        try:
            raw_text = note_path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            return []

        lines = raw_text.splitlines()
        start_index = None
        for index, line in enumerate(lines):
            normalized = line.strip().lower()
            if normalized.startswith("##") and "citações importantes" in normalized:
                start_index = index + 1
                break

        if start_index is None:
            return []

        section_lines = []
        for line in lines[start_index:]:
            if line.strip().startswith("#"):
                break
            section_lines.append(line)

        paragraphs = []
        current_paragraph = []
        for line in section_lines:
            if not line.strip():
                if current_paragraph:
                    paragraphs.append(" ".join(current_paragraph).strip())
                    current_paragraph = []
                continue
            current_paragraph.append(line.strip())

        if current_paragraph:
            paragraphs.append(" ".join(current_paragraph).strip())

        citations = []
        pattern = re.compile(r'([“"”])(?P<quote>.+?)\1.*?p\.\s*(?P<page>\d+)', re.IGNORECASE)
        for paragraph in paragraphs:
            for match in pattern.finditer(paragraph):
                quote = match.group("quote").strip()
                page = match.group("page").strip()
                if quote and page:
                    citations.append({"text": quote, "page": page})

        return citations

    def _last_read_book_progress(self) -> tuple[str, str, str] | None:
        manager = getattr(self.reading_controller, "reading_manager", None)
        if not manager:
            return None

        readings = getattr(manager, "readings", {}) or {}
        best_time = None
        best_entry = None
        for book_id, progress in readings.items():
            if not book_id or not progress:
                continue
            last_read = getattr(progress, "last_read", "") or ""
            try:
                last_read_time = datetime.fromisoformat(str(last_read).replace("Z", "+00:00"))
            except Exception:
                continue
            if best_time is None or last_read_time > best_time:
                best_time = last_read_time
                best_entry = (book_id, str(getattr(progress, "title", "") or ""), str(getattr(progress, "author", "") or ""))

        return best_entry

    def _load_intervalo_quote_data(self) -> dict | None:
        progress = self._last_read_book_progress()
        if not progress:
            return None

        book_id, title, author = progress
        manager = getattr(self.reading_controller, "reading_manager", None)
        book_dir = None
        if manager:
            try:
                book_dir = book_helpers.find_book_directory(manager, book_id, title=title, author=author)
            except Exception:
                book_dir = None

        if not book_dir:
            return None

        note_path = self._find_concepts_note_path(book_dir)
        if not note_path:
            return None

        citations = self._extract_quotes_from_concepts_note(note_path)
        if not citations:
            return None

        selected = random.choice(citations)
        return {
            "book_id": book_id,
            "title": title or book_dir.name,
            "author": author or (book_dir.parent.name if book_dir.parent else "Autor Desconhecido"),
            "page": selected["page"],
            "text": selected["text"],
            "note_path": str(note_path),
        }

    def _find_cover_file(self, book_dir: Path) -> Path | None:
        preferred = [book_dir / "cover.png", book_dir / "capa.png"]
        for candidate in preferred:
            if candidate.exists() and candidate.is_file():
                return candidate
        try:
            found = book_helpers.find_cover_file(book_dir)
            if found:
                found_path = Path(found)
                if found_path.exists() and found_path.is_file():
                    return found_path
        except Exception:
            pass
        return None

    def _create_blank_cover(self, cover_path: Path, title: str) -> None:
        pixmap = QPixmap(680, 920)
        pixmap.fill(QColor("#FFFFFF"))
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        frame_rect = pixmap.rect().adjusted(18, 18, -18, -18)
        painter.setPen(QColor("#C6CDD6"))
        painter.drawRoundedRect(frame_rect, 20, 20)

        title_rect = frame_rect.adjusted(50, 80, -50, -80)
        painter.setPen(QColor("#1F2933"))
        painter.setFont(QFont("Georgia", 44, QFont.Weight.Bold))
        text_flags = int(Qt.AlignmentFlag.AlignCenter) | int(Qt.TextFlag.TextWordWrap)
        painter.drawText(title_rect, text_flags, str(title or "Livro"))
        painter.end()
        pixmap.save(str(cover_path), "PNG")

    def _ensure_cover_file(self, book_dir: Path, title: str) -> Optional[Path]:
        cover_path = self._find_cover_file(book_dir)
        if cover_path:
            return cover_path
        generated_cover = book_dir / "cover.png"
        try:
            self._create_blank_cover(generated_cover, title)
            if generated_cover.exists() and generated_cover.is_file():
                return generated_cover
        except Exception as exc:
            logger.warning("Falha ao gerar capa placeholder para %s: %s", book_dir, exc)
        return None

    def _resolve_book_metadata(self, book_dir: Path) -> dict:
        metadata = book_helpers.load_book_metadata(book_dir) or {}
        title = str(metadata.get("title") or book_dir.name).strip()
        author = str(metadata.get("author") or (book_dir.parent.name if book_dir.parent else "Desconhecido")).strip()

        try:
            note_props = book_helpers.load_book_note_properties(book_dir, title=title) or {}
        except Exception:
            note_props = {}

        if note_props:
            title = str(note_props.get("title") or title).strip()
            author = str(note_props.get("author") or author).strip()
            total_pages = int(note_props.get("total_pages", metadata.get("total_pages", 0)) or 0)
        else:
            total_pages = int(metadata.get("total_pages", 0) or 0)

        return {
            "title": title,
            "author": author,
            "total_pages": total_pages,
        }

    def _reading_progress_for_book(self, book_id: str, title: str = "", author: str = "") -> dict:
        progress_data = {
            "percent": 0.0,
            "completed": False,
            "current_page": 0,
            "total_pages": 0,
            "last_activity": None,
            "registered_at": None,
        }
        manager = getattr(self.reading_controller, "reading_manager", None)
        if not manager:
            return progress_data

        entry = getattr(manager, "readings", {}).get(str(book_id or "").strip())
        if not entry and not book_id and title and author:
            for candidate_id, candidate in getattr(manager, "readings", {}).items():
                if str(getattr(candidate, "title", "")).strip().casefold() == title.strip().casefold() and str(getattr(candidate, "author", "")).strip().casefold() == author.strip().casefold():
                    entry = candidate
                    book_id = candidate_id
                    break

        if not entry:
            return progress_data

        total_pages = max(int(getattr(entry, "total_pages", 0) or 0), 1)
        current_page = max(int(getattr(entry, "current_page", 0) or 0), 0)
        progress_data["percent"] = max(0.0, min(100.0, (current_page / total_pages) * 100.0))
        progress_data["completed"] = current_page >= total_pages and total_pages > 0
        progress_data["current_page"] = current_page
        progress_data["total_pages"] = total_pages
        progress_data["last_activity"] = self._parse_datetime_value(getattr(entry, "last_read", "") or "")
        progress_data["registered_at"] = self._parse_datetime_value(getattr(entry, "start_date", "") or "")
        return progress_data

    def _collect_intervalo_books(self) -> list[dict]:
        books: list[dict] = []
        for root in self._books_roots():
            if not root.exists() or not root.is_dir():
                continue
            for author_dir in sorted(root.iterdir(), key=lambda p: p.name.lower()):
                if not author_dir.is_dir():
                    continue
                for book_dir in sorted(author_dir.iterdir(), key=lambda p: p.name.lower()):
                    if not book_dir.is_dir():
                        continue
                    metadata = self._resolve_book_metadata(book_dir)
                    cover_path = self._ensure_cover_file(book_dir, metadata["title"])
                    if not cover_path:
                        continue
                    book_id = ""
                    try:
                        note_props = book_helpers.load_book_note_properties(book_dir, title=metadata["title"])
                        book_id = str(note_props.get("book_id") or "").strip()
                    except Exception:
                        note_props = {}

                    progress = self._reading_progress_for_book(book_id, title=metadata["title"], author=metadata["author"])
                    last_read = progress["last_activity"] or progress["registered_at"]

                    books.append(
                        {
                            "book_id": book_id,
                            "title": metadata["title"],
                            "author": metadata["author"],
                            "book_dir": book_dir,
                            "cover_path": cover_path,
                            "current_page": progress["current_page"],
                            "total_pages": max(int(progress["total_pages"] or metadata["total_pages"] or 0), 0),
                            "last_read": last_read,
                            "registered_at": progress["registered_at"],
                            "source_file": "",
                            "is_aulas": metadata["author"].casefold() == AULAS_AUTHOR.casefold(),
                        }
                    )

        books.sort(key=self._intervalo_book_sort_key, reverse=True)
        return books

    def _configure_intervalo_scrollbar(self, books_count: int) -> None:
        if not hasattr(self, "intervalo_scrollbar"):
            return
        if books_count <= 0:
            self.intervalo_scrollbar.setEnabled(False)
            self.intervalo_scrollbar.setRange(0, 0)
            self.intervalo_scrollbar.setValue(0)
            return
        self.intervalo_scrollbar.setEnabled(True)
        self.intervalo_scrollbar.setRange(0, 1000000)
        self.intervalo_scrollbar.setPageStep(self._intervalo_visible_slots)
        self.intervalo_scrollbar.setSingleStep(1)
        current_value = max(0, min(self.intervalo_scrollbar.value(), self.intervalo_scrollbar.maximum()))
        self.intervalo_scrollbar.blockSignals(True)
        self.intervalo_scrollbar.setValue(current_value)
        self.intervalo_scrollbar.blockSignals(False)

    def _on_intervalo_scroll_changed(self, value: int) -> None:
        self._intervalo_scroll_offset = max(0, int(value or 0))
        if self._current_state == "intervalo":
            self._refresh_intervalo_library_content()

    def _mini_cover_pixmap(self, cover_path: Path | None, title: str, size: tuple[int, int]) -> QPixmap:
        width, height = size
        if cover_path and cover_path.exists():
            pixmap = QPixmap(str(cover_path))
            if not pixmap.isNull():
                return pixmap.scaled(
                    width,
                    height,
                    Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                    Qt.TransformationMode.SmoothTransformation,
                )

        pixmap = QPixmap(width, height)
        pixmap.fill(QColor("#1E2734"))
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QPen(QColor("#141A23"), 2))
        painter.setBrush(QColor("#263142"))
        painter.drawRoundedRect(pixmap.rect().adjusted(1, 1, -1, -1), 8, 8)
        painter.setPen(QColor("#E8EDF5"))
        font = QFont("Sans Serif", max(10, int(min(width, height) * 0.18)), QFont.Weight.Bold)
        painter.setFont(font)
        initials = "".join(part[0] for part in str(title or "Livro").split()[:2] if part).upper() or "BK"
        painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, initials)
        painter.end()
        return pixmap

    def _build_intervalo_card(self, book: dict, list_mode: bool = False) -> QWidget:
        card = QFrame()
        card.setObjectName("intervalo_book_card")
        card.setStyleSheet(
            "QFrame#intervalo_book_card { border: 1px solid #32404F; border-radius: 8px; background: #1A2230; }"
        )
        card_layout = QHBoxLayout(card) if list_mode else QVBoxLayout(card)
        card_layout.setContentsMargins(8, 8, 8, 8)
        card_layout.setSpacing(8)

        cover_size = (48, 68) if list_mode else (104, 144)
        cover_label = QLabel()
        cover_label.setObjectName("intervalo_cover_tile")
        cover_label.setFixedSize(*cover_size)
        cover_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        cover_label.setPixmap(self._mini_cover_pixmap(book.get("cover_path"), book.get("title", "Livro"), cover_size))
        cover_label.setStyleSheet("background: #0F141B; border: 1px solid #11161F; border-radius: 8px;")

        details = QWidget()
        details_layout = QVBoxLayout(details)
        details_layout.setContentsMargins(0, 0, 0, 0)
        details_layout.setSpacing(3)

        title_label = QLabel(str(book.get("title") or "Livro"))
        title_label.setWordWrap(True)
        title_label.setStyleSheet("color: #F2F5FA; font-weight: 600; font-size: 11px;")
        author_label = QLabel(str(book.get("author") or "Desconhecido"))
        author_label.setWordWrap(True)
        author_label.setStyleSheet("color: #9AA7BB; font-size: 10px;")
        details_layout.addWidget(title_label)
        details_layout.addWidget(author_label)

        if list_mode:
            total_pages = int(book.get("total_pages") or 0)
            progress_label = QLabel(f"p. {int(book.get('current_page') or 0)}/{total_pages if total_pages > 0 else '—'}")
            progress_label.setStyleSheet("color: #6EA8FF; font-size: 10px;")
            details_layout.addWidget(progress_label)
            card_layout.addWidget(cover_label)
            card_layout.addWidget(details, 1)
        else:
            card_layout.addWidget(cover_label, alignment=Qt.AlignmentFlag.AlignHCenter)
            card_layout.addWidget(details)

        return card

    def _clear_layout(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.setParent(None)

    def _refresh_intervalo_library_content(self):
        if not hasattr(self, "intervalo_books_layout"):
            return

        self._clear_layout(self.intervalo_books_layout)
        books = self._collect_intervalo_books()
        aulas_mode = self._intervalo_library_mode == "aulas"

        if aulas_mode:
            books = [book for book in books if book.get("is_aulas")]
        else:
            books = [book for book in books if not book.get("is_aulas")]

        self._intervalo_all_books = books
        self._configure_intervalo_scrollbar(len(books))

        if not books:
            if self.intervalo_empty_label:
                self.intervalo_empty_label.setVisible(True)
                if aulas_mode:
                    self.intervalo_empty_label.setText("Nenhum livro de Aulas encontrado.")
                else:
                    self.intervalo_empty_label.setText("Nenhum livro recente encontrado.")
            return

        if self.intervalo_empty_label:
            self.intervalo_empty_label.setVisible(False)

        total_books = len(books)
        window_size = self._intervalo_visible_slots
        start_index = self._intervalo_scroll_offset % total_books
        window_books = [books[(start_index + offset) % total_books] for offset in range(window_size)]

        for index, book in enumerate(window_books):
            row = index // 3
            col = index % 3
            tile = self._build_intervalo_cover_tile(book)
            self.intervalo_books_layout.addWidget(tile, row, col, alignment=Qt.AlignmentFlag.AlignCenter)

    def _render_intervalo(self, event):
        assistant_name = self._assistant_display_name()
        user_name = self._user_display_name()

        self._intervalo_books_cache = self._collect_intervalo_books()
        self._intervalo_quote_data = self._load_intervalo_quote_data()
        self._refresh_intervalo_library_content()
        self._start_intervalo_chat_animation(user_name, assistant_name)
        if hasattr(self, "intervalo_input_line"):
            self.intervalo_input_line.setText("")
            self.intervalo_input_line.setEnabled(True)
            self.intervalo_input_line.setVisible(True)
            self.intervalo_input_line.setFocus(Qt.FocusReason.OtherFocusReason)

    def _start_intervalo_chat_animation(self, user_name: str, assistant_name: str):
        if not hasattr(self, "intervalo_chat_view"):
            return

        self._intervalo_input_buffer = ""
        self._intervalo_chat_cursor_visible = True
        self._intervalo_chat_messages = []
        self._intervalo_assistant_reply_index = 0
        self._intervalo_chat_started_at = datetime.now()

        assistant_text = (
            "Sessão iniciada. Estou organizando seus livros e preparando o próximo bloco de leituras. "
            "Enquanto isso, se quiser, vá tomar um sol."
        )
        if self._intervalo_quote_data:
            assistant_text = (
                "Sessão iniciada. Estou organizando seus livros e preparando o próximo bloco de leituras. "
                "Enquanto isso, deixo uma citação do último livro lido:\n\n"
                f'"{self._intervalo_quote_data["text"]}" (p. {self._intervalo_quote_data["page"]})\n'
                f'{self._intervalo_quote_data["author"]} — {self._intervalo_quote_data["title"]}'
            )

        self._intervalo_chat_messages = []
        self._intervalo_chat_full_text = "Sessão iniciada. Estou organizando seus livros e preparando o próximo bloco de leituras."
        self._intervalo_chat_index = 0
        self._intervalo_chat_active = True
        self._intervalo_pending_assistant_message = {"name": assistant_name, "text": self._intervalo_chat_full_text}
        self._render_intervalo_chat()
        if hasattr(self, "_intervalo_chat_timer") and self._intervalo_chat_timer.isActive():
            self._intervalo_chat_timer.stop()
        self._intervalo_chat_timer.start()
        if hasattr(self, "_intervalo_cursor_timer") and not self._intervalo_cursor_timer.isActive():
            self._intervalo_cursor_timer.start()

        if self._intervalo_quote_data:
            self._intervalo_chat_messages.append(
                {
                    "role": "assistant",
                    "html": self._build_terminal_line(
                        assistant_name,
                        self._intervalo_chat_full_text,
                        color="#FFB347",
                        timestamp=self._terminal_timestamp(),
                    ),
                }
            )
            quote_text = (
                f'"{self._intervalo_quote_data["text"]}" (p. {self._intervalo_quote_data["page"]}) - '
                f'{self._intervalo_quote_data["author"]} — {self._intervalo_quote_data["title"]}'
            )
            self._intervalo_chat_full_text = quote_text
            self._intervalo_chat_index = 0
            self._intervalo_chat_active = True
            self._intervalo_pending_assistant_message = {"name": assistant_name, "text": quote_text}
            self._render_intervalo_chat()

    def _render_intervalo_chat(self):
        if not hasattr(self, "intervalo_chat_view"):
            return

        self.intervalo_chat_view.setHtml(self._build_intervalo_chat_html())
        scrollbar = self.intervalo_chat_view.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

        if self._intervalo_chat_index >= len(self._intervalo_chat_full_text):
            self._intervalo_chat_active = False
            if self._intervalo_pending_assistant_message:
                self._intervalo_chat_messages.append(
                    {
                        "role": "assistant",
                        "html": (
                            self._build_terminal_line(
                                self._intervalo_pending_assistant_message.get("name", self._assistant_display_name()),
                                self._intervalo_pending_assistant_message.get("text", ""),
                                color="#FFB347",
                                timestamp=self._terminal_timestamp(),
                            )
                        ),
                    }
                )
                self._intervalo_pending_assistant_message = None
                self._intervalo_chat_full_text = ""
                self._intervalo_chat_index = 0
            if hasattr(self, "_intervalo_chat_timer"):
                self._intervalo_chat_timer.stop()
            self.intervalo_chat_view.setHtml(self._build_intervalo_chat_html())
            scrollbar = self.intervalo_chat_view.verticalScrollBar()
            scrollbar.setValue(scrollbar.maximum())

    def _build_intervalo_chat_html(self) -> str:
        assistant_name = self._assistant_display_name()
        visible_text = self._intervalo_chat_full_text[: self._intervalo_chat_index]
        if self._intervalo_chat_index < len(self._intervalo_chat_full_text):
            visible_text += "▌"

        assistant_line = self._build_terminal_line(
            assistant_name,
            visible_text,
            color="#FFB347",
            timestamp=self._terminal_timestamp(),
        )

        parts = []
        if self._intervalo_chat_started_at is not None:
            parts.append(self._build_terminal_banner())
        for message in self._intervalo_chat_messages:
            parts.append(f'<div style="margin-bottom:6px;">{message["html"]}</div>')
        if self._intervalo_chat_active or self._intervalo_chat_full_text:
            parts.append(f'<div style="margin-bottom:6px;">{assistant_line}</div>')
        return (
            "<html><body style='margin:0; padding:0; background:transparent; font-family: \"DejaVu Sans Mono\", \"Noto Sans Mono\", monospace; font-size: 11px; line-height: 1.4; white-space: pre-wrap;'>"
            + "".join(parts)
            + "</body></html>"
        )

    def _toggle_intervalo_chat_cursor(self):
        if self._current_state != "intervalo":
            return
        self._intervalo_chat_cursor_visible = not self._intervalo_chat_cursor_visible
        self._render_intervalo_chat()

    def _advance_intervalo_chat_typing(self):
        if not self._intervalo_chat_active:
            return
        self._intervalo_chat_index = min(
            len(self._intervalo_chat_full_text),
            self._intervalo_chat_index + 1,
        )
        self._render_intervalo_chat()

    @staticmethod
    def _escape_html(value: str) -> str:
        return (
            str(value or "")
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )

    def _on_intervalo_input_submitted(self) -> None:
        if not hasattr(self, "intervalo_input_line"):
            return

        submitted = str(self.intervalo_input_line.text() or "").strip()
        if not submitted:
            return

        user_name = self._user_display_name()
        self._intervalo_chat_messages.append(
            {
                "role": "user",
                "html": self._build_terminal_line(
                    user_name,
                    submitted,
                    color="#58A6FF",
                    timestamp=self._terminal_timestamp(),
                ),
            }
        )
        self.intervalo_input_line.setText("")
        self._queue_intervalo_assistant_reply()

    def _handle_intervalo_keypress(self, event) -> bool:
        return False

    def _queue_intervalo_assistant_reply(self):
        replies = [
            "Entendido. Vou seguir reorganizando essas páginas com cuidado filosófico.",
            "Perfeito. A biblioteca continua respirando, mesmo em silêncio.",
            "Sim, eu também achei isso útil. Surpreendente, eu sei.",
        ]
        reply = replies[self._intervalo_assistant_reply_index % len(replies)]
        self._intervalo_assistant_reply_index += 1
        self._intervalo_chat_full_text = reply
        self._intervalo_chat_index = 0
        self._intervalo_chat_active = True
        self._intervalo_chat_cursor_visible = True
        self._intervalo_pending_assistant_message = {"name": self._assistant_display_name(), "text": reply}
        self._render_intervalo_chat()
        if hasattr(self, "_intervalo_chat_timer"):
            self._intervalo_chat_timer.stop()
            self._intervalo_chat_timer.start()

    def _terminal_timestamp(self) -> str:
        if self._intervalo_chat_started_at is None:
            return datetime.now().strftime("%H:%M:%S")
        return datetime.now().strftime("%H:%M:%S")

    def _build_terminal_banner(self) -> str:
        return (
            '<div style="margin-bottom:8px; color:#6B7A90;">'
            f'[{self._terminal_timestamp()}] conexão estabelecida'
            '</div>'
        )

    def _build_terminal_prompt(self, name: str) -> str:
        return (
            f'<span style="color:#6B7A90;">[{self._terminal_timestamp()}]</span> '
            f'<span style="color:#A8B5C8;">$</span> '
            f'<span style="color:#58A6FF;font-weight:700;">{self._escape_html(name)}</span>'
            f': '
        )

    def _build_terminal_line(self, name: str, text: str, color: str, timestamp: str) -> str:
        return (
            f'<span style="color:#6B7A90;">[{self._escape_html(timestamp)}]</span> '
            f'<span style="color:{color};font-weight:700;">{self._escape_html(name)}</span>'
            f': <span style="color:#D7DCE6;">{self._escape_html(text)}</span>'
        )

    def _build_intervalo_cover_tile(self, book: dict) -> QWidget:
        cover_label = QLabel()
        cover_label.setObjectName("intervalo_cover_tile")
        cover_label.setFixedSize(112, 156)
        cover_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        cover_label.setPixmap(
            self._mini_cover_pixmap(
                book.get("cover_path"),
                str(book.get("title") or "Livro"),
                (112, 156),
            )
        )
        cover_label.setStyleSheet("QLabel#intervalo_cover_tile { border: 1px solid #11161F; border-radius: 10px; background: #0F141B; }")
        return cover_label

    def _render_aula(self, event):
        # header
        title = event.get('title') or ''
        discipline = str(event.get('discipline') or event.get('metadata', {}).get('discipline') or '')
        start = event.get('start') or ''
        end = event.get('end') or ''
        self.aula_header.setText(f"{NerdIcons.CALENDAR} {title} — {discipline} ({start} — {end})")

        # clear grid
        for i in reversed(range(self.aula_books_layout.count())):
            w = self.aula_books_layout.itemAt(i).widget()
            if w:
                w.setParent(None)

        vault_root = None
        try:
            if self.vault_controller and hasattr(self.vault_controller, 'vault_path'):
                vault_root = Path(self.vault_controller.vault_path)
            elif self.reading_controller and hasattr(self.reading_controller, 'reading_manager') and hasattr(self.reading_controller.reading_manager, 'vault_path'):
                vault_root = Path(self.reading_controller.reading_manager.vault_path)
        except Exception:
            vault_root = None

        books = []
        if discipline and vault_root:
            try:
                books = book_helpers.load_discipline_books(str(vault_root), discipline)
            except Exception:
                logger.exception('Erro ao carregar livros da disciplina')

        # populate up to 4
        for idx, b in enumerate((books or [])[:4]):
            col = idx % 2
            row = idx // 2
            card = QFrame()
            card.setFrameShape(QFrame.Shape.StyledPanel)
            c_layout = QVBoxLayout(card)
            cover_path = b.get('cover_path')
            cover_lbl = QLabel()
            cover_lbl.setFixedSize(80, 120)
            if cover_path and Path(cover_path).exists():
                try:
                    pix = QPixmap(str(cover_path)).scaled(80, 120, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                    if not pix.isNull():
                        cover_lbl.setPixmap(pix)
                    else:
                        cover_lbl.setText('')
                except Exception:
                    pass
            title_lbl = QLabel(b.get('title') or '—')
            title_lbl.setWordWrap(True)
            read_btn = QPushButton('Ler')
            read_btn.clicked.connect(lambda _, bd=b: self.open_session.emit({'book_dir': bd.get('work_dir_abs'), 'event_data': event}))
            cnot_btn = QPushButton('Anotações')
            cnot_btn.clicked.connect(lambda _, ev=event: self.open_class_notes.emit(ev))
            chat_btn = QPushButton('Chat')
            chat_btn.clicked.connect(lambda _, d=discipline: self.open_discipline_chat.emit(d))

            c_layout.addWidget(cover_lbl)
            c_layout.addWidget(title_lbl)
            c_layout.addWidget(read_btn)
            c_layout.addWidget(cnot_btn)
            c_layout.addWidget(chat_btn)

            self.aula_books_layout.addWidget(card, row, col)

    def _render_leitura(self, event):
        # try to obtain book info
        book_id = None
        metadata = {}
        cover = None
        title = event.get('title') if event else 'Título do livro'
        total = None
        current = None
        pages_planned = None
        current_page = 0
        try:
            metadata = event.get('metadata') or {}
            book_id = metadata.get('book_id') or event.get('book_id')
            if self.reading_controller and hasattr(self.reading_controller, 'reading_manager') and book_id:
                try:
                    prog = self.reading_controller.reading_manager.get_reading_progress(book_id)
                    if isinstance(prog, dict):
                        title = prog.get('title') or prog.get('book_title') or metadata.get('title') or title
                        cover = prog.get('cover') or None
                        total = prog.get('total_pages')
                        current = prog.get('current_page')
                        pages_planned = metadata.get('pages_planned') or prog.get('pages_planned')
                    else:
                        title = metadata.get('title') or event.get('title') or title
                        total = None
                        current = None
                        pages_planned = metadata.get('pages_planned')
                except Exception:
                    title = metadata.get('title') or event.get('title') or title
                    total = None
                    current = None
                    pages_planned = metadata.get('pages_planned')
        except Exception:
            title = event.get('title') or title
            total = None
            current = None
            pages_planned = None

        book_dir = None
        note_props = {}
        try:
            book_title_candidate = metadata.get('title') or event.get('title') or title
            book_author_candidate = metadata.get('author') or event.get('author') or ''
            if self.reading_controller and hasattr(self.reading_controller, 'reading_manager'):
                book_dir = book_helpers.find_book_directory(
                    self.reading_controller.reading_manager,
                    book_id,
                    title=book_title_candidate,
                    author=book_author_candidate,
                )
            if not book_dir and isinstance(cover, str):
                cover_path = Path(cover)
                if cover_path.exists() and cover_path.parent.is_dir():
                    book_dir = cover_path.parent
            if book_dir:
                if not cover:
                    cover = book_helpers.find_cover_file(book_dir)
                note_props = book_helpers.load_book_note_properties(
                    book_dir,
                    book_id=book_id,
                    title=book_title_candidate,
                )
        except Exception:
            note_props = {}

        if note_props:
            if not book_id:
                book_id = str(note_props.get('book_id') or '').strip() or book_id
            title = str(note_props.get('title') or title or event.get('title') or 'Título do livro')
            self.leitura_book_title.setText(title)
            cleaned = []
            for key, value in sorted(note_props.items()):
                if isinstance(value, (list, tuple)):
                    value = ', '.join(str(item) for item in value)
                cleaned.append(f"<b>{str(key).title()}</b>: {str(value)}")
            self.leitura_properties_label.setText('<br>'.join(cleaned))
        else:
            self.leitura_book_title.setText(str(title or 'Título do livro'))
            self.leitura_properties_label.setText('Sem propriedades do livro encontradas.')

        weekly_counts = self._count_weekly_book_pages(book_id)
        self.leitura_weekly_sessions_chart.set_counts(weekly_counts)
        self._animate_weekly_sessions_chart()

        if cover and Path(str(cover)).exists():
            try:
                pix = QPixmap(str(cover))
                if not pix.isNull():
                    max_width = 180
                    max_height = 220
                    if pix.width() > max_width or pix.height() > max_height:
                        pix = pix.scaled(max_width, max_height, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                    self.leitura_cover.setPixmap(pix)
                    self.leitura_cover.setFixedSize(pix.size())
                else:
                    self.leitura_cover.setText('')
            except Exception:
                self.leitura_cover.setText('')
        else:
            self.leitura_cover.setText('')

        current_page = int(current or 0)
        total_pages = int(total or 0)
        self.leitura_progress_status.setText("Progresso de leitura")
        self.leitura_progress_summary_label.setText(
            f"{current_page} de {total_pages} páginas" if total_pages > 0 else "Progresso indisponível"
        )
        if total_pages > 0:
            fraction = current_page / total_pages
            self.leitura_progress_ring.set_progress(
                fraction,
                label=f"{current_page}/{total_pages}",
                subtitle="Páginas",
            )
        else:
            self.leitura_progress_ring.set_progress(0.0, label="0/0", subtitle="Páginas")

        if hasattr(self, "leitura_session_pages_label"):
            planned_pages = 0
            try:
                planned_pages = int(pages_planned or 0)
            except Exception:
                planned_pages = 0
            if planned_pages > 0:
                self.leitura_session_pages_label.setText(f"Páginas desta sessão: {planned_pages}")
            else:
                self.leitura_session_pages_label.setText("Páginas desta sessão: —")

        event_duration_minutes = self._resolve_event_duration_minutes(event)
        self._leitura_pomodoro_profiles = self._build_pomodoro_profiles(event_duration_minutes)
        if self._leitura_pomodoro_profiles:
            persisted_profile_id = self._load_persisted_leitura_profile_id(event)
            available_ids = {profile["id"] for profile in self._leitura_pomodoro_profiles}
            if persisted_profile_id in available_ids:
                self._selected_leitura_pomodoro_profile_id = persisted_profile_id
            elif self._selected_leitura_pomodoro_profile_id not in available_ids:
                self._selected_leitura_pomodoro_profile_id = self._leitura_pomodoro_profiles[0]["id"]
            selected_profile = next(
                (p for p in self._leitura_pomodoro_profiles if p["id"] == self._selected_leitura_pomodoro_profile_id),
                self._leitura_pomodoro_profiles[0],
            )
            self.leitura_pomodoro_profile_button.setText(
                f"Perfil: {selected_profile['label']}"
            )
            self.leitura_pomodoro_profile_button.setEnabled(True)
            self._apply_leitura_pomodoro_profile_visuals()
        else:
            self._selected_leitura_pomodoro_profile_id = ""
            self.leitura_pomodoro_profile_button.setText("Perfil indisponível")
            self.leitura_pomodoro_profile_button.setEnabled(False)
            self._apply_leitura_pomodoro_profile_visuals()

        # wire start button payload
        def _emit():
            payload = {'book_id': book_id, 'event_data': event}
            if book_dir:
                payload['book_dir'] = str(book_dir)
            selected_profile = self._selected_leitura_pomodoro_profile()
            if selected_profile:
                payload['pomodoro_profile'] = {
                    'id': selected_profile.get('id', ''),
                    'label': selected_profile.get('label', ''),
                    'blocks': list(selected_profile.get('blocks') or []),
                    'interval_minutes': selected_profile.get('interval_minutes', 0),
                    'total_minutes': selected_profile.get('total_minutes', 0),
                }
            self.open_session.emit(payload)

        try:
            self.leitura_start_btn.clicked.disconnect()
        except Exception:
            pass
        self.leitura_start_btn.clicked.connect(_emit)

    def _show_leitura_pomodoro_profiles_menu(self):
        if not self._leitura_pomodoro_profiles:
            return

        menu = QMenu(self)
        for profile in self._leitura_pomodoro_profiles:
            label = profile["label"]
            cycles = len(profile["blocks"])
            interval = profile.get("interval_minutes", 0)
            action = menu.addAction(f"{label} — {cycles} ciclos — intervalo {interval} min")
            action.setData(profile["id"])

        action = menu.exec(self.leitura_pomodoro_profile_button.mapToGlobal(self.leitura_pomodoro_profile_button.rect().bottomLeft()))
        if not action:
            return

        selected_id = action.data()
        selected_profile = next(
            (p for p in self._leitura_pomodoro_profiles if p["id"] == selected_id),
            None,
        )
        if selected_profile:
            self._selected_leitura_pomodoro_profile_id = selected_profile["id"]
            self.leitura_pomodoro_profile_button.setText(f"Perfil: {selected_profile['label']}")
            self._apply_leitura_pomodoro_profile_visuals()
            self._save_persisted_leitura_profile_id(selected_profile["id"], event=self._current_event)

    def _selected_leitura_pomodoro_profile(self):
        if not self._leitura_pomodoro_profiles:
            return None
        return next(
            (p for p in self._leitura_pomodoro_profiles if p["id"] == self._selected_leitura_pomodoro_profile_id),
            self._leitura_pomodoro_profiles[0],
        )

    def _leitura_profile_scope_key(self, event: dict | None = None) -> str:
        event = event or self._current_event or {}
        metadata = event.get("metadata") if isinstance(event.get("metadata"), dict) else {}
        book_id = str(event.get("book_id") or metadata.get("book_id") or "").strip()
        event_id = str(event.get("id") or metadata.get("id") or "").strip()
        if book_id:
            return f"ui/pomodoro_profile_by_book/{book_id}"
        if event_id:
            return f"ui/pomodoro_profile_by_event/{event_id}"
        return ""

    def _load_persisted_leitura_profile_id(self, event: dict | None = None) -> str:
        key = self._leitura_profile_scope_key(event)
        if not key:
            return ""
        try:
            return str(self.config_manager.get(key, "") or "").strip()
        except Exception:
            return ""

    def _save_persisted_leitura_profile_id(self, profile_id: str, event: dict | None = None):
        key = self._leitura_profile_scope_key(event)
        if not key or not profile_id:
            return
        try:
            self.config_manager.set(key, profile_id)
        except Exception:
            pass

    def _apply_leitura_pomodoro_profile_visuals(self):
        profile = self._selected_leitura_pomodoro_profile()
        if not profile:
            self.leitura_pomodoro_session_chip.setText("Sessão 25m")
            self.leitura_pomodoro_interval_chip.setText("Intervalo 5m")
            self.leitura_pomodoro_cycles_chip.setText("Ciclos 4")
            return

        blocks = profile.get("blocks") or []
        cycles = len(blocks)
        session_minutes = int(blocks[0]) if blocks else 25
        interval_minutes = profile.get("interval_minutes", 0)
        self.leitura_pomodoro_session_chip.setText(f"Sessão {session_minutes}m")
        self.leitura_pomodoro_interval_chip.setText(
            f"Intervalo {interval_minutes}m" if interval_minutes else "Intervalo 0m"
        )
        self.leitura_pomodoro_cycles_chip.setText(f"Ciclos {cycles}")

    def _resolve_event_duration_minutes(self, event):
        if not event:
            return 0
        metadata = event.get('metadata') or {}
        duration = metadata.get('duration_minutes') or event.get('duration_minutes')
        if isinstance(duration, (int, float)) and duration > 0:
            return int(duration)

        if isinstance(event.get('start'), str) and isinstance(event.get('end'), str):
            try:
                start = datetime.fromisoformat(event.get('start').replace('Z', '+00:00'))
                end = datetime.fromisoformat(event.get('end').replace('Z', '+00:00'))
                delta = end - start
                minutes = int(delta.total_seconds() / 60)
                return max(1, minutes)
            except Exception:
                pass

        return int(metadata.get('pages_planned') or 0)

    def _count_weekly_book_pages(self, book_id: str) -> list[int]:
        pages = [0] * 7
        if not book_id or not self.agenda_backend:
            return pages

        try:
            today = date.today()
            start_of_week = today - timedelta(days=today.weekday())
            for offset in range(7):
                day = start_of_week + timedelta(days=offset)
                day_key = day.strftime("%Y-%m-%d")
                events = []
                if hasattr(self.agenda_backend, "get_day_events"):
                    events = self.agenda_backend.get_day_events(day_key) or []
                elif hasattr(self.agenda_backend, "agenda_manager") and hasattr(self.agenda_backend.agenda_manager, "get_day_events"):
                    events = self.agenda_backend.agenda_manager.get_day_events(day_key) or []

                for ev in events:
                    if not isinstance(ev, dict):
                        continue
                    etype = str(ev.get("type") or ev.get("event_type") or "").strip().lower()
                    if etype and etype != "leitura":
                        continue
                    metadata = ev.get("metadata") if isinstance(ev.get("metadata"), dict) else {}
                    event_book_id = str(ev.get("book_id") or metadata.get("book_id") or "").strip()
                    if event_book_id != str(book_id).strip():
                        continue
                    pages_planned = 0
                    for key in ("pages_planned", "planned_pages"):
                        raw = metadata.get(key, ev.get(key))
                        try:
                            pages_planned = max(pages_planned, int(raw or 0))
                        except Exception:
                            continue
                    if pages_planned <= 0:
                        start_raw = str(ev.get("start") or "").strip()
                        end_raw = str(ev.get("end") or "").strip()
                        if start_raw and end_raw:
                            try:
                                start_dt = datetime.fromisoformat(start_raw.replace("Z", "+00:00"))
                                end_dt = datetime.fromisoformat(end_raw.replace("Z", "+00:00"))
                                duration_minutes = max(0, int((end_dt - start_dt).total_seconds() // 60))
                                pages_planned = max(0, int(round(duration_minutes / 6.0)))
                            except Exception:
                                pages_planned = 0
                    pages[offset] += max(0, int(pages_planned))
        except Exception:
            logger.debug("Falha ao calcular sessões semanais do livro", exc_info=True)
        return pages

    def _animate_weekly_sessions_chart(self):
        if not hasattr(self, "leitura_weekly_sessions_chart_fade"):
            return
        try:
            self.leitura_weekly_sessions_chart_fade.stop()
            self.leitura_weekly_sessions_chart_opacity.setOpacity(0.0)
            self.leitura_weekly_sessions_chart_fade.setStartValue(0.0)
            self.leitura_weekly_sessions_chart_fade.setEndValue(1.0)
            self.leitura_weekly_sessions_chart_fade.start()
        except Exception:
            pass

    @staticmethod
    def _build_pomodoro_profiles(total_minutes: int):
        total = max(1, int(total_minutes or 1))
        profiles = []
        candidates = [50, 45, 40, 35, 30, 25, 20, 15, 10]
        for work in candidates:
            max_cycles = total // work
            if max_cycles < 1:
                continue
            for cycles in range(1, min(max_cycles, 6) + 1):
                if cycles == 1:
                    if work == total:
                        profiles.append({
                            "id": f"{work}x{cycles}_0",
                            "label": f"{cycles}×{work} min",
                            "blocks": [work],
                            "interval_minutes": 0,
                            "total_minutes": total,
                        })
                    continue
                remaining = total - work * cycles
                if remaining < 0:
                    continue
                interval_raw = remaining / (cycles - 1)
                if interval_raw < 1 or interval_raw > 20:
                    continue
                interval = round(interval_raw, 1)
                if abs(interval_raw - interval) > 0.05:
                    continue
                total_with_breaks = work * cycles + interval * (cycles - 1)
                if abs(total_with_breaks - total) > 0.5:
                    continue
                profiles.append({
                    "id": f"{work}x{cycles}_{interval}",
                    "label": f"{cycles}×{work} min",
                    "blocks": [work] * cycles,
                    "interval_minutes": interval,
                    "total_minutes": total,
                })
        if not profiles:
            profiles.append({
                "id": f"default_{total}",
                "label": f"{total} min",
                "blocks": [total],
                "interval_minutes": 0,
                "total_minutes": total,
            })
        unique = {profile["id"]: profile for profile in profiles}
        return sorted(unique.values(), key=lambda p: (-len(p["blocks"]), p["blocks"][0]))

    # --- Signal emitters for buttons ---
    def _emit_open_notes(self):
        if self._current_event:
            try:
                self.open_class_notes.emit(self._current_event)
            except Exception:
                logger.exception('emit open_class_notes failed')

    def _emit_open_chat(self):
        if self._current_event:
            discipline = str(self._current_event.get('discipline') or self._current_event.get('metadata', {}).get('discipline') or '')
            try:
                if discipline:
                    self.open_discipline_chat.emit(discipline)
            except Exception:
                logger.exception('emit open_discipline_chat failed')

    def _emit_open_session(self):
        # prefer book_dir from current aula book selection; for leitura, use metadata/book_id
        if not self._current_event:
            return
        payload = {'event_data': self._current_event}
        # try to include book_id if present
        try:
            book_id = self._current_event.get('book_id') or None
            if not book_id:
                md = self._current_event.get('metadata') or {}
                book_id = md.get('book_id')
            if book_id:
                payload['book_id'] = book_id

            if self._current_event.get('book_dir'):
                payload['book_dir'] = self._current_event.get('book_dir')
            else:
                md = self._current_event.get('metadata') or {}
                if 'book_dir' in md:
                    payload['book_dir'] = md.get('book_dir')
            selected_profile = self._selected_leitura_pomodoro_profile()
            if selected_profile:
                payload['pomodoro_profile'] = {
                    'id': selected_profile.get('id', ''),
                    'label': selected_profile.get('label', ''),
                    'blocks': list(selected_profile.get('blocks') or []),
                    'interval_minutes': selected_profile.get('interval_minutes', 0),
                    'total_minutes': selected_profile.get('total_minutes', 0),
                }
        except Exception:
            pass

        try:
            self.open_session.emit(payload)
        except Exception:
            logger.exception('emit open_session failed')
