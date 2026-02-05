# ui/widgets/cards/time_card.py
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                            QPushButton, QProgressBar)
from PyQt6.QtCore import Qt, pyqtSignal, QTime
from PyQt6.QtGui import QPainter, QColor, QLinearGradient, QBrush, QPen, QFont

from .base_card import PhilosophyCard

class TimeCard(PhilosophyCard):
    """Card para blocos de tempo na agenda"""
    
    # Sinais
    start_clicked = pyqtSignal(dict)  # Iniciar atividade
    edit_clicked = pyqtSignal(dict)   # Editar atividade
    delete_clicked = pyqtSignal(dict) # Remover atividade
    
    def __init__(self, time_data: dict, parent=None):
        super().__init__(parent)
        self.time_data = time_data
        self.setup_ui()
        self.setup_connections()
        
    def setup_ui(self):
        """Configurar interface do bloco de tempo"""
        self.setMinimumHeight(80)
        
        # Layout principal horizontal
        main_layout = QHBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # Coluna esquerda: horário
        self.setup_time_column(main_layout)
        
        # Coluna central: atividade e progresso
        self.setup_activity_column(main_layout)
        
        # Coluna direita: ações
        self.setup_actions_column(main_layout)
        
        self.content_layout.addLayout(main_layout)
        
        # Estilo baseado no tipo de atividade
        activity_type = self.time_data.get('type', 'leitura')
        self.set_activity_style(activity_type)
        
    def setup_time_column(self, parent_layout):
        """Configurar coluna de horário"""
        time_widget = QWidget()
        time_layout = QVBoxLayout(time_widget)
        time_layout.setSpacing(2)
        
        # Horário de início
        start_time = self.time_data.get('start_time', '09:00')
        self.start_label = QLabel(start_time)
        self.start_label.setObjectName("time_card_start")
        self.start_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Horário de fim
        end_time = self.time_data.get('end_time', '10:00')
        self.end_label = QLabel(end_time)
        self.end_label.setObjectName("time_card_end")
        self.end_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        time_layout.addWidget(self.start_label)
        time_layout.addWidget(QLabel("–"))  # Separador
        time_layout.addWidget(self.end_label)
        
        parent_layout.addWidget(time_widget)
        
    def setup_activity_column(self, parent_layout):
        """Configurar coluna de atividade"""
        activity_widget = QWidget()
        activity_layout = QVBoxLayout(activity_widget)
        activity_layout.setSpacing(4)
        
        # Título da atividade
        title = self.time_data.get('title', 'Atividade sem título')
        self.title_label = QLabel(title)
        self.title_label.setObjectName("time_card_title")
        
        # Descrição
        description = self.time_data.get('description', '')
        if description:
            self.desc_label = QLabel(description)
            self.desc_label.setObjectName("time_card_desc")
            self.desc_label.setWordWrap(True)
            
        # Progresso (se aplicável)
        if 'progress' in self.time_data:
            self.progress_bar = QProgressBar()
            self.progress_bar.setValue(self.time_data['progress'])
            self.progress_bar.setTextVisible(True)
            self.progress_bar.setObjectName("time_card_progress")
            
        activity_layout.addWidget(self.title_label)
        if description:
            activity_layout.addWidget(self.desc_label)
        if hasattr(self, 'progress_bar'):
            activity_layout.addWidget(self.progress_bar)
            
        activity_layout.addStretch()
        parent_layout.addWidget(activity_widget, 1)  # Fator de expansão 1
        
    def setup_actions_column(self, parent_layout):
        """Configurar coluna de ações"""
        actions_widget = QWidget()
        actions_layout = QVBoxLayout(actions_widget)
        actions_layout.setSpacing(4)
        
        # Botão de iniciar/pausar
        self.start_button = QPushButton("▶")
        self.start_button.setObjectName("time_card_start_btn")
        self.start_button.setFixedSize(30, 30)
        self.start_button.setCursor(Qt.CursorShape.PointingHandCursor)
        
        # Botão de editar
        self.edit_button = QPushButton("✏️")
        self.edit_button.setObjectName("time_card_edit_btn")
        self.edit_button.setFixedSize(30, 30)
        self.edit_button.setCursor(Qt.CursorShape.PointingHandCursor)
        
        # Botão de excluir
        self.delete_button = QPushButton("🗑️")
        self.delete_button.setObjectName("time_card_delete_btn")
        self.delete_button.setFixedSize(30, 30)
        self.delete_button.setCursor(Qt.CursorShape.PointingHandCursor)
        
        actions_layout.addWidget(self.start_button)
        actions_layout.addWidget(self.edit_button)
        actions_layout.addWidget(self.delete_button)
        actions_layout.addStretch()
        
        parent_layout.addWidget(actions_widget)
        
    def setup_connections(self):
        """Conectar sinais dos botões"""
        self.start_button.clicked.connect(lambda: self.start_clicked.emit(self.time_data))
        self.edit_button.clicked.connect(lambda: self.edit_clicked.emit(self.time_data))
        self.delete_button.clicked.connect(lambda: self.delete_clicked.emit(self.time_data))
        
    def set_activity_style(self, activity_type: str):
        """Aplicar estilo baseado no tipo de atividade"""
        colors = {
            'leitura': '#556B2F',    # Verde oliva
            'revisão': '#8B7355',    # Sépia
            'produção': '#8B4513',   # Marrom sela
            'planejamento': '#5D8AA8', # Azul aço
            'descanso': '#4A7C59',   # Verde floresta
            'reunião': '#B68D40',    # Ouro velho
        }
        
        color = colors.get(activity_type, '#556B2F')
        self.setStyleSheet(f"""
            QLabel#time_card_title {{
                color: {color};
                font-weight: bold;
                font-size: 14px;
            }}
            
            QProgressBar#time_card_progress {{
                border: 1px solid {color}40;
                border-radius: 4px;
                text-align: center;
            }}
            
            QProgressBar#time_card_progress::chunk {{
                background-color: {color};
                border-radius: 3px;
            }}
        """)
        
    def update_progress(self, progress: int):
        """Atualizar progresso da atividade"""
        self.time_data['progress'] = progress
        if hasattr(self, 'progress_bar'):
            self.progress_bar.setValue(progress)
            
    def update_time_data(self, new_data: dict):
        """Atualizar dados do bloco de tempo"""
        self.time_data.update(new_data)
        
        # Atualizar labels
        self.start_label.setText(self.time_data.get('start_time', '09:00'))
        self.end_label.setText(self.time_data.get('end_time', '10:00'))
        self.title_label.setText(self.time_data.get('title', 'Atividade'))
        
        # Atualizar estilo
        activity_type = self.time_data.get('type', 'leitura')
        self.set_activity_style(activity_type)