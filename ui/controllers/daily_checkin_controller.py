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
from typing import Optional

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
                    if 'morning' in checkin.notes.lower():
                        self._morning_done_today = True
                    if 'evening' in checkin.notes.lower() or checkin.time > "12:00":
                        self._evening_done_today = True

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
        now = datetime.now()
        current_time = now.time()

        # Após 18h, se ainda não fez check-in noturno
        if current_time >= time(18, 0) and not self._evening_done_today:
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
            # Ainda hoje e não fez check-in noturno
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
