# ui/views/dashboard.py (versão atualizada)
"""
View principal do dashboard com design minimalista e limpo
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QFrame, QScrollArea, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QDateTime, pyqtSlot
from PyQt6.QtGui import QFont
import logging

from ui.widgets.cards.add_book_card import AddBookCard
from ui.widgets.cards.agenda_card import AgendaCard
from ui.widgets.cards.event_creation_card import EventCreationDialog
from ui.widgets.dialogs.weekly_event_editor_dialog import WeeklyEventEditorDialog

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
        self.agenda_backend = self._resolve_agenda_backend()
        
        # Cards
        self.add_book_card = None
        self.agenda_card = None
        self.event_creation_card = None
        self.event_creation_dialog = None
        self.weekly_event_editor_dialog = None
        
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

    def _resolve_agenda_backend(self):
        """Resolve backend de agenda (AgendaController ou AgendaManager)."""
        if self.agenda_controller:
            return self.agenda_controller

        if self.book_controller and hasattr(self.book_controller, "agenda_controller"):
            return self.book_controller.agenda_controller

        return None

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
        content_layout.setContentsMargins(20, 20, 20, 20)  # Margens para respiro
        content_layout.setSpacing(16)
        
        # Cabeçalho minimalista
        header = self.create_minimal_header()
        content_layout.addWidget(header)
        
        # ============ LINHA 1: Agenda + EventCreation + AddBook (40-30-30) ============
        row1_layout = QHBoxLayout()
        row1_layout.setSpacing(12)
        
        # 1. AgendaCard (40%)
        self.agenda_card = AgendaCard(
            agenda_controller=self.agenda_backend
        )
        self.agenda_card.setObjectName("dashboard_card")
        self.agenda_card.setMinimumHeight(400)  # Altura ajustada
        self.agenda_card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        row1_layout.addWidget(self.agenda_card, 80)  # 40% da largura
        
        # 2. EventCreationCard (30%)
        #if self.agenda_controller and self.reading_controller:
        #    self.event_creation_card = EventCreationCard(
        #       agenda_controller=self.agenda_controller,
        #        reading_manager=self.reading_controller.reading_manager
        #    )
        #    self.event_creation_card.setObjectName("dashboard_card")
        #    self.event_creation_card.setMinimumHeight(400)
        #    self.event_creation_card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        #    row1_layout.addWidget(self.event_creation_card, 50)  # 30% da largura
        #else:
            # Placeholder se não houver controllers
        #    placeholder = QLabel("Criação de Eventos\n(Controllers não configurados)")
        #    placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        #    placeholder.setStyleSheet("""
        #        background-color: #2A2A2A;
        #        border-radius: 8px;
        #        color: #888;
        #        font-size: 14px;
        #        padding: 20px;
         #   """)
        #    placeholder.setMinimumHeight(400)
         #   row1_layout.addWidget(placeholder, 30)
        
        # 3. AddBookCard (30%)
        self.add_book_card = AddBookCard(book_controller=self.book_controller)
        self.add_book_card.setObjectName("dashboard_card")
        self.add_book_card.setMinimumHeight(400)
        self.add_book_card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        row1_layout.addWidget(self.add_book_card, 20)  # 30% da largura
        
        content_layout.addLayout(row1_layout)
        
        # Adicionar stretcher no final para alinhar conteúdo no topo
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
            self.add_book_card.import_config_requested.connect(self.show_import_dialog)
        
        if self.agenda_card:
            self.agenda_card.navigate_to_detailed_view.connect(
                self.open_week_event_editor_dialog
            )
            self.agenda_card.item_clicked.connect(self.handle_agenda_item_clicked)
            self.agenda_card.quick_action.connect(self.handle_agenda_quick_action)
            self.agenda_card.add_event_requested.connect(self.open_event_creation_dialog)
            
            # Conectar sinais de sessão de leitura (agora na agenda)
            if hasattr(self.agenda_card, 'start_reading_session'):
                self.agenda_card.start_reading_session.connect(self.handle_start_session)
            if hasattr(self.agenda_card, 'edit_reading_session'):
                self.agenda_card.edit_reading_session.connect(self.handle_edit_session)
            if hasattr(self.agenda_card, 'skip_reading_session'):
                self.agenda_card.skip_reading_session.connect(self.handle_skip_session)
        
        # Conexões com controllers (se necessário)
        if self.book_controller:
            self.book_controller.book_processing_started.connect(self.on_book_processing_started)
            self.book_controller.book_processing_progress.connect(self.on_book_processing_progress)
            self.book_controller.book_processing_completed.connect(self.on_book_processing_completed)
            self.book_controller.book_processing_failed.connect(self.on_book_processing_failed)
            if hasattr(self.book_controller, "book_scheduled"):
                self.book_controller.book_scheduled.connect(self.on_book_scheduled)

        if self.book_controller and hasattr(self.book_controller, 'current_book_updated'):
            self.book_controller.current_book_updated.connect(self.update_current_book)
        
        if self.agenda_backend and hasattr(self.agenda_backend, 'agenda_updated'):
            self.agenda_backend.agenda_updated.connect(self.update_agenda_data)
        
        if self.reading_controller and hasattr(self.reading_controller, 'stats_updated'):
            self.reading_controller.stats_updated.connect(self.update_stats_data)
        
    def show_import_dialog(self, file_path, initial_metadata):
        """Mostrar diálogo de configuração de importação"""
        from ui.widgets.dialogs.book_import_dialog import BookImportDialog
        
        dialog = BookImportDialog(file_path, initial_metadata, self)
        dialog.import_confirmed.connect(
            lambda config: self.start_book_processing(config)
        )

        # Adicionar conexão para resetar o card se o diálogo for cancelado
        dialog.import_cancelled.connect(
            lambda: self.add_book_card.reset_to_idle() if self.add_book_card else None
        )

        dialog.exec()
    
    def start_book_processing(self, config):
        """Iniciar processamento do livro com configurações"""
        if not self.book_controller:
            logger.error("BookController não disponível")
            return
            
        try:
            # Mapear configurações para parâmetros do controller
            quality_map = {
                "Rápido (Rascunho)": "draft",
                "Padrão": "standard", 
                "Alta Qualidade": "high",
                "Acadêmico": "academic"
            }
            
            # Configurações básicas
            settings = {
                "file_path": config["file_path"],
                "quality": quality_map.get(config["quality"], "standard"),
                "use_llm": config["use_llm"],
                "auto_schedule": config["auto_schedule"],
                
                # Configurações avançadas
                "metadata": {
                    "title": config["title"],
                    "author": config["author"],
                    "year": config["year"],
                    "publisher": config["publisher"],
                    "isbn": config["isbn"],
                    "language": config["language"],
                    "genre": config["genre"],
                    "tags": config["tags"]
                },
                
                "notes_config": {
                    "structure": config["note_structure"],
                    "template": config["note_template"],
                    "vault_location": config["vault_location"]
                },
                
                "scheduling_config": {
                    "pages_per_day": config["pages_per_day"],
                    "start_date": config["start_date"],
                    "preferred_time": config["preferred_time"],
                    "strategy": config["strategy"]
                }
            }
            
            # Iniciar processamento (o card será atualizado via sinal do controller)
            self.book_controller.process_book_with_config(settings)
                
        except Exception as e:
            logger.error(f"Erro ao iniciar processamento: {e}")
            self.show_notification(f"Erro ao iniciar processamento: {str(e)}", "error")
    
    def on_book_processing_started(self, pipeline_id, file_name, settings):
        """Atualizar UI quando processamento inicia"""
        if self.add_book_card:
            if "file_path" not in settings:
                settings = {**settings, "file_path": file_name}
            self.add_book_card.on_processing_started(pipeline_id, settings)
    
    def on_book_processing_progress(self, pipeline_id, stage, percent, message):
        """Atualizar progresso do processamento"""
        if self.add_book_card:
            self.add_book_card.on_processing_progress(pipeline_id, stage, percent, message)
    
    def on_book_processing_completed(self, pipeline_id, result):
        """Finalizar processamento com sucesso"""
        if self.add_book_card:
            self.add_book_card.on_processing_completed(pipeline_id, result)
        
        # Mostrar notificação
        title = result.get("title", "Livro")
        self.show_notification(f"✓ '{title}' processado com sucesso!", "success")

        warnings = result.get("warnings", []) if isinstance(result, dict) else []
        if warnings:
            self.show_notification(f"⚠️ {warnings[0]}", "warning")
        
        # Atualizar outras partes do dashboard se necessário
        self.refresh_data()
    
    def on_book_processing_failed(self, pipeline_id, error):
        """Tratar falha no processamento"""
        if self.add_book_card:
            self.add_book_card.on_processing_failed(pipeline_id, error)
        
        self.show_notification(f"✗ Erro no processamento: {error[:100]}...", "error")

    @pyqtSlot(str, dict)
    def on_book_scheduled(self, _book_id, scheduling_result):
        """Atualiza agenda/card quando sessões de leitura são agendadas."""
        sessions = int(scheduling_result.get("agenda_events_created", 0))
        if self.agenda_card and hasattr(self.agenda_card, "refresh"):
            self.agenda_card.refresh()
        if sessions > 0:
            self.show_notification(f"📅 {sessions} sessão(ões) de leitura agendadas", "success")
    
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

        if self.agenda_card and hasattr(self.agenda_card, 'refresh'):
            try:
                self.agenda_card.refresh()
            except Exception as e:
                logger.error(f"Erro ao carregar agenda semanal: {e}")
        
        # Carregar estatísticas para referência
        if self.reading_controller and hasattr(self.reading_controller, 'reading_controller.stats'):
            try:
                stats = self.reading_controller.reading_controller.stats()
                # Extrai o que precisamos para daily_stats
                self.daily_stats = {
                    "total_books": stats.get("total_books", 0),
                    "books_in_progress": stats.get("books_in_progress", 0),
                    "total_pages_read": stats.get("total_pages_read", 0),
                    "completion_percentage": stats.get("completion_percentage", 0),
                    "average_reading_speed": stats.get("average_reading_speed", 0),
                    "pages_last_week": stats.get("pages_last_week", 0)
                }
            except Exception as e:
                logger.error(f"Erro ao carregar estatísticas: {e}")
        
        # Vault permanece em modo sob demanda para reduzir custo de boot.
    
    # ============ HANDLERS ============
    
    def handle_book_file_selected(self, file_path):
        """Processar arquivo de livro selecionado"""
        if self.book_controller:
            try:
                logger.info(f"Processando arquivo de livro: {file_path}")
                self.book_controller.process_file(file_path)
            except Exception as e:
                logger.error(f"Erro ao processar livro: {e}")
    
    def handle_book_processed(self, pipeline_id, result):
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
            self.open_event_creation_dialog()
        elif action_name == "add_reading_session":
            # Se a agenda tem uma ação para adicionar sessão de leitura
            self.navigate_to.emit('reading_scheduler')
    
    def handle_event_created(self, event_data):
        """Manipular evento criado no EventCreationCard"""
        logger.info(f"Evento criado: {event_data.get('title')}")

        try:
            if self.agenda_card and hasattr(self.agenda_card, 'refresh'):
                self.agenda_card.refresh()
            self.show_notification("✅ Evento criado com sucesso", "success")
        except Exception as e:
            logger.error(f"Erro ao atualizar agenda: {e}")
            self.show_notification(f"❌ Erro ao criar evento: {str(e)[:50]}", "error")
    
    def handle_event_scheduled(self, event_id):
        """Manipular evento agendado (para leituras)"""
        logger.info(f"Evento agendado: {event_id}")
        
        if event_id.startswith('reading_'):
            self.show_notification(f"📚 Sessões de leitura agendadas", "success")

            if self.agenda_card and hasattr(self.agenda_card, 'refresh'):
                try:
                    self.agenda_card.refresh()
                except Exception as e:
                    logger.error(f"Erro ao recarregar agenda: {e}")
    
    def handle_event_creation_cancelled(self):
        """Manipular cancelamento da criação de evento"""
        logger.info("Criação de evento cancelada")

    def open_event_creation_dialog(self):
        """Abre diálogo modal para criação de eventos."""
        reading_manager = None
        if self.reading_controller and hasattr(self.reading_controller, "reading_manager"):
            reading_manager = self.reading_controller.reading_manager

        dialog = EventCreationDialog(
            agenda_controller=self.agenda_backend,
            reading_manager=reading_manager,
            parent=self,
        )
        self.event_creation_dialog = dialog

        dialog.event_card.event_created.connect(self.handle_event_created)
        dialog.event_card.event_scheduled.connect(self.handle_event_scheduled)
        dialog.event_card.cancel_requested.connect(self.handle_event_creation_cancelled)

        dialog.exec()

    def open_week_event_editor_dialog(self):
        """Abre diálogo com lista e edição de eventos da semana visível."""
        week_start = None
        if self.agenda_card and hasattr(self.agenda_card, "current_week_start"):
            week_start = self.agenda_card.current_week_start

        reading_manager = None
        if self.reading_controller and hasattr(self.reading_controller, "reading_manager"):
            reading_manager = self.reading_controller.reading_manager

        dialog = WeeklyEventEditorDialog(
            agenda_backend=self.agenda_backend,
            reading_manager=reading_manager,
            week_start=week_start,
            parent=self,
        )
        self.weekly_event_editor_dialog = dialog
        dialog.event_changed.connect(self.refresh_data)
        dialog.exec()
    
    def handle_start_session(self, session_data):
        """Iniciar sessão de leitura (agora vindo da agenda)"""
        if self.reading_controller:
            try:
                metadata = session_data.get("metadata", {}) if isinstance(session_data, dict) else {}
                book_id = (
                    session_data.get("book_id")
                    or metadata.get("book_id")
                    or metadata.get("id")
                ) if isinstance(session_data, dict) else None
                target_pages = (
                    session_data.get("target_pages")
                    or metadata.get("pages_planned")
                    or 10
                ) if isinstance(session_data, dict) else 10

                if book_id and hasattr(self.reading_controller, "start_reading_session"):
                    self.reading_controller.start_reading_session(str(book_id), int(target_pages))
                    logger.info("Sessão de leitura iniciada para livro %s", book_id)
                else:
                    logger.warning("Sessão iniciada sem book_id válido no evento: %s", session_data)
            except Exception as e:
                logger.error(f"Erro ao iniciar sessão: {e}")

        self.navigate_to.emit('session')
    
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
    
    @pyqtSlot(str, list)
    def update_agenda_data(self, _date_str, agenda_data):
        """Atualizar agenda quando controller emite sinal"""
        self.today_agenda = agenda_data
        if self.agenda_card and hasattr(self.agenda_card, 'refresh'):
            self.agenda_card.refresh()
    
    @pyqtSlot(dict)
    def update_stats_data(self, stats_data):
        """Atualizar estatísticas quando controller emite sinal"""
        self.daily_stats = stats_data
    
    def show_notification(self, message: str, type: str = "info"):
        """Mostra notificação no dashboard"""
        # Esta função deve ser implementada ou conectada a um sistema de notificação
        print(f"[{type.upper()}] {message}")
        # Aqui você pode integrar com um sistema de notificação UI se existir
    
    def on_view_activated(self):
        """Chamado quando a view é ativada"""
        self.load_initial_data()
        
    def cleanup(self):
        """Limpeza antes de fechar"""
        if hasattr(self, 'greeting_timer'):
            self.greeting_timer.stop()
        if hasattr(self, 'update_timer'):
            self.update_timer.stop()
        
        # Limpar timer do vault se existir
        if hasattr(self, 'vault_timer'):
            self.vault_timer.stop()
        
        # Limpar recursos dos cards
        if self.add_book_card and hasattr(self.add_book_card, 'cleanup'):
            self.add_book_card.cleanup()
        if self.agenda_card and hasattr(self.agenda_card, 'cleanup'):
            self.agenda_card.cleanup()
        if self.event_creation_card and hasattr(self.event_creation_card, 'cleanup'):
            self.event_creation_card.cleanup()
        if self.event_creation_dialog:
            self.event_creation_dialog.close()
        if self.weekly_event_editor_dialog:
            self.weekly_event_editor_dialog.close()
