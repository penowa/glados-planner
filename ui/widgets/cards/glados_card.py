# ui/widgets/cards/glados_card.py
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                            QPushButton, QTextEdit, QFrame, QProgressBar,
                            QComboBox, QMenu)
from PyQt6.QtCore import Qt, pyqtSignal, pyqtSlot, QTimer, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import (QPainter, QColor, QLinearGradient, QBrush, QPen, 
                        QFont, QTextCursor, QAction)
import re

from .base_card import PhilosophyCard

class GladosCard(PhilosophyCard):
    """Card para o assistente GLaDOS com integração completa do backend"""
    
    # Sinais internos (somente para UI)
    ui_message_sent = pyqtSignal(str)      # Mensagem enviada pelo usuário
    ui_action_selected = pyqtSignal(str)   # Ação selecionada nos botões
    context_action_requested = pyqtSignal(str, dict)  # (ação, payload_contexto)
    
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
        self.current_context_payload = {}
        self.current_notes_context_text = ""
        
        # Inicializar atributos de widget para evitar AttributeError
        self.avatar_label = None
        self.progress_bar = None
        self.status_label = None
        self.chat_widget = None
        self.input_field = None
        self.send_button = None
        self.preset_combo = None
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
        
        self.name_label = QLabel("GLaDOS Assistant v3.0")
        self.name_label.setObjectName("glados_name")
        font = QFont()
        font.setBold(True)
        font.setPointSize(12)
        self.name_label.setFont(font)
        
        self.mode_label = QLabel("Preset: Balanceado")
        self.mode_label.setObjectName("glados_mode")
        
        info_layout.addWidget(self.name_label)
        info_layout.addWidget(self.mode_label)
        
        # Controles de geração (presets)
        controls_widget = QWidget()
        controls_layout = QHBoxLayout(controls_widget)
        controls_layout.setSpacing(10)
        
        preset_label = QLabel("Preset:")
        self.preset_combo = QComboBox()
        self.preset_combo.setObjectName("glados_mode_selector")
        self.preset_combo.addItems(["Rápido", "Balanceado", "Qualidade"])
        self.preset_combo.setCurrentText("Balanceado")
        self.preset_combo.setFixedWidth(140)

        controls_layout.addWidget(preset_label)
        controls_layout.addWidget(self.preset_combo)
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
        
        # Botões de ação contextual (substitui ações antigas)
        actions = [
            ("💬", "Chat Contextual", "context_chat", "Conversar usando as notas selecionadas"),
            ("🧠", "Pesquisa Semântica", "semantic_search", "Explorar relações semânticas das notas"),
            ("📝", "Texto por Template", "template_text", "Gerar texto baseado em templates do backend"),
        ]
        
        for icon, text, action_id, tooltip in actions:
            button = QPushButton(f"{icon} {text}")
            button.setObjectName("glados_action_button")
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.setToolTip(tooltip)
            button.clicked.connect(lambda checked, a=action_id: self.on_quick_action(a))
            button.setEnabled(False)
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
        
        # Botão de envio
        self.send_button = QPushButton("Enviar")
        self.send_button.setObjectName("primary_button")
        self.send_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.send_button.setFixedWidth(80)
        self.send_button.setFixedHeight(70)
        
        input_layout.addWidget(self.input_field, 1)
        input_layout.addWidget(self.send_button, 0, Qt.AlignmentFlag.AlignTop)
        
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
        self.preset_combo.currentTextChanged.connect(self.on_preset_changed)
        
        # Conexões do controller (se existir)
        if self.controller:
            try:
                if hasattr(self.controller, 'response_ready'):
                    self.controller.response_ready.connect(self.handle_backend_response)
                if hasattr(self.controller, 'vault_results_ready'):
                    self.controller.vault_results_ready.connect(self.handle_vault_results)
                if hasattr(self.controller, 'semantic_context_ready'):
                    self.controller.semantic_context_ready.connect(self.handle_semantic_context)
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
            message_with_context = self._compose_message_with_notes_context(message)
            use_semantic = self.auto_search_enabled and not bool(self.current_context_payload.get("notes"))
            self.controller.ask_glados(message_with_context, use_semantic, "Helio")
            
    @pyqtSlot(str)
    def on_quick_action(self, action_id):
        """Processar ação rápida"""
        self.ui_action_selected.emit(action_id)
        self.execute_context_action(action_id)
        
    @pyqtSlot(str)
    def on_preset_changed(self, preset_label: str):
        """Aplica preset de geração no backend."""
        self.mode_label.setText(f"Preset: {preset_label}")
        if not self.controller:
            return

        if hasattr(self.controller, "set_generation_preset"):
            result = self.controller.set_generation_preset(preset_label)
            self.status_label.setText(f"Preset: {result.get('preset', preset_label)}")
        
    @pyqtSlot()
    def on_analyze_brain(self):
        """Analisar cérebro do GLaDOS"""
        self.add_message_to_chat("Analisando cérebro GLaDOS...", "system")
        
    @pyqtSlot()
    def on_search_vault(self):
        """Buscar no vault"""
        query = self.input_field.toPlainText().strip() or self.last_query
        if not query:
            self.add_message_to_chat("Digite algo para buscar no vault.", "system")
            return

        self.add_message_to_chat(f"Buscando no vault por '{query}'...", "system")
        if self.controller and hasattr(self.controller, "search_vault"):
            self.controller.search_vault(query, limit=5, use_semantic=True)
        
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

    @pyqtSlot(dict)
    def handle_vault_results(self, results):
        """Mostra resumo dos resultados de busca no vault."""
        total = results.get("total", 0)
        query = results.get("query", "")
        method = results.get("method", "textual")
        self.add_message_to_chat(
            f"Busca concluída ({method}): {total} nota(s) para '{query}'.",
            "system",
        )

    @pyqtSlot(dict)
    def handle_semantic_context(self, context_data):
        """Mostra status de contexto semântico."""
        query = context_data.get("query", "")
        analysis = context_data.get("analysis", {})
        notes_analyzed = analysis.get("notes_analyzed", 0)
        self.add_message_to_chat(
            f"Contexto semântico pronto para '{query}' com {notes_analyzed} nota(s).",
            "system",
        )
        
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
        if self.preset_combo:
            self.on_preset_changed(self.preset_combo.currentText())
        self.add_message_to_chat("GLaDOS inicializada. Como posso ajudar?", "assistant")
        self.add_message_to_chat("Selecione notas no card do Vault para habilitar ações contextuais.", "system")

    @pyqtSlot(dict)
    def apply_vault_context(self, payload):
        """Recebe contexto selecionado no card do vault e comenta brevemente."""
        notes = payload.get("notes", [])
        self.current_context_payload = payload
        self.current_notes_context_text = ""

        if not notes:
            self._set_context_actions_enabled(False)
            self.stats_label.setText("Contexto: 0 notas")
            self.add_message_to_chat("Nenhuma nota foi selecionada para contexto.", "system")
            return

        self._set_context_actions_enabled(True)
        self.stats_label.setText(f"Contexto: {len(notes)} nota(s)")
        self.current_notes_context_text = self._build_notes_context_text(notes)

        self.add_message_to_chat(
            f"Contexto recebido do vault ({len(notes)} nota(s)). Vou usar o conteúdo dessas notas nas próximas respostas.",
            "system"
        )

    @pyqtSlot(str)
    def execute_context_action(self, action_id):
        """Executa ação escolhida para o contexto atual."""
        if not self.current_context_payload.get("notes"):
            self.add_message_to_chat("Selecione e confirme notas no card do vault primeiro.", "system")
            return

        self.context_action_requested.emit(action_id, self.current_context_payload)

        notes = self.current_context_payload.get("notes", [])
        context_text = self.current_notes_context_text or self._build_notes_context_text(notes)
        query_base = ", ".join([n.get("title", "") for n in notes[:4]])

        if action_id == "semantic_search":
            self.add_message_to_chat("Iniciando pesquisa semântica com o contexto selecionado...", "system")
            if self.controller and hasattr(self.controller, "get_semantic_context"):
                self.controller.get_semantic_context(context_text[:800], max_notes=min(5, max(1, len(notes))))

        elif action_id == "template_text":
            prompt = (
                "Com base no contexto selecionado do vault, sugira uma estrutura curta "
                "de texto alinhada a templates acadêmicos."
            )
            self.add_message_to_chat("Gerando proposta de texto com base em template...", "system")
            if self.controller and hasattr(self.controller, "ask_glados"):
                self.controller.ask_glados(
                    f"{prompt}\n\nContexto das notas selecionadas:\n{context_text}",
                    False,
                    "Helio"
                )

        else:
            self.add_message_to_chat(
                "Chat contextualizado ativado. Faça sua pergunta e vou considerar o contexto selecionado.",
                "system",
            )

    def _build_notes_context_text(self, notes):
        """Monta contexto textual completo a partir das notas selecionadas."""
        blocks = []

        for note in notes:
            title = note.get("title", "Sem título")
            path = note.get("path", "")
            tags = note.get("tags") or []
            content = (note.get("content") or note.get("content_preview") or "").strip()
            if not content:
                content = "(sem conteúdo disponível)"

            tags_text = ", ".join([str(tag) for tag in tags[:8]]) if tags else "sem tags"
            block = (
                f"Título: {title}\n"
                f"Caminho: {path}\n"
                f"Tags: {tags_text}\n"
                f"Conteúdo completo:\n{content}"
            )

            blocks.append(block)

        if not blocks:
            return "Sem contexto de notas disponível."

        return "\n\n".join(blocks)

    def _compose_message_with_notes_context(self, message: str) -> str:
        """Acopla contexto de notas à mensagem do chat quando disponível."""
        notes = self.current_context_payload.get("notes", [])
        if not notes:
            return message

        context_text = self.current_notes_context_text or self._build_notes_context_text(notes)
        compact_context = self._compress_context_for_query(context_text, message, max_chars=3500)
        return (
            "### INICIO_CONTEXTO_NOTAS ###\n"
            f"{compact_context}\n"
            "### FIM_CONTEXTO_NOTAS ###\n\n"
            "### PERGUNTA_USUARIO ###\n"
            f"{message}"
        )

    def _compress_context_for_query(self, context_text: str, query: str, max_chars: int = 3500) -> str:
        """
        Reduz contexto para caber no modelo fraco:
        1) prioriza blocos com maior sobreposição lexical com a pergunta;
        2) mantém no máximo alguns blocos;
        3) trunca cada bloco para evitar estouro.
        """
        text = (context_text or "").strip()
        if len(text) <= max_chars:
            return text

        blocks = [b.strip() for b in text.split("\n\n") if b.strip()]
        if not blocks:
            return text[:max_chars]

        query_terms = self._tokenize_for_match(query)

        def score_block(block: str) -> int:
            block_terms = self._tokenize_for_match(block)
            overlap = len(query_terms.intersection(block_terms))
            # Peso adicional para título/cabeçalho da nota
            header_bonus = 2 if ("Título:" in block or "CAPÍTULO" in block.upper()) else 0
            return overlap + header_bonus

        ranked = sorted(blocks, key=score_block, reverse=True)

        selected = []
        used = 0
        max_block_chars = 1200
        for block in ranked:
            block_text = block[:max_block_chars].rstrip()
            if used + len(block_text) + 2 > max_chars:
                continue
            selected.append(block_text)
            used += len(block_text) + 2
            if len(selected) >= 4:
                break

        if not selected:
            selected = [text[:max_chars].rstrip()]

        return "\n\n".join(selected)

    def _tokenize_for_match(self, text: str) -> set[str]:
        """Tokenização simples para ranquear relevância lexical."""
        tokens = re.findall(r"[a-zA-ZÀ-ÿ0-9]{4,}", (text or "").lower())
        stop = {
            "sobre", "texto", "capitulo", "capítulo", "conteudo", "conteúdo",
            "pergunta", "usuario", "usuário", "notas", "dessa", "desse",
            "como", "para", "isso", "essa", "este", "aqui"
        }
        return {t for t in tokens if t not in stop}

    def _set_context_actions_enabled(self, enabled: bool):
        """Habilita ou desabilita botões de ação contextual."""
        for button in self.action_buttons.values():
            button.setEnabled(enabled)
        
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
