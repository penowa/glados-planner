"""
Barra de navegação lateral
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QPushButton, QLabel, 
    QSpacerItem, QSizePolicy, QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QFont, QIcon, QPixmap

class NavigationBar(QWidget):
    """Barra de navegação lateral"""
    
    view_changed = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        self.current_view = 'dashboard'
        self.buttons = {}
        
        self.setup_ui()
        self.setup_connections()
    
    def setup_ui(self):
        """Configura interface da barra de navegação"""
        self.setObjectName("navigation_bar")
        self.setFixedWidth(240)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 30, 20, 30)
        layout.setSpacing(10)
        
        # Logo/Título
        logo_widget = self.create_logo()
        layout.addWidget(logo_widget)
        
        layout.addSpacing(30)
        
        # Botões de navegação principal
        nav_items = [
            {'id': 'dashboard', 'icon': '🏠', 'text': 'Dashboard'},
            {'id': 'library', 'icon': '📚', 'text': 'Biblioteca'},
            {'id': 'agenda', 'icon': '📅', 'text': 'Agenda'},
            {'id': 'focus', 'icon': '⏱️', 'text': 'Modo Foco'},
            {'id': 'concepts', 'icon': '🧠', 'text': 'Conceitos'},
        ]
        
        for item in nav_items:
            btn = self.create_nav_button(item['icon'], item['text'])
            btn.setObjectName(f"nav_btn_{item['id']}")
            btn.clicked.connect(lambda checked, v=item['id']: self.on_nav_click(v))
            
            if item['id'] == 'dashboard':
                btn.setProperty('active', True)
            
            self.buttons[item['id']] = btn
            layout.addWidget(btn)
        
        layout.addSpacing(20)
        
        # Separador
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(separator)
        
        layout.addSpacing(20)
        
        # Botões de navegação secundária
        secondary_items = [
            {'id': 'analytics', 'icon': '📊', 'text': 'Analytics'},
            {'id': 'goals', 'icon': '🎯', 'text': 'Metas'},
            {'id': 'glados', 'icon': '🤖', 'text': 'GLaDOS'},
            {'id': 'settings', 'icon': '⚙️', 'text': 'Configurações'},
        ]
        
        for item in secondary_items:
            btn = self.create_nav_button(item['icon'], item['text'])
            btn.setObjectName(f"nav_btn_{item['id']}")
            btn.clicked.connect(lambda checked, v=item['id']: self.on_nav_click(v))
            
            self.buttons[item['id']] = btn
            layout.addWidget(btn)
        
        # Spacer para empurrar conteúdo para cima
        layout.addSpacerItem(QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))
        
        # Footer
        footer = self.create_footer()
        layout.addWidget(footer)
    
    def create_logo(self):
        """Cria widget do logo"""
        logo_widget = QWidget()
        logo_layout = QVBoxLayout(logo_widget)
        logo_layout.setContentsMargins(0, 0, 0, 0)
        logo_layout.setSpacing(5)
        
        # Título principal
        title = QLabel("GLaDOS")
        title.setObjectName("nav_title")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setWordWrap(True)
        
        # Subtítulo
        subtitle = QLabel("Philosophy Planner")
        subtitle.setObjectName("nav_subtitle")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        logo_layout.addWidget(title)
        logo_layout.addWidget(subtitle)
        
        return logo_widget
    
    def create_nav_button(self, icon, text):
        """Cria botão de navegação"""
        btn = QPushButton(f"{icon}  {text}")
        btn.setObjectName("nav_button")
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setCheckable(True)
        btn.setMinimumHeight(50)
        
        return btn
    
    def create_footer(self):
        """Cria footer da barra de navegação"""
        footer = QWidget()
        footer.setObjectName("nav_footer")
        footer_layout = QVBoxLayout(footer)
        footer_layout.setContentsMargins(0, 10, 0, 0)
        footer_layout.setSpacing(5)
        
        # Status do sistema
        status_label = QLabel("🟢 Sistema operacional")
        status_label.setObjectName("nav_status")
        status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Versão
        version_label = QLabel("v1.0.0 Alpha")
        version_label.setObjectName("nav_version")
        version_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        footer_layout.addWidget(status_label)
        footer_layout.addWidget(version_label)
        
        return footer
    
    def setup_connections(self):
        """Configura conexões dos botões"""
        # Navegação já configurada em setup_ui
        pass
    
    def on_nav_click(self, view_name):
        """Lida com clique em botão de navegação"""
        # Atualizar estado dos botões
        for btn_id, btn in self.buttons.items():
            btn.setProperty('active', btn_id == view_name)
            btn.style().polish(btn)  # Forçar atualização do estilo
        
        # Emitir sinal
        self.current_view = view_name
        self.view_changed.emit(view_name)
    
    def set_active_view(self, view_name):
        """Define view ativa programaticamente"""
        if view_name in self.buttons:
            self.on_nav_click(view_name)