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
        self.field_confidence_labels = {}
        self.confidence_summary_label = None
        
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
        basic_layout.addRow("Título:", self._wrap_with_confidence("title", self.title_input))
        
        self.author_input = QLineEdit()
        self.author_input.setPlaceholderText("Autor do livro")
        basic_layout.addRow("Autor:", self._wrap_with_confidence("author", self.author_input))
        
        self.year_input = QLineEdit()
        self.year_input.setPlaceholderText("Ano de publicação")
        basic_layout.addRow("Ano:", self._wrap_with_confidence("year", self.year_input))
        
        self.publisher_input = QLineEdit()
        self.publisher_input.setPlaceholderText("Editora")
        basic_layout.addRow("Editora:", self._wrap_with_confidence("publisher", self.publisher_input))
        
        basic_group.setLayout(basic_layout)
        layout.addWidget(basic_group)
        
        # Grupo de metadados avançados
        advanced_group = QGroupBox("Metadados Avançados (Opcional)")
        advanced_layout = QFormLayout()
        
        self.isbn_input = QLineEdit()
        self.isbn_input.setPlaceholderText("ISBN")
        advanced_layout.addRow("ISBN:", self._wrap_with_confidence("isbn", self.isbn_input))
        
        self.language_combo = QComboBox()
        self.language_combo.addItems(["Português", "Inglês", "Espanhol", "Francês", "Alemão", "Outro"])
        advanced_layout.addRow("Idioma:", self._wrap_with_confidence("language", self.language_combo))
        
        self.genre_input = QLineEdit()
        self.genre_input.setPlaceholderText("Filosofia, Ficção, Não-ficção...")
        advanced_layout.addRow("Gênero:", self._wrap_with_confidence("genre", self.genre_input))
        
        advanced_group.setLayout(advanced_layout)
        layout.addWidget(advanced_group)
        
        # Tags
        tags_group = QGroupBox("Tags")
        tags_layout = QVBoxLayout()
        
        self.tags_input = QLineEdit()
        self.tags_input.setPlaceholderText("filosofia, existencialismo, literatura (separadas por vírgula)")
        tags_layout.addWidget(self.tags_input)
        tags_confidence = QLabel("Confiança tags: --")
        tags_confidence.setStyleSheet("color: #808080; font-size: 11px;")
        self.field_confidence_labels["tags"] = tags_confidence
        tags_layout.addWidget(tags_confidence)
        
        tags_group.setLayout(tags_layout)
        layout.addWidget(tags_group)

        self.confidence_summary_label = QLabel("Confiança da extração automática: --")
        self.confidence_summary_label.setWordWrap(True)
        self.confidence_summary_label.setStyleSheet("color: #707070; font-size: 11px;")
        layout.addWidget(self.confidence_summary_label)
        
        layout.addStretch()
        
        self.tab_widget.addTab(tab, "📋 Metadados")

    def _wrap_with_confidence(self, field_key, input_widget):
        """Cria linha com input + indicador de confiança."""
        container = QWidget()
        row_layout = QHBoxLayout(container)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.setSpacing(8)
        row_layout.addWidget(input_widget)

        confidence_label = QLabel("Confiança: --")
        confidence_label.setMinimumWidth(130)
        confidence_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        confidence_label.setStyleSheet("color: #808080; font-size: 11px;")
        row_layout.addWidget(confidence_label)

        self.field_confidence_labels[field_key] = confidence_label
        return container

    def _render_confidence(self, score):
        """Retorna texto e cor do indicador de confiança."""
        if score >= 0.85:
            return f"Alta ({int(score * 100)}%)", "#2E7D32"
        if score >= 0.60:
            return f"Média ({int(score * 100)}%)", "#B26A00"
        if score > 0:
            return f"Baixa ({int(score * 100)}%)", "#B03A2E"
        return "Não detectado", "#808080"

    def _apply_confidence_layer(self):
        """Aplica confiança por campo e resumo geral."""
        confidence_by_field = self.initial_metadata.get("confidence_by_field", {}) or {}
        available_scores = []

        for field, label in self.field_confidence_labels.items():
            data = confidence_by_field.get(field, {})
            score = float(data.get("score", 0.0) or 0.0)
            source = data.get("source", "Sem fonte")
            available_scores.append(score)

            confidence_text, color = self._render_confidence(score)
            if field == "tags":
                label.setText(f"Confiança tags: {confidence_text}")
            else:
                label.setText(confidence_text)
            label.setStyleSheet(f"color: {color}; font-size: 11px;")
            label.setToolTip(f"Origem: {source}")

        if self.confidence_summary_label:
            scores = [score for score in available_scores if score > 0]
            if scores:
                avg_score = sum(scores) / len(scores)
                confidence_text, color = self._render_confidence(avg_score)
                self.confidence_summary_label.setText(
                    f"Confiança média da extração automática: {confidence_text}. "
                    "Você pode revisar e editar qualquer campo."
                )
                self.confidence_summary_label.setStyleSheet(f"color: {color}; font-size: 11px;")
            else:
                self.confidence_summary_label.setText(
                    "Não foi possível estimar confiança dos metadados. Revise os campos manualmente."
                )
                self.confidence_summary_label.setStyleSheet("color: #808080; font-size: 11px;")
        
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
        
        structure_layout.addWidget(QLabel(
            "A estrutura é automática e sempre cria:\n"
            "• Nota completa do livro\n"
            "• Notas por capítulo\n"
            "• Nota de metadados/índice"
        ))
        
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
            self.year_input.setText(str(self.initial_metadata.get("year", "") or ""))
            self.publisher_input.setText(self.initial_metadata.get("publisher", ""))
            self.isbn_input.setText(self.initial_metadata.get("isbn", ""))
            self.genre_input.setText(self.initial_metadata.get("genre", ""))

            tags = self.initial_metadata.get("tags", [])
            if isinstance(tags, list):
                self.tags_input.setText(", ".join([str(tag) for tag in tags if str(tag).strip()]))
            elif isinstance(tags, str):
                self.tags_input.setText(tags)

            language = self.initial_metadata.get("language", "")
            if language:
                index = self.language_combo.findText(language)
                if index >= 0:
                    self.language_combo.setCurrentIndex(index)
                else:
                    other_index = self.language_combo.findText("Outro")
                    if other_index >= 0:
                        self.language_combo.setCurrentIndex(other_index)

            self._apply_confidence_layer()

            if "auto_schedule_default" in self.initial_metadata:
                self.auto_schedule_checkbox.setChecked(
                    bool(self.initial_metadata.get("auto_schedule_default", True))
                )
            
            # Atualizar estatísticas
            pages = self.initial_metadata.get("pages", 0)
            self.pages_label.setText(str(pages) if pages > 0 else "Desconhecido")

            requires_ocr = bool(self.initial_metadata.get("requires_ocr", False))
            self.ocr_checkbox.setChecked(requires_ocr)
            
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
            "note_structure": "Automático: completo + capítulos + metadados",
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
