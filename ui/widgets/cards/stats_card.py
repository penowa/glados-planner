# ui/widgets/cards/stats_card.py
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QGridLayout
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPainter, QColor, QLinearGradient, QFont, QPen, QBrush
import math

from .base_card import PhilosophyCard

class StatsCard(PhilosophyCard):
    """Card para exibir estatísticas visuais"""
    
    def __init__(self, title: str, stats_data: dict, chart_type: str = "bar", parent=None):
        super().__init__(parent)
        self.title = title
        self.stats_data = stats_data
        self.chart_type = chart_type
        self.setup_ui()
        
    def setup_ui(self):
        """Configurar interface do card de estatísticas"""
        self.setMinimumSize(300, 200)
        
        # Título
        self.title_label.setText(self.title)
        
        # Conteúdo baseado no tipo de gráfico
        if self.chart_type == "bar":
            self.setup_bar_chart()
        elif self.chart_type == "pie":
            self.setup_pie_chart()
        elif self.chart_type == "line":
            self.setup_line_chart()
        elif self.chart_type == "progress":
            self.setup_progress_chart()
            
    def setup_bar_chart(self):
        """Configurar gráfico de barras"""
        self.chart_widget = BarChartWidget(self.stats_data)
        self.content_layout.addWidget(self.chart_widget)
        
    def setup_pie_chart(self):
        """Configurar gráfico de pizza"""
        self.chart_widget = PieChartWidget(self.stats_data)
        self.content_layout.addWidget(self.chart_widget)
        
    def setup_line_chart(self):
        """Configurar gráfico de linhas"""
        self.chart_widget = LineChartWidget(self.stats_data)
        self.content_layout.addWidget(self.chart_widget)
        
    def setup_progress_chart(self):
        """Configurar múltiplas barras de progresso"""
        self.chart_widget = ProgressChartWidget(self.stats_data)
        self.content_layout.addWidget(self.chart_widget)
        
    def update_stats(self, new_data: dict):
        """Atualizar dados estatísticos"""
        self.stats_data.update(new_data)
        if hasattr(self, 'chart_widget'):
            self.chart_widget.update_data(self.stats_data)

class BarChartWidget(QWidget):
    """Widget de gráfico de barras simples"""
    
    def __init__(self, data: dict):
        super().__init__()
        self.data = data
        self.setMinimumHeight(120)
        
    def paintEvent(self, event):
        """Desenhar gráfico de barras"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        if not self.data:
            return
            
        # Configurar área de desenho
        margin = 20
        chart_width = self.width() - 2 * margin
        chart_height = self.height() - 40
        bar_width = chart_width / len(self.data)
        
        # Encontrar valor máximo para escala
        max_value = max(self.data.values()) if self.data.values() else 1
        
        # Desenhar eixo
        painter.setPen(QPen(QColor(150, 150, 150), 1))
        painter.drawLine(margin, self.height() - 20, 
                        self.width() - margin, self.height() - 20)
        
        # Desenhar barras
        for i, (label, value) in enumerate(self.data.items()):
            x = margin + i * bar_width + bar_width * 0.1
            bar_height = (value / max_value) * chart_height
            
            # Gradiente da barra
            gradient = QLinearGradient(x, self.height() - 20 - bar_height, 
                                      x + bar_width * 0.8, self.height() - 20)
            gradient.setColorAt(0, QColor(85, 107, 47))  # Verde oliva
            gradient.setColorAt(1, QColor(139, 115, 85))  # Sépia
            
            painter.setBrush(QBrush(gradient))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(x, self.height() - 20 - bar_height,
                                  bar_width * 0.8, bar_height, 3, 3)
            
            # Rótulo
            painter.setPen(QColor(200, 200, 200))
            painter.setFont(QFont("Arial", 8))
            text_width = painter.fontMetrics().horizontalAdvance(label)
            painter.drawText(x + bar_width * 0.4 - text_width // 2,
                           self.height() - 5, label)

class PieChartWidget(QWidget):
    """Widget de gráfico de pizza"""
    
    def __init__(self, data: dict):
        super().__init__()
        self.data = data
        self.setMinimumSize(150, 150)
        
    def paintEvent(self, event):
        """Desenhar gráfico de pizza"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        if not self.data:
            return
            
        # Cores para as fatias
        colors = [
            QColor(85, 107, 47),   # Verde oliva
            QColor(139, 115, 85),  # Sépia
            QColor(128, 0, 0),     # Vermelho escuro
            QColor(72, 61, 139),   # Azul escuro
            QColor(139, 69, 19),   # Marrom sela
        ]
        
        # Calcular total
        total = sum(self.data.values())
        if total == 0:
            return
            
        # Desenhar círculo
        center_x = self.width() // 2
        center_y = self.height() // 2
        radius = min(center_x, center_y) - 20
        
        start_angle = 0
        for i, (label, value) in enumerate(self.data.items()):
            # Calcular ângulo da fatia
            angle = int(value * 360 * 16 / total)
            
            # Desenhar fatia
            painter.setBrush(QBrush(colors[i % len(colors)]))
            painter.setPen(QPen(QColor(60, 60, 60), 1))
            painter.drawPie(center_x - radius, center_y - radius,
                          radius * 2, radius * 2,
                          start_angle, angle)
            
            start_angle += angle

class ProgressChartWidget(QWidget):
    """Widget com múltiplas barras de progresso"""
    
    def __init__(self, data: dict):
        super().__init__()
        self.data = data
        self.setup_ui()
        
    def setup_ui(self):
        """Configurar layout com barras de progresso"""
        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        
        for label, value in self.data.items():
            # Criar linha para cada item
            item_widget = QWidget()
            item_layout = QHBoxLayout(item_widget)
            item_layout.setContentsMargins(0, 0, 0, 0)
            
            # Rótulo
            label_widget = QLabel(label)
            label_widget.setFixedWidth(80)
            item_layout.addWidget(label_widget)
            
            # Barra de progresso
            progress_widget = ProgressBarWidget(value)
            item_layout.addWidget(progress_widget)
            
            # Valor
            value_widget = QLabel(f"{value}%")
            value_widget.setFixedWidth(40)
            item_layout.addWidget(value_widget)
            
            layout.addWidget(item_widget)
            
class ProgressBarWidget(QWidget):
    """Barra de progresso customizada"""
    
    def __init__(self, value: int, parent=None):
        super().__init__(parent)
        self.value = max(0, min(100, value))
        self.setFixedHeight(20)
        
    def paintEvent(self, event):
        """Desenhar barra de progresso"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Fundo da barra
        painter.setBrush(QBrush(QColor(60, 60, 60)))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(0, 0, self.width(), self.height(), 4, 4)
        
        # Preenchimento
        fill_width = int(self.width() * self.value / 100)
        if fill_width > 0:
            # Gradiente para preenchimento
            gradient = QLinearGradient(0, 0, fill_width, 0)
            gradient.setColorAt(0, QColor(85, 107, 47))  # Verde oliva
            gradient.setColorAt(1, QColor(139, 115, 85)) # Sépia
            
            painter.setBrush(QBrush(gradient))
            painter.drawRoundedRect(0, 0, fill_width, self.height(), 4, 4)