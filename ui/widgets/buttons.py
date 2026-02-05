# ui/widgets/buttons.py
from PyQt6.QtWidgets import QPushButton
from PyQt6.QtCore import QSize

class ActionButton(QPushButton):
    """Botão de ação primário"""
    
    def __init__(self, text: str = "", parent=None):
        super().__init__(text, parent)
        self.setObjectName("primary-button")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        
class IconButton(QPushButton):
    """Botão com ícone grande"""
    
    def __init__(self, icon_text: str = "", parent=None):
        super().__init__(icon_text, parent)
        self.setObjectName("icon-button")
        self.setFixedSize(60, 60)
        font = self.font()
        font.setPointSize(24)
        self.setFont(font)