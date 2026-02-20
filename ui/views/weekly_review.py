"""View de revisão semanal com métricas e gráficos de acompanhamento."""

from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional

from PyQt6.QtCore import QPointF, QRectF, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QPainter, QPen
from PyQt6.QtWidgets import (
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QToolBar,
    QVBoxLayout,
    QWidget,
)


class MoodTrendChartWidget(QWidget):
    """Gráfico de linha para variação de humor na semana."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.labels: List[str] = []
        self.values: List[Optional[float]] = []
        self.setMinimumHeight(210)

    def set_data(self, labels: List[str], values: List[Optional[float]]):
        self.labels = list(labels or [])
        self.values = list(values or [])
        self.update()

    def paintEvent(self, _event):
        painter = QPainter(self)
        try:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)

            chart = self.rect().adjusted(46, 16, -16, -34)
            if chart.width() <= 0 or chart.height() <= 0:
                return

            painter.setPen(QPen(QColor("#2D3748"), 1))
            painter.drawRect(chart)

            if not self.labels:
                self._draw_empty_message(painter, chart, "Sem dados de humor.")
                return

            # Linhas de grade (escala 1..5)
            for level in range(1, 6):
                ratio = (level - 1) / 4
                y = chart.bottom() - ratio * chart.height()
                painter.setPen(QPen(QColor("#334155"), 1, Qt.PenStyle.DashLine))
                painter.drawLine(chart.left(), int(y), chart.right(), int(y))
                painter.setPen(QColor("#94A3B8"))
                painter.setFont(QFont("FiraCode Nerd Font Propo", 8))
                painter.drawText(8, int(y + 4), str(level))

            step_x = chart.width() / max(len(self.labels) - 1, 1)

            def map_point(index: int, value: float) -> QPointF:
                x = chart.left() + step_x * index
                y = chart.bottom() - ((max(1.0, min(5.0, value)) - 1.0) / 4.0) * chart.height()
                return QPointF(x, y)

            # Linha principal
            painter.setPen(QPen(QColor("#38BDF8"), 2))
            last_point: Optional[QPointF] = None
            for idx, value in enumerate(self.values):
                if value is None:
                    last_point = None
                    continue
                point = map_point(idx, float(value))
                if last_point is not None:
                    painter.drawLine(last_point, point)
                last_point = point

            # Pontos e labels
            for idx, value in enumerate(self.values):
                if value is None:
                    continue
                point = map_point(idx, float(value))
                painter.setBrush(QColor("#7DD3FC"))
                painter.setPen(QPen(QColor("#0EA5E9"), 1))
                painter.drawEllipse(point, 4.0, 4.0)
                painter.setPen(QColor("#E2E8F0"))
                painter.setFont(QFont("FiraCode Nerd Font Propo", 8))
                painter.drawText(int(point.x() - 10), int(point.y() - 8), f"{float(value):.1f}")

            # Labels de dias
            painter.setPen(QColor("#E2E8F0"))
            painter.setFont(QFont("FiraCode Nerd Font Propo", 8))
            for idx, label in enumerate(self.labels):
                x = chart.left() + step_x * idx
                painter.drawText(int(x - 12), chart.bottom() + 16, str(label))
        finally:
            painter.end()

    def _draw_empty_message(self, painter: QPainter, chart_rect, text: str):
        painter.setPen(QColor("#64748B"))
        painter.setFont(QFont("FiraCode Nerd Font Propo", 10))
        painter.drawText(chart_rect, Qt.AlignmentFlag.AlignCenter, text)


class StatusBarChartWidget(QWidget):
    """Gráfico de barras para comparação entre status de atividades."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.entries: List[tuple[str, int, QColor]] = []
        self.setMinimumHeight(210)

    def set_data(self, entries: List[tuple[str, int, QColor]]):
        self.entries = list(entries or [])
        self.update()

    def paintEvent(self, _event):
        painter = QPainter(self)
        try:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)

            chart = self.rect().adjusted(24, 16, -24, -44)
            if chart.width() <= 0 or chart.height() <= 0:
                return

            painter.setPen(QPen(QColor("#2D3748"), 1))
            painter.drawRect(chart)

            if not self.entries:
                painter.setPen(QColor("#64748B"))
                painter.drawText(chart, Qt.AlignmentFlag.AlignCenter, "Sem atividades para comparar.")
                return

            max_value = max((value for _, value, _ in self.entries), default=1)
            max_value = max(max_value, 1)

            slot_w = chart.width() / max(len(self.entries), 1)
            bar_w = min(56, slot_w * 0.55)

            painter.setFont(QFont("FiraCode Nerd Font Propo", 9))
            for idx, (label, value, color) in enumerate(self.entries):
                x = chart.left() + slot_w * idx + (slot_w - bar_w) / 2
                height = chart.height() * (value / max_value if max_value else 0)
                y = chart.bottom() - height

                painter.setPen(QPen(color.darker(150), 1))
                painter.setBrush(color)
                if height > 0:
                    rect = QRectF(float(x), float(y), float(bar_w), float(height))
                    painter.drawRoundedRect(rect, 4.0, 4.0)

                painter.setPen(QColor("#E2E8F0"))
                painter.drawText(int(x), int(y - 4), int(bar_w), 16, Qt.AlignmentFlag.AlignCenter, str(value))
                painter.setPen(QColor("#94A3B8"))
                painter.drawText(int(x - 8), chart.bottom() + 16, int(bar_w + 16), 18, Qt.AlignmentFlag.AlignCenter, label)
        finally:
            painter.end()


