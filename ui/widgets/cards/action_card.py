# ui/widgets/cards/action_card.py
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QIcon, QFont, QPixmap, QPainter, QColor, QLinearGradient

from .base_card import PhilosophyCard

class ActionCard(PhilosophyCard):
    """Card para ações rápidas com ícones grandes"""
    
    # Sinal emitido quando card é clicado
    action_triggered = pyqtSignal(str)  # Emite o ID da ação
    
    def __init__(self, action_id: str, title: str, description: str = "", 
                 icon_text: str = "⚡", color: str = None, parent=None):
        super().__init__(parent)
        self.action_id = action_id
        self.title = title
        self.description = description
        self.icon_text = icon_text
        self.color = color or "#556B2F"  # Verde oliva padrão
        
        self.setup_ui()
        self.setup_connections()
        
    def setup_ui(self):
        """Configurar interface do card de ação"""
        self.setMinimumSize(180, 150)
        self.setMaximumSize(220, 180)
        
        # Remover divisória padrão
        self.divider.hide()
        
        # Layout centralizado
        self.main_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Ícone grande
        self.icon_label = QLabel(self.icon_text)
        self.icon_label.setObjectName("action_card_icon")
        self.icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Ajustar tamanho do ícone
        font = self.icon_label.font()
        font.setPointSize(32)
        self.icon_label.setFont(font)
        
        self.main_layout.insertWidget(0, self.icon_label)
        
        # Título
        self.title_label.setText(self.title)
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Descrição (se houver)
        if self.description:
            self.desc_label = QLabel(self.description)
            self.desc_label.setObjectName("action_card_description")
            self.desc_label.setWordWrap(True)
            self.desc_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.content_layout.addWidget(self.desc_label)
            
        # Adicionar cor personalizada
        self.setStyleSheet(f"""
            #action_card_icon {{
                color: {self.color};
                font-size: 32px;
            }}
        """)
        
    def setup_connections(self):
        """Conectar sinais de clique"""
        self.clicked.connect(lambda: self.action_triggered.emit(self.action_id))
        
    def set_icon(self, icon_text: str):
        """Alterar ícone do card"""
        self.icon_text = icon_text
        self.icon_label.setText(icon_text)
        
    def set_color(self, color: str):
        """Alterar cor do card"""
        self.color = color
        self.setStyleSheet(f"""
            #action_card_icon {{
                color: {color};
                font-size: 32px;
            }}
        """)

class QuickActionGrid(QWidget):
    """Grade de cards de ação rápida"""
    
    action_triggered = pyqtSignal(str)
    
    # Definições padrão de ações
    DEFAULT_ACTIONS = [
        {
            "id": "add_book",
            "title": "Adicionar Livro",
            "description": "Processar novo PDF/EPUB",
            "icon": "📚",
            "color": "#8B7355"  # Sépia
        },
        {
            "id": "start_pomodoro",
            "title": "Iniciar Foco",
            "description": "Timer Pomodoro 25min",
            "icon": "⏱️",
            "color": "#556B2F"  # Verde oliva
        },
        {
            "id": "add_note",
            "title": "Nova Nota",
            "description": "Anotação filosófica",
            "icon": "📝",
            "color": "#8B4513"  # Marrom sela
        },
        {
            "id": "ask_glados",
            "title": "Perguntar GLaDOS",
            "description": "Consultar assistente",
            "icon": "🤖",
            "color": "#5D8AA8"  # Azul aço
        },
        {
            "id": "view_stats",
            "title": "Ver Estatísticas",
            "description": "Progresso e métricas",
            "icon": "📊",
            "color": "#4A7C59"  # Verde floresta
        },
        {
            "id": "adjust_agenda",
            "title": "Ajustar Agenda",
            "description": "Reorganizar automaticamente",
            "icon": "🔄",
            "color": "#B68D40"  # Ouro velho
        }
    ]
    
    def __init__(self, actions=None, parent=None):
        super().__init__(parent)
        self.actions = actions or self.DEFAULT_ACTIONS
        self.setup_ui()
        
    def setup_ui(self):
        """Configurar grade de ações"""
        from PyQt6.QtWidgets import QGridLayout
        
        self.grid_layout = QGridLayout(self)
        self.grid_layout.setSpacing(12)
        self.grid_layout.setContentsMargins(0, 0, 0, 0)
        
        # Adicionar cards à grade
        self.cards = []
        row = 0
        col = 0
        
        for action_def in self.actions:
            card = ActionCard(
                action_id=action_def["id"],
                title=action_def["title"],
                description=action_def.get("description", ""),
                icon_text=action_def["icon"],
                color=action_def["color"]
            )
            card.action_triggered.connect(self.action_triggered)
            
            self.grid_layout.addWidget(card, row, col)
            self.cards.append(card)
            
            # Atualizar posição na grade
            col += 1
            if col >= 3:  # 3 colunas
                col = 0
                row += 1
                
    def add_action(self, action_def: dict):
        """Adicionar nova ação à grade"""
        self.actions.append(action_def)
        self.refresh_grid()
        
    def remove_action(self, action_id: str):
        """Remover ação da grade"""
        self.actions = [a for a in self.actions if a["id"] != action_id]
        self.refresh_grid()
        
    def refresh_grid(self):
        """Atualizar grade de ações"""
        # Limpar layout
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
                
        # Recriar cards
        self.cards = []
        row = 0
        col = 0
        
        for action_def in self.actions:
            card = ActionCard(
                action_id=action_def["id"],
                title=action_def["title"],
                description=action_def.get("description", ""),
                icon_text=action_def["icon"],
                color=action_def["color"]
            )
            card.action_triggered.connect(self.action_triggered)
            
            self.grid_layout.addWidget(card, row, col)
            self.cards.append(card)
            
            col += 1
            if col >= 3:
                col = 0
                row += 1