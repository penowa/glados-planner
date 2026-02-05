"""
Widgets de notificação
"""
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QFrame, QScrollArea
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
import logging

logger = logging.getLogger('GLaDOS.UI.Notifications')


class NotificationPanel(QWidget):
    """Painel de notificações"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.Popup)
        self.setFixedSize(400, 500)
        self.setObjectName("notification_panel")
        
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Cabeçalho
        header = QFrame()
        header.setObjectName("notification_header")
        header_layout = QVBoxLayout()
        
        title = QLabel("Notificações")
        title.setObjectName("notification_title")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        font = QFont("Georgia", 14, QFont.Weight.Bold)
        title.setFont(font)
        
        header_layout.addWidget(title)
        header.setLayout(header_layout)
        layout.addWidget(header)
        
        # Área de scroll para notificações
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        
        self.notifications_container = QWidget()
        self.notifications_layout = QVBoxLayout()
        self.notifications_layout.setSpacing(5)
        self.notifications_container.setLayout(self.notifications_layout)
        
        scroll_area.setWidget(self.notifications_container)
        layout.addWidget(scroll_area)
        
        # Rodapé
        footer = QFrame()
        footer_layout = QHBoxLayout()
        
        clear_btn = QPushButton("Limpar Todas")
        clear_btn.clicked.connect(self.clear_all)
        
        footer_layout.addWidget(clear_btn)
        footer.setLayout(footer_layout)
        layout.addWidget(footer)
        
        self.setLayout(layout)
    
    def set_notifications(self, notifications):
        """Define notificações a exibir"""
        self.clear_all()
        
        if not notifications:
            label = QLabel("Nenhuma notificação")
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.notifications_layout.addWidget(label)
            return
        
        for notif in notifications:
            widget = NotificationWidget(notif)
            self.notifications_layout.addWidget(widget)
    
    def clear_all(self):
        """Remove todas as notificações"""
        while self.notifications_layout.count():
            child = self.notifications_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()


class NotificationWidget(QFrame):
    """Widget individual de notificação"""
    
    def __init__(self, notification_data):
        super().__init__()
        self.notification_data = notification_data
        self.setObjectName("notification_widget")
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(5)
        
        # Título
        title = QLabel(self.notification_data.get('title', 'Sem título'))
        title.setObjectName("notification_item_title")
        
        # Mensagem
        message = QLabel(self.notification_data.get('message', ''))
        message.setObjectName("notification_item_message")
        message.setWordWrap(True)
        
        # Timestamp
        timestamp = QLabel(self.notification_data.get('timestamp', ''))
        timestamp.setObjectName("notification_item_time")
        
        layout.addWidget(title)
        layout.addWidget(message)
        layout.addWidget(timestamp)
        
        self.setLayout(layout)


class NotificationToast(QWidget):
    """Toast de notificação temporário"""
    
    def __init__(self, notif_type, title, message, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.ToolTip | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        
        # Configurar baseado no tipo
        colors = {
            'error': '#8B0000',
            'warning': '#FF8C00',
            'info': '#1E90FF',
            'success': '#2E8B57'
        }
        
        self.setStyleSheet(f"""
            NotificationToast {{
                background-color: {colors.get(notif_type, '#2D2D2D')};
                border: 2px solid #3A2C1F;
                border-radius: 8px;
                padding: 10px;
            }}
        """)
        
        layout = QVBoxLayout()
        
        title_label = QLabel(title)
        title_label.setStyleSheet("color: white; font-weight: bold;")
        
        message_label = QLabel(message)
        message_label.setStyleSheet("color: #F5F5DC;")
        message_label.setWordWrap(True)
        
        layout.addWidget(title_label)
        layout.addWidget(message_label)
        
        self.setLayout(layout)
        
        # Auto-fechar após 5 segundos
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(5000, self.close)