class ActivityPeriodChartWidget(QWidget):
    """Gráfico de barras empilhadas por atividade e período do dia."""

    PERIODS = ("Manhã", "Tarde", "Noite")
    PERIOD_COLORS = {
        "Manhã": QColor("#38BDF8"),
        "Tarde": QColor("#F59E0B"),
        "Noite": QColor("#A78BFA"),
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self.rows: List[tuple[str, Dict[str, float], float]] = []
        self.setMinimumHeight(260)

    def set_data(self, period_matrix: Dict[str, Dict[str, float]]):
        rows = []
        for activity, period_data in (period_matrix or {}).items():
            total = sum(max(0.0, float(period_data.get(period, 0.0) or 0.0)) for period in self.PERIODS)
            rows.append((activity, dict(period_data or {}), total))

        rows.sort(key=lambda item: item[2], reverse=True)
        self.rows = rows[:6]
        dynamic_height = 78 + len(self.rows) * 34
        self.setMinimumHeight(max(240, dynamic_height))
        self.update()

    def paintEvent(self, _event):
        painter = QPainter(self)
        try:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)

            if not self.rows:
                painter.setPen(QColor("#64748B"))
                painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "Sem dados por atividade.")
                return

            left_label_w = 132
            top = 28
            row_gap = 34
            bar_h = 14
            right_pad = 86
            chart_w = max(1, self.width() - left_label_w - right_pad)
            max_total = max((total for _, _, total in self.rows), default=1.0)
            max_total = max(max_total, 1.0)

            # Legenda
            legend_x = left_label_w
            painter.setFont(QFont("FiraCode Nerd Font Propo", 8))
            for period in self.PERIODS:
                color = self.PERIOD_COLORS[period]
                painter.setPen(QPen(color.darker(150), 1))
                painter.setBrush(color)
                painter.drawRoundedRect(legend_x, 8, 12, 8, 2, 2)
                painter.setPen(QColor("#94A3B8"))
                painter.drawText(legend_x + 16, 16, period)
                legend_x += 74

            for row_idx, (activity, values, total) in enumerate(self.rows):
                y = top + row_idx * row_gap
                painter.setPen(QColor("#CBD5E1"))
                painter.setFont(QFont("FiraCode Nerd Font Propo", 9, QFont.Weight.Medium))
                activity_label = activity if len(activity) <= 14 else f"{activity[:13]}…"
                painter.drawText(8, y + 11, activity_label)

                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(QColor("#1E293B"))
                painter.drawRoundedRect(left_label_w, y, chart_w, bar_h, 4, 4)

                if total > 0:
                    row_w = chart_w * (total / max_total)
                    cursor = float(left_label_w)
                    for period in self.PERIODS:
                        period_value = max(0.0, float(values.get(period, 0.0) or 0.0))
                        if period_value <= 0:
                            continue
                        seg_w = row_w * (period_value / total)
                        if seg_w <= 0:
                            continue
                        color = self.PERIOD_COLORS[period]
                        painter.setBrush(color)
                        segment_rect = QRectF(cursor, float(y), float(seg_w), float(bar_h))
                        painter.drawRoundedRect(segment_rect, 3.0, 3.0)
                        cursor += seg_w

                    best_period = max(self.PERIODS, key=lambda p: float(values.get(p, 0.0) or 0.0))
                    painter.setPen(QColor("#94A3B8"))
                    painter.setFont(QFont("FiraCode Nerd Font Propo", 8))
                    painter.drawText(left_label_w + chart_w + 6, y + 11, f"{total:.1f}h")
                    painter.drawText(left_label_w + chart_w + 6, y + 23, best_period)
        finally:
            painter.end()


