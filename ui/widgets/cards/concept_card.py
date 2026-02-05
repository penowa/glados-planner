# ui/widgets/cards/concept_card.py
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QPainter, QColor, QLinearGradient, QBrush, QPen, QFont

from .base_card import PhilosophyCard

class ConceptCard(PhilosophyCard):
    """Card para conceitos filosóficos com conexões visuais"""
    
    # Sinais
    concept_clicked = pyqtSignal(dict)      # Clicou no conceito
    connections_clicked = pyqtSignal(dict)  # Ver conexões
    notes_clicked = pyqtSignal(dict)        # Ver notas
    
    def __init__(self, concept_data: dict, parent=None):
        super().__init__(parent)
        self.concept_data = concept_data
        self.setup_ui()
        self.setup_connections()
        
    def setup_ui(self):
        """Configurar interface do card de conceito"""
        self.setMinimumSize(240, 160)
        
        # Layout principal
        main_layout = QVBoxLayout()
        main_layout.setSpacing(8)
        
        # Cabeçalho com título e badges
        self.setup_concept_header(main_layout)
        
        # Descrição do conceito
        self.setup_concept_description(main_layout)
        
        # Estatísticas do conceito
        self.setup_concept_stats(main_layout)
        
        # Botões de ação
        self.setup_concept_actions(main_layout)
        
        self.content_layout.addLayout(main_layout)
        
        # Cor baseada no domínio do conceito
        domain = self.concept_data.get('domain', 'ética')
        self.set_domain_style(domain)
        
    def setup_concept_header(self, parent_layout):
        """Configurar cabeçalho do conceito"""
        header_widget = QWidget()
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(0, 0, 0, 0)
        
        # Título do conceito
        title = self.concept_data.get('title', 'Conceito sem nome')
        self.title_label = QLabel(title)
        self.title_label.setObjectName("concept_card_title")
        
        # Badges (domínio, complexidade, etc.)
        badge_widget = self.create_badges_widget()
        
        header_layout.addWidget(self.title_label)
        header_layout.addStretch()
        header_layout.addWidget(badge_widget)
        
        parent_layout.addWidget(header_widget)
        
    def create_badges_widget(self):
        """Criar widget com badges do conceito"""
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setSpacing(4)
        
        # Badge de domínio
        domain = self.concept_data.get('domain', 'ética')
        domain_badge = QLabel(domain.upper()[:3])
        domain_badge.setObjectName("concept_domain_badge")
        domain_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Badge de complexidade
        complexity = self.concept_data.get('complexity', 3)
        complexity_badge = QLabel("★" * complexity)
        complexity_badge.setObjectName("concept_complexity_badge")
        
        layout.addWidget(domain_badge)
        layout.addWidget(complexity_badge)
        
        return widget
        
    def setup_concept_description(self, parent_layout):
        """Configurar descrição do conceito"""
        description = self.concept_data.get('description', 'Sem descrição disponível.')
        self.desc_label = QLabel(self.truncate_text(description, 120))
        self.desc_label.setObjectName("concept_card_description")
        self.desc_label.setWordWrap(True)
        self.desc_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        
        parent_layout.addWidget(self.desc_label)
        
    def setup_concept_stats(self, parent_layout):
        """Configurar estatísticas do conceito"""
        stats_widget = QWidget()
        stats_layout = QHBoxLayout(stats_widget)
        stats_layout.setSpacing(12)
        
        # Notas relacionadas
        notes_count = self.concept_data.get('notes_count', 0)
        notes_label = QLabel(f"📝 {notes_count}")
        notes_label.setObjectName("concept_stats_notes")
        
        # Conexões
        connections_count = self.concept_data.get('connections_count', 0)
        connections_label = QLabel(f"🔗 {connections_count}")
        connections_label.setObjectName("concept_stats_connections")
        
        # Revisões
        reviews_count = self.concept_data.get('reviews_count', 0)
        reviews_label = QLabel(f"🔄 {reviews_count}")
        reviews_label.setObjectName("concept_stats_reviews")
        
        stats_layout.addWidget(notes_label)
        stats_layout.addWidget(connections_label)
        stats_layout.addWidget(reviews_label)
        stats_layout.addStretch()
        
        parent_layout.addWidget(stats_widget)
        
    def setup_concept_actions(self, parent_layout):
        """Configurar botões de ação do conceito"""
        actions_widget = QWidget()
        actions_layout = QHBoxLayout(actions_widget)
        actions_layout.setSpacing(8)
        
        # Botão de ver conexões
        self.connections_button = QPushButton("Ver Conexões")
        self.connections_button.setObjectName("secondary_button")
        self.connections_button.setCursor(Qt.CursorShape.PointingHandCursor)
        
        # Botão de ver notas
        self.notes_button = QPushButton("Ver Notas")
        self.notes_button.setObjectName("secondary_button")
        self.notes_button.setCursor(Qt.CursorShape.PointingHandCursor)
        
        actions_layout.addWidget(self.connections_button)
        actions_layout.addWidget(self.notes_button)
        actions_layout.addStretch()
        
        parent_layout.addWidget(actions_widget)
        
    def setup_connections(self):
        """Conectar sinais dos botões"""
        self.connections_button.clicked.connect(lambda: self.connections_clicked.emit(self.concept_data))
        self.notes_button.clicked.connect(lambda: self.notes_clicked.emit(self.concept_data))
        self.clicked.connect(lambda: self.concept_clicked.emit(self.concept_data))
        
    def set_domain_style(self, domain: str):
        """Aplicar estilo baseado no domínio do conceito"""
        colors = {
            'ética': '#556B2F',       # Verde oliva
            'política': '#8B0000',    # Vermelho escuro
            'metafísica': '#4B0082',  # Índigo
            'epistemologia': '#2F4F4F', # Cinza ardósia
            'lógica': '#4682B4',      # Azul aço
            'estética': '#8B7355',    # Sépia
        }
        
        color = colors.get(domain.lower(), '#556B2F')
        self.setStyleSheet(f"""
            QLabel#concept_card_title {{
                color: {color};
                font-weight: bold;
                font-size: 16px;
            }}
            
            QLabel#concept_domain_badge {{
                background-color: {color}40;
                color: {color};
                border-radius: 8px;
                padding: 2px 6px;
                font-size: 10px;
                font-weight: bold;
            }}
            
            QLabel#concept_stats_notes,
            QLabel#concept_stats_connections,
            QLabel#concept_stats_reviews {{
                color: {color};
                font-size: 12px;
            }}
        """)
        
    def truncate_text(self, text: str, max_length: int) -> str:
        """Truncar texto se for muito longo"""
        if len(text) > max_length:
            return text[:max_length-3] + "..."
        return text