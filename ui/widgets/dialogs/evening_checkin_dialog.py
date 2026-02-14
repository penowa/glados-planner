"""
Diálogo para check-in noturno (encerramento do dia)
"""
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QSlider, QTextEdit, QGroupBox,
    QDialogButtonBox, QFormLayout
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont

from core.modules.daily_checkin import DailyCheckinSystem

import logging
from datetime import datetime

logger = logging.getLogger('GLaDOS.UI.EveningCheckinDialog')


class EveningCheckinDialog(QDialog):
    """Diálogo para preenchimento do check-in noturno"""

    def __init__(self, checkin_system: DailyCheckinSystem, parent=None):
        super().__init__(parent)
        self.checkin_system = checkin_system
        self.setWindowTitle("🌙 Check-in Noturno")
        self.setMinimumWidth(550)
        self.setModal(True)

        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        # Cabeçalho
        header = QLabel("Como foi o seu dia?")
        header.setFont(QFont("FiraCode Nerd Font", 14, QFont.Weight.Bold))
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(header)

        # Formulário
        form = QFormLayout()

        # Humor
        self.mood_slider = QSlider(Qt.Orientation.Horizontal)
        self.mood_slider.setRange(1, 5)
        self.mood_slider.setTickInterval(1)
        self.mood_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.mood_slider.setValue(3)
        self.mood_value = QLabel("3")
        self.mood_slider.valueChanged.connect(lambda v: self.mood_value.setText(str(v)))
        mood_layout = QHBoxLayout()
        mood_layout.addWidget(self.mood_slider)
        mood_layout.addWidget(self.mood_value)
        form.addRow("Humor (1-5):", mood_layout)

        # Conquistas
        self.achievements_edit = QTextEdit()
        self.achievements_edit.setPlaceholderText("O que você conquistou hoje? (um por linha)")
        self.achievements_edit.setMaximumHeight(80)
        form.addRow("Conquistas:", self.achievements_edit)

        # Desafios
        self.challenges_edit = QTextEdit()
        self.challenges_edit.setPlaceholderText("Quais desafios enfrentou?")
        self.challenges_edit.setMaximumHeight(80)
        form.addRow("Desafios:", self.challenges_edit)

        # Insights
        self.insights_edit = QTextEdit()
        self.insights_edit.setPlaceholderText("Teve algum insight ou aprendizado importante?")
        self.insights_edit.setMaximumHeight(80)
        form.addRow("Insights:", self.insights_edit)

        layout.addLayout(form)

        # Resumo automático (será preenchido após aceitar)
        self.summary_label = QLabel()
        self.summary_label.setWordWrap(True)
        self.summary_label.setStyleSheet("""
            background-color: #2A2A2A;
            padding: 10px;
            border-radius: 5px;
            color: #B0B0B0;
            font-style: italic;
        """)
        layout.addWidget(self.summary_label)

        # Botões
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def accept(self):
        """Salva o check-in noturno e fecha o diálogo"""
        try:
            mood = float(self.mood_slider.value())
            achievements = self.achievements_edit.toPlainText().strip().split('\n')
            achievements = [a.strip() for a in achievements if a.strip()]
            challenges = self.challenges_edit.toPlainText().strip().split('\n')
            challenges = [c.strip() for c in challenges if c.strip()]
            insights = self.insights_edit.toPlainText().strip().split('\n')
            insights = [i.strip() for i in insights if i.strip()]

            # Executa check-in noturno
            analysis = self.checkin_system.evening_checkin(
                mood_score=mood,
                achievements=achievements,
                challenges=challenges,
                insights=insights
            )

            # Mostra resumo
            self.summary_label.setText(f"📊 Resumo: {analysis['summary']}")
            logger.info(f"Check-in noturno salvo: humor={mood}, conquistas={len(achievements)}")

            # Aguarda um pouco para o usuário ver o resumo antes de fechar
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(2000, super().accept)

        except Exception as e:
            logger.error(f"Erro ao salvar check-in noturno: {e}")
            super().accept()  # Fecha mesmo assim

    def get_data(self):
        """Retorna os dados preenchidos (para uso externo)"""
        return {
            'mood': self.mood_slider.value(),
            'achievements': self.achievements_edit.toPlainText().strip(),
            'challenges': self.challenges_edit.toPlainText().strip(),
            'insights': self.insights_edit.toPlainText().strip()
        }
