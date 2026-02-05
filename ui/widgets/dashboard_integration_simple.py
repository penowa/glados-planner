# ui/widgets/dashboard_integration_simple.py
"""
Integração simples dos cards na dashboard existente
"""
from PyQt6.QtWidgets import QVBoxLayout, QHBoxLayout
from PyQt6.QtCore import pyqtSignal

from .cards.add_book_card import AddBookCard
from .cards.agenda_card import AgendaCard
from .cards.glados_card import GladosCard
from .cards.next_reading_session_card import NextReadingSessionCard

class DashboardSimpleIntegration:
    """Integração direta dos cards na dashboard existente"""
    
    def __init__(self, dashboard_view, controllers=None):
        self.dashboard = dashboard_view
        self.controllers = controllers
        
    def integrate_cards(self):
        """Substitui os widgets existentes pelos cards"""
        
        # 1. Substituir seção de livro atual por NextReadingSessionCard
        self.replace_book_section()
        
        # 2. Substituir seção de estatísticas por AddBookCard
        self.replace_stats_section()
        
        # 3. Manter AgendaCard e GladosCard nas posições existentes
        self.integrate_agenda_card()
        self.integrate_glados_card()
        
        # Conectar sinais
        self.setup_connections()
        
    def replace_book_section(self):
        """Substituir widget de livro atual por NextReadingSessionCard"""
        # Remover conteúdo da seção de livro
        while self.dashboard.book_layout.count():
            child = self.dashboard.book_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        
        # Criar e adicionar card de próxima sessão
        self.next_reading_card = NextReadingSessionCard()
        self.dashboard.book_layout.addWidget(self.next_reading_card)
        
        # Atualizar botões da seção
        self.dashboard.read_button.setText("▶ Iniciar Sessão")
        self.dashboard.read_button.clicked.disconnect()
        self.dashboard.read_button.clicked.connect(
            lambda: self.next_reading_card._toggle_session()
        )
        
    def replace_stats_section(self):
        """Substituir seção de estatísticas por AddBookCard"""
        # Encontrar e limpar container de estatísticas
        stats_container = self.dashboard.stats_section.findChild(QWidget, "minimal_stats_section")
        if stats_container:
            layout = stats_container.layout()
            if layout:
                while layout.count():
                    child = layout.takeAt(0)
                    if child.widget():
                        child.widget().deleteLater()
                
                # Adicionar AddBookCard
                self.add_book_card = AddBookCard()
                layout.addWidget(self.add_book_card)
    
    def integrate_agenda_card(self):
        """Substituir agenda existente por AgendaCard"""
        # Limpar layout da agenda
        while self.dashboard.agenda_layout.count():
            child = self.dashboard.agenda_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        
        # Criar e adicionar AgendaCard
        self.agenda_card = AgendaCard(
            agenda_controller=self.controllers.get('agenda') if self.controllers else None
        )
        self.dashboard.agenda_layout.addWidget(self.agenda_card)
    
    def integrate_glados_card(self):
        """Substituir seção GLaDOS existente por GladosCard"""
        # Limpar layout do GLaDOS
        while self.dashboard.message_layout.count():
            child = self.dashboard.message_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        
        # Criar e adicionar GladosCard
        self.glados_card = GladosCard(
            controller=self.controllers.get('glados') if self.controllers else None
        )
        self.dashboard.message_layout.addWidget(self.glados_card)
        
        # Remover campo de entrada antigo
        if hasattr(self.dashboard, 'glados_input'):
            self.dashboard.glados_input.setVisible(False)
        if hasattr(self.dashboard, 'ask_button'):
            self.dashboard.ask_button.setVisible(False)
    
    def setup_connections(self):
        """Configurar conexões entre os cards e dashboard"""
        # Conectar navegação da agenda
        if hasattr(self.agenda_card, 'navigate_to_agenda'):
            self.agenda_card.navigate_to_agenda.connect(
                lambda: self.dashboard.navigate_to.emit('agenda')
            )
        
        # Conectar adição de livro
        if hasattr(self.add_book_card, 'file_selected'):
            self.add_book_card.file_selected.connect(
                self.handle_book_file_selected
            )
        
        # Conectar sessões de leitura
        if hasattr(self.next_reading_card, 'start_session'):
            self.next_reading_card.start_session.connect(
                self.handle_start_session
            )
    
    def handle_book_file_selected(self, file_path):
        """Processar arquivo de livro selecionado"""
        if self.controllers and 'book' in self.controllers:
            try:
                self.controllers['book'].process_file(file_path)
            except Exception as e:
                print(f"Erro ao processar livro: {e}")
    
    def handle_start_session(self, session_data):
        """Iniciar sessão de leitura"""
        if self.controllers and 'reading' in self.controllers:
            try:
                self.controllers['reading'].start_session(session_data)
            except Exception as e:
                print(f"Erro ao iniciar sessão: {e}")