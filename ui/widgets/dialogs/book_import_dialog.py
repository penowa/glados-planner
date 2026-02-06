# ui/widgets/dialogs/book_import_dialog.py
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QGridLayout,
                            QLabel, QLineEdit, QComboBox, QCheckBox, 
                            QGroupBox, QPushButton, QSpinBox, QTextEdit,
                            QTabWidget, QWidget, QFormLayout, QDateTimeEdit,
                            QMessageBox, QScrollArea)
from PyQt6.QtCore import Qt, pyqtSignal, QDateTime
from PyQt6.QtGui import QFont, QIcon
import os
import logging

logger = logging.getLogger('GLaDOS.UI.BookImportDialog')

class BookImportDialog(QDialog):
    """Diálogo de configuração para importação de livros"""
    
    # Sinais
    import_confirmed = pyqtSignal(dict)  # Configurações confirmadas
    import_cancelled = pyqtSignal()
    
    def __init__(self, file_path, initial_metadata=None, parent=None):
        super().__init__(parent)
        self.file_path = file_path
        self.initial_metadata = initial_metadata or {}
        
        self.setup_ui()
        self.load_initial_data()
        
        self.setWindowTitle("Configurar Importação de Livro")
        self.setMinimumSize(700, 600)
        
    def setup_ui(self):
        """Configurar interface do diálogo"""
        main_layout = QVBoxLayout(self)
        
        # Cabeçalho
        header = QLabel(f"📖 Importar: {os.path.basename(self.file_path)}")
        header.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(header)
        
        # Tabs para organização
        self.tab_widget = QTabWidget()
        
        # Tab 1: Metadados básicos
        self.setup_metadata_tab()
        
        # Tab 2: Configurações de processamento
        self.setup_processing_tab()
        
        # Tab 3: Configurações de notas
        self.setup_notes_tab()
        
        # Tab 4: Agendamento de leitura
        self.setup_scheduling_tab()
        
        main_layout.addWidget(self.tab_widget)
        
        # Botões de ação
        button_layout = QHBoxLayout()
        
        self.cancel_button = QPushButton("Cancelar")
        self.cancel_button.clicked.connect(self.reject)
        
        self.import_button = QPushButton("Importar Livro")
        self.import_button.setObjectName("primary_button")
        self.import_button.clicked.connect(self.confirm_import)
        
        button_layout.addWidget(self.cancel_button)
        button_layout.addStretch()
        button_layout.addWidget(self.import_button)
        
        main_layout.addLayout(button_layout)
        
    def setup_metadata_tab(self):
        """Configurar tab de metadados"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Grupo de metadados básicos
        basic_group = QGroupBox("Metadados do Livro")
        basic_layout = QFormLayout()
        
        self.title_input = QLineEdit()
        self.title_input.setPlaceholderText("Título do livro")
        basic_layout.addRow("Título:", self.title_input)
        
        self.author_input = QLineEdit()
        self.author_input.setPlaceholderText("Autor do livro")
        basic_layout.addRow("Autor:", self.author_input)
        
        self.year_input = QLineEdit()
        self.year_input.setPlaceholderText("Ano de publicação")
        basic_layout.addRow("Ano:", self.year_input)
        
        self.publisher_input = QLineEdit()
        self.publisher_input.setPlaceholderText("Editora")
        basic_layout.addRow("Editora:", self.publisher_input)
        
        basic_group.setLayout(basic_layout)
        layout.addWidget(basic_group)
        
        # Grupo de metadados avançados
        advanced_group = QGroupBox("Metadados Avançados (Opcional)")
        advanced_layout = QFormLayout()
        
        self.isbn_input = QLineEdit()
        self.isbn_input.setPlaceholderText("ISBN")
        advanced_layout.addRow("ISBN:", self.isbn_input)
        
        self.language_combo = QComboBox()
        self.language_combo.addItems(["Português", "Inglês", "Espanhol", "Francês", "Alemão", "Outro"])
        advanced_layout.addRow("Idioma:", self.language_combo)
        
        self.genre_input = QLineEdit()
        self.genre_input.setPlaceholderText("Filosofia, Ficção, Não-ficção...")
        advanced_layout.addRow("Gênero:", self.genre_input)
        
        advanced_group.setLayout(advanced_layout)
        layout.addWidget(advanced_group)
        
        # Tags
        tags_group = QGroupBox("Tags")
        tags_layout = QVBoxLayout()
        
        self.tags_input = QLineEdit()
        self.tags_input.setPlaceholderText("filosofia, existencialismo, literatura (separadas por vírgula)")
        tags_layout.addWidget(self.tags_input)
        
        tags_group.setLayout(tags_layout)
        layout.addWidget(tags_group)
        
        layout.addStretch()
        
        self.tab_widget.addTab(tab, "📋 Metadados")
        
    def setup_processing_tab(self):
        """Configurar tab de processamento"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Qualidade de processamento
        quality_group = QGroupBox("Qualidade do Processamento")
        quality_layout = QVBoxLayout()
        
        self.quality_combo = QComboBox()
        self.quality_combo.addItems(["Padrão", "Rápido (Rascunho)", "Alta Qualidade", "Acadêmico"])
        self.quality_combo.setCurrentText("Padrão")
        quality_layout.addWidget(QLabel("Nível de qualidade:"))
        quality_layout.addWidget(self.quality_combo)
        
        quality_group.setLayout(quality_layout)
        layout.addWidget(quality_group)
        
        # Opções de extração
        extraction_group = QGroupBox("Opções de Extração")
        extraction_layout = QVBoxLayout()
        
        self.ocr_checkbox = QCheckBox("Usar OCR se necessário (para PDFs escaneados)")
        self.ocr_checkbox.setChecked(True)
        extraction_layout.addWidget(self.ocr_checkbox)
        
        self.llm_enhancement_checkbox = QCheckBox("Usar IA para aprimorar extração (recomendado)")
        self.llm_enhancement_checkbox.setChecked(True)
        extraction_layout.addWidget(self.llm_enhancement_checkbox)
        
        self.preserve_layout_checkbox = QCheckBox("Preservar layout original (imagens, tabelas)")
        extraction_layout.addWidget(self.preserve_layout_checkbox)
        
        extraction_group.setLayout(extraction_layout)
        layout.addWidget(extraction_group)
        
        # Estatísticas do arquivo
        stats_group = QGroupBox("Informações do Arquivo")
        stats_layout = QFormLayout()
        
        file_size = os.path.getsize(self.file_path) / (1024 * 1024)  # MB
        self.size_label = QLabel(f"{file_size:.2f} MB")
        stats_layout.addRow("Tamanho:", self.size_label)
        
        # Estas informações viriam da análise do arquivo
        self.pages_label = QLabel("Analisando...")
        stats_layout.addRow("Páginas estimadas:", self.pages_label)
        
        self.estimated_time_label = QLabel("Calculando...")
        stats_layout.addRow("Tempo estimado:", self.estimated_time_label)
        
        stats_group.setLayout(stats_layout)
        layout.addWidget(stats_group)
        
        layout.addStretch()
        
        self.tab_widget.addTab(tab, "⚙️ Processamento")
        
    def setup_notes_tab(self):
        """Configurar tab de notas"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Estrutura de notas
        structure_group = QGroupBox("Estrutura das Notas")
        structure_layout = QVBoxLayout()
        
        self.note_structure_combo = QComboBox()
        self.note_structure_combo.addItems([
            "Uma nota por capítulo (Recomendado)",
            "Nota única para todo o livro",
            "Uma nota por seção",
            "Uma nota por página"
        ])
        structure_layout.addWidget(QLabel("Como dividir o conteúdo:"))
        structure_layout.addWidget(self.note_structure_combo)
        
        # Configurações específicas por estrutura
        self.pages_per_note_spin = QSpinBox()
        self.pages_per_note_spin.setRange(1, 100)
        self.pages_per_note_spin.setValue(10)
        self.pages_per_note_spin.setSuffix(" páginas por nota")
        structure_layout.addWidget(self.pages_per_note_spin)
        
        structure_group.setLayout(structure_layout)
        layout.addWidget(structure_group)
        
        # Template de notas
        template_group = QGroupBox("Template das Notas")
        template_layout = QVBoxLayout()
        
        self.template_combo = QComboBox()
        self.template_combo.addItems([
            "Padrão (Livro)",
            "Acadêmico (com citações)",
            "Minimalista",
            "Personalizado"
        ])
        template_layout.addWidget(QLabel("Template:"))
        template_layout.addWidget(self.template_combo)
        
        template_group.setLayout(template_layout)
        layout.addWidget(template_group)
        
        # Localização no vault
        location_group = QGroupBox("Localização no Vault")
        location_layout = QVBoxLayout()
        
        self.vault_location_input = QLineEdit()
        self.vault_location_input.setText("01-LEITURAS/")
        self.vault_location_input.setPlaceholderText("Caminho no vault do Obsidian")
        location_layout.addWidget(QLabel("Pasta de destino:"))
        location_layout.addWidget(self.vault_location_input)
        
        location_group.setLayout(location_layout)
        layout.addWidget(location_group)
        
        layout.addStretch()
        
        self.tab_widget.addTab(tab, "📝 Notas")
        
    def setup_scheduling_tab(self):
        """Configurar tab de agendamento"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Configurações de leitura
        reading_group = QGroupBox("Configurações de Leitura")
        reading_layout = QFormLayout()
        
        self.auto_schedule_checkbox = QCheckBox("Agendar leitura automaticamente")
        self.auto_schedule_checkbox.setChecked(True)
        reading_layout.addRow(self.auto_schedule_checkbox)
        
        self.pages_per_day_spin = QSpinBox()
        self.pages_per_day_spin.setRange(1, 100)
        self.pages_per_day_spin.setValue(20)
        self.pages_per_day_spin.setSuffix(" páginas por dia")
        reading_layout.addRow("Meta diária:", self.pages_per_day_spin)
        
        self.start_date_edit = QDateTimeEdit()
        self.start_date_edit.setDateTime(QDateTime.currentDateTime().addDays(1))
        self.start_date_edit.setCalendarPopup(True)
        reading_layout.addRow("Data de início:", self.start_date_edit)
        
        self.reading_time_combo = QComboBox()
        self.reading_time_combo.addItems([
            "Manhã (08:00-12:00)",
            "Tarde (14:00-18:00)", 
            "Noite (19:00-22:00)",
            "Qualquer horário"
        ])
        reading_layout.addRow("Horário preferencial:", self.reading_time_combo)
        
        reading_group.setLayout(reading_layout)
        layout.addWidget(reading_group)
        
        # Estratégia de agendamento
        strategy_group = QGroupBox("Estratégia de Agendamento")
        strategy_layout = QVBoxLayout()
        
        self.strategy_combo = QComboBox()
        self.strategy_combo.addItems([
            "Equilibrado (Recomendado)",
            "Intensivo (terminar rápido)",
            "Leve (apenas finais de semana)",
            "Personalizado"
        ])
        strategy_layout.addWidget(QLabel("Estratégia:"))
        strategy_layout.addWidget(self.strategy_combo)
        
        # Estimativa
        self.estimate_label = QLabel("Duração estimada: Calculando...")
        strategy_layout.addWidget(self.estimate_label)
        
        strategy_group.setLayout(strategy_layout)
        layout.addWidget(strategy_group)
        
        layout.addStretch()
        
        self.tab_widget.addTab(tab, "📅 Agendamento")
        
    def load_initial_data(self):
        """Carregar dados iniciais do arquivo"""
        # Preencher metadados iniciais
        if self.initial_metadata:
            self.title_input.setText(self.initial_metadata.get("title", ""))
            self.author_input.setText(self.initial_metadata.get("author", ""))
            
            # Atualizar estatísticas
            pages = self.initial_metadata.get("pages", 0)
            self.pages_label.setText(str(pages) if pages > 0 else "Desconhecido")
            
            # Calcular tempo estimado baseado em páginas
            if pages > 0:
                estimated_minutes = pages * 0.5  # 30 segundos por página
                if estimated_minutes > 60:
                    self.estimated_time_label.setText(f"{estimated_minutes/60:.1f} horas")
                else:
                    self.estimated_time_label.setText(f"{estimated_minutes:.0f} minutos")
                    
                # Atualizar estimativa de leitura
                pages_per_day = self.pages_per_day_spin.value()
                days = pages / pages_per_day
                self.estimate_label.setText(f"Duração estimada: {days:.0f} dias")
        
    def confirm_import(self):
        """Confirmar importação com as configurações selecionadas"""
        # Validar dados obrigatórios
        if not self.title_input.text().strip():
            QMessageBox.warning(self, "Atenção", "Por favor, insira um título para o livro.")
            self.title_input.setFocus()
            return
            
        # Coletar todas as configurações
        config = {
            # Metadados
            "title": self.title_input.text().strip(),
            "author": self.author_input.text().strip(),
            "year": self.year_input.text().strip(),
            "publisher": self.publisher_input.text().strip(),
            "isbn": self.isbn_input.text().strip(),
            "language": self.language_combo.currentText(),
            "genre": self.genre_input.text().strip(),
            "tags": [tag.strip() for tag in self.tags_input.text().split(",") if tag.strip()],
            
            # Processamento
            "quality": self.quality_combo.currentText(),
            "use_ocr": self.ocr_checkbox.isChecked(),
            "use_llm": self.llm_enhancement_checkbox.isChecked(),
            "preserve_layout": self.preserve_layout_checkbox.isChecked(),
            
            # Notas
            "note_structure": self.note_structure_combo.currentText(),
            "pages_per_note": self.pages_per_note_spin.value(),
            "note_template": self.template_combo.currentText(),
            "vault_location": self.vault_location_input.text().strip(),
            
            # Agendamento
            "auto_schedule": self.auto_schedule_checkbox.isChecked(),
            "pages_per_day": self.pages_per_day_spin.value(),
            "start_date": self.start_date_edit.dateTime().toString(Qt.DateFormat.ISODate),
            "preferred_time": self.reading_time_combo.currentText(),
            "strategy": self.strategy_combo.currentText(),
            
            # Arquivo
            "file_path": self.file_path,
            "file_name": os.path.basename(self.file_path)
        }
        
        # Emitir sinal com configurações
        self.import_confirmed.emit(config)
        self.accept()
        
    def reject(self):
        """Cancelar importação"""
        self.import_cancelled.emit()
        super().reject()