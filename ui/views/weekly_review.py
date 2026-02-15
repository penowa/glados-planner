"""View de revisão semanal com métricas de estudo."""

from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QScrollArea,
    QToolBar,
    QVBoxLayout,
    QWidget,
)


class WeeklyReviewView(QWidget):
    navigate_to = pyqtSignal(str)

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

        self.reading_status_box = QGroupBox("Leituras Atrasadas / Adiantadas")
        reading_layout = QVBoxLayout(self.reading_status_box)
        self.reading_status_list = QListWidget()
        reading_layout.addWidget(self.reading_status_list)
        self.content.addWidget(self.reading_status_box)

        self.periods_box = QGroupBox("Períodos de Estudo")
        periods_layout = QVBoxLayout(self.periods_box)
        self.periods_list = QListWidget()
        periods_layout.addWidget(self.periods_list)
        self.content.addWidget(self.periods_box)

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

    def _compute_best_periods(self, events: List) -> Dict[str, float]:
        buckets = defaultdict(float)
        productive = {"leitura", "revisao", "producao", "aula", "seminario", "prova"}
        for event in events:
            if event.type.value not in productive:
                continue
            h = event.start.hour
            period = "Noite" if h >= 18 else ("Tarde" if h >= 12 else "Manhã")
            buckets[period] += max(0.0, event.duration_minutes() / 60.0)
        return dict(buckets)

    def _compute_reading_status(self) -> List[str]:
        agenda_ctrl = self.controllers.get("agenda")
        reading_manager = getattr(getattr(agenda_ctrl, "agenda_manager", None), "reading_manager", None)
        if not reading_manager or not hasattr(reading_manager, "list_books"):
            return []

        now = datetime.now().date()
        rows = []
        for book in reading_manager.list_books(include_progress=True):
            title = book.get("title", "Livro")
            pct = float(book.get("percentage", 0.0) or 0.0)
            # Usa progresso + última leitura como heurística de atraso/adianto.
            last_read_raw = str(book.get("last_read", "") or "")
            last_read_days = None
            try:
                last_read = datetime.fromisoformat(last_read_raw.replace("Z", "+00:00")).date()
                last_read_days = (now - last_read).days
            except Exception:
                pass

            if pct >= 95:
                rows.append(f"✅ {title}: adiantada ({pct:.0f}%)")
            elif last_read_days is not None and last_read_days >= 7:
                rows.append(f"⚠️ {title}: atrasada (sem progresso há {last_read_days} dias)")
            elif pct >= 60:
                rows.append(f"🟢 {title}: no ritmo ({pct:.0f}%)")
            else:
                rows.append(f"🕒 {title}: precisa acelerar ({pct:.0f}%)")
        return rows

    def refresh(self):
        week_start, week_end = self._week_window()
        self.subtitle.setText(f"Período analisado: {week_start.strftime('%d/%m/%Y')} até {week_end.strftime('%d/%m/%Y')}")

        events = self._collect_week_events(week_start, week_end)
        checkin_system = self._get_checkin_system()

        # Dias produtivos
        productive_days = set()
        day_workload = defaultdict(float)
        completed = 0
        total = 0
        for event in events:
            total += 1
            if event.completed:
                completed += 1
            if event.type.value in {"leitura", "revisao", "producao", "aula", "seminario", "prova"}:
                day_workload[event.start.date().isoformat()] += event.duration_minutes()
        for day, minutes in day_workload.items():
            if minutes >= 120:
                productive_days.add(day)

        if checkin_system:
            for item in checkin_system.get_recent_checkins(days=7):
                if float(item.get("productivity_score", 0.0) or 0.0) >= 6.0:
                    productive_days.add(item.get("date", ""))

        completion_rate = (completed / total * 100) if total else 0.0
        self.productive_days_label.setText(f"Dias produtivos: {len([d for d in productive_days if d])}/7")
        self.completion_label.setText(f"Taxa de conclusão: {completion_rate:.0f}%")

        periods = self._compute_best_periods(events)
        if periods:
            best_period = max(periods.items(), key=lambda x: x[1])[0]
            self.best_period_label.setText(f"Melhor período: {best_period}")
        else:
            self.best_period_label.setText("Melhor período: --")

        self.periods_list.clear()
        for period in ("Manhã", "Tarde", "Noite"):
            hours = periods.get(period, 0.0)
            self.periods_list.addItem(QListWidgetItem(f"{period}: {hours:.1f}h de estudo"))

        self.reading_status_list.clear()
        reading_rows = self._compute_reading_status()
        if not reading_rows:
            self.reading_status_list.addItem(QListWidgetItem("Sem dados de leitura suficientes."))
        else:
            for row in reading_rows:
                self.reading_status_list.addItem(QListWidgetItem(row))

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
        for s in suggestions:
            self.suggestions_list.addItem(QListWidgetItem(s))

    def on_view_activated(self):
        self.refresh()

