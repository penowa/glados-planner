# ui/widgets/cards/glados_card.py
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                            QPushButton, QTextEdit, QFrame, QProgressBar,
                            QComboBox, QSlider, QMenu)
from PyQt6.QtCore import Qt, pyqtSignal, pyqtSlot, QTimer, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import (QPainter, QColor, QLinearGradient, QBrush, QPen, 
                        QFont, QTextCursor, QAction)

from .base_card import PhilosophyCard

class GladosCard(PhilosophyCard):
    """Card para o assistente GLaDOS com integração completa do backend"""
    
    # Sinais internos (somente para UI)
    ui_message_sent = pyqtSignal(str)      # Mensagem enviada pelo usuário
    ui_action_selected = pyqtSignal(str)   # Ação selecionada nos botões
    
    def __init__(self, controller=None, parent=None):
        super().__init__(parent)
        
        # Controladora do backend (import condicional para evitar circular)
        try:
            from controllers.glados_controller import GladosController, GladosUIAdapter
            self.controller = controller or GladosController()
            self.adapter = GladosUIAdapter(self.controller)
        except ImportError:
            self.controller = None
            self.adapter = None
        
        # Estado da UI
        self.is_processing = False
        self.last_query = ""
        self.auto_search_enabled = True
        
        # Inicializar atributos de widget para evitar AttributeError
        self.avatar_label = None
        self.progress_bar = None
        self.status_label = None
        self.chat_widget = None
        self.input_field = None
        self.send_button = None
        self.clear_button = None
        self.mode_combo = None
        self.intensity_slider = None
        self.sarcasm_button = None
        self.action_buttons = {}
        
        # Configurar UI primeiro
        self.setup_ui()
        
        # Configurar animações depois que os widgets existem
        self.setup_animations()
        
        # Configurar conexões
        self.setup_controller_connections()
        
        # Carregar estado inicial
        self.load_initial_state()
        
    def setup_ui(self):
        """Configurar interface do card GLaDOS"""
        self.setMinimumHeight(400)
        self.setMaximumWidth(800)
        
        # Layout principal
        main_layout = QVBoxLayout()
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(15, 15, 15, 15)
        
        # Cabeçalho com controles
        self.setup_glados_header(main_layout)
        
        # Barra de status e progresso
        self.setup_status_bar(main_layout)
        
        # Área de chat
        self.setup_chat_area(main_layout)
        
        # Painel de controle rápido
        self.setup_quick_controls(main_layout)
        
        # Campo de entrada
        self.setup_input_area(main_layout)
        
        # Adicionar ao layout do card
        self.content_layout.addLayout(main_layout)
        
        # Aplicar estilos
        self.apply_styles()
        
    def setup_glados_header(self, parent_layout):
        """Configurar cabeçalho com controles do GLaDOS"""
        header_widget = QWidget()
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(15)
        
        # Avatar GLaDOS
        self.avatar_label = QLabel("🤖")
        self.avatar_label.setObjectName("glados_avatar")
        self.avatar_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.avatar_label.setFixedSize(40, 40)
        
        # Informações e título
        info_widget = QWidget()
        info_layout = QVBoxLayout(info_widget)
        info_layout.setSpacing(2)
        
        self.name_label = QLabel("GLaDOS Assistant v2.0")
        self.name_label.setObjectName("glados_name")
        font = QFont()
        font.setBold(True)
        font.setPointSize(12)
        self.name_label.setFont(font)
        
        self.mode_label = QLabel("Modo: Acadêmico")
        self.mode_label.setObjectName("glados_mode")
        
        info_layout.addWidget(self.name_label)
        info_layout.addWidget(self.mode_label)
        
        # Controles de personalidade
        controls_widget = QWidget()
        controls_layout = QHBoxLayout(controls_widget)
        controls_layout.setSpacing(10)
        
        # Seletor de modo
        self.mode_combo = QComboBox()
        self.mode_combo.setObjectName("glados_mode_selector")
        self.mode_combo.addItems(["Acadêmico", "Criativo", "Técnico", "Casual"])
        
        # Controle de intensidade
        intensity_label = QLabel("Intensidade:")
        self.intensity_slider = QSlider(Qt.Orientation.Horizontal)
        self.intensity_slider.setRange(0, 100)
        self.intensity_slider.setValue(70)
        self.intensity_slider.setFixedWidth(80)
        
        # Botão de sarcasmo
        self.sarcasm_button = QPushButton("Sarcasmo: ON")
        self.sarcasm_button.setCheckable(True)
        self.sarcasm_button.setChecked(True)
        self.sarcasm_button.setFixedWidth(100)
        
        controls_layout.addWidget(intensity_label)
        controls_layout.addWidget(self.intensity_slider)
        controls_layout.addWidget(self.mode_combo)
        controls_layout.addWidget(self.sarcasm_button)
        controls_layout.addStretch()
        
        # Menu de sistema
        self.setup_system_menu(header_layout)
        
        header_layout.addWidget(self.avatar_label)
        header_layout.addWidget(info_widget)
        header_layout.addWidget(controls_widget, 1)
        
        parent_layout.addWidget(header_widget)
        
    def setup_system_menu(self, header_layout):
        """Configurar menu do sistema"""
        menu_button = QPushButton("⚙️")
        menu_button.setFixedSize(30, 30)
        menu_button.setCursor(Qt.CursorShape.PointingHandCursor)
        
        menu = QMenu(self)
        
        # Ações do sistema
        actions = [
            ("🧠", "Analisar Cérebro", self.on_analyze_brain),
            ("🔍", "Buscar no Vault", self.on_search_vault),
            ("💾", "Salvar Estado", self.on_save_state),
            ("🧹", "Limpar Cache", self.on_clear_cache),
            ("📊", "Status do Sistema", self.on_show_status),
            ("❓", "Ajuda", self.on_show_help)
        ]
        
        for icon, text, slot in actions:
            action = menu.addAction(f"{icon} {text}")
            action.triggered.connect(slot)
        
        menu_button.setMenu(menu)
        header_layout.addWidget(menu_button)
        
    def setup_status_bar(self, parent_layout):
        """Configurar barra de status e progresso"""
        status_widget = QWidget()
        status_layout = QHBoxLayout(status_widget)
        status_layout.setContentsMargins(0, 5, 0, 5)
        status_layout.setSpacing(10)
        
        # Barra de progresso
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setFixedHeight(6)
        self.progress_bar.setTextVisible(False)
        
        # Label de status
        self.status_label = QLabel("Pronto")
        self.status_label.setObjectName("glados_status_label")
        
        # Stats
        self.stats_label = QLabel("Cache: 0 hits")
        self.stats_label.setObjectName("glados_stats")
        
        status_layout.addWidget(self.progress_bar, 1)
        status_layout.addWidget(self.status_label)
        status_layout.addWidget(self.stats_label)
        
        parent_layout.addWidget(status_widget)
        
    def setup_chat_area(self, parent_layout):
        """Configurar área de chat"""
        self.chat_widget = QTextEdit()
        self.chat_widget.setObjectName("glados_chat")
        self.chat_widget.setReadOnly(True)
        self.chat_widget.setMinimumHeight(200)
        self.chat_widget.setMaximumHeight(300)
        
        parent_layout.addWidget(self.chat_widget, 1)
        
    def setup_quick_controls(self, parent_layout):
        """Configurar controles rápidos"""
        controls_widget = QWidget()
        controls_layout = QHBoxLayout(controls_widget)
        controls_layout.setSpacing(8)
        
        # Botões de ação rápida
        actions = [
            ("💭", "Pensar", "think", "Refletir sobre o último tópico"),
            ("📚", "Contexto", "context", "Obter contexto semântico"),
            ("🎯", "Focar", "focus", "Focar no tópico atual"),
            ("🔗", "Relacionar", "relate", "Encontrar relações"),
            ("📝", "Resumir", "summarize", "Resumir conversa"),
            ("🔄", "Reformular", "rephrase", "Reformular última resposta")
        ]
        
        for icon, text, action_id, tooltip in actions:
            button = QPushButton(f"{icon} {text}")
            button.setObjectName("glados_action_button")
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.setToolTip(tooltip)
            button.clicked.connect(lambda checked, a=action_id: self.on_quick_action(a))
            controls_layout.addWidget(button)
            self.action_buttons[action_id] = button
            
        parent_layout.addWidget(controls_widget)
        
    def setup_input_area(self, parent_layout):
        """Configurar área de entrada"""
        input_widget = QWidget()
        input_layout = QHBoxLayout(input_widget)
        input_layout.setSpacing(8)
        
        # Campo de entrada
        self.input_field = QTextEdit()
        self.input_field.setObjectName("glados_input")
        self.input_field.setMaximumHeight(70)
        self.input_field.setPlaceholderText("Pergunte a GLaDOS...")
        
        # Botões de envio
        button_widget = QWidget()
        button_layout = QVBoxLayout(button_widget)
        button_layout.setSpacing(5)
        button_layout.setContentsMargins(0, 0, 0, 0)
        
        self.send_button = QPushButton("Enviar")
        self.send_button.setObjectName("primary_button")
        self.send_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.send_button.setFixedWidth(80)
        
        self.clear_button = QPushButton("Limpar")
        self.clear_button.setObjectName("secondary_button")
        self.clear_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.clear_button.setFixedWidth(80)
        
        button_layout.addWidget(self.send_button)
        button_layout.addWidget(self.clear_button)
        
        input_layout.addWidget(self.input_field, 1)
        input_layout.addWidget(button_widget)
        
        parent_layout.addWidget(input_widget)
        
    def setup_animations(self):
        """Configurar animações do GLaDOS"""
        # Verificar se avatar_label existe (deve existir após setup_ui)
        if not hasattr(self, 'avatar_label') or self.avatar_label is None:
            return
            
        # Animação do avatar
        self.avatar_animation = QPropertyAnimation(self.avatar_label, b"geometry")
        self.avatar_animation.setDuration(300)
        self.avatar_animation.setEasingCurve(QEasingCurve.Type.InOutQuad)
        
        # Timer para animação periódica
        self.animation_timer = QTimer()
        self.animation_timer.timeout.connect(self.animate_avatar)
        self.animation_timer.start(5000)
        
    def apply_styles(self):
        """Aplicar estilos CSS"""
        self.setStyleSheet("""
            #glados_chat {
                background-color: #1a1a1a;
                border: 1px solid #333;
                border-radius: 5px;
                color: #e0e0e0;
                font-family: 'Courier New', monospace;
                font-size: 13px;
                padding: 8px;
            }
            #glados_input {
                background-color: #2a2a2a;
                border: 1px solid #444;
                border-radius: 5px;
                color: #ffffff;
                font-size: 14px;
                padding: 8px;
            }
            #glados_action_button {
                background-color: #333;
                border: 1px solid #555;
                border-radius: 4px;
                color: #ff9900;
                padding: 6px 12px;
                font-size: 12px;
            }
            #glados_action_button:hover {
                background-color: #444;
                border-color: #ff9900;
            }
            #glados_status_label {
                color: #888;
                font-size: 11px;
                font-style: italic;
            }
            #glados_mode_selector {
                background-color: #2a2a2a;
                color: #fff;
                border: 1px solid #444;
                border-radius: 4px;
                padding: 4px;
            }
        """)
        
    def setup_controller_connections(self):
        """Conectar sinais da controladora"""
        # Conexões UI básicas
        self.send_button.clicked.connect(self.send_message)
        self.clear_button.clicked.connect(self.clear_chat)
        self.mode_combo.currentTextChanged.connect(self.on_mode_changed)
        self.intensity_slider.valueChanged.connect(self.on_intensity_changed)
        self.sarcasm_button.toggled.connect(self.on_sarcasm_toggled)
        
        # Conexões do controller (se existir)
        if self.controller:
            try:
                if hasattr(self.controller, 'response_ready'):
                    self.controller.response_ready.connect(self.handle_backend_response)
                if hasattr(self.controller, 'processing_started'):
                    self.controller.processing_started.connect(self.handle_processing_started)
                if hasattr(self.controller, 'processing_completed'):
                    self.controller.processing_completed.connect(self.handle_processing_completed)
                if hasattr(self.controller, 'error_occurred'):
                    self.controller.error_occurred.connect(self.handle_error)
            except Exception as e:
                print(f"Erro ao conectar sinais do controller: {e}")
        
    # ============== SLOTS E HANDLERS ==============
    
    @pyqtSlot()
    def send_message(self):
        """Enviar mensagem"""
        message = self.input_field.toPlainText().strip()
        if not message:
            return
            
        self.last_query = message
        self.add_message_to_chat(message, "user")
        self.input_field.clear()
        
        # Simular resposta se não houver controller
        if not self.controller:
            QTimer.singleShot(1000, lambda: self.add_message_to_chat(
                f"Você perguntou: '{message}'. GLaDOS está processando...", 
                "assistant"
            ))
        else:
            # Usar controller real
            self.controller.ask_glados(message, self.auto_search_enabled, "Helio")
            
    @pyqtSlot(str)
    def on_quick_action(self, action_id):
        """Processar ação rápida"""
        self.ui_action_selected.emit(action_id)
        self.add_message_to_chat(f"Ação: {action_id}", "system")
        
    @pyqtSlot(str)
    def on_mode_changed(self, mode):
        """Mudar modo de operação"""
        self.mode_label.setText(f"Modo: {mode}")
        
    @pyqtSlot(int)
    def on_intensity_changed(self, value):
        """Atualizar intensidade da personalidade"""
        pass  # Implementar se necessário
        
    @pyqtSlot(bool)
    def on_sarcasm_toggled(self, checked):
        """Atualizar estado do sarcasmo"""
        self.sarcasm_button.setText(f"Sarcasmo: {'ON' if checked else 'OFF'}")
        
    @pyqtSlot()
    def on_analyze_brain(self):
        """Analisar cérebro do GLaDOS"""
        self.add_message_to_chat("Analisando cérebro GLaDOS...", "system")
        
    @pyqtSlot()
    def on_search_vault(self):
        """Buscar no vault"""
        self.add_message_to_chat("Buscando no vault...", "system")
        
    @pyqtSlot()
    def on_save_state(self):
        """Salvar estado"""
        self.add_message_to_chat("Estado salvo", "system")
        
    @pyqtSlot()
    def on_clear_cache(self):
        """Limpar cache"""
        self.add_message_to_chat("Cache limpo", "system")
        
    @pyqtSlot()
    def on_show_status(self):
        """Mostrar status do sistema"""
        status = "📊 Status do Sistema:\n• GLaDOS: Online\n• Modo: Funcional"
        self.add_message_to_chat(status, "system")
        
    @pyqtSlot()
    def on_show_help(self):
        """Mostrar ajuda"""
        help_text = """
        🤖 Comandos do GLaDOS:
        
        • Envie mensagens no campo de texto
        • Use os botões de ação rápida
        • Ajuste o modo e intensidade
        • Acesse opções no menu ⚙️
        """
        self.add_message_to_chat(help_text, "system")
        
    # ============== HANDLERS DO CONTROLLER ==============
    
    @pyqtSlot(dict)
    def handle_backend_response(self, response):
        """Processar resposta do backend"""
        text = response.get("text", "Sem resposta")
        self.add_message_to_chat(text, "assistant")
        
    @pyqtSlot(str, str)
    def handle_processing_started(self, task_type, message):
        """Iniciar indicação de processamento"""
        self.is_processing = True
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)
        self.status_label.setText(message)
        
    @pyqtSlot(str)
    def handle_processing_completed(self, task_type):
        """Finalizar processamento"""
        self.is_processing = False
        self.progress_bar.setVisible(False)
        self.status_label.setText("Pronto")
        
    @pyqtSlot(str, str, str)
    def handle_error(self, error_type, error_message, context):
        """Processar erro"""
        self.add_message_to_chat(f"Erro: {error_message}", "error")
        self.handle_processing_completed("error")
        
    # ============== MÉTODOS AUXILIARES ==============
    
    def add_message_to_chat(self, message, sender="user", metadata=None):
        """Adicionar mensagem formatada ao chat"""
        if sender == "user":
            prefix = "<b style='color: #4FC3F7;'>Você:</b> "
            bg_color = "#1a3a5f"
        elif sender == "assistant":
            prefix = "<b style='color: #FF9800;'>GLaDOS:</b> "
            bg_color = "#332211"
        elif sender == "system":
            prefix = "<i style='color: #8BC34A;'>Sistema:</i> "
            bg_color = "#1a331a"
        elif sender == "error":
            prefix = "<b style='color: #F44336;'>Erro:</b> "
            bg_color = "#331a1a"
        else:
            prefix = ""
            bg_color = "#2a2a2a"
            
        html_message = f"""
        <div style="
            margin: 5px 0;
            padding: 8px 12px;
            background-color: {bg_color};
            border-radius: 8px;
        ">
            {prefix}<span style="color: #f0f0f0;">{message}</span>
        </div>
        """
        
        self.chat_widget.append(html_message)
        self.chat_widget.moveCursor(QTextCursor.MoveOperation.End)
        
    def clear_chat(self):
        """Limpar área de chat"""
        self.chat_widget.clear()
        self.add_message_to_chat("Chat limpo", "system")
        
    def load_initial_state(self):
        """Carregar estado inicial"""
        self.add_message_to_chat("GLaDOS inicializado. Como posso ajudar?", "assistant")
        
    def animate_avatar(self):
        """Animar avatar do GLaDOS"""
        if not self.is_processing and self.avatar_label:
            current_geom = self.avatar_label.geometry()
            self.avatar_animation.stop()
            self.avatar_animation.setStartValue(current_geom)
            self.avatar_animation.setEndValue(current_geom.adjusted(0, -3, 0, -3))
            self.avatar_animation.start()
            
            QTimer.singleShot(300, self.reverse_avatar_animation)
            
    def reverse_avatar_animation(self):
        """Reverter animação do avatar"""
        if not self.is_processing and self.avatar_label:
            current_geom = self.avatar_label.geometry()
            self.avatar_animation.setStartValue(current_geom)
            self.avatar_animation.setEndValue(current_geom.adjusted(0, 3, 0, 3))
            self.avatar_animation.start()
            
    def closeEvent(self, event):
        """Lidar com fechamento"""
        if hasattr(self, 'animation_timer'):
            self.animation_timer.stop()
        super().closeEvent(event)