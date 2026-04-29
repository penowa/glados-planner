"""
Widgets de notificação
"""
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QLabel,
    QPushButton,
    QFrame,
    QScrollArea,
    QHBoxLayout,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
import logging

logger = logging.getLogger('GLaDOS.UI.Notifications')


class NotificationPanel(QWidget):
    """Painel de notificações"""
    
    def __init__(self, event_bus=None, parent=None):
        super().__init__(parent)
        self.event_bus = event_bus
        self.setWindowFlags(Qt.WindowType.Popup)
        self.setFixedSize(400, 500)
        self.setObjectName("notification_panel")
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
        
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Cabeçalho
        header = QFrame()
        header.setObjectName("notification_header")
        header_layout = QVBoxLayout()
        
        title = QLabel("Histórico de notificações")
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
        
        clear_btn = QPushButton("Limpar histórico")
        clear_btn.clicked.connect(self.clear_all)
        
        footer_layout.addWidget(clear_btn)
        footer_layout.addStretch(1)
        footer.setLayout(footer_layout)
        layout.addWidget(footer)
        
        self.setLayout(layout)
    
    def set_notifications(self, notifications):
        """Define notificações a exibir"""
        self._clear_widgets()
        
        if not notifications:
            label = QLabel("Nenhuma notificação")
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.notifications_layout.addWidget(label)
            return
        
        for notif in notifications:
            widget = NotificationWidget(notif)
            self.notifications_layout.addWidget(widget)
        self.notifications_layout.addStretch(1)
    
    def _clear_widgets(self):
        """Remove widgets atuais da lista."""
        while self.notifications_layout.count():
            child = self.notifications_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

    def clear_all(self):
        """Limpa histórico persistido e UI."""
        if self.event_bus and hasattr(self.event_bus, "clear_notifications"):
            self.event_bus.clear_notifications()
        self.set_notifications([])


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
        if message.text():
            layout.addWidget(message)
        if timestamp.text():
            layout.addWidget(timestamp)
        
        self.setLayout(layout)