class WeeklyReviewView(QWidget):
    navigate_to = pyqtSignal(str)

    TRACKABLE_TYPES = {
        "aula",
        "leitura",
        "producao",
        "revisao",
        "revisão",
        "seminario",
        "prova",
        "orientacao",
        "grupo_estudo",
        "revisao_dominical",
    }

    PRODUCTIVE_TYPES = {"leitura", "revisao", "revisão", "producao", "aula", "seminario", "prova"}

    PERIODS = ("Manhã", "Tarde", "Noite")

    TYPE_LABELS = {
        "aula": "Aula",
        "leitura": "Leitura",
        "producao": "Produção",
        "revisao": "Revisão",
        "revisão": "Revisão",
        "seminario": "Seminário",
        "prova": "Prova",
        "orientacao": "Orientação",
        "grupo_estudo": "Grupo Estudo",
        "revisao_dominical": "Revisão Semanal",
        "casual": "Casual",
    }

    def __init__(self, controllers: Optional[Dict] = None):
        super().__init__()
        self.controllers = controllers or {}
        self.setup_ui()
        self.refresh()

    def setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self.toolbar = QToolBar()
        self.back_btn = QPushButton("← Voltar")
        self.back_btn.clicked.connect(lambda: self.navigate_to.emit("dashboard"))
        self.refresh_btn = QPushButton("Atualizar")
        self.refresh_btn.clicked.connect(self.refresh)
        self.toolbar.addWidget(self.back_btn)
        self.toolbar.addSeparator()
        self.toolbar.addWidget(self.refresh_btn)
        root.addWidget(self.toolbar)

        self.title = QLabel("Revisão Semanal")
        self.title.setStyleSheet("font-size: 22px; font-weight: 700; color: #F8FAFC; padding: 10px 16px;")
        root.addWidget(self.title)

        self.subtitle = QLabel("")
        self.subtitle.setStyleSheet("color: #94A3B8; padding: 0 16px 10px 16px;")
        root.addWidget(self.subtitle)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        container = QWidget()
        self.content = QVBoxLayout(container)
        self.content.setContentsMargins(16, 8, 16, 16)
        self.content.setSpacing(12)
        scroll.setWidget(container)
        root.addWidget(scroll, 1)

        self.stats_box = QGroupBox("Resumo da Semana")
        stats_layout = QHBoxLayout(self.stats_box)
        self.productive_days_label = QLabel("Dias produtivos: --")
        self.best_period_label = QLabel("Melhor período: --")
        self.completion_label = QLabel("Taxa de conclusão: --")
        for label in (self.productive_days_label, self.best_period_label, self.completion_label):
            label.setStyleSheet("color: #E2E8F0; font-weight: 600;")
            stats_layout.addWidget(label)
        self.content.addWidget(self.stats_box)

        self.mood_chart_box = QGroupBox("Variação de Humor na Semana")
        mood_layout = QVBoxLayout(self.mood_chart_box)
        self.mood_chart = MoodTrendChartWidget()
        mood_layout.addWidget(self.mood_chart)
        self.content.addWidget(self.mood_chart_box)

        self.status_chart_box = QGroupBox("Concluídas x Atrasadas x Puladas")
        status_layout = QVBoxLayout(self.status_chart_box)
        self.status_chart = StatusBarChartWidget()
        status_layout.addWidget(self.status_chart)
        self.content.addWidget(self.status_chart_box)

        self.activity_period_box = QGroupBox("Período Mais Produtivo por Atividade")
        activity_period_layout = QVBoxLayout(self.activity_period_box)
        self.activity_period_chart = ActivityPeriodChartWidget()
        activity_period_layout.addWidget(self.activity_period_chart)
        self.content.addWidget(self.activity_period_box)

        self.open_sessions_box = QGroupBox("Progresso das Sessões Agendadas em Aberto")
        self.open_sessions_box.setMinimumHeight(420)
        open_layout = QVBoxLayout(self.open_sessions_box)
        self.open_sessions_scroll = QScrollArea()
        self.open_sessions_scroll.setWidgetResizable(True)
        self.open_sessions_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.open_sessions_scroll.setMinimumHeight(340)
        self.open_sessions_container = QWidget()
        self.open_sessions_layout = QVBoxLayout(self.open_sessions_container)
        self.open_sessions_layout.setContentsMargins(0, 0, 0, 0)
        self.open_sessions_layout.setSpacing(8)
        self.open_sessions_scroll.setWidget(self.open_sessions_container)
        open_layout.addWidget(self.open_sessions_scroll)
        self.content.addWidget(self.open_sessions_box)

        self.suggestions_box = QGroupBox("Sugestões da Revisão")
        suggestions_layout = QVBoxLayout(self.suggestions_box)
        self.suggestions_list = QListWidget()
        suggestions_layout.addWidget(self.suggestions_list)
        self.content.addWidget(self.suggestions_box)

    def _week_window(self) -> tuple[date, date]:
        today = datetime.now().date()
        week_start = today - timedelta(days=today.weekday())  # segunda
        week_end = week_start + timedelta(days=6)  # domingo
        return week_start, week_end

    def _period_for_hour(self, hour: int) -> str:
        if hour >= 18:
            return "Noite"
        if hour >= 12:
            return "Tarde"
        return "Manhã"

    def _event_type_value(self, event) -> str:
        return str(getattr(getattr(event, "type", None), "value", "") or "").strip().lower()

    def _event_type_label(self, event) -> str:
        raw = self._event_type_value(event)
        return self.TYPE_LABELS.get(raw, raw.title() if raw else "Atividade")

    def _is_trackable_event(self, event) -> bool:
        event_type = self._event_type_value(event)
        return event_type in self.TRACKABLE_TYPES

    def _is_skipped_event(self, event) -> bool:
        metadata = getattr(event, "metadata", {}) or {}
        progress_notes = getattr(event, "progress_notes", []) or []
        joined_notes = " ".join(str(note).strip().lower() for note in progress_notes if str(note).strip())

        status_value = ""
        if isinstance(metadata, dict):
            status_value = str(metadata.get("status") or metadata.get("session_status") or "").strip().lower()
            if bool(metadata.get("skipped")):
                return True
            if metadata.get("skip_reason"):
                return True

        if status_value == "skipped":
            return True
        return any(token in joined_notes for token in ("skip", "pulad", "adiada definitivamente"))

    def _get_checkin_system(self):
        daily = self.controllers.get("daily_checkin")
        return getattr(daily, "checkin_system", None)

    def _collect_week_events(self, week_start: date, week_end: date):
        agenda_ctrl = self.controllers.get("agenda")
        agenda_manager = getattr(agenda_ctrl, "agenda_manager", None)
        if not agenda_manager:
            return []
        return [
            event for event in agenda_manager.events.values()
            if week_start <= event.start.date() <= week_end
        ]

    def _compute_mood_series(
        self,
        checkin_system,
        week_start: date,
        week_end: date,
    ) -> tuple[List[str], List[Optional[float]]]:
        days = [week_start + timedelta(days=offset) for offset in range(7)]
        labels = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]
        grouped: Dict[date, List[float]] = defaultdict(list)

        if checkin_system and hasattr(checkin_system, "get_recent_checkins"):
            for row in checkin_system.get_recent_checkins(days=14):
                raw_date = str(row.get("date", "")).strip()
                if not raw_date:
                    continue
                try:
                    day = datetime.strptime(raw_date, "%Y-%m-%d").date()
                except Exception:
                    continue
                if day < week_start or day > week_end:
                    continue
                mood = float(row.get("mood_score", 0.0) or 0.0)
                if mood > 0:
                    grouped[day].append(mood)

        values: List[Optional[float]] = []
        for day in days:
            series = grouped.get(day, [])
            if not series:
                values.append(None)
            else:
                values.append(round(sum(series) / len(series), 2))
        return labels, values

    def _compute_status_breakdown(self, events: List) -> Dict[str, int]:
        now = datetime.now()
        counts = {"Concluídas": 0, "Atrasadas": 0, "Puladas": 0}

        for event in events:
            if not self._is_trackable_event(event):
                continue

            if bool(getattr(event, "completed", False)):
                counts["Concluídas"] += 1
                continue

            if self._is_skipped_event(event):
                counts["Puladas"] += 1
                continue

            end_dt = getattr(event, "end", None)
            if isinstance(end_dt, datetime) and end_dt < now:
                counts["Atrasadas"] += 1

        return counts

    def _compute_activity_period_matrix(self, events: List) -> Dict[str, Dict[str, float]]:
        matrix = defaultdict(lambda: {"Manhã": 0.0, "Tarde": 0.0, "Noite": 0.0})

        for event in events:
            if not self._is_trackable_event(event):
                continue
            if not bool(getattr(event, "completed", False)):
                continue

            start_dt = getattr(event, "start", None)
            if not isinstance(start_dt, datetime):
                continue

            period = self._period_for_hour(start_dt.hour)
            activity = self._event_type_label(event)
            matrix[activity][period] += max(0.0, float(event.duration_minutes()) / 60.0)

        # Fallback com eventos não concluídos quando semana ainda está no início.
        if not matrix:
            for event in events:
                if not self._is_trackable_event(event):
                    continue
                start_dt = getattr(event, "start", None)
                if not isinstance(start_dt, datetime):
                    continue
                period = self._period_for_hour(start_dt.hour)
                activity = self._event_type_label(event)
                matrix[activity][period] += max(0.0, float(event.duration_minutes()) / 60.0)

        return dict(matrix)

    def _collect_open_sessions(self, events: List) -> List[Dict]:
        now = datetime.now()
        rows: List[Dict] = []

        for event in sorted(events, key=lambda item: getattr(item, "start", datetime.min)):
            if not self._is_trackable_event(event):
                continue
            if bool(getattr(event, "completed", False)):
                continue
            if self._is_skipped_event(event):
                continue

            start_dt = getattr(event, "start", None)
            end_dt = getattr(event, "end", None)
            if not isinstance(start_dt, datetime) or not isinstance(end_dt, datetime):
                continue

            if now <= start_dt:
                progress = 0
                status = "planejada"
            elif now >= end_dt:
                progress = 100
                status = "atrasada"
            else:
                total_seconds = max((end_dt - start_dt).total_seconds(), 1.0)
                elapsed = max(0.0, (now - start_dt).total_seconds())
                progress = int(max(0.0, min(100.0, (elapsed / total_seconds) * 100.0)))
                status = "em andamento"

            rows.append(
                {
                    "title": str(getattr(event, "title", "Sessão") or "Sessão"),
                    "start": start_dt,
                    "progress": progress,
                    "status": status,
                }
            )

        return rows[:24]

    def _clear_layout_widgets(self, layout: QVBoxLayout):
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            child_layout = item.layout()
            if widget is not None:
                widget.deleteLater()
            elif child_layout is not None:
                self._clear_layout_widgets(child_layout)

    def _status_color(self, status: str) -> str:
        if status == "em andamento":
            return "#F59E0B"
        if status == "atrasada":
            return "#F97316"
        return "#38BDF8"

    def _render_open_sessions(self, rows: List[Dict]):
        self._clear_layout_widgets(self.open_sessions_layout)

        if not rows:
            empty = QLabel("Sem sessões abertas nesta semana.")
            empty.setStyleSheet("color: #94A3B8; padding: 8px;")
            self.open_sessions_layout.addWidget(empty)
            self.open_sessions_layout.addStretch()
            return

        for row in rows:
            wrapper = QFrame()
            wrapper.setStyleSheet(
                "QFrame { background-color: #111827; border: 1px solid #1F2937; border-radius: 8px; }"
            )
            root = QVBoxLayout(wrapper)
            root.setContentsMargins(10, 8, 10, 8)
            root.setSpacing(6)

            header = QHBoxLayout()
            title = QLabel(f"{row['start'].strftime('%a %d/%m %H:%M')} • {row['title']}")
            title.setStyleSheet("color: #E2E8F0; font-weight: 600;")
            header.addWidget(title, 1)

            status_label = QLabel(str(row.get("status", "")).title())
            status_label.setStyleSheet(
                f"color: {self._status_color(row.get('status', ''))}; font-weight: 700;"
            )
            header.addWidget(status_label)
            root.addLayout(header)

            bar = QProgressBar()
            bar.setRange(0, 100)
            bar.setValue(int(row.get("progress", 0)))
            bar.setFormat(f"{int(row.get('progress', 0))}%")
            bar.setStyleSheet(
                f"""
                QProgressBar {{
                    background-color: #0F172A;
                    color: #E2E8F0;
                    border: 1px solid #1E293B;
                    border-radius: 5px;
                    text-align: center;
                    min-height: 16px;
                }}
                QProgressBar::chunk {{
                    background-color: {self._status_color(row.get('status', ''))};
                    border-radius: 5px;
                }}
                """
            )
            root.addWidget(bar)
            self.open_sessions_layout.addWidget(wrapper)

        self.open_sessions_layout.addStretch()

    def refresh(self):
        week_start, week_end = self._week_window()
        self.subtitle.setText(f"Período analisado: {week_start.strftime('%d/%m/%Y')} até {week_end.strftime('%d/%m/%Y')}")

        events = self._collect_week_events(week_start, week_end)
        checkin_system = self._get_checkin_system()

        # Resumo rápido
        productive_days = set()
        day_workload = defaultdict(float)
        completed = 0
        total = 0
        for event in events:
            if not self._is_trackable_event(event):
                continue

            total += 1
            if bool(getattr(event, "completed", False)):
                completed += 1

            event_type = self._event_type_value(event)
            if event_type in self.PRODUCTIVE_TYPES:
                day_workload[event.start.date().isoformat()] += event.duration_minutes()

        for day_key, minutes in day_workload.items():
            if minutes >= 120:
                productive_days.add(day_key)

        if checkin_system:
            for item in checkin_system.get_recent_checkins(days=7):
                if float(item.get("productivity_score", 0.0) or 0.0) >= 6.0:
                    productive_days.add(item.get("date", ""))

        completion_rate = (completed / total * 100) if total else 0.0
        self.productive_days_label.setText(f"Dias produtivos: {len([d for d in productive_days if d])}/7")
        self.completion_label.setText(f"Taxa de conclusão: {completion_rate:.0f}%")

        # Melhor período (agregado)
        period_matrix = self._compute_activity_period_matrix(events)
        period_totals = defaultdict(float)
        for data in period_matrix.values():
            for period in self.PERIODS:
                period_totals[period] += float(data.get(period, 0.0) or 0.0)

        if period_totals:
            best_period = max(period_totals.items(), key=lambda item: item[1])[0]
            self.best_period_label.setText(f"Melhor período: {best_period}")
        else:
            self.best_period_label.setText("Melhor período: --")

        # 1) Humor na semana
        mood_labels, mood_values = self._compute_mood_series(checkin_system, week_start, week_end)
        self.mood_chart.set_data(mood_labels, mood_values)

        # 2) Concluídas x Atrasadas x Puladas
        breakdown = self._compute_status_breakdown(events)
        self.status_chart.set_data(
            [
                ("Concluídas", int(breakdown.get("Concluídas", 0)), QColor("#22C55E")),
                ("Atrasadas", int(breakdown.get("Atrasadas", 0)), QColor("#FB923C")),
                ("Puladas", int(breakdown.get("Puladas", 0)), QColor("#EF4444")),
            ]
        )

        # 3) Período mais produtivo por atividade
        self.activity_period_chart.set_data(period_matrix)

        # 4) Progresso de sessões agendadas em aberto
        open_sessions = self._collect_open_sessions(events)
        self._render_open_sessions(open_sessions)

        suggestions = []
        agenda_ctrl = self.controllers.get("agenda")
        agenda_manager = getattr(agenda_ctrl, "agenda_manager", None)
        if agenda_manager and hasattr(agenda_manager, "suggest_optimizations"):
            for suggestion in agenda_manager.suggest_optimizations()[:3]:
                msg = suggestion.get("message") or suggestion.get("suggestion") or "Ajuste recomendado."
                suggestions.append(f"• {msg}")

        if checkin_system and hasattr(checkin_system, "get_trends"):
            trends = checkin_system.get_trends(days=30)
            for rec in trends.get("recommendations", [])[:3]:
                suggestions.append(f"• {rec}")

        if not suggestions:
            suggestions = ["• Continue com a rotina atual e mantenha consistência diária."]

        self.suggestions_list.clear()
        for suggestion in suggestions:
            self.suggestions_list.addItem(QListWidgetItem(suggestion))

    def on_view_activated(self):
        self.refresh()
