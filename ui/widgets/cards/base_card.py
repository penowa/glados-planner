# ui/widgets/cards/base_card.py
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QPushButton
from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve, pyqtProperty, pyqtSignal, QRect
from PyQt6.QtGui import QPainter, QBrush, QColor, QLinearGradient, QPen, QFont

class PhilosophyCard(QFrame):
    """Classe base para todos os cards com animações e efeitos"""
    
    clicked = pyqtSignal()  # Sinal emitido quando o card é clicado
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Inicializar atributos antes de chamar setup_base_ui
        self._elevation = 2.0  # Mudar para float
        self._scale = 1.0
        
        # Inicializar animações como None
        self.hover_animation = None
        self.click_animation = None
        
        self.setup_base_ui()
        self.setup_animations()
        
    def setup_base_ui(self):
        """Configura UI base do card"""
        # Layout principal
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(16, 16, 16, 16)
        self.main_layout.setSpacing(8)
        
        # Título do card
        self.title_label = QLabel()
        self.title_label.setObjectName("card_title")
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.main_layout.addWidget(self.title_label)
        
        # Linha divisória
        self.divider = QFrame()
        self.divider.setFrameShape(QFrame.Shape.HLine)
        self.divider.setFrameShadow(QFrame.Shadow.Sunken)
        self.divider.setObjectName("card_divider")
        self.main_layout.addWidget(self.divider)
        
        # Área de conteúdo (será preenchida pelas subclasses)
        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(0, 8, 0, 8)
        self.main_layout.addWidget(self.content_widget)
        
        # Rodapé do card
        self.footer_widget = QWidget()
        self.footer_layout = QHBoxLayout(self.footer_widget)
        self.footer_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.addWidget(self.footer_widget)
        
        # Estilo base
        self.setObjectName("philosophy_card")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        
    def setup_animations(self):
        """Configura animações do card"""
        # Animação de hover
        self.hover_animation = QPropertyAnimation(self, b"elevation")
        self.hover_animation.setDuration(200)
        self.hover_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        
        # Animação de clique
        self.click_animation = QPropertyAnimation(self, b"scale")
        self.click_animation.setDuration(100)
        self.click_animation.setEasingCurve(QEasingCurve.Type.OutQuad)
        
        # Configurar valores iniciais
        self.set_elevation(self._elevation)
        self.set_scale(self._scale)
    
    def setup_connections(self):
        """Configura conexões de eventos"""
        pass
    
    def get_elevation(self):
        """Getter para propriedade de elevação"""
        return self._elevation
        
    def set_elevation(self, value):
        """Setter para propriedade de elevação"""
        self._elevation = float(value)  # Garantir que é float
        self.update()
        
    def get_scale(self):
        """Getter para propriedade de escala"""
        return self._scale
        
    def set_scale(self, value):
        """Setter para propriedade de escala"""
        self._scale = float(value)
        self.update()
        
    elevation = pyqtProperty(float, get_elevation, set_elevation)
    scale = pyqtProperty(float, get_scale, set_scale)
    
    def enterEvent(self, event):
        """Quando mouse entra no card"""
        if self.isEnabled() and self.hover_animation:
            self.hover_animation.stop()
            self.hover_animation.setStartValue(self.elevation)
            self.hover_animation.setEndValue(8.0)  # Mudar para float
            self.hover_animation.start()
        super().enterEvent(event)
        
    def leaveEvent(self, event):
        """Quando mouse sai do card"""
        if self.isEnabled() and self.hover_animation:
            self.hover_animation.stop()
            self.hover_animation.setStartValue(self.elevation)
            self.hover_animation.setEndValue(2.0)  # Mudar para float
            self.hover_animation.start()
        super().leaveEvent(event)
        
    def mousePressEvent(self, event):
        """Quando card é pressionado"""
        if event.button() == Qt.MouseButton.LeftButton and self.isEnabled() and self.click_animation:
            self.click_animation.stop()
            self.click_animation.setStartValue(1.0)
            self.click_animation.setEndValue(0.95)
            self.click_animation.start()
        super().mousePressEvent(event)
        
    def mouseReleaseEvent(self, event):
        """Quando card é liberado"""
        if event.button() == Qt.MouseButton.LeftButton and self.isEnabled() and self.click_animation:
            self.click_animation.stop()
            self.click_animation.setStartValue(self.scale)
            self.click_animation.setEndValue(1.0)
            self.click_animation.start()
            self.clicked.emit()
        super().mouseReleaseEvent(event)
        
    def paintEvent(self, event):
        """Pinta o card com sombras e efeitos"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        try:
            # Configurar cores baseadas no tema
            bg_color = QColor(30, 41, 59)  # Azul escuro para o tema dark
            
            # Desenhar fundo com bordas arredondadas
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(bg_color))
            painter.drawRoundedRect(self.rect(), 12, 12)
            
            # Adicionar sombra baseada na elevação (mais sutil)
            if self._elevation > 2.0:
                shadow_color = QColor(0, 0, 0, 15)
                # Converter elevação para inteiro para evitar erro no translated
                elevation_int = int(self._elevation)
                shadow_rect = QRect(
                    self.rect().x(), 
                    self.rect().y() + elevation_int,
                    self.rect().width(),
                    self.rect().height()
                )
                painter.setBrush(QBrush(shadow_color))
                painter.drawRoundedRect(shadow_rect, 12, 12)
                
            # Borda sutil
            border_color = QColor(71, 85, 105, 100)
            painter.setPen(QPen(border_color, 1))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRoundedRect(self.rect().adjusted(0, 0, -1, -1), 12, 12)
        finally:
            # Garantir que o painter seja finalizado mesmo em caso de erro
            painter.end()
        
    def set_title(self, title):
        """Define o título do card"""
        self.title_label.setText(title)
        
    def set_content(self, widget):
        """Define o conteúdo do card"""
        # Remover conteúdo anterior
        while self.content_layout.count():
            child = self.content_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        # Adicionar novo conteúdo
        self.content_layout.addWidget(widget)
        
    def set_minimizable(self, minimizable):
        """Habilita/desabilita minimização do card"""
        # Implementação opcional para cards que podem ser minimizados
        pass
        
    def set_draggable(self, draggable):
        """Habilita/desabilita arrastar do card"""
        # Implementação opcional para cards que podem ser arrastados
        pass
    
    def cleanup(self):
        """Limpa recursos e animações"""
        if self.hover_animation:
            self.hover_animation.stop()
        if self.click_animation:
            self.click_animation.stop()