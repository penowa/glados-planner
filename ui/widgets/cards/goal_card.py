# ui/widgets/cards/goal_card.py
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QProgressBar
from PyQt6.QtCore import Qt, pyqtSignal, QDate
from PyQt6.QtGui import QPainter, QColor, QLinearGradient, QBrush, QPen, QFont

from .base_card import PhilosophyCard

class GoalCard(PhilosophyCard):
    """Card para metas e objetivos com progresso visual"""
    
    # Sinais
    goal_clicked = pyqtSignal(dict)      # Clicou na meta
    update_clicked = pyqtSignal(dict)    # Atualizar progresso
    celebrate_clicked = pyqtSignal(dict) # Celebrar conquista
    
    def __init__(self, goal_data: dict, parent=None):
        super().__init__(parent)
        self.goal_data = goal_data
        self.setup_ui()
        self.setup_connections()
        
    def setup_ui(self):
        """Configurar interface do card de meta"""
        self.setMinimumSize(280, 180)
        
        # Layout principal
        main_layout = QVBoxLayout()
        main_layout.setSpacing(10)
        
        # Cabeçalho com título e prazo
        self.setup_goal_header(main_layout)
        
        # Barra de progresso principal
        self.setup_progress_section(main_layout)
        
        # Métricas e estatísticas
        self.setup_goal_metrics(main_layout)
        
        # Botões de ação
        self.setup_goal_actions(main_layout)
        
        self.content_layout.addLayout(main_layout)
        
        # Estilo baseado na prioridade
        priority = self.goal_data.get('priority', 'medium')
        self.set_priority_style(priority)
        
    def setup_goal_header(self, parent_layout):
        """Configurar cabeçalho da meta"""
        header_widget = QWidget()
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(0, 0, 0, 0)
        
        # Título da meta
        title = self.goal_data.get('title', 'Meta sem título')
        self.title_label = QLabel(title)
        self.title_label.setObjectName("goal_card_title")
        
        # Prazo
        deadline = self.goal_data.get('deadline', '')
        if deadline:
            deadline_label = QLabel(f"📅 {deadline}")
            deadline_label.setObjectName("goal_card_deadline")
            
        header_layout.addWidget(self.title_label)
        if deadline:
            header_layout.addStretch()
            header_layout.addWidget(deadline_label)
            
        parent_layout.addWidget(header_widget)
        
    def setup_progress_section(self, parent_layout):
        """Configurar seção de progresso"""
        progress_widget = QWidget()
        progress_layout = QVBoxLayout(progress_widget)
        progress_layout.setSpacing(4)
        
        # Barra de progresso visual
        progress = self.goal_data.get('progress', 0)
        self.progress_bar = GoalProgressBar(progress)
        
        # Texto de progresso
        progress_text = QLabel(f"Progresso: {progress}%")
        progress_text.setObjectName("goal_card_progress_text")
        progress_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        progress_layout.addWidget(self.progress_bar)
        progress_layout.addWidget(progress_text)
        
        parent_layout.addWidget(progress_widget)
        
    def setup_goal_metrics(self, parent_layout):
        """Configurar métricas da meta"""
        metrics_widget = QWidget()
        metrics_layout = QHBoxLayout(metrics_widget)
        metrics_layout.setSpacing(12)
        
        # Tempo restante
        days_left = self.goal_data.get('days_left', 0)
        time_label = QLabel(f"⏳ {days_left} dias")
        time_label.setObjectName("goal_card_time")
        
        # Submetas concluídas
        subgoals = self.goal_data.get('subgoals', [])
        completed = sum(1 for sg in subgoals if sg.get('completed', False))
        total = len(subgoals)
        subgoals_label = QLabel(f"✅ {completed}/{total}")
        subgoals_label.setObjectName("goal_card_subgoals")
        
        # Dificuldade
        difficulty = self.goal_data.get('difficulty', 3)
        difficulty_label = QLabel("★" * difficulty)
        difficulty_label.setObjectName("goal_card_difficulty")
        
        metrics_layout.addWidget(time_label)
        metrics_layout.addWidget(subgoals_label)
        metrics_layout.addWidget(difficulty_label)
        metrics_layout.addStretch()
        
        parent_layout.addWidget(metrics_widget)
        
    def setup_goal_actions(self, parent_layout):
        """Configurar botões de ação da meta"""
        actions_widget = QWidget()
        actions_layout = QHBoxLayout(actions_widget)
        actions_layout.setSpacing(8)
        
        # Botão de atualizar progresso
        self.update_button = QPushButton("Atualizar")
        self.update_button.setObjectName("secondary_button")
        self.update_button.setCursor(Qt.CursorShape.PointingHandCursor)
        
        # Botão de celebrar (aparece quando concluído)
        if self.goal_data.get('progress', 0) >= 100:
            self.celebrate_button = QPushButton("🎉 Celebrar!")
            self.celebrate_button.setObjectName("primary_button")
            self.celebrate_button.setCursor(Qt.CursorShape.PointingHandCursor)
            actions_layout.addWidget(self.celebrate_button)
        else:
            actions_layout.addWidget(self.update_button)
            
        actions_layout.addStretch()
        
        parent_layout.addWidget(actions_widget)
        
    def setup_connections(self):
        """Conectar sinais dos botões"""
        self.update_button.clicked.connect(lambda: self.update_clicked.emit(self.goal_data))
        if hasattr(self, 'celebrate_button'):
            self.celebrate_button.clicked.connect(lambda: self.celebrate_clicked.emit(self.goal_data))
        self.clicked.connect(lambda: self.goal_clicked.emit(self.goal_data))
        
    def set_priority_style(self, priority: str):
        """Aplicar estilo baseado na prioridade"""
        colors = {
            'high': '#8B0000',    # Vermelho escuro - urgente
            'medium': '#B68D40',  # Ouro velho - importante
            'low': '#556B2F',     # Verde oliva - normal
            'completed': '#4A7C59' # Verde floresta - concluído
        }
        
        progress = self.goal_data.get('progress', 0)
        if progress >= 100:
            color = colors['completed']
        else:
            color = colors.get(priority, '#556B2F')
            
        self.setStyleSheet(f"""
            QLabel#goal_card_title {{
                color: {color};
                font-weight: bold;
                font-size: 16px;
            }}
            
            QLabel#goal_card_deadline {{
                color: {color}80;
                font-size: 12px;
            }}
            
            QLabel#goal_card_progress_text {{
                color: {color};
                font-size: 12px;
                font-weight: bold;
            }}
        """)
        
    def update_progress(self, progress: int):
        """Atualizar progresso da meta"""
        self.goal_data['progress'] = max(0, min(100, progress))
        self.progress_bar.set_progress(progress)
        
        # Atualizar texto
        progress_text = self.findChild(QLabel, "goal_card_progress_text")
        if progress_text:
            progress_text.setText(f"Progresso: {progress}%")
            
        # Atualizar botões se concluído
        if progress >= 100 and not hasattr(self, 'celebrate_button'):
            # Remover botão de atualizar
            if hasattr(self, 'update_button'):
                self.update_button.hide()
                
            # Adicionar botão de celebrar
            self.celebrate_button = QPushButton("🎉 Celebrar!")
            self.celebrate_button.setObjectName("primary_button")
            self.celebrate_button.setCursor(Qt.CursorShape.PointingHandCursor)
            self.celebrate_button.clicked.connect(lambda: self.celebrate_clicked.emit(self.goal_data))
            
            # Adicionar ao layout
            actions_widget = self.findChild(QWidget)
            if actions_widget:
                actions_layout = actions_widget.layout()
                if actions_layout:
                    actions_layout.insertWidget(0, self.celebrate_button)

