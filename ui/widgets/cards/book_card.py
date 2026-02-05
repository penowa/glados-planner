# ui/widgets/cards/book_card.py
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                            QPushButton, QSizePolicy)
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QPixmap, QPainter, QColor, QLinearGradient, QFont, QBrush, QPen
import hashlib

from .base_card import PhilosophyCard

class BookCard(PhilosophyCard):
    """Card para exibir informações de um livro com progresso circular"""
    
    # Sinais
    read_clicked = pyqtSignal(dict)  # Emite dados do livro quando clicado em "Ler"
    notes_clicked = pyqtSignal(dict)  # Para acessar notas do livro
    options_clicked = pyqtSignal(dict) # Para menu de opções
    
    def __init__(self, book_data: dict, parent=None):
        super().__init__(parent)
        self.book_data = book_data
        self.cover_color = self.generate_cover_color(book_data.get('title', ''))
        self.setup_ui()
        self.setup_connections()
        
    def setup_ui(self):
        """Configurar interface do card de livro"""
        # Definir tamanho fixo para consistência
        self.setFixedSize(280, 360)
        
        # Título do livro
        title = self.book_data.get('title', 'Livro sem título')
        self.title_label.setText(self.truncate_text(title, 30))
        self.title_label.setWordWrap(True)
        
        # Área de conteúdo específica do livro
        self.setup_book_content()
        
        # Rodapé com botões de ação
        self.setup_book_footer()
        
    def setup_book_content(self):
        """Configurar conteúdo específico do livro"""
        # Layout horizontal para capa e informações
        content_layout = QHBoxLayout()
        
        # Capa do livro (gerada proceduralmente)
        self.cover_widget = BookCoverWidget(
            title=self.book_data.get('title', ''),
            author=self.book_data.get('author', ''),
            color=self.cover_color,
            progress=self.book_data.get('progress', 0)
        )
        content_layout.addWidget(self.cover_widget)
        
        # Informações do livro
        info_widget = self.create_book_info_widget()
        content_layout.addWidget(info_widget)
        
        self.content_layout.addLayout(content_layout)
        
    def create_book_info_widget(self):
        """Criar widget com informações do livro"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(6)
        
        # Autor
        author = self.book_data.get('author', 'Autor desconhecido')
        author_label = QLabel(f"<b>Autor:</b><br>{self.truncate_text(author, 25)}")
        author_label.setObjectName("book_card_author")
        author_label.setWordWrap(True)
        layout.addWidget(author_label)
        
        # Páginas
        current_page = self.book_data.get('current_page', 0)
        total_pages = self.book_data.get('total_pages', 0)
        pages_text = f"<b>Páginas:</b><br>{current_page}/{total_pages}"
        pages_label = QLabel(pages_text)
        pages_label.setObjectName("book_card_pages")
        layout.addWidget(pages_label)
        
        # Status
        status = self.book_data.get('status', 'não iniciado')
        status_label = QLabel(f"<b>Status:</b><br>{status}")
        status_label.setObjectName("book_card_status")
        layout.addWidget(status_label)
        
        # Data de último acesso
        last_read = self.book_data.get('last_read', 'Nunca')
        last_read_label = QLabel(f"<b>Última leitura:</b><br>{last_read}")
        last_read_label.setObjectName("book_card_last_read")
        layout.addWidget(last_read_label)
        
        layout.addStretch()
        return widget
        
    def setup_book_footer(self):
        """Configurar rodapé com botões de ação"""
        # Botão de ler/continuar
        self.read_button = QPushButton("▶ Continuar")
        self.read_button.setObjectName("primary_button")
        self.read_button.setCursor(Qt.CursorShape.PointingHandCursor)
        
        # Botão de notas
        self.notes_button = QPushButton("📝 Notas")
        self.notes_button.setObjectName("secondary_button")
        self.notes_button.setCursor(Qt.CursorShape.PointingHandCursor)
        
        # Botão de opções
        self.options_button = QPushButton("⋯")
        self.options_button.setObjectName("icon_button")
        self.options_button.setFixedSize(30, 30)
        self.options_button.setCursor(Qt.CursorShape.PointingHandCursor)
        
        # Adicionar ao layout
        self.footer_layout.addWidget(self.read_button)
        self.footer_layout.addWidget(self.notes_button)
        self.footer_layout.addWidget(self.options_button)
        
    def setup_connections(self):
        """Conectar sinais dos botões"""
        self.read_button.clicked.connect(lambda: self.read_clicked.emit(self.book_data))
        self.notes_button.clicked.connect(lambda: self.notes_clicked.emit(self.book_data))
        self.options_button.clicked.connect(lambda: self.options_clicked.emit(self.book_data))
        
    def generate_cover_color(self, title: str) -> str:
        """Gerar cor única baseada no título do livro"""
        if not title:
            return "#8B7355"  # Cor padrão sépia
            
        # Gerar hash do título
        hash_val = hashlib.md5(title.encode()).hexdigest()
        
        # Converter para valores HSL
        hue = int(hash_val[:8], 16) % 360
        saturation = 40 + int(hash_val[8:12], 16) % 30  # 40-70%
        lightness = 30 + int(hash_val[12:16], 16) % 30  # 30-60%
        
        return f"hsl({hue}, {saturation}%, {lightness}%)"
        
    def truncate_text(self, text: str, max_length: int) -> str:
        """Truncar texto se for muito longo"""
        if len(text) > max_length:
            return text[:max_length-3] + "..."
        return text
        
    def update_book_data(self, new_data: dict):
        """Atualizar dados do livro no card"""
        self.book_data.update(new_data)
        self.cover_widget.set_progress(self.book_data.get('progress', 0))
        # TODO: Atualizar outros elementos visuais

class BookCoverWidget(QWidget):
    """Widget para gerar capas de livros proceduralmente"""
    
    def __init__(self, title: str, author: str, color: str, progress: int = 0):
        super().__init__()
        self.title = title
        self.author = author
        self.color = color
        self.progress = progress
        self.setFixedSize(120, 160)
        
    def paintEvent(self, event):
        """Pintar capa do livro proceduralmente"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Fundo da capa
        self.draw_book_cover(painter)
        
        # Anel de progresso
        self.draw_progress_ring(painter)
        
        # Texto do título e autor
        self.draw_text(painter)
        
    def draw_book_cover(self, painter):
        """Desenhar capa do livro com efeitos"""
        # Gradiente de fundo
        gradient = QLinearGradient(0, 0, self.width(), self.height())
        color = QColor(self.color)
        gradient.setColorAt(0, color.lighter(120))
        gradient.setColorAt(1, color.darker(120))
        
        painter.setBrush(QBrush(gradient))
        painter.setPen(QPen(QColor(60, 60, 60), 2))
        painter.drawRoundedRect(5, 5, self.width()-10, self.height()-10, 8, 8)
        
        # Efeito de lombada
        painter.setBrush(QBrush(color.darker(150)))
        painter.drawRect(self.width()-15, 10, 5, self.height()-20)
        
        # Detalhes decorativos
        painter.setPen(QPen(QColor(255, 255, 255, 30), 1))
        for i in range(5, self.height()-10, 15):
            painter.drawLine(10, i, self.width()-20, i)
            
    def draw_progress_ring(self, painter):
        """Desenhar anel de progresso na capa"""
        center_x = self.width() // 2
        center_y = self.height() // 2
        radius = 20
        
        # Anel de fundo
        painter.setPen(QPen(QColor(100, 100, 100), 3))
        painter.drawEllipse(center_x - radius, center_y - radius, 
                           radius * 2, radius * 2)
        
        # Arco de progresso
        if self.progress > 0:
            angle = int(self.progress * 360 / 100 * 16)
            pen = QPen(QColor(85, 107, 47), 4)  # Verde oliva
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            painter.setPen(pen)
            painter.drawArc(center_x - radius, center_y - radius,
                          radius * 2, radius * 2,
                          90 * 16, -angle)
        
    def draw_text(self, painter):
        """Desenhar texto na capa"""
        # Título
        painter.setPen(QColor(245, 245, 220))  # Bege claro
        font = QFont("Georgia", 8, QFont.Weight.Bold)
        painter.setFont(font)
        
        # Quebrar título em múltiplas linhas
        words = self.title.split()
        lines = []
        current_line = []
        
        for word in words:
            current_line.append(word)
            test_line = ' '.join(current_line)
            
            # Verificar se linha cabe
            if painter.fontMetrics().horizontalAdvance(test_line) > self.width() - 20:
                lines.append(' '.join(current_line[:-1]))
                current_line = [word]
                
        if current_line:
            lines.append(' '.join(current_line))
            
        # Desenhar linhas
        y_pos = 30
        for i, line in enumerate(lines[:3]):  # Máximo 3 linhas
            painter.drawText(10, y_pos, self.width() - 20, 20,
                           Qt.AlignmentFlag.AlignCenter, line)
            y_pos += 15
            
    def set_progress(self, progress: int):
        """Atualizar progresso do livro"""
        self.progress = max(0, min(100, progress))
        self.update()