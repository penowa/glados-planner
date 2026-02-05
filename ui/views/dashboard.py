"""
View principal do dashboard com design minimalista e limpo
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QFrame, QScrollArea
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QDateTime, pyqtSlot
from PyQt6.QtGui import QFont
import logging

from ui.widgets.cards.add_book_card import AddBookCard
from ui.widgets.cards.agenda_card import AgendaCard
from ui.widgets.cards.glados_card import GladosCard

logger = logging.getLogger('GLaDOS.UI.Dashboard')

class DashboardView(QWidget):
    """View principal do dashboard com design minimalista"""
    
    # Sinais
    refresh_requested = pyqtSignal()
    navigate_to = pyqtSignal(str)  # Novo sinal para navegação
    
    def __init__(self, controllers=None):
        super().__init__()
        
        # Armazenar controllers
        self.controllers = controllers
        self.book_controller = controllers.get('book') if controllers else None
        self.agenda_controller = controllers.get('agenda') if controllers else None
        self.reading_controller = controllers.get('reading') if controllers else None
        self.glados_controller = controllers.get('glados') if controllers else None
        
        # Cards
        self.add_book_card = None
        self.agenda_card = None
        self.glados_card = None
        
        # Dados em tempo real
        self.current_reading = None
        self.today_agenda = []
        self.daily_stats = {}
        
        self.setup_ui()
        self.setup_connections()
        self.setup_timers()
        
        logger.info("DashboardView inicializado com cards integrados")
    
    def handle_navigation(self, destination):
        """Método para tratamento de navegação interna"""
        pass
    
    def setup_ui(self):
        """Configura interface do dashboard com cards integrados"""
        self.setObjectName("dashboard_view")
        
        # Layout principal com scroll
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Scroll area para conteúdo principal
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        
        # Widget de conteúdo
        content_widget = QWidget()
        content_widget.setObjectName("content_widget")
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(16)
        
        # Cabeçalho minimalista
        header = self.create_minimal_header()
        content_layout.addWidget(header)
        
        # Linha 1: AgendaCard ocupa toda a largura
        self.agenda_card = AgendaCard(
            agenda_controller=self.agenda_controller
        )
        self.agenda_card.setObjectName("dashboard_card")
        self.agenda_card.setMinimumHeight(280)  # Altura mínima para melhor visualização
        content_layout.addWidget(self.agenda_card)
        
        # Linha 2: AddBookCard + GladosCard (50/50)
        row2_layout = QHBoxLayout()
        row2_layout.setSpacing(12)
        
        # Criar e configurar AddBookCard
        self.add_book_card = AddBookCard()
        self.add_book_card.setObjectName("dashboard_card")
        
        # Criar e configurar GladosCard
        self.glados_card = GladosCard(
            controller=self.glados_controller
        )
        self.glados_card.setObjectName("dashboard_card")
        
        # Proporções 50/50
        row2_layout.addWidget(self.add_book_card, 50)
        row2_layout.addWidget(self.glados_card, 50)
        content_layout.addLayout(row2_layout)
        
        # Adicionar stretcher no final
        content_layout.addStretch()
        
        scroll_area.setWidget(content_widget)
        main_layout.addWidget(scroll_area)
        
        # Inicializar com dados
        QTimer.singleShot(100, self.load_initial_data)
    
    def create_minimal_header(self):
        """Cria cabeçalho minimalista"""
        header = QWidget()
        header.setObjectName("minimal_header")
        header.setFixedHeight(60)
        
        layout = QHBoxLayout(header)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        
        # Boas-vindas limpa
        self.greeting_label = QLabel(self.get_time_greeting())
        self.greeting_label.setObjectName("minimal_greeting")
        self.greeting_label.setFont(QFont("FiraCode Nerd Font Propo", 18, QFont.Weight.Medium))
        
        # Data atual sutil
        self.date_label = QLabel(QDateTime.currentDateTime().toString("dddd, dd 'de' MMMM"))
        self.date_label.setObjectName("minimal_date")
        self.date_label.setFont(QFont("FiraCode Nerd Font Propo", 10))
        self.date_label.setStyleSheet("color: #8A94A6;")
        
        # Botão de refresh
        refresh_button = QPushButton("🔄")
        refresh_button.setObjectName("minimal_refresh_button")
        refresh_button.setFixedSize(32, 32)
        refresh_button.setToolTip("Atualizar dashboard")
        refresh_button.clicked.connect(self.refresh_data)
        
        layout.addWidget(self.greeting_label)
        layout.addStretch()
        layout.addWidget(self.date_label)
        layout.addWidget(refresh_button)
        
        # Separador sutil
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        separator.setStyleSheet("background-color: #252A32;")
        separator.setFixedHeight(1)
        
        container = QVBoxLayout()
        container.addWidget(header)
        container.addWidget(separator)
        
        final_widget = QWidget()
        final_widget.setLayout(container)
        return final_widget
    
    def get_time_greeting(self):
        """Retorna saudação baseada na hora"""
        hour = QDateTime.currentDateTime().time().hour()
        if hour < 12:
            return "🌅 Bom dia Hélio"
        elif hour < 18:
            return "☀️ Boa tarde Hélio"
        else:
            return "🌙 Boa noite Hélio"
    
    def setup_connections(self):
        """Configura conexões com controllers e cards"""
        # Conectar sinais dos cards
        if self.add_book_card:
            self.add_book_card.file_selected.connect(self.handle_book_file_selected)
            self.add_book_card.processing_completed.connect(self.handle_book_processed)
        
        if self.agenda_card:
            self.agenda_card.navigate_to_agenda.connect(
                lambda: self.navigate_to.emit('agenda')
            )
            self.agenda_card.item_clicked.connect(self.handle_agenda_item_clicked)
            self.agenda_card.quick_action.connect(self.handle_agenda_quick_action)
            
            # Conectar sinais de sessão de leitura (agora na agenda)
            if hasattr(self.agenda_card, 'start_reading_session'):
                self.agenda_card.start_reading_session.connect(self.handle_start_session)
            if hasattr(self.agenda_card, 'edit_reading_session'):
                self.agenda_card.edit_reading_session.connect(self.handle_edit_session)
            if hasattr(self.agenda_card, 'skip_reading_session'):
                self.agenda_card.skip_reading_session.connect(self.handle_skip_session)
        
        if self.glados_card:
            self.glados_card.ui_message_sent.connect(self.handle_glados_message)
            self.glados_card.ui_action_selected.connect(self.handle_glados_action)
        
        # Conexões com controllers (se necessário)
        if self.book_controller and hasattr(self.book_controller, 'current_book_updated'):
            self.book_controller.current_book_updated.connect(self.update_current_book)
        
        if self.agenda_controller and hasattr(self.agenda_controller, 'agenda_updated'):
            self.agenda_controller.agenda_updated.connect(self.update_agenda_data)
        
        if self.reading_controller and hasattr(self.reading_controller, 'stats_updated'):
            self.reading_controller.stats_updated.connect(self.update_stats_data)
    
    def setup_timers(self):
        """Configura timers para atualizações"""
        # Timer para atualizar saudação
        self.greeting_timer = QTimer()
        self.greeting_timer.timeout.connect(self.update_greeting)
        self.greeting_timer.start(60000)  # 1 minuto
        
        # Timer para atualizar dados
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.refresh_data)
        self.update_timer.start(300000)  # 5 minutos
    
    def load_initial_data(self):
        """Carrega dados iniciais dos controllers"""
        logger.info("Carregando dados iniciais do dashboard")
        
        # Carregar dados para AgendaCard (que agora inclui sessões de leitura)
        if self.agenda_controller and hasattr(self.agenda_controller, 'get_today_agenda'):
            try:
                agenda_data = self.agenda_controller.get_today_agenda()
                if self.agenda_card and hasattr(self.agenda_card, 'on_agenda_loaded'):
                    self.agenda_card.on_agenda_loaded(agenda_data)
            except Exception as e:
                logger.error(f"Erro ao carregar agenda: {e}")
        
        # Carregar estatísticas para referência
        if self.reading_controller and hasattr(self.reading_controller, 'get_daily_stats'):
            try:
                self.daily_stats = self.reading_controller.get_daily_stats()
            except Exception as e:
                logger.error(f"Erro ao carregar estatísticas: {e}")
    
    # ============ HANDLERS ============
    
    def handle_book_file_selected(self, file_path):
        """Processar arquivo de livro selecionado"""
        if self.book_controller:
            try:
                logger.info(f"Processando arquivo de livro: {file_path}")
                self.book_controller.process_file(file_path)
            except Exception as e:
                logger.error(f"Erro ao processar livro: {e}")
    
    def handle_book_processed(self, result):
        """Manipular livro processado com sucesso"""
        if result.get('status') == 'completed':
            logger.info(f"Livro processado: {result.get('file_path')}")
            # Atualizar dados se necessário
            self.refresh_data()
    
    def handle_agenda_item_clicked(self, item_data):
        """Manipular clique em item da agenda"""
        logger.info(f"Item da agenda clicado: {item_data.get('title', 'Sem título')}")
        # Aqui pode abrir um diálogo de edição, etc.
    
    def handle_agenda_quick_action(self, action_name, data):
        """Manipular ação rápida da agenda"""
        logger.info(f"Ação rápida da agenda: {action_name}")
        if action_name == "add_event":
            self.navigate_to.emit('agenda')
        elif action_name == "add_reading_session":
            # Se a agenda tem uma ação para adicionar sessão de leitura
            self.navigate_to.emit('reading_scheduler')
    
    def handle_start_session(self, session_data):
        """Iniciar sessão de leitura (agora vindo da agenda)"""
        if self.reading_controller:
            try:
                self.reading_controller.start_session(session_data)
                logger.info("Sessão de leitura iniciada")
                # Atualizar a agenda após iniciar sessão
                self.refresh_data()
            except Exception as e:
                logger.error(f"Erro ao iniciar sessão: {e}")
    
    def handle_edit_session(self, session_data):
        """Editar sessão de leitura (agora vindo da agenda)"""
        logger.info(f"Editando sessão: {session_data.get('id', 'N/A')}")
        # Aqui pode abrir um diálogo de edição
        self.navigate_to.emit('reading_scheduler')
    
    def handle_skip_session(self, session_data):
        """Pular sessão de leitura (agora vindo da agenda)"""
        logger.info(f"Pulando sessão: {session_data.get('id', 'N/A')}")
        if self.reading_controller and hasattr(self.reading_controller, 'skip_session'):
            try:
                self.reading_controller.skip_session(session_data.get('id'))
                logger.info("Sessão pulada")
                # Atualizar dados
                self.refresh_data()
            except Exception as e:
                logger.error(f"Erro ao pular sessão: {e}")
        else:
            # Atualizar dados da próxima sessão
            self.refresh_data()
    
    def handle_glados_message(self, message):
        """Manipular mensagem enviada ao GLaDOS"""
        logger.info(f"Mensagem GLaDOS: {message[:50]}...")
        # O próprio GladosCard já lida com a mensagem através do controller
    
    def handle_glados_action(self, action_id):
        """Manipular ação rápida do GLaDOS"""
        logger.info(f"Ação GLaDOS: {action_id}")
        # O próprio GladosCard já lida com a ação
    
    # ============ SLOTS ============
    
    @pyqtSlot()
    def update_greeting(self):
        """Atualizar saudação baseada na hora"""
        self.greeting_label.setText(self.get_time_greeting())
        self.date_label.setText(QDateTime.currentDateTime().toString("dddd, dd 'de' MMMM"))
    
    @pyqtSlot()
    def refresh_data(self):
        """Atualizar dados do dashboard"""
        self.refresh_requested.emit()
        self.load_initial_data()
        logger.debug("Dados do dashboard atualizados")
    
    @pyqtSlot(dict)
    def update_current_book(self, book_data):
        """Atualizar livro atual quando controller emite sinal"""
        self.current_reading = book_data
        # Notificar agenda sobre mudança no livro atual
        if self.agenda_card and hasattr(self.agenda_card, 'set_current_book'):
            self.agenda_card.set_current_book(book_data)
    
    @pyqtSlot(list)
    def update_agenda_data(self, agenda_data):
        """Atualizar agenda quando controller emite sinal"""
        self.today_agenda = agenda_data
        if self.agenda_card and hasattr(self.agenda_card, 'on_agenda_loaded'):
            self.agenda_card.on_agenda_loaded(agenda_data)
    
    @pyqtSlot(dict)
    def update_stats_data(self, stats_data):
        """Atualizar estatísticas quando controller emite sinal"""
        self.daily_stats = stats_data
    
    def on_view_activated(self):
        """Chamado quando a view é ativada"""
        self.load_initial_data()
    
    def cleanup(self):
        """Limpeza antes de fechar"""
        if hasattr(self, 'greeting_timer'):
            self.greeting_timer.stop()
        if hasattr(self, 'update_timer'):
            self.update_timer.stop()
        
        # Limpar recursos dos cards
        if self.add_book_card and hasattr(self.add_book_card, 'cleanup'):
            self.add_book_card.cleanup()
        if self.agenda_card and hasattr(self.agenda_card, 'cleanup'):
            self.agenda_card.cleanup()
        if self.glados_card and hasattr(self.glados_card, 'closeEvent'):
            self.glados_card.closeEvent(None)