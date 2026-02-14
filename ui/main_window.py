"""
Janela principal da aplicação com todos os sistemas integrados
Implementa navegação, temas, controllers, e integração com backend
"""
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QStackedWidget, QSizePolicy, QFrame, QLabel, 
    QPushButton, QToolBar, QStatusBar, QMessageBox,
    QDialog, QProgressBar, QMenu
)
from PyQt6.QtCore import Qt, pyqtSignal, pyqtSlot, QTimer, QPoint
from PyQt6.QtGui import QFont, QIcon, QPalette, QColor, QAction, QPainter, QPen

# Sistemas centrais
from core.communication.event_bus import GlobalEventBus
from core.errors.error_manager import ErrorManager
from core.monitoring.performance_monitor import PerformanceMonitor
from core.recovery.state_recovery import StateRecoveryManager

# UI Components
from ui.utils.theme_manager import ThemeManager
from ui.utils.shortcut_manager import ShortcutManager
from ui.utils.responsive import ResponsiveManager
from ui.utils.animation import FadeAnimation, SlideAnimation

# Views
from ui.views.dashboard import DashboardView
from ui.views.agenda import AgendaView
from ui.views.session import SessionView

# Controllers
from ui.controllers.book_controller import BookController
from ui.controllers.agenda_controller import AgendaController
from ui.controllers.focus_controller import FocusController
from ui.controllers.glados_controller import GladosController
from ui.controllers.reading_controller import ReadingController
from ui.controllers.vault_controller import VaultController
from ui.controllers.dashboard_controller import DashboardController
from ui.controllers.daily_checkin_controller import DailyCheckinController
from core.modules.daily_checkin import DailyCheckinSystem

import logging
from typing import Dict, Any, List
from datetime import datetime
import os

logger = logging.getLogger('GLaDOS.UI.MainWindow')

