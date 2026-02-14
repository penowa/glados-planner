"""
Diálogo para check-in matinal (início do dia)
"""
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QSlider, QTextEdit, QGroupBox,
    QDialogButtonBox, QFormLayout, QSpinBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont

from core.modules.daily_checkin import DailyCheckinSystem

import logging
from datetime import datetime

logger = logging.getLogger('GLaDOS.UI.MorningCheckinDialog')


class MorningCheckinDialog(QDialog):
    """Diálogo para preenchimento do check-in matinal"""

    def __init__(self, checkin_system: DailyCheckinSystem, parent=None):
        super().__init__(parent)
        self.checkin_system = checkin_system
        self.setWindowTitle("☀️ Check-in Matinal")
        self.setMinimumWidth(500)
        self.setModal(True)

        self._setup_ui()
        self._load_suggestions()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        # Cabeçalho
        header = QLabel("Como você está começando o dia?")
        header.setFont(QFont("FiraCode Nerd Font", 14, QFont.Weight.Bold))
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(header)

        # Formulário
        form = QFormLayout()

        # Energia
        self.energy_slider = QSlider(Qt.Orientation.Horizontal)
        self.energy_slider.setRange(1, 5)
        self.energy_slider.setTickInterval(1)
        self.energy_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.energy_slider.setValue(3)
        self.energy_value = QLabel("3")
        self.energy_slider.valueChanged.connect(lambda v: self.energy_value.setText(str(v)))
        energy_layout = QHBoxLayout()
        energy_layout.addWidget(self.energy_slider)
        energy_layout.addWidget(self.energy_value)
        form.addRow("Nível de Energia (1-5):", energy_layout)

        # Foco
        self.focus_slider = QSlider(Qt.Orientation.Horizontal)
        self.focus_slider.setRange(1, 5)
        self.focus_slider.setTickInterval(1)
        self.focus_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.focus_slider.setValue(3)
        self.focus_value = QLabel("3")
        self.focus_slider.valueChanged.connect(lambda v: self.focus_value.setText(str(v)))
        focus_layout = QHBoxLayout()
        focus_layout.addWidget(self.focus_slider)
        focus_layout.addWidget(self.focus_value)
        form.addRow("Nível de Foco (1-5):", focus_layout)

        # Metas do dia (opcional)
        self.goals_edit = QTextEdit()
        self.goals_edit.setPlaceholderText("Quais são suas metas principais para hoje? (opcional)")
        self.goals_edit.setMaximumHeight(80)
        form.addRow("Metas do Dia:", self.goals_edit)

        layout.addLayout(form)

        # Dica personalizada
        self.tip_label = QLabel()
        self.tip_label.setWordWrap(True)
        self.tip_label.setStyleSheet("""
            background-color: #2A2A2A;
            padding: 10px;
            border-radius: 5px;
            color: #B0B0B0;
            font-style: italic;
        """)
        layout.addWidget(self.tip_label)

        # Botões
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def _load_suggestions(self):
        """Carrega dica personalizada baseada nos níveis padrão"""
        energy = self.energy_slider.value()
        focus = self.focus_slider.value()
        tip = self.checkin_system._get_morning_tip(energy, focus)
        self.tip_label.setText(f"💡 Dica: {tip}")

        # Atualizar dica quando sliders mudarem
        self.energy_slider.valueChanged.connect(self._update_tip)
        self.focus_slider.valueChanged.connect(self._update_tip)

    def _update_tip(self):
        energy = self.energy_slider.value()
        focus = self.focus_slider.value()
        tip = self.checkin_system._get_morning_tip(energy, focus)
        self.tip_label.setText(f"💡 Dica: {tip}")

    def accept(self):
        """Salva o check-in matinal e fecha o diálogo"""
        try:
            energy = float(self.energy_slider.value())
            focus = float(self.focus_slider.value())
            goals = self.goals_edit.toPlainText().strip().split('\n')
            goals = [g.strip() for g in goals if g.strip()]

            # Executa a rotina matinal
            routine = self.checkin_system.morning_routine(
                energy_level=energy,
                focus_score=focus,
                goals_today=goals
            )

            logger.info(f"Check-in matinal salvo: energia={energy}, foco={focus}")
            super().accept()

        except Exception as e:
            logger.error(f"Erro ao salvar check-in matinal: {e}")
            # Talvez mostrar mensagem de erro

    def get_data(self):
        """Retorna os dados preenchidos (para uso externo)"""
        return {
            'energy': self.energy_slider.value(),
            'focus': self.focus_slider.value(),
            'goals': self.goals_edit.toPlainText().strip()
        }
