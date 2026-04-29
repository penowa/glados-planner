# ui/widgets/dialogs/book_import_dialog.py
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QGridLayout,
                            QLabel, QLineEdit, QComboBox, QCheckBox, 
                            QGroupBox, QPushButton, QSpinBox, QTextEdit,
                            QTabWidget, QWidget, QFormLayout, QDateTimeEdit,
                            QMessageBox, QScrollArea, QProgressBar)
from PyQt6.QtCore import Qt, pyqtSignal, QDateTime
from PyQt6.QtGui import QFont, QIcon
import os
import logging
from pathlib import Path
from typing import Optional

from ui.utils.discipline_links import ensure_discipline_note, list_disciplines, resolve_vault_root

try:
    from core.config.settings import settings as core_settings
except Exception:
    core_settings = None

logger = logging.getLogger('GLaDOS.UI.BookImportDialog')

class BookImportDialog(QDialog):
    """Diálogo de configuração para importação de livros"""
    
    # Sinais
    import_confirmed = pyqtSignal(dict)  # Configurações confirmadas
    import_cancelled = pyqtSignal()
    
    def __init__(self, file_path, initial_metadata=None, parent=None, book_controller=None):
        super().__init__(parent)
        self.file_path = file_path
        self.initial_metadata = initial_metadata or {}
        self.book_controller = book_controller
        self.field_confidence_labels = {}
        self.confidence_summary_label = None
        self._vault_root = self._resolve_vault_root()
        self.processing_summary_label = None
        self.processing_recommendations = None
        self.runtime_group = None
        self.runtime_stage_label = None
        self.runtime_message_label = None
        self.runtime_progress_bar = None
        self.runtime_log = None
        self.current_pipeline_id = None
        self._awaiting_pipeline_start = False
        self._processing_active = False
        self._processing_finished = False
        
        self.setup_ui()
        self.load_initial_data()
        self._connect_processing_signals()
        
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

        self._setup_runtime_feedback(main_layout)
        
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

    def _setup_runtime_feedback(self, parent_layout):
        """Adiciona área de progresso do processamento."""
        self.runtime_group = QGroupBox("Andamento da Importação")
        self.runtime_group.setVisible(False)
        runtime_layout = QVBoxLayout(self.runtime_group)

        self.runtime_stage_label = QLabel("Aguardando início...")
        self.runtime_stage_label.setStyleSheet("font-weight: 600;")
        runtime_layout.addWidget(self.runtime_stage_label)

        self.runtime_progress_bar = QProgressBar()
        self.runtime_progress_bar.setRange(0, 100)
        self.runtime_progress_bar.setValue(0)
        runtime_layout.addWidget(self.runtime_progress_bar)

        self.runtime_message_label = QLabel("O progresso aparecerá aqui quando a importação começar.")
        self.runtime_message_label.setWordWrap(True)
        self.runtime_message_label.setStyleSheet("color: #707070; font-size: 11px;")
        runtime_layout.addWidget(self.runtime_message_label)

        self.runtime_log = QTextEdit()
        self.runtime_log.setReadOnly(True)
        self.runtime_log.setMinimumHeight(90)
        runtime_layout.addWidget(self.runtime_log)

        parent_layout.addWidget(self.runtime_group)

    def _connect_processing_signals(self):
        """Conecta o diálogo aos sinais do controller para mostrar progresso real."""
        if not self.book_controller:
            return
        try:
            self.book_controller.book_processing_started.connect(self._on_processing_started)
            self.book_controller.book_processing_progress.connect(self._on_processing_progress)
            self.book_controller.book_processing_completed.connect(self._on_processing_completed)
            self.book_controller.book_processing_failed.connect(self._on_processing_failed)
        except Exception as exc:
            logger.warning("Falha ao conectar sinais de progresso do livro: %s", exc)
        
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
        self.quality_combo.currentTextChanged.connect(self._update_processing_insights)
        quality_layout.addWidget(QLabel("Nível de qualidade:"))
        quality_layout.addWidget(self.quality_combo)
        
        quality_group.setLayout(quality_layout)
        layout.addWidget(quality_group)
        
        # Opções de extração
        extraction_group = QGroupBox("Opções de Extração")
        extraction_layout = QVBoxLayout()
        
        self.ocr_checkbox = QCheckBox("Usar OCR se necessário (para PDFs escaneados)")
        self.ocr_checkbox.setChecked(True)
        self.ocr_checkbox.toggled.connect(self._update_processing_insights)
        extraction_layout.addWidget(self.ocr_checkbox)
        
        self.llm_enhancement_checkbox = QCheckBox("Usar IA para aprimorar extração (recomendado)")
        self.llm_enhancement_checkbox.setChecked(True)
        extraction_layout.addWidget(self.llm_enhancement_checkbox)
        
        self.preserve_layout_checkbox = QCheckBox("Preservar layout original (imagens, tabelas)")
        self.preserve_layout_checkbox.toggled.connect(self._update_processing_insights)
        extraction_layout.addWidget(self.preserve_layout_checkbox)
        
        extraction_group.setLayout(extraction_layout)
        layout.addWidget(extraction_group)

        ocr_group = QGroupBox("OCR e Retomada")
        ocr_layout = QVBoxLayout()

        self.scan_heavy_checkbox = QCheckBox("Priorizar modo OCR pesado para PDFs escaneados")
        self.scan_heavy_checkbox.setChecked(False)
        self.scan_heavy_checkbox.toggled.connect(self._update_processing_insights)
        ocr_layout.addWidget(self.scan_heavy_checkbox)

        self.resume_ocr_checkbox = QCheckBox("Retomar OCR salvo automaticamente quando houver cache")
        self.resume_ocr_checkbox.setChecked(True)
        self.resume_ocr_checkbox.toggled.connect(self._update_processing_insights)
        ocr_layout.addWidget(self.resume_ocr_checkbox)

        self.processing_summary_label = QLabel("Analisando estratégia de processamento...")
        self.processing_summary_label.setWordWrap(True)
        self.processing_summary_label.setStyleSheet("color: #707070; font-size: 11px;")
        ocr_layout.addWidget(self.processing_summary_label)

        self.processing_recommendations = QTextEdit()
        self.processing_recommendations.setReadOnly(True)
        self.processing_recommendations.setMinimumHeight(110)
        self.processing_recommendations.setPlaceholderText("Recomendações de OCR e processamento aparecerão aqui.")
        ocr_layout.addWidget(self.processing_recommendations)

        ocr_group.setLayout(ocr_layout)
        layout.addWidget(ocr_group)
        
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

        discipline_group = QGroupBox("Disciplina")
        discipline_layout = QVBoxLayout()
        selector_row = QHBoxLayout()
        self.discipline_input = QComboBox()
        self.discipline_input.setEditable(True)
        self.discipline_input.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.discipline_input.setSizePolicy(self.discipline_input.sizePolicy().horizontalPolicy(), self.discipline_input.sizePolicy().verticalPolicy())
        self._reload_disciplines()
        self.new_discipline_button = QPushButton("Nova")
        self.new_discipline_button.clicked.connect(self._create_selected_discipline)
        selector_row.addWidget(self.discipline_input, 1)
        selector_row.addWidget(self.new_discipline_button)
        discipline_layout.addWidget(QLabel("Nome da disciplina (obrigatório para PDF):"))
        discipline_layout.addLayout(selector_row)
        discipline_group.setLayout(discipline_layout)
        layout.addWidget(discipline_group)
        
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

        self.deadline_date_edit = QDateTimeEdit()
        self.deadline_date_edit.setDateTime(QDateTime.currentDateTime().addDays(30))
        self.deadline_date_edit.setCalendarPopup(True)
        reading_layout.addRow("Data limite:", self.deadline_date_edit)
        
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
        self.start_date_edit.dateTimeChanged.connect(self._update_schedule_estimate)
        self.deadline_date_edit.dateTimeChanged.connect(self._update_schedule_estimate)
        self.pages_per_day_spin.valueChanged.connect(self._update_schedule_estimate)
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
            self.scan_heavy_checkbox.setChecked(requires_ocr)
            self.preserve_layout_checkbox.setChecked(bool(self.initial_metadata.get("preserve_layout", requires_ocr)))

            if requires_ocr and self.quality_combo.currentText() == "Padrão":
                self.quality_combo.setCurrentText("Alta Qualidade")
            
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
        self._update_schedule_estimate()

        self._update_processing_insights()

    def _metadata_recommendations(self) -> list[str]:
        """Compõe recomendações a partir dos metadados iniciais."""
        recommendations = list(self.initial_metadata.get("recommendations", []) or [])
        pages = int(self.initial_metadata.get("pages", 0) or 0)
        requires_ocr = bool(self.initial_metadata.get("requires_ocr", False))

        if requires_ocr:
            recommendations.append(
                "Este arquivo parece escaneado. O processamento deve usar OCR pesado e pode levar mais tempo."
            )
            recommendations.append(
                "Se a importação parar no meio, uma nova execução poderá continuar do progresso salvo."
            )
        if pages >= 300:
            recommendations.append(
                "Livro longo detectado. Considere processar em qualidade alta apenas se a extração padrão ficar ruim."
            )
        if not recommendations:
            recommendations.append("PDF/EPUB com perfil comum. O processamento padrão deve ser suficiente.")

        deduped = []
        seen = set()
        for item in recommendations:
            normalized = str(item).strip()
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            deduped.append(normalized)
        return deduped

    def _update_processing_insights(self):
        """Atualiza resumo de OCR/processamento conforme estado do diálogo."""
        if not self.processing_summary_label or not self.processing_recommendations:
            return

        requires_ocr = bool(self.initial_metadata.get("requires_ocr", False))
        pages = int(self.initial_metadata.get("pages", 0) or 0)
        quality = self.quality_combo.currentText()
        use_ocr = self.ocr_checkbox.isChecked()
        heavy_mode = self.scan_heavy_checkbox.isChecked()
        resume_mode = self.resume_ocr_checkbox.isChecked()
        preserve_layout = self.preserve_layout_checkbox.isChecked()

        if requires_ocr and use_ocr:
            summary = (
                "PDF escaneado detectado. O importador deve usar OCR com cache por página e "
                "retomada automática do progresso."
            )
        elif requires_ocr and not use_ocr:
            summary = (
                "PDF escaneado detectado, mas o OCR foi desativado. A extração de texto provavelmente falhará."
            )
        else:
            summary = "Texto nativo detectado ou OCR não parece obrigatório. O fluxo padrão deve ser usado."

        details = [
            f"Qualidade selecionada: {quality}.",
            "Modo OCR pesado: ativado." if heavy_mode else "Modo OCR pesado: automático.",
            "Retomada de OCR: ativada." if resume_mode else "Retomada de OCR: desativada.",
            "Preservação de layout: ativada." if preserve_layout else "Preservação de layout: desativada.",
        ]

        if pages:
            if requires_ocr:
                details.append(
                    f"Estimativa inicial: {pages} página(s). Em scan pesado, a primeira execução pode ser lenta."
                )
            else:
                details.append(f"Estimativa inicial: {pages} página(s).")

        self.processing_summary_label.setText(summary + "\n\n" + " ".join(details))

        recommendations = self._metadata_recommendations()
        if requires_ocr and use_ocr and resume_mode:
            recommendations.append(
                "O cache de OCR será reaproveitado em novas tentativas para evitar retrabalho."
            )
        if requires_ocr and quality == "Acadêmico":
            recommendations.append(
                "O modo acadêmico prioriza fidelidade, mas pode aumentar bastante o tempo de processamento."
            )
        elif requires_ocr and quality == "Rápido (Rascunho)":
            recommendations.append(
                "O modo rascunho reduz custo, mas não é indicado para PDFs escaneados difíceis."
            )

        self.processing_recommendations.setPlainText(
            "\n".join(f"• {item}" for item in recommendations)
        )

    def _update_schedule_estimate(self):
        """Atualiza estimativa do plano de leitura com base no prazo."""
        if not hasattr(self, "estimate_label"):
            return

        pages = int(self.initial_metadata.get("pages", 0) or 0)
        start_dt = self.start_date_edit.dateTime()
        deadline_dt = self.deadline_date_edit.dateTime()
        if deadline_dt < start_dt:
            self.estimate_label.setText("Duração estimada: ajuste a data limite para depois do início")
            return

        days_window = max(1, start_dt.daysTo(deadline_dt) + 1)
        if pages <= 0:
            self.estimate_label.setText(f"Janela de leitura: {days_window} dia(s)")
            return

        suggested_pages = max(1, (pages + days_window - 1) // days_window)
        manual_pages = int(self.pages_per_day_spin.value() or 1)
        self.estimate_label.setText(
            f"Janela de leitura: {days_window} dia(s) | "
            f"Meta sugerida para cumprir o prazo: {suggested_pages} pág/dia | "
            f"Meta atual: {manual_pages} pág/dia"
        )

    def _append_runtime_log(self, text: str):
        """Acrescenta mensagem ao log do processamento."""
        if not self.runtime_log or not text:
            return
        existing = self.runtime_log.toPlainText().strip()
        self.runtime_log.setPlainText((existing + "\n" + text).strip() if existing else text)
        cursor = self.runtime_log.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        self.runtime_log.setTextCursor(cursor)

    def _stage_bounds(self, stage: str) -> tuple[int, int]:
        """Mapeia estágio do pipeline para faixa do progresso global."""
        mapping = {
            "initialization": (0, 8),
            "analysis": (8, 18),
            "extraction": (18, 70),
            "structuring": (70, 82),
            "llm_enhancement": (82, 90),
            "integration": (90, 97),
            "scheduling": (97, 100),
            "completed": (100, 100),
        }
        return mapping.get(stage, (0, 100))

    def _overall_progress(self, stage: str, percent: int) -> int:
        """Converte progresso do estágio em progresso global."""
        start, end = self._stage_bounds(stage)
        if end <= start:
            return max(0, min(100, end))
        bounded = max(0, min(100, int(percent)))
        span = end - start
        return max(0, min(100, start + round(span * (bounded / 100))))

    def _friendly_stage_name(self, stage: str) -> str:
        """Nome amigável do estágio atual."""
        names = {
            "initialization": "Inicializando",
            "analysis": "Analisando arquivo",
            "extraction": "Extraindo conteúdo",
            "structuring": "Estruturando notas",
            "llm_enhancement": "Aprimorando com IA",
            "integration": "Integrando ao sistema",
            "scheduling": "Agendando leitura",
            "completed": "Concluído",
        }
        return names.get(stage or "", stage or "Processando")

    def _set_inputs_enabled(self, enabled: bool):
        """Habilita/desabilita edição durante o processamento."""
        self.tab_widget.setEnabled(enabled)
        self.import_button.setEnabled(enabled or self._processing_finished)

    def _set_runtime_waiting(self):
        """Mostra feedback de espera antes do pipeline emitir o primeiro evento."""
        if not self.runtime_group:
            return
        self.runtime_group.setVisible(True)
        self.runtime_progress_bar.setValue(2)
        self.runtime_stage_label.setText("Preparando importação...")
        self.runtime_message_label.setText(
            "O processamento está sendo iniciado. Você pode acompanhar o andamento aqui ou fechar e deixá-lo em segundo plano."
        )
        self.runtime_log.clear()
        self._append_runtime_log("Importação solicitada. Aguardando início do pipeline...")

    def _finalize_runtime_ui(self, success: bool, message: str):
        """Atualiza a UI ao fim do processamento."""
        self._processing_active = False
        self._processing_finished = True
        self._awaiting_pipeline_start = False
        self.runtime_group.setVisible(True)
        self.runtime_progress_bar.setValue(100 if success else max(self.runtime_progress_bar.value(), 1))
        self.runtime_stage_label.setText("Importação concluída" if success else "Importação com falha")
        self.runtime_message_label.setText(message)
        self.import_button.setText("Fechar")
        self.import_button.setEnabled(True)
        self.cancel_button.setText("Fechar")
        self._append_runtime_log(message)

    def _on_processing_started(self, pipeline_id: str, file_name: str, settings: dict):
        """Recebe o início do pipeline e ativa a barra de progresso."""
        target_path = str((settings or {}).get("file_path") or "").strip()
        if os.path.abspath(target_path) != os.path.abspath(str(self.file_path)):
            return
        if not self._awaiting_pipeline_start and self.current_pipeline_id != pipeline_id:
            return

        self.current_pipeline_id = pipeline_id
        self._processing_active = True
        self._awaiting_pipeline_start = False
        self.runtime_group.setVisible(True)
        self.runtime_progress_bar.setValue(3)
        self.runtime_stage_label.setText("Inicializando")
        self.runtime_message_label.setText(f"Pipeline {pipeline_id} iniciado para {file_name}.")
        self.cancel_button.setText("Fechar em segundo plano")
        self.import_button.setEnabled(False)
        self._append_runtime_log(f"Pipeline {pipeline_id} iniciado.")

    def _on_processing_progress(self, pipeline_id: str, stage: str, percent: int, message: str):
        """Atualiza barra e mensagens conforme o pipeline avança."""
        if pipeline_id != self.current_pipeline_id:
            return

        self.runtime_group.setVisible(True)
        self.runtime_stage_label.setText(self._friendly_stage_name(stage))
        self.runtime_progress_bar.setValue(self._overall_progress(stage, percent))
        self.runtime_message_label.setText(message or self._friendly_stage_name(stage))
        self._append_runtime_log(f"{self._friendly_stage_name(stage)}: {message or f'{percent}%'}")

    def _on_processing_completed(self, pipeline_id: str, result: dict):
        """Finaliza o monitoramento quando a importação termina com sucesso."""
        if pipeline_id != self.current_pipeline_id:
            return

        warnings = list((result or {}).get("warnings", []) or [])
        title = str((result or {}).get("title") or self.title_input.text().strip() or "Livro")
        message = f"'{title}' foi processado com sucesso."
        if warnings:
            message += f" Aviso: {warnings[0]}"
            for warning in warnings:
                self._append_runtime_log(f"Aviso: {warning}")

        self._set_inputs_enabled(False)
        self._finalize_runtime_ui(True, message)

    def _on_processing_failed(self, pipeline_id: str, error: str):
        """Exibe falha do pipeline e permite ao usuário fechar o diálogo."""
        if pipeline_id != self.current_pipeline_id:
            return

        self._set_inputs_enabled(False)
        self._finalize_runtime_ui(False, f"Falha no processamento: {error}")

    def confirm_import(self):
        """Confirmar importação com as configurações selecionadas"""
        if self._processing_finished:
            self.accept()
            return

        # Validar dados obrigatórios
        if not self.title_input.text().strip():
            QMessageBox.warning(self, "Atenção", "Por favor, insira um título para o livro.")
            self.title_input.setFocus()
            return

        discipline_name = self._selected_discipline()

        if str(self.file_path).lower().endswith(".pdf") and not discipline_name:
            QMessageBox.warning(
                self,
                "Disciplina obrigatória",
                "Para processar PDF, informe o nome da disciplina na aba de notas.",
            )
            self.tab_widget.setCurrentIndex(2)
            self.discipline_input.setFocus()
            return

        if discipline_name:
            self._ensure_discipline_exists(discipline_name)

        if self.deadline_date_edit.dateTime() < self.start_date_edit.dateTime():
            QMessageBox.warning(
                self,
                "Prazo inválido",
                "A data limite da leitura deve ser igual ou posterior à data de início.",
            )
            self.tab_widget.setCurrentIndex(3)
            self.deadline_date_edit.setFocus()
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
            "scan_heavy_mode": self.scan_heavy_checkbox.isChecked(),
            "resume_ocr": self.resume_ocr_checkbox.isChecked(),
            
            # Notas
            "note_structure": "Automático: completo + capítulos + metadados",
            "note_template": self.template_combo.currentText(),
            "vault_location": self.vault_location_input.text().strip(),
            "discipline": discipline_name,
            
            # Agendamento
            "auto_schedule": self.auto_schedule_checkbox.isChecked(),
            "pages_per_day": self.pages_per_day_spin.value(),
            "start_date": self.start_date_edit.dateTime().toString(Qt.DateFormat.ISODate),
            "deadline": self.deadline_date_edit.dateTime().date().toString("yyyy-MM-dd"),
            "preferred_time": self.reading_time_combo.currentText(),
            "strategy": self.strategy_combo.currentText(),
            
            # Arquivo
            "file_path": self.file_path,
            "file_name": os.path.basename(self.file_path),
            "detected_requires_ocr": bool(self.initial_metadata.get("requires_ocr", False)),
            "processing_recommendations": self._metadata_recommendations(),
        }
        
        # Emitir sinal com configurações
        if self.book_controller:
            self._awaiting_pipeline_start = True
            self._processing_finished = False
            self.current_pipeline_id = None
            self._set_inputs_enabled(False)
            self._set_runtime_waiting()
            self.import_button.setText("Importando...")
        self.import_confirmed.emit(config)
        if not self.book_controller:
            self.accept()

    def _resolve_vault_root(self):
        candidates = [getattr(getattr(core_settings, "paths", None), "vault", "")]
        return resolve_vault_root(*candidates)

    def _reload_disciplines(self):
        current = self._selected_discipline()
        self.discipline_input.clear()
        names = list_disciplines(self._vault_root) if self._vault_root else []
        self.discipline_input.addItems(names)
        if current:
            idx = self.discipline_input.findText(current)
            if idx >= 0:
                self.discipline_input.setCurrentIndex(idx)
            else:
                self.discipline_input.setEditText(current)

    def _selected_discipline(self) -> str:
        return self.discipline_input.currentText().strip() if self.discipline_input else ""

    def _ensure_discipline_exists(self, discipline: str) -> Optional[Path]:
        if not self._vault_root:
            return None
        return ensure_discipline_note(self._vault_root, discipline)

    def _create_selected_discipline(self):
        name = self._selected_discipline()
        if not name:
            QMessageBox.information(self, "Disciplina", "Informe o nome da nova disciplina.")
            self.discipline_input.setFocus()
            return
        created = self._ensure_discipline_exists(name)
        if not created:
            QMessageBox.warning(self, "Disciplina", "Não foi possível criar a nota da disciplina.")
            return
        self._reload_disciplines()
        
    def reject(self):
        """Cancelar importação"""
        if not self._processing_active and not self._processing_finished:
            self.import_cancelled.emit()
        super().reject()
