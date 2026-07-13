"""DynamicEventCard: shows imminent event (class/reading) or weekly summary.

Minimal, safe implementation matching requested API and signals.
"""
from datetime import datetime, timedelta, date
import logging
from pathlib import Path

from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QRectF, QPropertyAnimation
from PyQt6.QtGui import QPixmap, QPainter, QPen, QColor, QFont
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QStackedWidget, QScrollArea, QGridLayout, QSizePolicy, QFrame,
    QMenu, QGraphicsOpacityEffect,
)

from ui.utils.nerd_icons import NerdIcons, nerd_font
from ui.utils.config_manager import ConfigManager

from ui.utils import book_helpers

logger = logging.getLogger("GLaDOS.UI.DynamicEventCard")


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

        self._current_state = "base"  # base | aula | leitura
        self._current_event = None
        self._is_updating = False
        self._leitura_pomodoro_profiles = []
        self._selected_leitura_pomodoro_profile_id = ""

        self._build_ui()
        self._connect_signals()

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

        self.stack = QStackedWidget()

        # Base page
        self.base_page = QWidget()
        b_layout = QVBoxLayout(self.base_page)
        b_layout.setContentsMargins(12, 12, 12, 12)
        title = QLabel(f"{NerdIcons.CALENDAR} Resumo da Semana")
        title.setFont(nerd_font(12, weight=600))
        b_layout.addWidget(title)

        stats_row = QHBoxLayout()
        self.reading_hours_label = QLabel("📚 0h de leitura")
        self.mood_avg_label = QLabel("🙂 Humor 0.0/5")
        stats_row.addWidget(self.reading_hours_label)
        stats_row.addStretch()
        stats_row.addWidget(self.mood_avg_label)
        b_layout.addLayout(stats_row)

        self.base_page.setLayout(b_layout)

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
            etype = str(chosen.get('type') or '').strip().lower()
            if etype in {'aula'}:
                new_state = 'aula'
            elif etype in {'leitura'}:
                new_state = 'leitura'

        if new_state == self._current_state and chosen == self._current_event:
            return

        self._current_state = new_state
        self._current_event = chosen

        if new_state == 'base':
            self._render_base()
            self.stack.setCurrentWidget(self.base_page)
        elif new_state == 'aula':
            self._render_aula(chosen)
            self.stack.setCurrentWidget(self.aula_page)
        elif new_state == 'leitura':
            self._render_leitura(chosen)
            self.stack.setCurrentWidget(self.leitura_page)

    def _render_base(self):
        # compute reading hours last 7 days
        hours = 0.0
        mood_avg = 0.0
        try:
            if self.reading_controller and hasattr(self.reading_controller, 'reading_manager') and hasattr(self.reading_controller.reading_manager, 'get_reading_progress'):
                prog = self.reading_controller.reading_manager.get_reading_progress() or []
                # prog may be list of dicts with duration_minutes and last_read
                total_minutes = 0
                cutoff = datetime.now() - timedelta(days=7)
                for item in prog:
                    try:
                        lm = item.get('last_read') or item.get('updated_at')
                        if lm:
                            lm_dt = datetime.fromisoformat(str(lm))
                            if lm_dt >= cutoff:
                                total_minutes += int(item.get('duration_minutes', 0))
                    except Exception:
                        continue
                hours = total_minutes / 60.0

            if self.daily_checkin_controller and hasattr(self.daily_checkin_controller, 'get_checkins'):
                checkins = self.daily_checkin_controller.get_checkins() or []
                cutoff = datetime.now() - timedelta(days=7)
                scores = []
                for c in checkins:
                    try:
                        t = c.get('timestamp') or c.get('created_at') or c.get('date')
                        if not t:
                            continue
                        t_dt = datetime.fromisoformat(str(t))
                        if t_dt >= cutoff and 'mood_score' in c:
                            scores.append(float(c.get('mood_score', 0)))
                    except Exception:
                        continue
                if scores:
                    mood_avg = sum(scores) / len(scores)
        except Exception:
            logger.exception('Erro ao calcular estatísticas base')

        self.reading_hours_label.setText(f"📚 {hours:.1f}h de leitura")
        self.mood_avg_label.setText(f"🙂 Humor {mood_avg:.1f}/5")

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
