# ui/widgets/cards/add_book_card.py
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                            QPushButton, QSizePolicy, QFrame, QFileDialog,
                            QProgressBar, QMenu, QToolButton, QCheckBox)
from PyQt6.QtCore import Qt, pyqtSignal, QSize, QPoint, QTimer, QPropertyAnimation, QEasingCurve, QTime, QEvent
from PyQt6.QtGui import (QPixmap, QPainter, QColor, QLinearGradient, QFont, 
                        QBrush, QPen, QIcon, QPainterPath)
import hashlib
import os
import logging

from .base_card import PhilosophyCard

logger = logging.getLogger('GLaDOS.UI.AddBookCard')

class AddBookCard(PhilosophyCard):
    """Card especializado para adicionar novos livros ao sistema"""
    
    # Sinais atualizados
    file_selected = pyqtSignal(str)  # Caminho do arquivo selecionado
    import_config_requested = pyqtSignal(str, dict)  # (file_path, initial_metadata)
    processing_started = pyqtSignal(str, dict)  # (pipeline_id, settings)
    processing_progress = pyqtSignal(str, str, int, str)  # (pipeline_id, stage, percent, message)
    processing_completed = pyqtSignal(str, dict)  # (pipeline_id, result)
    processing_failed = pyqtSignal(str, str)  # (pipeline_id, error)
    
    def __init__(self, parent=None, book_controller=None):
        # Inicializar estado antes de chamar a classe base
        self.is_dragging = False
        self.drag_position = QPoint()
        self.current_state = "idle"  # idle, selecting, processing, success, error
        self.processing_steps = []
        self.current_step = 0
        self.total_steps = 5
        
        # Referência ao controller
        self.book_controller = book_controller
        
        # Informações do processamento atual
        self.current_pipeline_id = None
        self.processing_tasks = {}  # pipeline_id -> task_info
        
        # Inicializar widgets que serão usados em animações
        self.central_icon = None
        self.select_file_button = None
        self.options_button = None
        self.options_menu = None
        self.help_text = None
        self.drop_area = None
        self.progress_bar = None
        self.status_label = None
        self.auto_schedule_checkbox = None
        self.idle_timer = None
        self.processing_timer = None
        self.pulse_animation = None
        
        # Timer para atualização de progresso
        self.progress_update_timer = QTimer()
        self.progress_update_timer.timeout.connect(self.update_processing_status)
        
        # Chamar classe base
        super().__init__(parent)
        
        # Configurar UI específica deste card
        self.setup_ui()
        self.setup_connections()
        
    def setup_ui(self):
        """Configurar interface do card de adição"""
        # Definir tamanho fixo para consistência
        self.setFixedSize(280, 360)
        self.setAcceptDrops(True)  # Permitir drag and drop
        
        # Remover botão de fechar do card base (se existir)
        if hasattr(self, 'close_button'):
            self.close_button.hide()
        
        # Definir título do card
        if hasattr(self, 'title_label'):
            self.title_label.setText("Adicionar Novo Livro")
            self.title_label.setStyleSheet("color: #4A90E2; font-weight: bold; font-size: 14px;")
        
        # Área de conteúdo principal
        self.setup_content_area()
        
        # Rodapé com botões de ação
        self.setup_footer()
        
        # Estados visuais
        self.update_visual_state()
        self.update_help_text()
        self.apply_theme_styles()

    def setup_connections(self):
        """Configura conexões de sinais e slots"""
        if self.central_icon:
            self.central_icon.mousePressEvent = self._on_central_icon_clicked
        
        if self.drop_area:
            self.drop_area.file_dropped.connect(self.handle_file_selected)

    def _on_central_icon_clicked(self, event):
        """Manipula clique no ícone central"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.select_file()

    def set_state(self, state):
        """Define o estado do card e atualiza a UI"""
        self.current_state = state
        self.update_visual_state()
        self.update_help_text()

    def update_help_text(self):
        """Atualiza o texto de ajuda baseado no estado"""
        help_texts = {
            "idle": "Clique no ícone para adicionar um novo livro\nou arraste um arquivo PDF/EPUB aqui",
            "selecting": "Selecione um arquivo...",
            "analyzing": "Analisando arquivo...",
            "processing": "Processando livro...",
            "success": "Livro processado com sucesso!",
            "error": "Ocorreu um erro. Clique para tentar novamente."
        }
        
        text = help_texts.get(self.current_state, help_texts["idle"])
        if self.help_text:
            self.help_text.setText(text)
            self.help_text.setVisible(True)

    def update_visual_state(self):
        """Atualiza a aparência visual baseada no estado"""
        # Atualizar ícone central
        if self.central_icon:
            self.central_icon.set_state(self.current_state)
        
        # Mostrar/ocultar elementos baseado no estado
        is_idle_or_selecting = self.current_state in ["idle", "selecting"]
        is_processing = self.current_state == "processing"
        is_final_state = self.current_state in ["success", "error"]
        
        if self.drop_area:
            self.drop_area.setVisible(is_idle_or_selecting)
        
        if self.progress_bar:
            self.progress_bar.setVisible(is_processing)
        
        if self.help_text:
            self.help_text.setVisible(is_idle_or_selecting or is_final_state)
        
        if self.status_label:
            self.status_label.setVisible(not is_idle_or_selecting)
        
        if self.eta_label:
            self.eta_label.setVisible(is_processing)

        if self.auto_schedule_checkbox:
            self.auto_schedule_checkbox.setVisible(not is_processing)

    def setup_footer(self):
        """Configura área de rodapé (se necessário)"""
        # Esta função pode ficar vazia por enquanto
        pass
       
    def setup_content_area(self):
        """Configurar área de conteúdo principal"""
        # Widget principal
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setSpacing(6)
        content_layout.setContentsMargins(2, 0, 2, 4)

        # Área de drop (drag and drop)
        self.drop_area = DropAreaWidget()
        self.drop_area.setVisible(False)
        content_layout.addWidget(self.drop_area, 0, Qt.AlignmentFlag.AlignHCenter)

        # Ícone central (ação de clique)
        self.central_icon = AddBookIconWidget()
        content_layout.addWidget(self.central_icon, 0, Qt.AlignmentFlag.AlignHCenter)
        self._apply_idle_area_proportion()
        
        # Texto explicativo
        self.help_text = QLabel()
        self.help_text.setWordWrap(True)
        self.help_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.help_text.setProperty("role", "help_text")
        content_layout.addWidget(self.help_text)
        
        # Progress bar (para processamento)
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #E0E0E0;
                border-radius: 4px;
                background-color: #F5F5F5;
                height: 6px;
            }
            QProgressBar::chunk {
                background-color: #4A90E2;
                border-radius: 4px;
            }
        """)
        content_layout.addWidget(self.progress_bar)
        
        # Status label com mais informações
        self.status_label = QLabel()
        self.status_label.setWordWrap(True)
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setProperty("role", "status_text")
        content_layout.addWidget(self.status_label)
        
        # Tempo estimado
        self.eta_label = QLabel()
        self.eta_label.setWordWrap(True)
        self.eta_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.eta_label.setProperty("role", "eta_text")
        self.eta_label.setVisible(False)
        content_layout.addWidget(self.eta_label)

        self.auto_schedule_checkbox = QCheckBox("Agendar sessões automaticamente")
        self.auto_schedule_checkbox.setChecked(True)
        self.auto_schedule_checkbox.setToolTip(
            "Se desmarcado, o processamento importa o livro sem criar sessões de leitura."
        )
        content_layout.addWidget(self.auto_schedule_checkbox, 0, Qt.AlignmentFlag.AlignHCenter)
        
        # Adicionar ao layout principal
        self.content_widget = content_widget
        self.content_layout = content_layout
        self.main_layout.addWidget(self.content_widget)
        
        # Atualizar texto baseado no estado
        self.update_help_text()
        self.apply_theme_styles()

    def _apply_idle_area_proportion(self):
        """Define proporção visual 80/20 entre drag area e botão."""
        # Card fixo de 360px; reservamos bloco principal para interação.
        interactive_block = 280
        drag_height = int(interactive_block * 0.8)   # 224
        button_height = int(interactive_block * 0.2) # 56

        if self.drop_area:
            self.drop_area.setFixedHeight(drag_height)
            self.drop_area.setFixedWidth(248)

        if self.central_icon:
            self.central_icon.setFixedHeight(button_height)
            self.central_icon.setFixedWidth(248)

    def changeEvent(self, event):
        """Reaplica estilos quando o tema/paleta muda."""
        if event.type() in (QEvent.Type.PaletteChange, QEvent.Type.StyleChange):
            self.apply_theme_styles()
        super().changeEvent(event)

    def apply_theme_styles(self):
        """Aplicar estilos baseados na paleta ativa do tema."""
        palette = self.palette()
        accent = palette.color(palette.ColorRole.Highlight).name()
        text_primary = palette.color(palette.ColorRole.WindowText).name()
        text_secondary = palette.color(palette.ColorRole.Mid).name()
        text_tertiary = palette.color(palette.ColorRole.Midlight).name()
        panel = palette.color(palette.ColorRole.Base).name()
        panel_alt = palette.color(palette.ColorRole.AlternateBase).name()

        if hasattr(self, "title_label") and self.title_label:
            self.title_label.setStyleSheet(
                f"color: {accent}; font-weight: bold; font-size: 14px;"
            )

        if self.help_text:
            self.help_text.setStyleSheet(
                f"QLabel {{ color: {text_secondary}; font-size: 12px; padding: 5px; }}"
            )

        if self.status_label:
            self.status_label.setStyleSheet(
                f"QLabel {{ font-size: 11px; color: {text_secondary}; padding: 2px; margin-top: 5px; }}"
            )

        if self.eta_label:
            self.eta_label.setStyleSheet(
                f"QLabel {{ font-size: 10px; color: {text_tertiary}; font-style: italic; }}"
            )

        if self.progress_bar:
            self.progress_bar.setStyleSheet(
                "QProgressBar {"
                f"border: 1px solid {text_tertiary};"
                "border-radius: 4px;"
                f"background-color: {panel};"
                "height: 6px;"
                "}"
                "QProgressBar::chunk {"
                f"background-color: {accent};"
                "border-radius: 4px;"
                "}"
            )

        if self.central_icon:
            self.central_icon.set_color(accent)

        if self.drop_area:
            self.drop_area.apply_theme_colors(
                accent=accent,
                text=text_secondary,
                bg=panel_alt
            )
        
    def select_file(self):
        """Abrir diálogo para selecionar arquivo"""
        if self.current_state == "processing":
            return
            
        file_dialog = QFileDialog()
        file_dialog.setFileMode(QFileDialog.FileMode.ExistingFile)
        file_dialog.setNameFilter("Documentos (*.pdf *.epub);;Todos os arquivos (*)")
        
        if file_dialog.exec():
            files = file_dialog.selectedFiles()
            if files:
                self.handle_file_selected(files[0])
                
    def handle_file_selected(self, file_path):
        """Processar arquivo selecionado"""
        if not os.path.exists(file_path):
            self.show_error(f"Arquivo não encontrado: {file_path}")
            return
            
        file_name = os.path.basename(file_path)
        valid_extensions = ['.pdf', '.epub']
        file_ext = os.path.splitext(file_path)[1].lower()
        
        if file_ext not in valid_extensions:
            self.show_error(f"Formato não suportado: {file_ext}")
            return
        
        # Analisar arquivo para obter metadados iniciais
        self.set_state("analyzing")
        self.status_label.setText(f"Analisando: {file_name}")
        
        # Usar o book_controller para análise rápida
        if self.book_controller:
            try:
                # Análise básica do arquivo
                metadata = self.quick_analyze_file(file_path)
                metadata["auto_schedule_default"] = bool(
                    self.auto_schedule_checkbox.isChecked() if self.auto_schedule_checkbox else True
                )
                
                # Emitir sinal para abrir diálogo de configuração
                self.import_config_requested.emit(file_path, metadata)
                
                # Resetar estado para idle
                #QTimer.singleShot(500, lambda: self.set_state("idle"))
                
            except Exception as e:
                self.show_error(f"Erro na análise: {str(e)}")
        else:
            # Sem controller, apenas emitir sinal
            self.import_config_requested.emit(file_path, {})
            
    def quick_analyze_file(self, file_path):
        """Análise rápida do arquivo para obter metadados iniciais."""
        from pathlib import Path
        import re

        def _extract_year(raw_value):
            if not raw_value:
                return ""
            # Suporta formatos como "D:20190510120000" e datas ISO.
            match = re.search(r"(19|20)\d{2}", str(raw_value))
            return match.group(0) if match else ""

        def _extract_isbn(text):
            if not text:
                return ""
            # Aceita ISBN-10 e ISBN-13 com separadores.
            pattern = re.compile(r"\b(?:97[89][\-\s]?)?(?:\d[\-\s]?){9,12}[\dXx]\b")
            for candidate in pattern.findall(text):
                cleaned = re.sub(r"[^0-9Xx]", "", candidate).upper()
                if len(cleaned) in (10, 13):
                    return cleaned
            return ""

        def _normalize_language(raw_language):
            if not raw_language:
                return ""
            lang = str(raw_language).strip().lower()
            mapping = {
                "pt": "Português",
                "pt-br": "Português",
                "por": "Português",
                "portuguese": "Português",
                "en": "Inglês",
                "eng": "Inglês",
                "english": "Inglês",
                "es": "Espanhol",
                "spa": "Espanhol",
                "spanish": "Espanhol",
                "fr": "Francês",
                "fra": "Francês",
                "fre": "Francês",
                "french": "Francês",
                "de": "Alemão",
                "deu": "Alemão",
                "ger": "Alemão",
                "german": "Alemão"
            }
            return mapping.get(lang, "Outro")
        
        metadata = {
            "file_path": file_path,
            "file_name": os.path.basename(file_path),
            "file_size": os.path.getsize(file_path),
            "pages": 0,
            "requires_ocr": False,
            "title": "",
            "author": "",
            "year": "",
            "publisher": "",
            "isbn": "",
            "language": "",
            "genre": "",
            "tags": [],
            "confidence_by_field": {}
        }

        confidence = metadata["confidence_by_field"]

        def _set_confidence(field, score, source):
            current = confidence.get(field, {})
            current_score = float(current.get("score", 0.0))
            if score >= current_score:
                confidence[field] = {
                    "score": round(float(score), 2),
                    "source": source
                }
        
        try:
            if file_path.endswith('.pdf'):
                import fitz  # PyMuPDF

                with fitz.open(file_path) as doc:
                    metadata["pages"] = len(doc)
                    pdf_meta = doc.metadata or {}
                    
                    # Metadados embutidos.
                    metadata["title"] = (pdf_meta.get("title") or "").strip()
                    if metadata["title"]:
                        _set_confidence("title", 0.95, "Metadado embutido do PDF")

                    metadata["author"] = (pdf_meta.get("author") or "").strip()
                    if metadata["author"]:
                        _set_confidence("author", 0.95, "Metadado embutido do PDF")

                    metadata["publisher"] = (
                        pdf_meta.get("publisher")
                        or pdf_meta.get("producer")
                        or pdf_meta.get("creator")
                        or ""
                    ).strip()
                    if metadata["publisher"]:
                        _set_confidence("publisher", 0.7, "Metadado técnico do PDF")

                    metadata["genre"] = (pdf_meta.get("subject") or "").strip()
                    if metadata["genre"]:
                        _set_confidence("genre", 0.75, "Campo subject do PDF")

                    metadata["year"] = _extract_year(
                        pdf_meta.get("creationDate") or pdf_meta.get("modDate")
                    )
                    if metadata["year"]:
                        _set_confidence("year", 0.6, "Data de criação/modificação do PDF")

                    metadata["language"] = _normalize_language(pdf_meta.get("language"))
                    if metadata["language"]:
                        _set_confidence("language", 0.8, "Metadado de idioma do PDF")
                    
                    keywords = (pdf_meta.get("keywords") or "").strip()
                    if keywords:
                        keyword_tags = [
                            tag.strip()
                            for tag in re.split(r"[,;|]", keywords)
                            if tag.strip()
                        ]
                        metadata["tags"].extend(keyword_tags)
                        _set_confidence("tags", 0.7, "Keywords do PDF")
                    
                    metadata["isbn"] = _extract_isbn(
                        " ".join(
                            [
                                keywords,
                                metadata["genre"],
                                metadata["title"],
                                metadata["author"]
                            ]
                        )
                    )
                    if metadata["isbn"]:
                        _set_confidence("isbn", 0.75, "ISBN inferido de metadados PDF")
                    
                    # Verificar se precisa de OCR
                    # Simplificado: verifica se há texto na primeira página
                    if len(doc) > 0:
                        page = doc[0]
                        text = page.get_text()
                        metadata["requires_ocr"] = len(text.strip()) < 100

                    # Fallback para campos faltantes: tentar inferir pela capa/primeiras páginas.
                    sampled_text = ""
                    for idx in range(min(5, len(doc))):
                        sampled_text += "\n" + (doc[idx].get_text() or "")

                    lines = [line.strip() for line in sampled_text.splitlines() if line.strip()]
                    if not metadata["title"]:
                        for line in lines[:30]:
                            if 4 <= len(line) <= 120 and not re.match(r"^\d+$", line):
                                metadata["title"] = line
                                _set_confidence("title", 0.55, "Inferido das primeiras páginas do PDF")
                                break

                    if not metadata["author"]:
                        by_pattern = re.compile(r"^(?:por|by)\s+(.+)$", re.IGNORECASE)
                        for line in lines[:40]:
                            match = by_pattern.match(line)
                            if match:
                                metadata["author"] = match.group(1).strip()
                                _set_confidence("author", 0.5, "Inferido por padrão 'por/by' no PDF")
                                break

                    if not metadata["isbn"]:
                        metadata["isbn"] = _extract_isbn(sampled_text)
                        if metadata["isbn"]:
                            _set_confidence("isbn", 0.6, "ISBN inferido do texto inicial do PDF")
                    
            elif file_path.endswith('.epub'):
                import zipfile
                import xml.etree.ElementTree as ET
                
                with zipfile.ZipFile(file_path, 'r') as epub:
                    # Ler metadados do OPF
                    for file in epub.namelist():
                        if file.endswith('.opf'):
                            content = epub.read(file).decode('utf-8')
                            root = ET.fromstring(content)
                            
                            # Namespace
                            ns = {'opf': 'http://www.idpf.org/2007/opf',
                                  'dc': 'http://purl.org/dc/elements/1.1/'}
                            
                            # Extrair múltiplos metadados.
                            title_elem = root.find('.//dc:title', ns)
                            if title_elem is not None and title_elem.text:
                                metadata["title"] = title_elem.text.strip()
                                _set_confidence("title", 0.98, "Metadado OPF do EPUB")

                            creator_elems = root.findall('.//dc:creator', ns)
                            creators = [elem.text.strip() for elem in creator_elems if elem is not None and elem.text]
                            if creators:
                                metadata["author"] = ", ".join(creators)
                                _set_confidence("author", 0.98, "Metadado OPF do EPUB")

                            publisher_elem = root.find('.//dc:publisher', ns)
                            if publisher_elem is not None and publisher_elem.text:
                                metadata["publisher"] = publisher_elem.text.strip()
                                _set_confidence("publisher", 0.9, "Metadado OPF do EPUB")

                            date_elem = root.find('.//dc:date', ns)
                            if date_elem is not None and date_elem.text:
                                metadata["year"] = _extract_year(date_elem.text)
                                if metadata["year"]:
                                    _set_confidence("year", 0.9, "Metadado OPF do EPUB")

                            language_elem = root.find('.//dc:language', ns)
                            if language_elem is not None and language_elem.text:
                                metadata["language"] = _normalize_language(language_elem.text)
                                _set_confidence("language", 0.9, "Metadado OPF do EPUB")

                            subject_elems = root.findall('.//dc:subject', ns)
                            subjects = [elem.text.strip() for elem in subject_elems if elem is not None and elem.text]
                            if subjects:
                                metadata["genre"] = subjects[0]
                                metadata["tags"].extend(subjects)
                                _set_confidence("genre", 0.85, "Metadado subject do EPUB")
                                _set_confidence("tags", 0.85, "Subjects do EPUB")

                            identifier_elems = root.findall('.//dc:identifier', ns)
                            identifiers = " ".join(
                                [elem.text.strip() for elem in identifier_elems if elem is not None and elem.text]
                            )
                            metadata["isbn"] = _extract_isbn(identifiers)
                            if metadata["isbn"]:
                                _set_confidence("isbn", 0.9, "Identifier do EPUB")
                                
                            break

        except Exception as e:
            logger.warning(f"Erro na análise rápida: {e}")

        if not metadata["title"]:
            metadata["title"] = Path(file_path).stem
            _set_confidence("title", 0.2, "Fallback: nome do arquivo")
        if not metadata["language"]:
            metadata["language"] = "Português"
            _set_confidence("language", 0.2, "Fallback padrão do sistema")
        metadata["tags"] = list(dict.fromkeys(metadata["tags"]))  # remove duplicatas preservando ordem
            
        return metadata
    
    def start_processing(self, pipeline_id, settings, file_name=None):
        """Iniciar monitoramento do processamento"""
        if not isinstance(settings, dict):
            settings = {}

        self.current_pipeline_id = pipeline_id
        self.set_state("processing")
        
        # Armazenar informações da tarefa
        self.processing_tasks[pipeline_id] = {
            "settings": settings,
            "start_time": QTime.currentTime(),
            "stages": {}
        }
        
        # Atualizar UI
        display_name = file_name or os.path.basename(settings.get("file_path", "arquivo"))
        self.status_label.setText(f"Processando: {display_name}")
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.eta_label.setVisible(True)
        self.eta_label.setText("Estimando tempo...")
        
        # Iniciar timer de atualização
        self.progress_update_timer.start(500)  # Atualizar a cada 500ms
        
        self.processing_started.emit(pipeline_id, settings)
        
    def update_processing_status(self):
        """Atualizar status do processamento em tempo real"""
        if not self.current_pipeline_id or self.current_state != "processing":
            return
            
        # Aqui você pode buscar status do pipeline do BookController
        if self.book_controller:
            try:
                status = self.book_controller.get_processing_status(self.current_pipeline_id)
                
                if status.get("status") == "not_found":
                    # Pipeline não encontrado, pode ter terminado
                    self.progress_update_timer.stop()
                    return
                    
                # Atualizar progresso baseado no estágio atual
                stage = status.get("current_stage")
                if stage:
                    # Mapear estágio para porcentagem
                    stage_progress = self.map_stage_to_progress(stage)
                    self.progress_bar.setValue(stage_progress)
                    
                    # Atualizar mensagem
                    stage_name = self.get_stage_display_name(stage)
                    self.status_label.setText(f"{stage_name}...")
                    
                    # Calcular e atualizar ETA
                    self.update_eta(stage, status)
                    
            except Exception as e:
                logger.error(f"Erro ao buscar status: {e}")
    
    def map_stage_to_progress(self, stage):
        """Mapear estágio do pipeline para porcentagem de progresso"""
        stage_mapping = {
            "initialization": 10,
            "analysis": 20,
            "extraction": 40,
            "structuring": 60,
            "llm_enhancement": 75,
            "integration": 90,
            "scheduling": 95,
            "completed": 100
        }
        return stage_mapping.get(stage, 0)
    
    def get_stage_display_name(self, stage):
        """Obter nome amigável para o estágio"""
        display_names = {
            "initialization": "Inicializando",
            "analysis": "Analisando livro",
            "extraction": "Extraindo conteúdo",
            "structuring": "Estruturando notas",
            "llm_enhancement": "Aprimorando com IA",
            "integration": "Integrando sistemas",
            "scheduling": "Agendando leitura",
            "completed": "Concluído"
        }
        return display_names.get(stage, stage)
    
    def update_eta(self, stage, status):
        """Atualizar estimativa de tempo restante"""
        # Esta é uma implementação simplificada
        # Em um sistema real, você calcularia baseado no tempo médio por estágio
        stage_times = {
            "initialization": 5,
            "analysis": 15,
            "extraction": 30,
            "structuring": 20,
            "llm_enhancement": 60,
            "integration": 10,
            "scheduling": 5
        }
        
        if stage in stage_times:
            remaining_stages = list(stage_times.keys())
            current_index = remaining_stages.index(stage) if stage in remaining_stages else 0
            
            # Calcular tempo estimado para estágios restantes
            total_remaining = sum(list(stage_times.values())[current_index:])
            self.eta_label.setText(f"Tempo estimado: ~{total_remaining}s restantes")

    def on_processing_started(self, pipeline_id, file_name=None, settings=None):
        """Método para ser chamado quando o processamento inicia"""
        # Compatibilidade com chamadas antigas: (pipeline_id, settings)
        if isinstance(file_name, dict) and settings is None:
            settings = file_name
            file_name = None
        self.start_processing(pipeline_id, settings or {}, file_name)
    
    def on_processing_progress(self, pipeline_id, stage, percent, message):
        """Atualizar progresso quando receber sinal do controller"""
        if pipeline_id == self.current_pipeline_id:
            self.progress_bar.setValue(percent)
            self.status_label.setText(message)
            
            # Atualizar ETA se disponível
            if "minutos" in message.lower() or "segundos" in message.lower():
                self.eta_label.setText(message)
    
    def on_processing_completed(self, pipeline_id, result):
        """Finalizar processamento com sucesso"""
        if pipeline_id == self.current_pipeline_id:
            self.set_state("success")
            self.progress_bar.setVisible(False)
            self.eta_label.setVisible(False)
            
            book_title = result.get("title", "Livro")
            self.status_label.setText(f"✓ {book_title} processado com sucesso!")
            
            # Parar timer de atualização
            self.progress_update_timer.stop()
            
            # Resetar após delay
            QTimer.singleShot(3000, self.reset_to_idle)
            
            self.processing_completed.emit(pipeline_id, result)
    
    def on_processing_failed(self, pipeline_id, error):
        """Tratar falha no processamento"""
        if pipeline_id == self.current_pipeline_id:
            self.set_state("error")
            self.progress_bar.setVisible(False)
            self.eta_label.setVisible(False)
            
            self.status_label.setText(f"✗ Erro: {error[:100]}...")
            
            # Parar timer de atualização
            self.progress_update_timer.stop()
            
            # Resetar após delay
            QTimer.singleShot(5000, self.reset_to_idle)
            
            self.processing_failed.emit(pipeline_id, error)
    
    def show_error(self, message):
        """Mostrar mensagem de erro"""
        self.set_state("error")
        self.status_label.setText(f"✗ {message}")
        QTimer.singleShot(3000, self.reset_to_idle)
    
    def reset_to_idle(self):
        """Resetar o card para o estado inicial"""
        self.set_state("idle")
        self.current_pipeline_id = None
        if self.progress_bar:
            self.progress_bar.setValue(0)
            self.progress_bar.setVisible(False)
        if self.status_label:
            self.status_label.clear()
        if self.eta_label:
            self.eta_label.clear()
            self.eta_label.setVisible(False)
        self.update_visual_state()
        self.update_help_text()

