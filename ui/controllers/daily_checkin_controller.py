"""
Controller para integração do sistema de check-in diário com a UI.
Gerencia notificações, diálogos e detecção de horários apropriados.
"""
from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot, QTimer, QDateTime, Qt
from PyQt6.QtWidgets import QDialog

from core.modules.daily_checkin import DailyCheckinSystem
from ui.widgets.dialogs.morning_checkin_dialog import MorningCheckinDialog
from ui.widgets.dialogs.evening_checkin_dialog import EveningCheckinDialog

import logging
from datetime import datetime, time
from typing import Any, Dict, Optional

logger = logging.getLogger('GLaDOS.Controllers.DailyCheckin')


class DailyCheckinController(QObject):
    """Controla o fluxo de check-ins diários (matinal e noturno)"""

    # Sinais para a UI
    morning_checkin_needed = pyqtSignal()          # Deve mostrar notificação matinal
    evening_checkin_needed = pyqtSignal()          # Deve mostrar notificação noturna
    checkin_completed = pyqtSignal(str, dict)      # (tipo, dados) tipo: 'morning' ou 'evening'

    def __init__(self, checkin_system: DailyCheckinSystem, agenda_controller=None, parent=None):
        super().__init__(parent)
        self.checkin_system = checkin_system
        self.agenda_controller = agenda_controller

        # Estado interno
        self._morning_done_today = False
        self._evening_done_today = False
        self._last_check_date = None

        # Timers
        self._setup_timers()

        # Conectar com agenda se disponível
        if agenda_controller:
            self._connect_agenda()

        # Verificar estado inicial
        self._check_today_status()

        logger.info("DailyCheckinController inicializado")

    def _setup_timers(self):
        """Configura timers para verificação periódica"""
        # Timer minuto a minuto para verificar hora do dia
        self.minute_timer = QTimer()
        self.minute_timer.timeout.connect(self._check_time_of_day)
        self.minute_timer.start(60000)  # 1 minuto

        # Timer para verificar fim do dia (mais espaçado)
        self.evening_check_timer = QTimer()
        self.evening_check_timer.timeout.connect(self._check_evening_condition)
        self.evening_check_timer.start(300000)  # 5 minutos

    def _connect_agenda(self):
        """Conecta sinais da agenda para detecção de fim de tarefas"""
        if hasattr(self.agenda_controller, 'event_completed'):
            self.agenda_controller.event_completed.connect(self._on_event_completed)

    def _check_today_status(self):
        """Verifica se já foram feitos check-ins hoje"""
        today = datetime.now().strftime("%Y-%m-%d")
        if self._last_check_date != today:
            self._last_check_date = today
            self._morning_done_today = False
            self._evening_done_today = False

            # Carregar check-ins existentes para hoje
            for checkin in self.checkin_system.checkins.values():
                if checkin.date == today:
                    checkin_type = self._infer_checkin_type(checkin)
                    if checkin_type == "morning":
                        self._morning_done_today = True
                    elif checkin_type == "evening":
                        self._evening_done_today = True

    def _infer_checkin_type(self, checkin) -> str:
        """Infere tipo do check-in a partir de notas e horário."""
        notes = str(getattr(checkin, "notes", "") or "").strip().lower()
        if any(token in notes for token in ("morning", "matinal", "manhã")):
            return "morning"
        if any(token in notes for token in ("evening", "noturno", "noite")):
            return "evening"

        time_raw = str(getattr(checkin, "time", "") or "").strip()
        try:
            parsed = datetime.strptime(time_raw, "%H:%M").time()
        except Exception:
            return ""
        return "morning" if parsed < time(12, 0) else "evening"

    def _resolve_event_type(self, event: Any) -> str:
        """Extrai tipo do evento em formato estável."""
        if isinstance(event, dict):
            raw = event.get("type")
            if hasattr(raw, "value"):
                raw = getattr(raw, "value", "")
            return str(raw or "").strip().lower()

        event_type = getattr(event, "type", None)
        if hasattr(event_type, "value"):
            return str(getattr(event_type, "value", "") or "").strip().lower()
        return str(event_type or "").strip().lower()

    def _resolve_event_end(self, event: Any) -> Optional[datetime]:
        """Obtém término do evento, suportando dicionário e objeto."""
        end_value = event.get("end") if isinstance(event, dict) else getattr(event, "end", None)
        if isinstance(end_value, datetime):
            return end_value

        raw = str(end_value or "").strip()
        if not raw:
            return None
        try:
            return datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except Exception:
            try:
                return datetime.strptime(raw, "%Y-%m-%d %H:%M")
            except Exception:
                return None

    def _iter_today_events(self):
        """Retorna eventos de hoje (objetos ou dicionários)."""
        if not self.agenda_controller:
            return []

        today = datetime.now().date()
        events = []
        agenda_manager = getattr(self.agenda_controller, "agenda_manager", None)
        event_map = getattr(agenda_manager, "events", None)

        if isinstance(event_map, dict):
            for event in event_map.values():
                start_dt = getattr(event, "start", None)
                if isinstance(start_dt, datetime) and start_dt.date() == today:
                    events.append(event)
            return events

        if hasattr(self.agenda_controller, "load_agenda"):
            date_str = today.strftime("%Y-%m-%d")
            try:
                loaded = self.agenda_controller.load_agenda(date_str) or []
                events.extend(loaded)
            except Exception:
                return []
        return events

    def _get_last_activity_end(self) -> Optional[datetime]:
        """
        Retorna horário final da última atividade agendada de hoje.

        Ignora eventos de check-in para não antecipar o gatilho noturno.
        """
        latest_end: Optional[datetime] = None
        for event in self._iter_today_events():
            event_type = self._resolve_event_type(event)
            if event_type == "checkin":
                continue

            end_dt = self._resolve_event_end(event)
            if not isinstance(end_dt, datetime):
                continue
            if latest_end is None or end_dt > latest_end:
                latest_end = end_dt
        return latest_end

    def _get_evening_trigger_datetime(self) -> datetime:
        """
        Define início do lembrete noturno.

        Regra: após a última atividade do dia; sem atividades, usa 18:00.
        """
        now = datetime.now()
        last_event_end = self._get_last_activity_end()
        if last_event_end:
            return last_event_end
        return datetime.combine(now.date(), time(18, 0))

    def get_dashboard_state(self) -> Dict[str, Any]:
        """
        Estado do botão de check-in na dashboard.

        Returns:
            active_type: 'morning' | 'evening' | None
            pulse: se botão deve pulsar
            waiting_evening: evening pendente, porém ainda antes do gatilho
            evening_trigger_time: HH:MM do início esperado para check-in noturno
        """
        self._check_today_status()
        now = datetime.now()

        morning_pending = not self._morning_done_today
        evening_pending = not self._evening_done_today
        morning_window_open = now.time() < time(18, 0)

        evening_trigger = self._get_evening_trigger_datetime()
        evening_due = evening_pending and now >= evening_trigger

        if morning_pending and morning_window_open:
            active_type = "morning"
            pulse = True
        elif evening_due:
            active_type = "evening"
            pulse = True
        elif evening_pending:
            active_type = "evening"
            pulse = False
        else:
            active_type = None
            pulse = False

        return {
            "active_type": active_type,
            "pulse": pulse,
            "morning_pending": morning_pending,
            "evening_pending": evening_pending,
            "waiting_evening": bool(evening_pending and not evening_due),
            "evening_trigger_time": evening_trigger.strftime("%H:%M"),
        }

    def _check_time_of_day(self):
        """Verifica se é hora de mostrar check-in matinal"""
        now = datetime.now()
        current_time = now.time()

        # Período matinal: entre 5h e 12h
        if time(5, 0) <= current_time <= time(12, 0):
            if not self._morning_done_today:
                self.morning_checkin_needed.emit()

    def _check_evening_condition(self):
        """Verifica se é hora de mostrar check-in noturno (após 18h ou fim da agenda)"""
        self._check_today_status()
        if self._morning_done_today is False and datetime.now().time() < time(18, 0):
            return

        dashboard_state = self.get_dashboard_state()
        if dashboard_state.get("active_type") == "evening" and dashboard_state.get("pulse"):
            self.evening_checkin_needed.emit()

    def _on_event_completed(self, event_id: str, completed: bool):
        """Quando um evento da agenda é completado, verifica se todos foram concluídos"""
        if not self.agenda_controller:
            return

        today = datetime.now().strftime("%Y-%m-%d")
        events_today = self.agenda_controller.load_agenda(today)

        # Se todos os eventos estão concluídos
        all_completed = all(event.get('completed', False) for event in events_today)

        if all_completed and not self._evening_done_today:
            dashboard_state = self.get_dashboard_state()
            if dashboard_state.get("active_type") == "evening" and dashboard_state.get("pulse"):
                self.evening_checkin_needed.emit()

    # ===== Métodos públicos =====

    @pyqtSlot()
    def show_morning_dialog(self, parent=None):
        """Abre o diálogo de check-in matinal"""
        if self._morning_done_today:
            logger.info("Check-in matinal já realizado hoje")
            return

        dialog = MorningCheckinDialog(self.checkin_system, parent)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self._morning_done_today = True
            self.checkin_completed.emit('morning', dialog.get_data())

    @pyqtSlot()
    def show_evening_dialog(self, parent=None):
        """Abre o diálogo de check-in noturno"""
        if self._evening_done_today:
            logger.info("Check-in noturno já realizado hoje")
            return

        dialog = EveningCheckinDialog(self.checkin_system, parent)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self._evening_done_today = True
            self.checkin_completed.emit('evening', dialog.get_data())

    @pyqtSlot(result=bool)
    def is_morning_pending(self) -> bool:
        """Retorna True se check-in matinal pendente"""
        self._check_today_status()
        return not self._morning_done_today

    @pyqtSlot(result=bool)
    def is_evening_pending(self) -> bool:
        """Retorna True se check-in noturno pendente"""
        self._check_today_status()
        return not self._evening_done_today

    def cleanup(self):
        """Para timers ao encerrar"""
        self.minute_timer.stop()
        self.evening_check_timer.stop()
        logger.info("DailyCheckinController finalizado")
