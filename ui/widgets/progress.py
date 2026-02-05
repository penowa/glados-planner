"""
Widget de progresso circular
"""
from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt, QRect
from PyQt6.QtGui import QPainter, QPen, QBrush, QColor, QFont

class ProgressRing(QWidget):
    """Anel de progresso circular"""
    
    def __init__(self, value=0, size=100):
        super().__init__()
        self.value = max(0, min(100, value))
        self.size = size
        self.setFixedSize(size, size)
        
        # Cores padrão
        self.bg_color = QColor(50, 50, 50)
        self.progress_color = QColor(85, 107, 47)  # Verde oliva
        self.text_color = QColor(245, 245, 220)    # Bege claro
    
    def set_value(self, value):
        """Define valor do progresso (0-100)"""
        self.value = max(0, min(100, value))
        self.update()
    
    def set_colors(self, bg_color=None, progress_color=None, text_color=None):
        """Define cores personalizadas"""
        if bg_color:
            self.bg_color = bg_color
        if progress_color:
            self.progress_color = progress_color
        if text_color:
            self.text_color = text_color
        self.update()
    
    def paintEvent(self, event):
        """Desenha o anel de progresso"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Calcular tamanhos
        center = self.rect().center()
        radius = min(self.width(), self.height()) // 2 - 5
        pen_width = 8
        
        # Fundo do anel
        painter.setPen(QPen(self.bg_color, pen_width))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(center, radius - pen_width // 2, radius - pen_width // 2)
        
        # Arco de progresso
        pen = QPen(self.progress_color, pen_width)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        
        # Calcular ângulo do arco
        span_angle = int(self.value * 360 / 100 * 16)  # 1/16 de grau
        
        # Desenhar arco (começa no topo, sentido horário)
        painter.drawArc(
            center.x() - radius + pen_width // 2,
            center.y() - radius + pen_width // 2,
            (radius - pen_width // 2) * 2,
            (radius - pen_width // 2) * 2,
            90 * 16,  # Começar no topo (90 graus * 16)
            -span_angle  # Negativo para sentido horário
        )
        
        # Texto central
        painter.setPen(self.text_color)
        painter.setFont(QFont("Arial", max(10, radius // 5), QFont.Weight.Bold))
        painter.drawText(
            self.rect(),
            Qt.AlignmentFlag.AlignCenter,
            f"{self.value}%"
        )