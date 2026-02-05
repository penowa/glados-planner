"""
Widgets de tratamento de erro
"""
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTextEdit
from PyQt6.QtCore import Qt
import logging

logger = logging.getLogger('GLaDOS.UI.Error')


class ErrorRecoveryDialog(QDialog):
    """Diálogo de recuperação de erro"""
    
    def __init__(self, title, message, resolution, recovery_manager, parent=None):
        super().__init__(parent)
        self.title = title
        self.message = message
        self.resolution = resolution or {}
        self.recovery_manager = recovery_manager
        
        self.setWindowTitle("Erro do Sistema")
        self.setFixedSize(500, 400)
        
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(15)
        
        # Título do erro
        title_label = QLabel(self.title)
        title_label.setObjectName("error_title")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Mensagem do erro
        message_text = QTextEdit()
        message_text.setText(self.message)
        message_text.setReadOnly(True)
        message_text.setFixedHeight(100)
        
        # Ações de recuperação
        actions_label = QLabel("Ações de Recuperação Disponíveis:")
        actions_label.setObjectName("error_actions_label")
        
        # Botões de ação
        buttons_layout = QHBoxLayout()
        
        if self.resolution.get('recovery_actions'):
            for action in self.resolution['recovery_actions']:
                btn = QPushButton(action.get('label', 'Recuperar'))
                btn.clicked.connect(
                    lambda checked, a=action: self.execute_recovery(a)
                )
                buttons_layout.addWidget(btn)
        
        # Botão de ignorar
        ignore_btn = QPushButton("Ignorar")
        ignore_btn.clicked.connect(self.reject)
        buttons_layout.addWidget(ignore_btn)
        
        layout.addWidget(title_label)
        layout.addWidget(message_text)
        layout.addWidget(actions_label)
        layout.addLayout(buttons_layout)
        
        self.setLayout(layout)
    
    def execute_recovery(self, action):
        """Executa ação de recuperação"""
        if self.recovery_manager:
            # Executar ação através do recovery manager
            pass
        
        self.accept()