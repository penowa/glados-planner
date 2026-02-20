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

from ui.widgets.cards.agenda_card import AgendaCard
from ui.widgets.cards.upcoming_commitments_card import UpcomingCommitmentsCard
from ui.widgets.cards.event_creation_card import EventCreationDialog
from ui.widgets.dialogs.weekly_event_editor_dialog import WeeklyEventEditorDialog

logger = logging.getLogger('GLaDOS.UI.Dashboard')

class DashboardView(QWidget):
    """View principal do dashboard com design minimalista"""
    
    # Sinais
    refresh_requested = pyqtSignal()
    navigate_to = pyqtSignal(str)  # Novo sinal para navegação
    review_requested = pyqtSignal(dict)
    review_workspace_requested = pyqtSignal(dict)
    
    def __init__(self, controllers=None):
        super().__init__()
        
        # Armazenar controllers
        self.controllers = controllers
        self.book_controller = controllers.get('book') if controllers else None
        self.agenda_controller = controllers.get('agenda') if controllers else None
        self.reading_controller = controllers.get('reading') if controllers else None
        self.daily_checkin_controller = controllers.get('daily_checkin') if controllers else None
        self.agenda_backend = self._resolve_agenda_backend()
        
        # Cards
        self.upcoming_commitments_card = None
        self.agenda_card = None
        self.event_creation_card = None
        self.event_creation_dialog = None
        self.weekly_event_editor_dialog = None
        
        # Dados em tempo real
        self.current_reading = None
        self.today_agenda = []
        self.daily_stats = {}
        self.user_name = "Usuário"
        self.assistant_name = "GLaDOS"
        self.checkin_action_button = None
        self._checkin_pulse_active = False
        self._checkin_pulse_phase = False
        self._active_checkin_type = None
        self._all_checkins_done = False
        self._load_identity_from_settings()
        
        self.setup_ui()
        self.setup_connections()
        self.setup_timers()
        self._refresh_checkin_button_state()
        
        logger.info("DashboardView inicializado com cards integrados")

    def _load_identity_from_settings(self):
        """Carrega nomes customizáveis (usuário/assistente) do settings.yaml."""
        try:
            from core.config.settings import Settings
            current_settings = Settings.from_yaml()
            glados_cfg = current_settings.llm.glados
            self.user_name = str(glados_cfg.user_name or "").strip() or self.user_name
            self.assistant_name = str(glados_cfg.glados_name or "").strip() or self.assistant_name
        except Exception:
            # Mantém fallback local quando configurações ainda não estão disponíveis.
            pass

    def update_identity(self, user_name: str | None = None, assistant_name: str | None = None):
        """Atualiza nomes exibidos na UI em tempo de execução."""
        if user_name is not None:
            normalized_user = str(user_name).strip()
            if normalized_user:
                self.user_name = normalized_user
        if assistant_name is not None:
            normalized_assistant = str(assistant_name).strip()
            if normalized_assistant:
                self.assistant_name = normalized_assistant
        self.update_greeting()
    
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
        
        # ============ LINHA 1: Agenda + Próximos compromissos ============
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
        
        # 2. Próximos compromissos (sem ícones, com tipos por cor)
        self.upcoming_commitments_card = UpcomingCommitmentsCard(
            agenda_backend=self.agenda_backend,
            max_items=5,
        )
        self.upcoming_commitments_card.setObjectName("dashboard_card")
        self.upcoming_commitments_card.setMinimumHeight(320)
        self.upcoming_commitments_card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        row1_layout.addWidget(self.upcoming_commitments_card, 20)
        
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

        # Botão único de check-in (matinal/noturno)
        self.checkin_action_button = QPushButton("É hora do check-up!")
        self.checkin_action_button.setObjectName("dashboard_checkin_button")
        self.checkin_action_button.setMinimumWidth(220)
        self.checkin_action_button.setFixedHeight(32)
        self.checkin_action_button.clicked.connect(self._handle_dashboard_checkin)
        
        layout.addWidget(self.greeting_label)
        layout.addStretch()
        layout.addWidget(self.date_label)
        layout.addWidget(self.checkin_action_button)
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
        user_display_name = self.user_name or "Usuário"
        hour = QDateTime.currentDateTime().time().hour()
        if hour < 12:
            return f"🌅 Bom dia {user_display_name}"
        elif hour < 18:
            return f"☀️ Boa tarde {user_display_name}"
        else:
            return f"🌙 Boa noite {user_display_name}"
    
    def setup_connections(self):
        """Configura conexões com controllers e cards"""
        # Conectar sinais dos cards
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
            if hasattr(self.agenda_card, 'start_review_session'):
                self.agenda_card.start_review_session.connect(self.handle_start_review_session)
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

        if self.daily_checkin_controller:
            if hasattr(self.daily_checkin_controller, "morning_checkin_needed"):
                self.daily_checkin_controller.morning_checkin_needed.connect(self._refresh_checkin_button_state)
            if hasattr(self.daily_checkin_controller, "evening_checkin_needed"):
                self.daily_checkin_controller.evening_checkin_needed.connect(self._refresh_checkin_button_state)
            if hasattr(self.daily_checkin_controller, "checkin_completed"):
                self.daily_checkin_controller.checkin_completed.connect(self._on_checkin_completed)
        
    def show_import_dialog(self, file_path, initial_metadata):
        """Mostrar diálogo de configuração de importação"""
        from ui.widgets.dialogs.book_import_dialog import BookImportDialog
        
        dialog = BookImportDialog(file_path, initial_metadata, self)
        dialog.import_confirmed.connect(
            lambda config: self.start_book_processing(config)
        )

        # Adicionar conexão para resetar o card se o diálogo for cancelado
        dialog.import_cancelled.connect(lambda: None)

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
        return
    
    def on_book_processing_progress(self, pipeline_id, stage, percent, message):
        """Atualizar progresso do processamento"""
        return
    
    def on_book_processing_completed(self, pipeline_id, result):
        """Finalizar processamento com sucesso"""
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

        # Timer para recalcular estado do botão de check-in
        self.checkin_state_timer = QTimer()
        self.checkin_state_timer.timeout.connect(self._refresh_checkin_button_state)
        self.checkin_state_timer.start(30000)  # 30 segundos

        # Timer para animação de pulso
        self.checkin_pulse_timer = QTimer()
        self.checkin_pulse_timer.timeout.connect(self._toggle_checkin_pulse)
        self.checkin_pulse_timer.start(700)
    
    def load_initial_data(self):
        """Carrega dados iniciais dos controllers"""
        logger.info("Carregando dados iniciais do dashboard")

        if self.agenda_card and hasattr(self.agenda_card, 'refresh'):
            try:
                self.agenda_card.refresh()
            except Exception as e:
                logger.error(f"Erro ao carregar agenda semanal: {e}")
        if self.upcoming_commitments_card and hasattr(self.upcoming_commitments_card, 'refresh'):
            try:
                self.upcoming_commitments_card.refresh()
            except Exception as e:
                logger.error(f"Erro ao carregar próximos compromissos: {e}")
        
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
        self._refresh_checkin_button_state()
    
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
        event_type = str(item_data.get("type", "")).strip().lower()
        if event_type in {"revisao", "revisão"}:
            self.review_workspace_requested.emit(dict(item_data or {}))

    def handle_agenda_quick_action(self, action_name, data):
        """Manipular ação rápida da agenda"""
        logger.info(f"Ação rápida da agenda: {action_name}")
        if action_name == "add_event":
            self.open_event_creation_dialog()
        elif action_name == "add_reading_session":
            # Se a agenda tem uma ação para adicionar sessão de leitura
            self.navigate_to.emit('reading_scheduler')
        elif action_name == "open_review_plan":
            self.review_requested.emit(
                {
                    "source": "dashboard",
                    "requested_at": QDateTime.currentDateTime().toString(Qt.DateFormat.ISODate),
                }
            )
    
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

    def handle_start_review_session(self, event_data):
        """Abre workspace de revisão para evento de revisão da agenda."""
        logger.info(f"Abrindo revisão agendada: {event_data.get('id', 'N/A')}")
        self.review_workspace_requested.emit(dict(event_data or {}))
    
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
        if self.upcoming_commitments_card and hasattr(self.upcoming_commitments_card, 'refresh'):
            self.upcoming_commitments_card.refresh()
        self._refresh_checkin_button_state()
    
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
        self._refresh_checkin_button_state()

    @pyqtSlot(str, dict)
    def _on_checkin_completed(self, _checkin_type, _data):
        self._refresh_checkin_button_state()

    def _handle_dashboard_checkin(self):
        controller = self.daily_checkin_controller
        if not controller:
            self.show_notification("Sistema de check-in indisponível.", "warning")
            return

        state = controller.get_dashboard_state() if hasattr(controller, "get_dashboard_state") else {}
        active_type = str(state.get("active_type") or "").strip().lower()
        dialog_parent = self.window() if isinstance(self.window(), QWidget) else self

        if active_type == "morning":
            controller.show_morning_dialog(dialog_parent)
        elif active_type == "evening":
            controller.show_evening_dialog(dialog_parent)
        elif hasattr(controller, "is_morning_pending") and controller.is_morning_pending():
            controller.show_morning_dialog(dialog_parent)
        elif hasattr(controller, "is_evening_pending") and controller.is_evening_pending():
            controller.show_evening_dialog(dialog_parent)
        else:
            self.show_notification("Check-ins do dia já concluídos.", "info")

        self._refresh_checkin_button_state()

    def _toggle_checkin_pulse(self):
        if not self._checkin_pulse_active:
            return
        self._checkin_pulse_phase = not self._checkin_pulse_phase
        self._apply_checkin_button_style()

    def _refresh_checkin_button_state(self):
        button = self.checkin_action_button
        if not button:
            return

        button.setText("É hora do check-up!")
        controller = self.daily_checkin_controller
        if not controller:
            button.setEnabled(False)
            button.setVisible(True)
            button.setToolTip("Controller de check-in não inicializado.")
            self._active_checkin_type = None
            self._checkin_pulse_active = False
            self._checkin_pulse_phase = False
            self._all_checkins_done = False
            self._apply_checkin_button_style()
            return

        button.setEnabled(True)
        state = controller.get_dashboard_state() if hasattr(controller, "get_dashboard_state") else {}
        morning_pending = bool(state.get("morning_pending"))
        evening_pending = bool(state.get("evening_pending"))
        active_type = str(state.get("active_type") or "").strip().lower()
        waiting_evening = bool(state.get("waiting_evening"))
        evening_trigger = str(state.get("evening_trigger_time") or "").strip()
        now_hour = QDateTime.currentDateTime().time().hour()
        is_after_18 = now_hour >= 18

        pulse = bool(state.get("pulse"))
        should_show_morning = (not is_after_18) and morning_pending
        should_show_evening = is_after_18 and evening_pending
        should_show_button = should_show_morning or should_show_evening

        self._active_checkin_type = None
        if should_show_morning:
            self._active_checkin_type = "morning"
        elif should_show_evening:
            self._active_checkin_type = "evening"

        button.setVisible(should_show_button)
        self._checkin_pulse_active = pulse
        self._all_checkins_done = (not morning_pending and not evening_pending)
        if not pulse:
            self._checkin_pulse_phase = False

        if active_type == "morning":
            button.setToolTip("Check-in matinal pendente. O alerta visual encerra às 18h.")
        elif active_type == "evening" and pulse:
            button.setToolTip("Última atividade do dia passou. Faça o check-in noturno.")
        elif morning_pending:
            button.setToolTip("Check-in matinal ainda não registrado.")
        elif evening_pending and waiting_evening:
            if evening_trigger:
                button.setToolTip(f"Check-in noturno ficará em destaque após {evening_trigger}.")
            else:
                button.setToolTip("Check-in noturno ficará em destaque após a última atividade do dia.")
        elif evening_pending:
            button.setToolTip("Check-in noturno pendente.")
        else:
            button.setToolTip("Check-ins do dia concluídos.")

        self._apply_checkin_button_style()

    def _apply_checkin_button_style(self):
        if not self.checkin_action_button:
            return

        active_type = self._active_checkin_type
        pulse_on = bool(self._checkin_pulse_active and self._checkin_pulse_phase)

        if active_type == "morning":
            base_bg = "#B8890A"
            pulse_bg = "#D4A30C"
            border = "#F5D56A"
            text = "#1B1B1B"
        elif active_type == "evening":
            base_bg = "#A47908"
            pulse_bg = "#C6920A"
            border = "#EBC85D"
            text = "#1B1B1B"
        elif self._all_checkins_done:
            base_bg = "#14532D"
            pulse_bg = base_bg
            border = "#22C55E"
            text = "#DCFCE7"
        else:
            base_bg = "#1F2937"
            pulse_bg = "#334155"
            border = "#475569"
            text = "#E2E8F0"

        current_bg = pulse_bg if pulse_on else base_bg
        hover_bg = pulse_bg if self._checkin_pulse_active else "#D4A30C"

        self.checkin_action_button.setStyleSheet(
            f"""
            QPushButton#dashboard_checkin_button {{
                background-color: {current_bg};
                color: {text};
                border: 1px solid {border};
                border-radius: 10px;
                padding: 6px 12px;
                font-size: 11px;
                font-weight: 700;
            }}
            QPushButton#dashboard_checkin_button:hover {{
                background-color: {hover_bg};
                border-color: #FFE08A;
            }}
            QPushButton#dashboard_checkin_button:pressed {{
                background-color: #8E6707;
            }}
            QPushButton#dashboard_checkin_button:disabled {{
                background-color: #1E293B;
                color: #64748B;
                border-color: #334155;
            }}
            """
        )
        
    def cleanup(self):
        """Limpeza antes de fechar"""
        if hasattr(self, 'greeting_timer'):
            self.greeting_timer.stop()
        if hasattr(self, 'update_timer'):
            self.update_timer.stop()
        if hasattr(self, 'checkin_state_timer'):
            self.checkin_state_timer.stop()
        if hasattr(self, 'checkin_pulse_timer'):
            self.checkin_pulse_timer.stop()
        
        # Limpar timer do vault se existir
        if hasattr(self, 'vault_timer'):
            self.vault_timer.stop()
        
        # Limpar recursos dos cards
        if self.agenda_card and hasattr(self.agenda_card, 'cleanup'):
            self.agenda_card.cleanup()
        if self.event_creation_card and hasattr(self.event_creation_card, 'cleanup'):
            self.event_creation_card.cleanup()
        if self.event_creation_dialog:
            self.event_creation_dialog.close()
        if self.weekly_event_editor_dialog:
            self.weekly_event_editor_dialog.close()
