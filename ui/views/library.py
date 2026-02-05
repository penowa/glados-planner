"""
View da biblioteca de livros com navegação
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QFrame, QScrollArea
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
import logging

logger = logging.getLogger('GLaDOS.UI.LibraryView')

class LibraryView(QWidget):
    """View da biblioteca com navegação"""
    
    # Sinais
    navigate_to = pyqtSignal(str)
    
    def __init__(self, reading_controller=None):
        super().__init__()
        self.reading_controller = reading_controller
        self.setup_ui()
        
        logger.info("LibraryView inicializada")
    
    def setup_ui(self):
        """Configura interface da biblioteca com navegação"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 24, 24, 24)
        main_layout.setSpacing(24)
        
        # Cabeçalho com navegação
        header_layout = QHBoxLayout()
        
        # Botão voltar
        back_button = QPushButton("← Voltar")
        back_button.setObjectName("navigation_button")
        back_button.clicked.connect(lambda: self.navigate_to.emit('dashboard'))
        
        # Título
        title = QLabel("📚 Biblioteca Filosófica")
        title.setObjectName("view_title")
        title.setFont(QFont("FiraCode Nerd Font Propo", 18, QFont.Weight.Medium))
        
        header_layout.addWidget(back_button)
        header_layout.addStretch()
        header_layout.addWidget(title)
        header_layout.addStretch()
        
        main_layout.addLayout(header_layout)
        
        # Separador
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        separator.setStyleSheet("background-color: #252A32; height: 1px;")
        main_layout.addWidget(separator)
        
        # Scroll area para conteúdo
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(32)
        
        # Mensagem de placeholder
        message = QLabel(
            "🏛️ <b>Sua Biblioteca de Sabedoria</b><br><br>"
            "Aqui estão todos os livros filosóficos que você está explorando.<br><br>"
            "<b>Funcionalidades em desenvolvimento:</b><br>"
            "• Grid de livros com capas personalizadas<br>"
            "• Filtros por autor, disciplina e status<br>"
            "• Sistema de tags e categorias<br>"
            "• Progresso de leitura visual<br>"
            "• Recomendações baseadas em seus interesses"
        )
        message.setObjectName("placeholder_message")
        message.setAlignment(Qt.AlignmentFlag.AlignCenter)
        message.setWordWrap(True)
        message.setFont(QFont("FiraCode Nerd Font Propo", 10))
        
        content_layout.addWidget(message)
        
        # Grid de navegação rápida
        quick_nav_label = QLabel("🚀 Navegação Rápida")
        quick_nav_label.setObjectName("section_title")
        quick_nav_label.setFont(QFont("FiraCode Nerd Font Propo", 12, QFont.Weight.Medium))
        content_layout.addWidget(quick_nav_label)
        
        nav_grid = QGridLayout()
        nav_grid.setSpacing(16)
        
        # Botões de navegação
        nav_buttons = [
            ("📅 Agenda", "agenda", "📅"),
            ("🎯 Modo Foco", "focus", "🎯"),
            ("🧠 Conceitos", "concepts", "🧠"),
            ("📊 Dashboard", "dashboard", "📊"),
        ]
        
        for i, (text, target, icon) in enumerate(nav_buttons):
            btn = self.create_nav_button(text, target, icon)
            nav_grid.addWidget(btn, i // 2, i % 2)
        
        content_layout.addLayout(nav_grid)
        
        # Ações específicas da biblioteca
        actions_label = QLabel("📚 Ações da Biblioteca")
        actions_label.setObjectName("section_title")
        actions_label.setFont(QFont("FiraCode Nerd Font Propo", 12, QFont.Weight.Medium))
        content_layout.addWidget(actions_label)
        
        # Botões de ação
        actions_layout = QHBoxLayout()
        actions_layout.setSpacing(12)
        
        action_buttons = [
            ("➕ Adicionar Livro", self.on_add_book),
            ("🔍 Buscar Livros", self.on_search_books),
            ("📊 Ver Estatísticas", self.on_view_stats),
        ]
        
        for text, callback in action_buttons:
            btn = QPushButton(text)
            btn.setObjectName("primary_button")
            btn.clicked.connect(callback)
            btn.setFont(QFont("FiraCode Nerd Font Propo", 10))
            actions_layout.addWidget(btn)
        
        actions_layout.addStretch()
        content_layout.addLayout(actions_layout)
        
        # Exemplo de livros (placeholder)
        books_label = QLabel("📖 Seus Livros Recentes")
        books_label.setObjectName("section_title")
        books_label.setFont(QFont("FiraCode Nerd Font Propo", 12, QFont.Weight.Medium))
        content_layout.addWidget(books_label)
        
        books_grid = QGridLayout()
        books_grid.setSpacing(16)
        
        # Livros de exemplo
        example_books = [
            ("A República", "Platão", "📘"),
            ("Ética a Nicômaco", "Aristóteles", "📙"),
            ("Crítica da Razão Pura", "Kant", "📗"),
            ("Assim Falou Zaratustra", "Nietzsche", "📕"),
        ]
        
        for i, (title, author, icon) in enumerate(example_books):
            book_widget = self.create_book_card(title, author, icon)
            books_grid.addWidget(book_widget, i // 2, i % 2)
        
        content_layout.addLayout(books_grid)
        content_layout.addStretch()
        
        scroll_area.setWidget(content_widget)
        main_layout.addWidget(scroll_area)
    
    def create_nav_button(self, text, target, icon):
        """Cria botão de navegação"""
        btn = QPushButton(f"{icon} {text}")
        btn.setObjectName("nav_card_button")
        btn.clicked.connect(lambda: self.navigate_to.emit(target))
        btn.setFont(QFont("FiraCode Nerd Font Propo", 10))
        btn.setMinimumHeight(80)
        return btn
    
    def create_book_card(self, title, author, icon):
        """Cria card de livro de exemplo"""
        card = QFrame()
        card.setObjectName("book_card")
        
        layout = QVBoxLayout(card)
        layout.setSpacing(12)
        
        # Ícone
        icon_label = QLabel(icon)
        icon_label.setFont(QFont("Segoe UI Emoji", 32))
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Título
        title_label = QLabel(title)
        title_label.setFont(QFont("FiraCode Nerd Font Propo", 11, QFont.Weight.Medium))
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setWordWrap(True)
        
        # Autor
        author_label = QLabel(f"<i>{author}</i>")
        author_label.setFont(QFont("FiraCode Nerd Font Propo", 9))
        author_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        author_label.setStyleSheet("color: #8A94A6;")
        
        layout.addWidget(icon_label)
        layout.addWidget(title_label)
        layout.addWidget(author_label)
        
        return card
    
    def on_add_book(self):
        """Abre diálogo para adicionar livro"""
        if self.reading_controller and hasattr(self.reading_controller, 'show_add_book_dialog'):
            self.reading_controller.show_add_book_dialog()
        else:
            logger.warning("Controller não disponível para adicionar livro")
    
    def on_search_books(self):
        """Abre busca de livros"""
        logger.info("Abrindo busca de livros")
        # TODO: Implementar busca
    
    def on_view_stats(self):
        """Mostra estatísticas de leitura"""
        logger.info("Mostrando estatísticas")
        # TODO: Implementar estatísticas
    
    def on_view_activated(self):
        """Chamado quando a view é ativada"""
        logger.info("LibraryView ativada")
        if self.reading_controller and hasattr(self.reading_controller, 'load_books'):
            self.reading_controller.load_books()
    
    def cleanup(self):
        """Limpeza antes de fechar"""
        pass