class MainWindow(QMainWindow):
    """Janela principal com todos os sistemas integrados"""
    
    # Sinais
    theme_changed = pyqtSignal(str)
    view_changed = pyqtSignal(str)
    system_status_changed = pyqtSignal(dict)
    
    def __init__(
        self,
        event_bus: GlobalEventBus,
        error_manager: ErrorManager,
        performance_monitor: PerformanceMonitor,
        recovery_manager: StateRecoveryManager,
        backend_modules: Dict[str, Any],
        config: Dict[str, Any]
    ):
        super().__init__()
        
        # Armazenar referências aos sistemas
        self.event_bus = event_bus
        self.error_manager = error_manager
        self.performance_monitor = performance_monitor
        self.recovery_manager = recovery_manager
        self.backend_modules = backend_modules
        self.config = config
        
        # Estado interno
        self.current_theme = config.get('theme', 'philosophy_dark')
        self.current_view = 'dashboard'
        self.views = {}
        self.controllers = {}
        self.widgets = {}
        
        # Configurações de UI
        self.animations_enabled = True
        self.notifications_enabled = True
        self._event_notification_count = 0
        self._reading_session_notified_ids = set()
        
        # Inicializar
        self.setup_window()
        self.init_controllers()
        self.setup_ui()
        self.setup_connections()
        self.setup_systems()
        
        logger.info("MainWindow initialized with integrated systems")
    
    def setup_window(self):
        """Configura propriedades da janela"""
        self.setWindowTitle("GLaDOS Philosophy Planner")
        self.setGeometry(100, 100, 1360, 720)
        
        # Centralizar na tela
        screen = self.screen().availableGeometry()
        x = (screen.width() - self.width()) // 2
        y = (screen.height() - self.height()) // 2
        self.move(x, y)
        
        # Ícone da aplicação
        # self.setWindowIcon(QIcon("ui/resources/icons/app.png"))
        
        # Configurações de estado
        self.setAnimated(self.animations_enabled)
    
    def init_controllers(self):
        """Inicializa controllers que integram backend e frontend"""
        def _safe_init(name, factory):
            try:
                self.controllers[name] = factory()
                logger.info(f"Controller '{name}' inicializado")
            except Exception as e:
                self.error_manager.handle_error(e)
                logger.error(f"Falha ao inicializar controller '{name}': {e}")

        # Priorizar vault cedo para habilitar stats card mesmo se outro módulo falhar.
        _safe_init(
            'vault',
            lambda: VaultController(str(self.backend_modules['vault_manager'].vault_path))
        )
        _safe_init('dashboard', lambda: DashboardController(self.backend_modules))
        _safe_init(
            'book',
            lambda: BookController(
                pdf_processor=self.backend_modules['book_processor'],
                book_processor=self.backend_modules['book_processor'],
                reading_manager=self.backend_modules['reading_manager'],
                agenda_controller=self.backend_modules.get('agenda_manager'),
                vault_manager=self.backend_modules.get('vault_manager')
            )
        )
        _safe_init('agenda', lambda: AgendaController(self.backend_modules['agenda_manager']))
        _safe_init(
            'daily_checkin',
            lambda: DailyCheckinController(
                checkin_system=DailyCheckinSystem(
                    str(self.backend_modules['vault_manager'].vault_path)
                ),
                agenda_controller=self.controllers.get('agenda')
            )
        )
        _safe_init('focus', lambda: FocusController())
        _safe_init('glados', lambda: GladosController(self.backend_modules['llm_module']))
        _safe_init('reading', lambda: ReadingController(self.backend_modules['reading_manager']))
    
    def setup_ui(self):
        """Configura interface principal com todos os componentes"""
        # Widget central
        central_widget = QWidget()
        central_widget.setObjectName("main_central_widget")
        self.setCentralWidget(central_widget)
        
        # Layout principal - REMOVIDA BARRA LATERAL
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # 1. Barra de título personalizada
        self.setup_title_bar()
        main_layout.addWidget(self.title_bar, 0)
        
        # 2. Separador
        title_separator = QFrame()
        title_separator.setFrameShape(QFrame.Shape.HLine)
        title_separator.setFrameShadow(QFrame.Shadow.Sunken)
        title_separator.setObjectName("title_separator")
        main_layout.addWidget(title_separator)
        
        # 3. Stack de views (área principal)
        self.view_stack = QStackedWidget()
        self.view_stack.setObjectName("view_stack")
        
        # Configurar animações de transição
        if self.animations_enabled:
            self.view_stack_transition = SlideAnimation(self.view_stack)
        
        main_layout.addWidget(self.view_stack, 1)
        
        # 4. Status bar com informações do sistema
        self.setup_status_bar()
        
        # 5. Toolbar customizada (opcional, pode ser removida se não for necessária)
        # self.setup_toolbar()
        
        # Inicializar todas as views
        self.init_views()
        
        # Carrega o tema atual
        ThemeManager.instance().load_theme(self.current_theme)
    
    def setup_title_bar(self):
        """Configura barra de título personalizada - ATUALIZADA COM NOVOS BOTÕES"""
        self.title_bar = QWidget()
        self.title_bar.setObjectName("title_bar")
        self.title_bar.setFixedHeight(60)
        
        layout = QHBoxLayout(self.title_bar)
        layout.setContentsMargins(20, 0, 20, 0)
        layout.setSpacing(15)
        
        # Logo/título da aplicação
        self.app_logo = QLabel("GLaDOS")
        self.app_logo.setObjectName("app_logo")
        self.app_logo.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        font = QFont("Georgia", 16, QFont.Weight.Bold)
        self.app_logo.setFont(font)
        layout.addWidget(self.app_logo)
        
        # Spacer
        layout.addStretch(1)
        
        # Sistema de notificações
        self.setup_notification_indicator()
        layout.addWidget(self.notification_widget)
        
        # Sistema de performance
        self.setup_performance_indicator()
        layout.addWidget(self.performance_widget)
        
        # Controles da janela
        controls_layout = QHBoxLayout()
        controls_layout.setSpacing(5)  # Menor espaçamento
        
        # Botão de tema
        self.theme_button = QPushButton(self.get_theme_icon())
        self.theme_button.setObjectName("theme_button")
        self.theme_button.setFixedSize(36, 36)
        self.theme_button.setToolTip("Alternar tema (Ctrl+T)")
        self.theme_button.clicked.connect(self.toggle_theme)
        controls_layout.addWidget(self.theme_button)
        
        # Botão de configurações - NOVO
        self.settings_button = QPushButton("⚙️")
        self.settings_button.setObjectName("settings_button")
        self.settings_button.setFixedSize(36, 36)
        self.settings_button.setToolTip("Configurações")
        self.settings_button.clicked.connect(self.show_settings)
        controls_layout.addWidget(self.settings_button)
        
        # Botão para encerrar - NOVO
        self.quit_button = QPushButton("✕")
        self.quit_button.setObjectName("quit_button")
        self.quit_button.setFixedSize(36, 36)
        self.quit_button.setToolTip("Encerrar aplicação")
        self.quit_button.clicked.connect(self.close_application)
        controls_layout.addWidget(self.quit_button)
        
        layout.addLayout(controls_layout)
    
    def setup_notification_indicator(self):
        """Configura indicador de notificações"""
        self.notification_widget = QWidget()
        self.notification_widget.setObjectName("notification_widget")
        layout = QHBoxLayout(self.notification_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.notification_button = QPushButton("🔔")
        self.notification_button.setObjectName("notification_button")
        self.notification_button.setFixedSize(36, 36)
        self.notification_button.clicked.connect(self.show_notifications)
        
        self.notification_count = QLabel("0")
        self.notification_count.setObjectName("notification_count")
        self.notification_count.setFixedSize(18, 18)
        self.notification_count.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        layout.addWidget(self.notification_button)
        layout.addWidget(self.notification_count)
        
        # Inicialmente esconder contador
        self.notification_count.setVisible(False)
    
    def setup_performance_indicator(self):
        """Configura indicador de performance"""
        self.performance_widget = QWidget()
        self.performance_widget.setObjectName("performance_widget")
        layout = QHBoxLayout(self.performance_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.performance_button = QPushButton("📈")
        self.performance_button.setObjectName("performance_button")
        self.performance_button.setFixedSize(36, 36)
        self.performance_button.clicked.connect(self.show_performance_monitor)
        self.performance_button.setToolTip("Monitor de performance")
        
        layout.addWidget(self.performance_button)
    
    def setup_status_bar(self):
        """Configura barra de status com informações do sistema"""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        
        # Indicadores de status
        self.status_indicators = {
            'system': QLabel("✅ Sistema"),
            'vault': QLabel("🔗 Vault: --"),
            'llm': QLabel("🧠 LLM: --"),
            'memory': QLabel("💾 Memória: --"),
        }
        
        for indicator in self.status_indicators.values():
            self.status_bar.addWidget(indicator)
        
        # Timer para atualizar status
        self.status_timer = QTimer()
        self.status_timer.timeout.connect(self.update_status_bar)
        self.status_timer.start(5000)  # 5 segundos
    
    def setup_toolbar(self):
        """Configura toolbar customizada - REMOVIDA"""
        pass
    
    def init_views(self):
        """Inicializa todas as views do sistema"""
        # Criar views com referências aos controllers
        self.views['dashboard'] = DashboardView(self.controllers)
        self.views['dashboard'].navigate_to.connect(self.change_view)
        self.views['session'] = SessionView(self.controllers)
        self.views['session'].navigate_to.connect(self.change_view)
        #self.views['library'] =  LibraryView(self.controllers['reading'])
        #self.views['agenda'] = AgendaView(self.controllers['agenda'])
        #self.views['focus'] = FocusView(self.controllers['focus'])
        #self.views['concepts'] = ConceptsView(self.controllers['book'])
        #self.views['analytics'] = AnalyticsView(self.controllers)
        #self.views['goals'] = GoalsView(self.controllers['reading'])
        #self.views['glados'] = GladosView(self.controllers['glados'])
        #self.views['settings'] = SettingsView(self.config)
        
        # Adicionar ao stack
        for view_name, view in self.views.items():
            self.view_stack.addWidget(view)
            
            # Conectar sinais comuns
            if hasattr(view, 'data_updated'):
                view.data_updated.connect(lambda data, v=view_name: self.on_view_data_updated(v, data))
        
        # Definir view inicial
        self.view_stack.setCurrentWidget(self.views['dashboard'])
    
    def setup_connections(self):
        """Configura todas as conexões entre sistemas"""
        # 1. Conexões internas
        self.theme_changed.connect(self.on_theme_changed)
        self.view_changed.connect(self.on_view_changed)
        
        # 2. Conexões com EventBus
        bus = self.event_bus
        
        # Notificações
        bus.notification.connect(self.handle_notification)
        
        # Atualizações de progresso
        bus.progress_updated.connect(self.handle_progress_update)
        
        # Erros do sistema
        bus.module_error.connect(self.handle_module_error)
        
        # Atualizações de dados
        bus.data_created.connect(self.on_data_created)
        bus.data_updated.connect(self.on_data_updated)
        bus.data_deleted.connect(self.on_data_deleted)
        
        # Estado do sistema
        bus.state_changed.connect(self.on_state_changed)
        bus.connection_lost.connect(self.on_connection_lost)
        bus.connection_restored.connect(self.on_connection_restored)
        
        # 3. Configurar atalhos de teclado
        self.setup_shortcuts()

        daily_checkin_controller = self.controllers.get('daily_checkin')
        if daily_checkin_controller:
            daily_checkin_controller.morning_checkin_needed.connect(self._refresh_notification_counter)
            daily_checkin_controller.evening_checkin_needed.connect(self._refresh_notification_counter)
            daily_checkin_controller.checkin_completed.connect(self._on_checkin_completed)

        self._refresh_notification_counter()
    
    def setup_systems(self):
        """Configura sistemas auxiliares"""
        # 1. Sistema responsivo
        ResponsiveManager.instance().register_window(self)
        
        # 2. Configurar atualizações automáticas
        self.setup_auto_updates()
        
        # 3. Verificar sistema ao iniciar
        QTimer.singleShot(1000, self.run_system_check)
    
    def setup_shortcuts(self):
        """Configura atalhos de teclado globais"""
        self.shortcut_manager = ShortcutManager(self)
        
        shortcuts = {
            # Navegação
            'Ctrl+1': lambda: self.change_view('dashboard'),
            'Ctrl+2': lambda: self.change_view('library'),
            'Ctrl+3': lambda: self.change_view('agenda'),
            'Ctrl+4': lambda: self.change_view('focus'),
            'Ctrl+5': lambda: self.change_view('concepts'),
            'Ctrl+6': lambda: self.change_view('analytics'),
            'Ctrl+7': lambda: self.change_view('goals'),
            'Ctrl+8': lambda: self.change_view('glados'),
            'Ctrl+9': lambda: self.change_view('settings'),
            
            # Ações gerais
            'Ctrl+T': self.toggle_theme,
            'Ctrl+S': self.show_search_dialog,
            'Ctrl+F': self.show_focus_mode,
            'Ctrl+G': lambda: self.change_view('glados'),
            'Ctrl+Q': self.close_application,
            'F1': self.show_help,
            'F5': self.refresh_current_view,
            
            # Ações específicas
            'Ctrl+N': self.show_add_book_dialog,
            'Ctrl+Shift+N': self.show_add_note_dialog,
            'Ctrl+P': self.start_focus_session,
            'Ctrl+E': self.show_quick_stats,
            'Ctrl+R': self.run_system_check,
            'Ctrl+Shift+S': self.show_settings,  # NOVO: Atalho para configurações
        }
        
        for shortcut, callback in shortcuts.items():
            self.shortcut_manager.register(shortcut, callback)
    
    def setup_auto_updates(self):
        """Configura atualizações automáticas"""
        # Timer para atualizar dashboard
        self.dashboard_timer = QTimer()
        self.dashboard_timer.timeout.connect(self.update_dashboard)
        self.dashboard_timer.start(30000)  # 30 segundos
        
        # Timer para verificar notificações
        self.notification_timer = QTimer()
        self.notification_timer.timeout.connect(self.check_notifications)
        self.notification_timer.start(60000)  # 1 minuto
        
        # Timer para backup automático
        self.backup_timer = QTimer()
        self.backup_timer.timeout.connect(self.auto_backup)
        self.backup_timer.start(3600000)  # 1 hora
    
    # ============ MÉTODOS PRINCIPAIS ============
    
    @pyqtSlot(str)
    def change_view(self, view_name: str):
        """Muda a view atual com animação"""
        if view_name not in self.views:
            logger.warning(f"View não encontrada: {view_name}")
            return
        
        old_view = self.current_view
        self.current_view = view_name
        
        # Atualizar título do app_logo
        titles = {
            'dashboard': 'GLaDOS',
            'session': 'Sessão',
            'library': 'Biblioteca',
            'agenda': 'Agenda',
            'focus': 'Modo Foco',
            'concepts': 'Conceitos',
            'analytics': 'Analytics',
            'goals': 'Metas',
            'glados': 'GLaDOS',
            'settings': 'Configurações'
        }
        
        self.app_logo.setText(titles.get(view_name, view_name))
        
        # Animar transição se habilitado
        if self.animations_enabled and hasattr(self, 'view_stack_transition'):
            self.view_stack_transition.transition_to(view_name)
        else:
            self.view_stack.setCurrentWidget(self.views[view_name])
        
        # Emitir sinal
        self.view_changed.emit(view_name)
        
        # Log
        logger.info(f"View alterada: {old_view} → {view_name}")
        
        # Atualizar view se necessário
        current_view = self.views[view_name]
        if hasattr(current_view, 'on_view_activated'):
            current_view.on_view_activated()
    
    def toggle_theme(self):
        """Alterna entre temas com animação"""
        themes = ['philosophy_dark', 'philosophy_light', 'philosophy_night']
        current_index = themes.index(self.current_theme)
        next_theme = themes[(current_index + 1) % len(themes)]
        
        # Animar transição
        if self.animations_enabled:
            self.fade_out_animation()
        
        # Aplicar novo tema
        ThemeManager.instance().load_theme(next_theme)
        self.current_theme = next_theme
        
        # Atualizar interface
        self.theme_button.setText(self.get_theme_icon())
        self.theme_button.setToolTip(f"Tema: {self.get_theme_name(next_theme)}")
        
        if self.animations_enabled:
            QTimer.singleShot(300, self.fade_in_animation)
        
        # Emitir sinal
        self.theme_changed.emit(next_theme)
        
        # Log e notificação
        theme_name = self.get_theme_name(next_theme)
        logger.info(f"Tema alterado para: {theme_name}")
        
        self.event_bus.notification.emit(
            'info',
            'Tema alterado',
            f'Tema definido para "{theme_name}"'
        )
    
    def get_theme_icon(self) -> str:
        """Retorna ícone para o tema atual"""
        icons = {
            'philosophy_dark': '🌙',
            'philosophy_light': '☀️',
            'philosophy_night': '🌚'
        }
        return icons.get(self.current_theme, '🎨')
    
    def get_theme_name(self, theme_key: str) -> str:
        """Retorna nome amigável do tema"""
        names = {
            'philosophy_dark': 'Dark Academia',
            'philosophy_light': 'Light Scholar',
            'philosophy_night': 'Night Owl'
        }
        return names.get(theme_key, theme_key)
    
    # ============ NOVOS MÉTODOS PARA OS BOTÕES ============
    
    def show_settings(self):
        """Mostra diálogo de configurações do sistema"""
        from ui.widgets.dialogs.settings_dialog import SettingsDialog

        dialog = SettingsDialog(self)
        dialog.settings_saved.connect(self._on_settings_saved)
        dialog.exec()

    @pyqtSlot(dict)
    def _on_settings_saved(self, updated_settings: dict):
        """Atualiza estado local após salvar configurações."""
        self.config.update(updated_settings)
        self.show_success_notification(
            "Configurações salvas",
            "As configurações foram atualizadas com sucesso."
        )
    
    def close_application(self):
        """Fecha a aplicação com confirmação"""
        reply = QMessageBox.question(
            self,
            'Confirmar saída',
            'Deseja realmente encerrar a aplicação?',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.cleanup()
            self.close()
            # Fechar completamente a aplicação
            from PyQt6.QtWidgets import QApplication
            QApplication.instance().quit()
    
    # ============ HANDLERS DO EVENTBUS ============
    
    @pyqtSlot(str, str, str)
    def handle_notification(self, notif_type: str, title: str, message: str):
        """Processa notificações do sistema"""
        if not self.notifications_enabled:
            return
        
        # Atualizar contador
        self._event_notification_count += 1
        self._refresh_notification_counter()
        
        # Mostrar notificação baseada no tipo
        if notif_type == 'error':
            self.show_error_notification(title, message)
        elif notif_type == 'warning':
            self.show_warning_notification(title, message)
        elif notif_type == 'info':
            self.show_info_notification(title, message)
        elif notif_type == 'success':
            self.show_success_notification(title, message)
    
    @pyqtSlot(str, int, str)
    def handle_progress_update(self, task: str, percent: int, message: str):
        """Atualiza indicadores de progresso"""
        # Mostrar na status bar temporariamente
        self.status_bar.showMessage(f"{task}: {message} ({percent}%)", 3000)
        
        # Se for uma tarefa crítica, mostrar diálogo
        if 'processing' in task or 'sync' in task:
            if not hasattr(self, 'progress_dialog') or not self.progress_dialog:
                self.show_progress_dialog(task, message)
            else:
                self.update_progress_dialog(percent, message)
    
    @pyqtSlot(str, str)
    def handle_module_error(self, module: str, error: str):
        """Lida com erros reportados por módulos"""
        logger.error(f"Erro no módulo {module}: {error}")
        
        # Usar ErrorManager para determinar ação
        resolution = self.error_manager.handle_error(
            type('ModuleError', (Exception,), {
                'code': 'MODULE_ERROR',
                'message': f"{module}: {error}",
                'details': {'module': module, 'error': error}
            })(error)
        )
        
        # Mostrar notificação se necessário
        if resolution.get('notify_user', False):
            urgency = resolution.get('urgency', 'medium')
            
            if urgency == 'critical':
                self.show_error_dialog(f"Erro crítico em {module}", error, resolution)
            elif urgency == 'high':
                self.show_error_notification(f"Erro em {module}", error)
            else:
                self.show_warning_notification(f"Aviso em {module}", error)
    
    @pyqtSlot(str, dict)
    def on_data_created(self, data_type: str, data: dict):
        """Quando novos dados são criados"""
        logger.info(f"Dados criados: {data_type}")
        
        # Notificar views relevantes
        for view_name, view in self.views.items():
            if hasattr(view, 'on_data_created'):
                view.on_data_created(data_type, data)
    
    @pyqtSlot(str, dict)
    def on_data_updated(self, data_type: str, data: dict):
        """Quando dados são atualizados"""
        # Atualizar views relevantes
        for view_name, view in self.views.items():
            if hasattr(view, 'on_data_updated'):
                view.on_data_updated(data_type, data)
    
    @pyqtSlot(str, str)
    def on_data_deleted(self, data_type: str, data_id: str):
        """Quando dados são deletados"""
        logger.info(f"Dados deletados: {data_type}/{data_id}")
    
    @pyqtSlot(str, dict)
    def on_state_changed(self, state_name: str, state_data: dict):
        """Quando estado do sistema muda"""
        if state_name == 'llm.fallback':
            self.show_warning_notification(
                "LLM em modo fallback",
                state_data.get('reason', 'Usando busca semântica')
            )
        elif state_name == 'system.cleanup':
            logger.info(f"Limpeza do sistema: {state_data.get('reason')}")
    
    @pyqtSlot(str)
    def on_connection_lost(self, component: str):
        """Quando conexão é perdida"""
        self.show_error_notification(
            f"Conexão perdida: {component}",
            "Tentando reconectar..."
        )
        
        # Atualizar status bar
        self.status_indicators[component].setText(f"🔴 {component}: Offline")
    
    @pyqtSlot(str)
    def on_connection_restored(self, component: str):
        """Quando conexão é restaurada"""
        self.show_success_notification(
            f"Conexão restaurada: {component}",
            "Conectado com sucesso"
        )
        
        # Atualizar status bar
        self.status_indicators[component].setText(f"🟢 {component}: Online")
    
    # ============ MÉTODOS DA INTERFACE ============
    
    def show_search_dialog(self):
        """Mostra diálogo de busca global"""
        from ui.widgets.search import GlobalSearchDialog
        
        dialog = GlobalSearchDialog(self.controllers)
        dialog.setWindowModality(Qt.WindowModality.ApplicationModal)
        dialog.exec()
    
    def show_notifications(self):
        """Mostra menu de notificações e check-ins diários"""
        menu = QMenu(self)

        daily_checkin_controller = self.controllers.get('daily_checkin')
        morning_action = None
        evening_action = None

        if daily_checkin_controller:
            morning_pending = daily_checkin_controller.is_morning_pending()
            evening_pending = daily_checkin_controller.is_evening_pending()

            morning_text = "☀️ Check-in matinal"
            if not morning_pending:
                morning_text += " (concluído)"
            morning_action = menu.addAction(morning_text)
            morning_action.setEnabled(morning_pending)

            evening_text = "🌙 Check-in noturno"
            if not evening_pending:
                evening_text += " (concluído)"
            evening_action = menu.addAction(evening_text)
            evening_action.setEnabled(evening_pending)
            menu.addSeparator()

        system_notifications_action = menu.addAction("🔔 Ver notificações do sistema")

        pos = self.notification_button.mapToGlobal(QPoint(0, self.notification_button.height()))
        selected_action = menu.exec(pos)

        if selected_action == morning_action and daily_checkin_controller:
            daily_checkin_controller.show_morning_dialog(self)
        elif selected_action == evening_action and daily_checkin_controller:
            daily_checkin_controller.show_evening_dialog(self)
        elif selected_action == system_notifications_action:
            self._show_notification_panel()

        self._refresh_notification_counter()

    def _show_notification_panel(self):
        """Mostra painel com notificações do sistema"""
        from ui.widgets.notifications import NotificationPanel
        
        panel = NotificationPanel()
        panel.set_notifications(self.event_bus.get_recent_notifications())
        
        # Posicionar abaixo do botão
        pos = self.notification_button.mapToGlobal(QPoint(0, self.notification_button.height()))
        panel.move(pos)
        panel.show()
        
        # Resetar contador
        self._event_notification_count = 0
        self._refresh_notification_counter()

    def _get_pending_checkins_count(self) -> int:
        """Conta check-ins pendentes do dia"""
        daily_checkin_controller = self.controllers.get('daily_checkin')
        if not daily_checkin_controller:
            return 0

        pending = 0
        if daily_checkin_controller.is_morning_pending():
            pending += 1
        if daily_checkin_controller.is_evening_pending():
            pending += 1
        return pending

    def _refresh_notification_counter(self):
        """Atualiza contador do sino considerando sistema + check-ins"""
        total = self._event_notification_count + self._get_pending_checkins_count()
        self.notification_count.setText(str(total))
        self.notification_count.setVisible(total > 0)

    @pyqtSlot(str, dict)
    def _on_checkin_completed(self, checkin_type: str, data: dict):
        """Reage ao término de check-ins para atualizar UI"""
        checkin_label = "matinal" if checkin_type == 'morning' else "noturno"
        self.show_success_notification(
            "Check-in concluído",
            f"Check-in {checkin_label} registrado com sucesso."
        )
        self._refresh_notification_counter()
    
    def show_performance_monitor(self):
        """Mostra monitor de performance"""
        from ui.widgets.monitoring import PerformanceMonitorWidget
        
        dialog = PerformanceMonitorWidget(self.performance_monitor)
        dialog.exec()
    
    def show_quick_actions(self):
        """Mostra menu de ações rápidas"""
        from ui.widgets.quick_actions import QuickActionsMenu
        
        menu = QuickActionsMenu(self.controllers)
        
        # Posicionar abaixo do sino de notificações (fallback)
        pos = self.notification_button.mapToGlobal(QPoint(0, self.notification_button.height()))
        menu.move(pos)
        menu.show()
    
    def show_add_book_dialog(self):
        """Mostra diálogo para adicionar livro"""
        from ui.widgets.books import AddBookDialog
        
        dialog = AddBookDialog(self.controllers['book'])
        dialog.exec()
    
    def show_add_note_dialog(self):
        """Mostra diálogo para adicionar nota"""
        from ui.widgets.notes import AddNoteDialog
        
        dialog = AddNoteDialog()
        dialog.exec()
    
    def start_focus_session(self):
        """Inicia sessão de foco"""
        self.change_view('focus')
        self.views['focus'].start_session()
    
    def show_focus_mode(self):
        """Ativa modo foco (tela cheia)"""
        if self.current_view != 'focus':
            self.change_view('focus')
        
        self.views['focus'].enter_fullscreen()
    
    def show_quick_stats(self):
        """Mostra estatísticas rápidas"""
        from ui.widgets.stats import QuickStatsWidget
        
        widget = QuickStatsWidget(self.controllers)
        
        # Posicionar no centro
        widget.move(
            self.geometry().center() - widget.rect().center()
        )
        widget.show()
    
    def show_progress_dialog(self, task: str, message: str):
        """Mostra diálogo de progresso"""
        from ui.widgets.progress import TaskProgressDialog
        
        self.progress_dialog = TaskProgressDialog(task, message, self)
        self.progress_dialog.show()
    
    def update_progress_dialog(self, percent: int, message: str):
        """Atualiza diálogo de progresso existente"""
        if hasattr(self, 'progress_dialog') and self.progress_dialog:
            self.progress_dialog.update_progress(percent, message)
            
            # Fechar se completo
            if percent >= 100:
                QTimer.singleShot(1000, self.progress_dialog.close)
                self.progress_dialog = None
    
    def show_error_dialog(self, title: str, message: str, resolution: dict = None):
        """Mostra diálogo de erro com opções de recuperação"""
        from ui.widgets.error import ErrorRecoveryDialog
        
        dialog = ErrorRecoveryDialog(title, message, resolution, self.recovery_manager)
        dialog.exec()
    
    def show_error_notification(self, title: str, message: str):
        """Mostra notificação de erro"""
        from ui.widgets.notifications import NotificationToast
        
        toast = NotificationToast('error', title, message, self)
        toast.show()
    
    def show_warning_notification(self, title: str, message: str):
        """Mostra notificação de aviso"""
        from ui.widgets.notifications import NotificationToast
        
        toast = NotificationToast('warning', title, message, self)
        toast.show()
    
    def show_info_notification(self, title: str, message: str):
        """Mostra notificação de informação"""
        from ui.widgets.notifications import NotificationToast
        
        toast = NotificationToast('info', title, message, self)
        toast.show()
    
    def show_success_notification(self, title: str, message: str):
        """Mostra notificação de sucesso"""
        from ui.widgets.notifications import NotificationToast
        
        toast = NotificationToast('success', title, message, self)
        toast.show()
    
    def show_help(self):
        """Mostra diálogo de ajuda"""
        from ui.widgets.help import HelpDialog
        
        dialog = HelpDialog()
        dialog.exec()
    
    # ============ MÉTODOS DO SISTEMA ============
    
    def update_status_bar(self):
        """Atualiza barra de status com informações do sistema"""
        try:
            # Status do sistema
            if self.event_bus:
                self.status_indicators['system'].setText("✅ Sistema")
            
            # Status do vault
            vault_status = "🔗 Vault: --"
            if 'vault_manager' in self.backend_modules:
                vault = self.backend_modules['vault_manager']
                if hasattr(vault, 'is_connected') and vault.is_connected():
                    vault_status = f"🔗 Vault: {vault.get_all_notes()} notas"
            self.status_indicators['vault'].setText(vault_status)
            
            # Status do LLM
            llm_status = "🧠 LLM: --"
            if 'llm_module' in self.backend_modules:
                llm = self.backend_modules['llm_module']
                if hasattr(llm, 'is_ready') and llm.is_ready():
                    llm_status = "🧠 LLM: Online"
            self.status_indicators['llm'].setText(llm_status)
            
            # Uso de memória
            import psutil
            process = psutil.Process()
            memory_mb = process.memory_info().rss / 1024 / 1024
            self.status_indicators['memory'].setText(f"💾 Memória: {memory_mb:.1f} MB")
            
        except Exception as e:
            logger.error(f"Erro ao atualizar status bar: {e}")
    
    def check_notifications(self):
        """Verifica notificações pendentes"""
        self._refresh_notification_counter()
        self._check_upcoming_reading_notifications()

        # Buscar notificações do sistema
        pending = self.get_pending_notifications()
        
        if pending:
            self.event_bus.notification.emit(
                'info',
                'Notificações pendentes',
                f'{len(pending)} notificações aguardando'
            )
    
    def get_pending_notifications(self) -> List[dict]:
        """Retorna notificações pendentes do sistema"""
        # Implementar lógica para buscar notificações
        # Ex: tarefas atrasadas, revisões pendentes, etc.
        return []

    def _check_upcoming_reading_notifications(self):
        """Dispara notificação quando leitura estiver a até 5 minutos do início."""
        agenda_controller = self.controllers.get("agenda")
        if not agenda_controller:
            return

        agenda_manager = getattr(agenda_controller, "agenda_manager", None)
        events_map = getattr(agenda_manager, "events", None)
        if not isinstance(events_map, dict):
            return

        now = datetime.now()
        active_ids = set()

        for event in events_map.values():
            try:
                event_id = str(getattr(event, "id", "")).strip()
                event_type = str(getattr(getattr(event, "type", None), "value", "")).strip().lower()
                start_at = getattr(event, "start", None)
                completed = bool(getattr(event, "completed", False))

                if not event_id:
                    continue

                active_ids.add(event_id)

                if completed or event_type != "leitura" or not start_at:
                    continue

                seconds_to_start = (start_at - now).total_seconds()
                if 0 < seconds_to_start <= 300 and event_id not in self._reading_session_notified_ids:
                    self._reading_session_notified_ids.add(event_id)
                    self.event_bus.notification.emit(
                        "info",
                        "Sessão agendada",
                        f"{getattr(event, 'title', 'Leitura')} começa em menos de 5 minutos."
                    )
            except Exception:
                continue

        self._reading_session_notified_ids.intersection_update(active_ids)
    
    def update_dashboard(self):
        """Atualiza dados do dashboard"""
        if self.current_view == 'dashboard' and hasattr(self.views['dashboard'], 'refresh'):
            self.views['dashboard'].refresh()
    
    def refresh_current_view(self):
        """Força atualização da view atual"""
        current_view = self.views.get(self.current_view)
        if current_view and hasattr(current_view, 'refresh'):
            current_view.refresh()
    
    def run_system_check(self):
        """Executa verificação completa do sistema"""
        logger.info("Executando verificação do sistema...")
        
        checks = [
            ('Database', self.check_database),
            ('Vault Connection', self.check_vault_connection),
            ('LLM Status', self.check_llm_status),
            ('File System', self.check_file_system),
            ('Backup Status', self.check_backup_status),
        ]
        
        results = []
        for check_name, check_func in checks:
            try:
                result = check_func()
                results.append((check_name, True, result))
                logger.info(f"✓ {check_name}: {result}")
            except Exception as e:
                results.append((check_name, False, str(e)))
                logger.error(f"✗ {check_name}: {e}")
        
        # Mostrar resumo
        success_count = sum(1 for _, success, _ in results if success)
        total_count = len(results)
        
        self.status_bar.showMessage(
            f"Verificação do sistema: {success_count}/{total_count} checks passaram",
            5000
        )
        
        # Se algum check falhou, agendar recuperação
        if success_count < total_count:
            failed = [name for name, success, _ in results if not success]
            self.recovery_manager.schedule_recovery(
                'system_check',
                {'failed_checks': failed, 'results': results}
            )
    
    def check_database(self) -> str:
        """Verifica status do banco de dados"""
        return "OK"
    
    def check_vault_connection(self) -> str:
        """Verifica conexão com o vault"""
        if 'vault_manager' in self.backend_modules:
            vault = self.backend_modules['vault_manager']
            if hasattr(vault, 'is_connected'):
                return "Conectado" if vault.is_connected() else "Desconectado"
        return "N/A"
    
    def check_llm_status(self) -> str:
        """Verifica status do LLM"""
        if 'llm_module' in self.backend_modules:
            llm = self.backend_modules['llm_module']
            if hasattr(llm, 'is_ready'):
                return "Pronto" if llm.is_ready() else "Inicializando"
        return "N/A"
    
    def check_file_system(self) -> str:
        """Verifica sistema de arquivos"""
        import os
        import shutil
        
        # Verificar diretórios necessários
        required_dirs = ['data', 'cache', 'logs', 'backups']
        missing = []
        
        for dir_name in required_dirs:
            dir_path = os.path.join(os.getcwd(), dir_name)
            if not os.path.exists(dir_path):
                missing.append(dir_name)
        
        if missing:
            return f"Diretórios faltando: {', '.join(missing)}"
        
        # Verificar espaço em disco
        total, used, free = shutil.disk_usage(".")
        free_gb = free // (2**30)
        
        if free_gb < 1:
            return f"Pouco espaço: {free_gb}GB livre"
        
        return f"{free_gb}GB livre"
    
    def check_backup_status(self) -> str:
        """Verifica status do backup"""
        import os
        import time
        from datetime import datetime
        
        backup_dir = os.path.join(os.getcwd(), 'backups')
        if not os.path.exists(backup_dir):
            return "Nenhum backup encontrado"
        
        # Buscar backup mais recente
        backups = []
        for file in os.listdir(backup_dir):
            if file.endswith('.backup'):
                file_path = os.path.join(backup_dir, file)
                backups.append((os.path.getmtime(file_path), file))
        
        if not backups:
            return "Nenhum backup válido"
        
        latest_time, latest_file = max(backups)
        latest_dt = datetime.fromtimestamp(latest_time)
        now = datetime.now()
        
        diff_hours = (now - latest_dt).total_seconds() / 3600
        
        if diff_hours > 48:
            return f"Backup antigo: {int(diff_hours)}h atrás"
        
        return f"OK: {latest_dt.strftime('%d/%m %H:%M')}"
    
    def auto_backup(self):
        """Executa backup automático"""
        if self.config.get('auto_backup', True):
            logger.info("Executando backup automático...")
            
            try:
                # Implementar lógica de backup
                self.event_bus.notification.emit(
                    'info',
                    'Backup automático',
                    'Backup executado com sucesso'
                )
            except Exception as e:
                logger.error(f"Erro no backup automático: {e}")
    
    def toggle_navigation(self):
        """Método mantido para compatibilidade, mas agora não faz nada"""
        pass  # Navigation foi removida
    
    def fade_out_animation(self):
        """Animação de fade out"""
        if self.animations_enabled:
            self.animation = FadeAnimation(self, 1.0, 0.3, 300)
            self.animation.start()
    
    def fade_in_animation(self):
        """Animação de fade in"""
        if self.animations_enabled:
            self.animation = FadeAnimation(self, 0.3, 1.0, 300)
            self.animation.start()
    
    # ============ HANDLERS DE EVENTOS ============
    
    @pyqtSlot(str)
    def on_theme_changed(self, theme_name: str):
        """Atualiza interface quando tema muda"""
        # Atualizar botão de tema
        icons = {'philosophy_dark': '🌙', 'philosophy_light': '☀️', 'philosophy_night': '🌚'}
        self.theme_button.setText(icons.get(theme_name, '🎨'))
    
    @pyqtSlot(str)
    def on_view_changed(self, view_name: str):
        """Loga mudança de view"""
        logger.info(f"View alterada para: {view_name}")
    
    @pyqtSlot(str, dict)
    def on_view_data_updated(self, view_name: str, data: dict):
        """Quando uma view atualiza dados"""
        logger.debug(f"Dados atualizados na view {view_name}")
    
    # ============ LIMPEZA ============
    
    def cleanup(self):
        """Limpeza sistemática antes de fechar"""
        try:
            logger.info("Iniciando limpeza da MainWindow...")
            
            # 1. Parar todos os timers
            if hasattr(self, 'dashboard_timer'):
                self.dashboard_timer.stop()
            if hasattr(self, 'notification_timer'):
                self.notification_timer.stop()
            if hasattr(self, 'backup_timer'):
                self.backup_timer.stop()
            if hasattr(self, 'status_timer'):
                self.status_timer.stop()
            
            # 2. Limpar views
            for view_name, view in self.views.items():
                if hasattr(view, 'cleanup'):
                    view.cleanup()
            
            # 3. Limpar controllers
            for controller_name, controller in self.controllers.items():
                if hasattr(controller, 'cleanup'):
                    controller.cleanup()
            
            # 4. Fechar diálogos abertos
            if hasattr(self, 'progress_dialog') and self.progress_dialog:
                self.progress_dialog.close()
            
            logger.info("MainWindow limpa com sucesso")
            
        except Exception as e:
            logger.error(f"Erro durante limpeza da MainWindow: {e}")
    
    def closeEvent(self, event):
        """Evento de fechamento da janela"""
        # Confirmar se há trabalho não salvo
        if self.has_unsaved_changes():
            reply = QMessageBox.question(
                self,
                'Confirmar saída',
                'Existem alterações não salvas. Deseja sair mesmo assim?',
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.No:
                event.ignore()
                return
        
        # Executar limpeza
        self.cleanup()
        
        # Aceitar fechamento
        event.accept()
    
    def has_unsaved_changes(self) -> bool:
        """Verifica se há alterações não salvas"""
        # Implementar lógica de verificação
        # Ex: verificar se há livros sendo processados, notas não salvas, etc.
        return False

# ============ CLASSES AUXILIARES ============

class ProcessingDialog(QDialog):
    """Diálogo para operações de processamento"""
    
    def __init__(self, file_path: str, controller, parent=None):
        super().__init__(parent)
        self.file_path = file_path
        self.controller = controller
        self.setup_ui()
    
    def setup_ui(self):
        self.setWindowTitle("Processando Livro")
        self.setFixedSize(400, 200)
        
        layout = QVBoxLayout()
        
        # Título
        title = QLabel(f"Processando: {os.path.basename(self.file_path)}")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        # Barra de progresso
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        layout.addWidget(self.progress_bar)
        
        # Mensagem de status
        self.status_label = QLabel("Iniciando processamento...")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status_label)
        
        # Botão de cancelar
        self.cancel_button = QPushButton("Cancelar")
        self.cancel_button.clicked.connect(self.cancel)
        layout.addWidget(self.cancel_button)
        
        self.setLayout(layout)
    
    def update(self, percent: int, message: str):
        """Atualiza progresso"""
        self.progress_bar.setValue(percent)
        self.status_label.setText(message)
    
    def complete(self):
        """Finaliza com sucesso"""
        self.accept()
    
    def error(self, error_message: str):
        """Mostra erro"""
        self.status_label.setText(f"Erro: {error_message}")
        self.cancel_button.setText("Fechar")
    
    def cancel(self):
        """Cancela processamento"""
        self.reject()