class AddBookIconWidget(QWidget):
    """Widget de ícone personalizado para o card de adicionar"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.color = QColor("#4A90E2")
        self._scale = 1.0
        self.state = "idle"
        self.setFixedSize(248, 56)
        
    @property
    def scale(self):
        return self._scale
        
    @scale.setter
    def scale(self, value):
        self._scale = value
        self.update()

    def set_color(self, color):
        if isinstance(color, str):
            self.color = QColor(color)
        else:
            self.color = color
        self.update()
        
    def set_state(self, state):
        self.state = state
        self.update()
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        painter.save()
        rect = self.rect().adjusted(2, 2, -2, -2)
        base = self.color.lighter(190) if self.state in ("idle", "selecting") else self.color.lighter(175)
        painter.setBrush(QBrush(base))
        painter.setPen(QPen(self.color, 2, Qt.PenStyle.DashLine))
        painter.drawRoundedRect(rect, 10, 10)

        #painter.setPen(QPen(self.color.darker(110), 3))
        #cx = self.width() // 2
        #cy = self.height() // 2 - 2
        #painter.drawLine(cx, cy - 7, cx, cy + 7)
        #painter.drawLine(cx - 7, cy, cx + 7, cy)

        painter.setPen(QPen(self.color.darker(130), 1))
        painter.setFont(QFont("Sans Serif", 8))
        painter.drawText(self.rect().adjusted(0, 18, 0, 0), Qt.AlignmentFlag.AlignHCenter, "Clique para selecionar")
        painter.restore()
            
    #def draw_plus_icon(self, painter):
        #painter.setBrush(QBrush(self.color))
        #painter.drawEllipse(30, 30, 40, 40)
        #painter.setPen(QPen(Qt.GlobalColor.white, 4))
        #painter.drawLine(50, 40, 50, 60)
        #painter.drawLine(40, 50, 60, 50)
        
    def draw_processing_icon(self, painter):
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QPen(self.color, 3))
        painter.drawEllipse(30, 30, 40, 40)
        from PyQt6.QtCore import QTime
        current_time = QTime.currentTime()
        angle = (current_time.msec() // 20) % 360
        painter.setPen(QPen(Qt.GlobalColor.white, 4))
        painter.drawArc(32, 32, 36, 36, angle * 16, 120 * 16)
        
    def draw_success_icon(self, painter):
        painter.setBrush(QBrush(self.color))
        painter.setPen(QPen(self.color.darker(130), 2))
        painter.drawEllipse(30, 30, 40, 40)
        painter.setPen(QPen(Qt.GlobalColor.white, 4))
        path = QPainterPath()
        path.moveTo(40, 52)
        path.lineTo(48, 60)
        path.lineTo(62, 44)
        painter.drawPath(path)
        
    def draw_error_icon(self, painter):
        painter.setBrush(QBrush(self.color))
        painter.setPen(QPen(self.color.darker(130), 2))
        painter.drawEllipse(30, 30, 40, 40)
        painter.setPen(QPen(Qt.GlobalColor.white, 4))
        painter.drawLine(42, 42, 58, 58)
        painter.drawLine(42, 58, 58, 42)

    def mousePressEvent(self, event):
        """Permite clique no ícone"""
        if event.button() == Qt.MouseButton.LeftButton:
            # Emitir um sinal se necessário, ou apenas aceitar o evento
            event.accept()
        super().mousePressEvent(event)

class DropAreaWidget(QFrame):
    """Área especializada para drag and drop de arquivos"""
    file_dropped = pyqtSignal(str)
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(224)
        self.setAcceptDrops(True)
        self._accent_color = "#4A90E2"
        self._text_color = "#666666"
        self._bg_color = "rgba(255, 255, 255, 0.7)"
        self.reset_style()
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.icon_label = QLabel("＋")
        self.icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.icon_label.setFixedSize(56, 56)
        self.icon_label.setStyleSheet(
            "font-size: 30px; font-weight: bold; color: white; "
            "background-color: #4A90E2; border-radius: 28px;"
        )
        layout.addStretch(1)
        layout.addWidget(self.icon_label, 0, Qt.AlignmentFlag.AlignCenter)
        layout.addStretch(1)
        self.text_label = QLabel("Arraste e solte aqui")
        self.text_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.text_label.setStyleSheet(f"color: {self._text_color}; font-size: 11px;")
        self.text_label.setVisible(False)

    def apply_theme_colors(self, accent: str, text: str, bg: str):
        self._accent_color = accent
        self._text_color = text
        self._bg_color = bg
        self.text_label.setStyleSheet(f"color: {self._text_color}; font-size: 11px;")
        self.icon_label.setStyleSheet(
            f"font-size: 30px; font-weight: bold; color: white; "
            f"background-color: {self._accent_color}; border-radius: 28px;"
        )
        self.reset_style()
        
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self.setStyleSheet("""
                DropAreaWidget {
                    border: 1px solid %s;
                    border-radius: 8px;
                    background-color: rgba(74, 144, 226, 0.08);
                }
            """ % self._accent_color)
            
    def dragLeaveEvent(self, event):
        self.reset_style()
        
    def dropEvent(self, event):
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            if urls:
                file_path = urls[0].toLocalFile()
                self.file_dropped.emit(file_path)
                event.acceptProposedAction()
        self.reset_style()
        
    def reset_style(self):
        self.setStyleSheet("""
            DropAreaWidget {
                border: 1px solid transparent;
                border-radius: 8px;
                background-color: transparent;
            }
            DropAreaWidget:hover {
                border-color: rgba(0, 0, 0, 0.08);
                background-color: rgba(0, 0, 0, 0.02);
            }
        """)
