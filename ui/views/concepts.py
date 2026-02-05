"""
Tela da Rede de Conceitos com navegação
"""
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame, QScrollArea, QLineEdit, QComboBox
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
import logging

logger = logging.getLogger('GLaDOS.UI.ConceptsView')


class ConceptsView(QWidget):
    """Tela da rede de conceitos filosóficos com navegação"""
    
    # Sinais
    concept_selected = pyqtSignal(str)
    connection_added = pyqtSignal(str, str)
    navigate_to = pyqtSignal(str)  # Novo sinal para navegação
    
    def __init__(self, controller=None):
        super().__init__()
        self.controller = controller
        self.current_concept = None
        self.concepts = []
        self.connections = []
        
        self.setup_ui()
        self.setup_connections()
        
        logger.info("ConceptsView inicializada")
    
    def setup_ui(self):
        """Configura interface da rede de conceitos com navegação"""
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(24, 24, 24, 24)
        main_layout.setSpacing(16)
        
        # Barra de cabeçalho com navegação
        header_layout = QHBoxLayout()
        
        # Botão voltar
        back_button = QPushButton("← Voltar")
        back_button.setObjectName("navigation_button")
        back_button.clicked.connect(lambda: self.navigate_to.emit('dashboard'))
        
        # Título
        title = QLabel("🧠 Rede de Conceitos")
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
        
        # Barra de ferramentas
        toolbar_layout = QHBoxLayout()
        
        # Filtros
        self.filter_combo = QComboBox()
        self.filter_combo.addItems(["Todos", "Ética", "Política", "Metafísica", "Epistemologia", "Lógica"])
        self.filter_combo.setFixedWidth(150)
        self.filter_combo.setFont(QFont("FiraCode Nerd Font Propo", 9))
        
        # Busca
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Buscar conceitos...")
        self.search_input.setFixedWidth(200)
        self.search_input.setFont(QFont("FiraCode Nerd Font Propo", 9))
        
        # Botões de ação
        self.new_concept_btn = QPushButton("➕ Novo")
        self.new_concept_btn.setObjectName("concept_action_button")
        self.new_concept_btn.setFont(QFont("FiraCode Nerd Font Propo", 9))
        
        self.new_connection_btn = QPushButton("🔗 Conectar")
        self.new_connection_btn.setObjectName("concept_action_button")
        self.new_connection_btn.setFont(QFont("FiraCode Nerd Font Propo", 9))
        
        # Botão de navegação rápida
        self.dashboard_btn = QPushButton("📊 Dashboard")
        self.dashboard_btn.setObjectName("concept_action_button")
        self.dashboard_btn.setFont(QFont("FiraCode Nerd Font Propo", 9))
        
        toolbar_layout.addWidget(QLabel("Filtrar:"))
        toolbar_layout.addWidget(self.filter_combo)
        toolbar_layout.addWidget(self.search_input)
        toolbar_layout.addStretch()
        toolbar_layout.addWidget(self.new_concept_btn)
        toolbar_layout.addWidget(self.new_connection_btn)
        toolbar_layout.addWidget(self.dashboard_btn)
        
        main_layout.addLayout(toolbar_layout)
        
        # Área de conteúdo dividida
        content_layout = QHBoxLayout()
        content_layout.setSpacing(20)
        
        # Painel esquerdo: Rede visual (placeholder)
        network_frame = QFrame()
        network_frame.setObjectName("concepts_network_frame")
        network_frame.setMinimumSize(600, 400)
        
        network_layout = QVBoxLayout()
        network_layout.addWidget(QLabel("🧠 <b>Rede de Conceitos</b>"))
        network_layout.addWidget(QLabel(
            "Visualização gráfica das conexões entre ideias filosóficas.<br><br>"
            "Cada nó representa um conceito, cada linha uma relação.<br>"
            "Arraste para reorganizar, clique para explorar."
        ))
        network_layout.addStretch()
        network_frame.setLayout(network_layout)
        
        content_layout.addWidget(network_frame, 2)  # 2/3 da largura
        
        # Painel direito: Detalhes do conceito
        details_frame = QFrame()
        details_frame.setObjectName("concept_details_frame")
        details_frame.setFixedWidth(300)
        
        details_layout = QVBoxLayout()
        details_layout.setSpacing(16)
        
        # Título do conceito
        self.concept_title = QLabel("Nenhum conceito selecionado")
        self.concept_title.setObjectName("concept_title")
        self.concept_title.setFont(QFont("FiraCode Nerd Font Propo", 16, QFont.Weight.Medium))
        self.concept_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Informações do conceito
        self.concept_info = QLabel("Selecione um conceito na lista abaixo para ver detalhes")
        self.concept_info.setObjectName("concept_info")
        self.concept_info.setFont(QFont("FiraCode Nerd Font Propo", 9))
        self.concept_info.setWordWrap(True)
        self.concept_info.setStyleSheet("color: #8A94A6; padding: 12px;")
        self.concept_info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Conexões
        connections_label = QLabel("🔗 Conexões:")
        connections_label.setObjectName("section_label")
        connections_label.setFont(QFont("FiraCode Nerd Font Propo", 11, QFont.Weight.Medium))
        
        self.connections_list = QLabel("Nenhuma conexão")
        self.connections_list.setObjectName("connections_list")
        self.connections_list.setFont(QFont("FiraCode Nerd Font Propo", 9))
        self.connections_list.setWordWrap(True)
        self.connections_list.setStyleSheet("color: #8A94A6;")
        
        # Botões de ação
        action_layout = QHBoxLayout()
        action_layout.setSpacing(8)
        
        self.view_notes_btn = QPushButton("📖 Notas")
        self.view_notes_btn.setObjectName("concept_detail_button")
        self.view_notes_btn.setFont(QFont("FiraCode Nerd Font Propo", 9))
        self.view_notes_btn.setEnabled(False)
        
        self.review_btn = QPushButton("🎯 Revisar")
        self.review_btn.setObjectName("concept_detail_button")
        self.review_btn.setFont(QFont("FiraCode Nerd Font Propo", 9))
        self.review_btn.setEnabled(False)
        
        self.explore_btn = QPushButton("🔍 Explorar")
        self.explore_btn.setObjectName("concept_detail_button")
        self.explore_btn.setFont(QFont("FiraCode Nerd Font Propo", 9))
        self.explore_btn.setEnabled(False)
        
        action_layout.addWidget(self.view_notes_btn)
        action_layout.addWidget(self.review_btn)
        action_layout.addWidget(self.explore_btn)
        
        details_layout.addWidget(self.concept_title)
        details_layout.addWidget(self.concept_info)
        details_layout.addStretch()
        details_layout.addWidget(connections_label)
        details_layout.addWidget(self.connections_list)
        details_layout.addStretch()
        details_layout.addLayout(action_layout)
        
        details_frame.setLayout(details_layout)
        content_layout.addWidget(details_frame, 1)  # 1/3 da largura
        
        main_layout.addLayout(content_layout)
        
        # Lista de conceitos
        concepts_label = QLabel("📋 Conceitos Disponíveis:")
        concepts_label.setObjectName("section_label")
        concepts_label.setFont(QFont("FiraCode Nerd Font Propo", 11, QFont.Weight.Medium))
        main_layout.addWidget(concepts_label)
        
        # Scroll area para lista de conceitos
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFixedHeight(150)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        
        self.concepts_container = QWidget()
        self.concepts_layout = QHBoxLayout()
        self.concepts_layout.setSpacing(10)
        self.concepts_layout.setContentsMargins(8, 8, 8, 8)
        self.concepts_container.setLayout(self.concepts_layout)
        
        # Adicionar alguns conceitos de exemplo
        example_concepts = [
            ("Dialética", "Sócrates/Platão"),
            ("Eudaimonia", "Aristóteles"),
            ("Cogito", "Descartes"),
            ("Imperativo Categórico", "Kant"),
            ("Vontade de Poder", "Nietzsche"),
            ("Dasein", "Heidegger"),
        ]
        
        for name, author in example_concepts:
            concept_btn = QPushButton(f"{name}\n<small>{author}</small>")
            concept_btn.setObjectName("concept_button")
            concept_btn.setFont(QFont("FiraCode Nerd Font Propo", 9))
            concept_btn.clicked.connect(
                lambda checked, n=name, a=author: self.select_concept_example(n, a)
            )
            self.concepts_layout.addWidget(concept_btn)
        
        self.concepts_layout.addStretch()
        scroll_area.setWidget(self.concepts_container)
        main_layout.addWidget(scroll_area)
        
        self.setLayout(main_layout)
    
    def setup_connections(self):
        """Configura conexões de sinais"""
        self.filter_combo.currentTextChanged.connect(self.filter_concepts)
        self.search_input.textChanged.connect(self.search_concepts)
        self.new_concept_btn.clicked.connect(self.add_new_concept)
        self.new_connection_btn.clicked.connect(self.add_new_connection)
        self.dashboard_btn.clicked.connect(lambda: self.navigate_to.emit('dashboard'))
        self.view_notes_btn.clicked.connect(self.view_concept_notes)
        self.review_btn.clicked.connect(self.review_concept)
        self.explore_btn.clicked.connect(self.explore_concept)
        
        if self.controller:
            if hasattr(self.controller, 'concepts_loaded'):
                self.controller.concepts_loaded.connect(self.on_concepts_loaded)
            if hasattr(self.controller, 'concept_updated'):
                self.controller.concept_updated.connect(self.on_concept_updated)
    
    def select_concept_example(self, name, author):
        """Seleciona um conceito de exemplo"""
        example_concept = {
            'name': name,
            'author': author,
            'discipline': 'Filosofia',
            'note_count': 3,
            'book_count': 2,
            'connections': [
                {'name': 'Ética', 'type': 'relacionado'},
                {'name': 'Metafísica', 'type': 'fundamenta'}
            ],
            'notes': [
                {'title': f'Notas sobre {name}'},
                {'title': f'Aplicações de {name}'}
            ]
        }
        self.select_concept(example_concept)
    
    def select_concept(self, concept):
        """Seleciona um conceito para detalhes"""
        self.current_concept = concept
        
        # Atualizar interface
        self.concept_title.setText(concept.get('name', 'Sem nome'))
        
        info_text = f"""
        <b>Autor:</b> {concept.get('author', 'Vários')}<br>
        <b>Disciplina:</b> {concept.get('discipline', 'Filosofia')}<br>
        <b>Notas relacionadas:</b> {concept.get('note_count', 0)}<br>
        <b>Livros:</b> {concept.get('book_count', 0)}
        """
        self.concept_info.setText(info_text)
        
        # Conexões
        connections = concept.get('connections', [])
        if connections:
            connections_text = "<br>".join(
                f"• {conn['name']} <small>({conn['type']})</small>" for conn in connections[:5]
            )
            if len(connections) > 5:
                connections_text += f"<br>... e mais {len(connections) - 5}"
        else:
            connections_text = "Nenhuma conexão definida"
        self.connections_list.setText(connections_text)
        
        # Habilitar botões
        has_notes = concept.get('note_count', 0) > 0 or concept.get('notes', [])
        self.view_notes_btn.setEnabled(has_notes)
        self.review_btn.setEnabled(True)
        self.explore_btn.setEnabled(True)
        
        self.concept_selected.emit(concept.get('id', ''))
        
        logger.info(f"Conceito selecionado: {concept.get('name')}")
    
    def filter_concepts(self, filter_text):
        """Filtra conceitos por disciplina"""
        if self.controller and hasattr(self.controller, 'filter_concepts'):
            self.controller.filter_concepts(filter_text)
        else:
            logger.info(f"Filtrando por: {filter_text}")
    
    def search_concepts(self, search_text):
        """Busca conceitos por texto"""
        if search_text and len(search_text) >= 2:
            if self.controller and hasattr(self.controller, 'search_concepts'):
                self.controller.search_concepts(search_text)
            else:
                logger.info(f"Buscando: {search_text}")
    
    def add_new_concept(self):
        """Adiciona novo conceito"""
        from ui.widgets.concepts import AddConceptDialog
        
        dialog = AddConceptDialog(self.controller)
        if dialog.exec():
            new_concept = dialog.get_concept_data()
            logger.info(f"Novo conceito criado: {new_concept.get('name')}")
    
    def add_new_connection(self):
        """Adiciona nova conexão entre conceitos"""
        if not self.current_concept:
            logger.warning("Nenhum conceito selecionado para criar conexão")
            return
        
        from ui.widgets.concepts import AddConnectionDialog
        
        dialog = AddConnectionDialog(self.current_concept, self.controller)
        if dialog.exec():
            connection_data = dialog.get_connection_data()
            self.connection_added.emit(
                self.current_concept.get('id'),
                connection_data['target_id']
            )
            logger.info(f"Nova conexão criada para {self.current_concept.get('name')}")
    
    def view_concept_notes(self):
        """Visualiza notas do conceito"""
        if self.current_concept:
            from ui.widgets.notes import ConceptNotesDialog
            
            dialog = ConceptNotesDialog(self.current_concept, self.controller)
            dialog.exec()
    
    def review_concept(self):
        """Inicia revisão do conceito"""
        if self.current_concept:
            from ui.widgets.concepts import ConceptReviewDialog
            
            dialog = ConceptReviewDialog(self.current_concept, self.controller)
            dialog.exec()
    
    def explore_concept(self):
        """Explora conceito relacionado"""
        logger.info(f"Explorando conceito: {self.current_concept.get('name')}")
        # TODO: Implementar exploração de conceitos
    
    def on_concepts_loaded(self, concepts_data):
        """Carrega conceitos do controller"""
        self.concepts = concepts_data
        self.display_concepts()
        
        logger.info(f"{len(concepts_data)} conceitos carregados")
    
    def display_concepts(self):
        """Exibe conceitos na lista"""
        # Limpar lista atual
        while self.concepts_layout.count():
            child = self.concepts_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        
        # Adicionar conceitos
        for concept in self.concepts[:10]:  # Limitar a 10 para performance
            concept_btn = QPushButton(concept.get('name', 'Sem nome'))
            concept_btn.setObjectName("concept_button")
            concept_btn.setToolTip(concept.get('description', ''))
            concept_btn.clicked.connect(
                lambda checked, c=concept: self.select_concept(c)
            )
            concept_btn.setFont(QFont("FiraCode Nerd Font Propo", 9))
            self.concepts_layout.addWidget(concept_btn)
        
        self.concepts_layout.addStretch()
    
    def on_concept_updated(self, concept_data):
        """Atualiza conceito quando modificado"""
        if (self.current_concept and 
            self.current_concept.get('id') == concept_data.get('id')):
            self.current_concept.update(concept_data)
            self.select_concept(self.current_concept)
    
    def on_view_activated(self):
        """Chamado quando a view é ativada"""
        if self.controller and hasattr(self.controller, 'load_concepts'):
            self.controller.load_concepts()
    
    def refresh(self):
        """Atualiza a view"""
        self.on_view_activated()
    
    def cleanup(self):
        """Limpeza antes de fechar"""
        pass