class GoalProgressBar(QWidget):
    """Barra de progresso visual para metas"""
    
    def __init__(self, progress: int = 0, parent=None):
        super().__init__(parent)
        self.progress = max(0, min(100, progress))
        self.setFixedHeight(30)
        
    def paintEvent(self, event):
        """Desenhar barra de progresso personalizada"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Fundo da barra
        painter.setBrush(QBrush(QColor(60, 60, 60)))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(0, 0, self.width(), self.height(), 6, 6)
        
        # Preenchimento com gradiente
        fill_width = int(self.width() * self.progress / 100)
        if fill_width > 0:
            gradient = QLinearGradient(0, 0, fill_width, 0)
            
            # Gradiente colorido baseado no progresso
            if self.progress < 30:
                gradient.setColorAt(0, QColor(128, 0, 0))    # Vermelho escuro
                gradient.setColorAt(1, QColor(178, 34, 34))  # Vermelho fogo
            elif self.progress < 70:
                gradient.setColorAt(0, QColor(184, 134, 11)) # Ouro escuro
                gradient.setColorAt(1, QColor(218, 165, 32)) # Ouro
            else:
                gradient.setColorAt(0, QColor(85, 107, 47))  # Verde oliva
                gradient.setColorAt(1, QColor(107, 142, 35)) # Verde oliva claro
                
            painter.setBrush(QBrush(gradient))
            painter.drawRoundedRect(0, 0, fill_width, self.height(), 6, 6)
            
        # Texto de porcentagem
        painter.setPen(QColor(245, 245, 220))  # Bege claro
        painter.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        text = f"{self.progress}%"
        text_width = painter.fontMetrics().horizontalAdvance(text)
        painter.drawText((self.width() - text_width) // 2, 
                        self.height() // 2 + 5, text)
        
    def set_progress(self, progress: int):
        """Atualizar progresso e redesenhar"""
        self.progress = max(0, min(100, progress))
        self.update()