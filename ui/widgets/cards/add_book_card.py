# ui/widgets/cards/add_book_card.py
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                            QPushButton, QSizePolicy, QFrame, QFileDialog,
                            QProgressBar, QMenu, QToolButton)
from PyQt6.QtCore import Qt, pyqtSignal, QSize, QPoint, QTimer, QPropertyAnimation, QEasingCurve, QTime
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

    def setup_footer(self):
        """Configura área de rodapé (se necessário)"""
        # Esta função pode ficar vazia por enquanto
        pass
       
    def setup_content_area(self):
        """Configurar área de conteúdo principal"""
        # Widget principal
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setSpacing(10)
        content_layout.setContentsMargins(5, 5, 5, 5)
        
        # Ícone central
        self.central_icon = AddBookIconWidget()
        content_layout.addWidget(self.central_icon, 0, Qt.AlignmentFlag.AlignCenter)
        
        # Texto explicativo
        self.help_text = QLabel()
        self.help_text.setWordWrap(True)
        self.help_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.help_text.setStyleSheet("""
            QLabel {
                color: #666666;
                font-size: 12px;
                padding: 5px;
            }
        """)
        content_layout.addWidget(self.help_text)
        
        # Área de drop (drag and drop)
        self.drop_area = DropAreaWidget()
        self.drop_area.setVisible(False)
        content_layout.addWidget(self.drop_area)
        
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
        self.status_label.setStyleSheet("""
            QLabel {
                font-size: 11px;
                color: #888888;
                padding: 2px;
                margin-top: 5px;
            }
        """)
        content_layout.addWidget(self.status_label)
        
        # Tempo estimado
        self.eta_label = QLabel()
        self.eta_label.setWordWrap(True)
        self.eta_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.eta_label.setStyleSheet("""
            QLabel {
                font-size: 10px;
                color: #999999;
                font-style: italic;
            }
        """)
        self.eta_label.setVisible(False)
        content_layout.addWidget(self.eta_label)
        
        # Adicionar ao layout principal
        self.content_widget = content_widget
        self.content_layout = content_layout
        self.main_layout.addWidget(self.content_widget)
        
        # Atualizar texto baseado no estado
        self.update_help_text()
        
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
        """Análise rápida do arquivo para obter metadados básicos"""
        import fitz  # PyMuPDF
        from pathlib import Path
        
        metadata = {
            "file_path": file_path,
            "file_name": os.path.basename(file_path),
            "file_size": os.path.getsize(file_path),
            "pages": 0,
            "requires_ocr": False
        }
        
        try:
            if file_path.endswith('.pdf'):
                with fitz.open(file_path) as doc:
                    metadata["pages"] = len(doc)
                    
                    # Tentar extrair título do PDF
                    if doc.metadata.get('title'):
                        metadata["title"] = doc.metadata['title']
                    else:
                        # Usar nome do arquivo como título
                        metadata["title"] = Path(file_path).stem
                    
                    # Verificar se precisa de OCR
                    # Simplificado: verifica se há texto na primeira página
                    if len(doc) > 0:
                        page = doc[0]
                        text = page.get_text()
                        metadata["requires_ocr"] = len(text.strip()) < 100
                        
                    metadata["author"] = doc.metadata.get('author', '')
                    
            elif file_path.endswith('.epub'):
                # Análise básica de EPUB
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
                            
                            # Extrair título
                            title_elem = root.find('.//dc:title', ns)
                            if title_elem is not None:
                                metadata["title"] = title_elem.text
                            else:
                                metadata["title"] = Path(file_path).stem
                                
                            # Extrair autor
                            author_elem = root.find('.//dc:creator', ns)
                            if author_elem is not None:
                                metadata["author"] = author_elem.text
                                
                            break
                            
        except Exception as e:
            logger.warning(f"Erro na análise rápida: {e}")
            metadata["title"] = Path(file_path).stem
            
        return metadata
    
    def start_processing(self, pipeline_id, settings):
        """Iniciar monitoramento do processamento"""
        self.current_pipeline_id = pipeline_id
        self.set_state("processing")
        
        # Armazenar informações da tarefa
        self.processing_tasks[pipeline_id] = {
            "settings": settings,
            "start_time": QTime.currentTime(),
            "stages": {}
        }
        
        # Atualizar UI
        file_name = os.path.basename(settings.get("file_path", "arquivo"))
        self.status_label.setText(f"Processando: {file_name}")
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
        self.self_state = "idle"
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
        self.setFixedSize(100, 100)
        
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
        painter.translate(self.width()/2, self.height()/2)
        painter.scale(self._scale, self._scale)
        painter.translate(-self.width()/2, -self.height()/2)
        
        bg_color = self.color.lighter(180) if self.state == "idle" else self.color.lighter(150)
        painter.setBrush(QBrush(bg_color))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(10, 10, 80, 80)
        
        if self.state == "idle":
            self.draw_plus_icon(painter)
        elif self.state == "processing":
            self.draw_processing_icon(painter)
        elif self.state == "success":
            self.draw_success_icon(painter)
        elif self.state == "error":
            self.draw_error_icon(painter)
        else:
            self.draw_plus_icon(painter)
        painter.restore()
            
    def draw_plus_icon(self, painter):
        painter.setBrush(QBrush(self.color))
        painter.drawEllipse(30, 30, 40, 40)
        painter.setPen(QPen(Qt.GlobalColor.white, 4))
        painter.drawLine(50, 40, 50, 60)
        painter.drawLine(40, 50, 60, 50)
        
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
        self.setFixedHeight(80)
        self.setAcceptDrops(True)
        self.reset_style()
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.icon_label = QLabel("📄")
        self.icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.icon_label.setStyleSheet("font-size: 24px;")
        layout.addWidget(self.icon_label)
        self.text_label = QLabel("Solte arquivos aqui")
        self.text_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.text_label.setStyleSheet("color: #666666; font-size: 11px;")
        layout.addWidget(self.text_label)
        
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self.setStyleSheet("""
                DropAreaWidget {
                    border: 2px dashed #4A90E2;
                    border-radius: 8px;
                    background-color: rgba(74, 144, 226, 0.1);
                }
            """)
            
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
                border: 2px dashed #CCCCCC;
                border-radius: 8px;
                background-color: rgba(255, 255, 255, 0.7);
            }
            DropAreaWidget:hover {
                border-color: #4A90E2;
                background-color: rgba(74, 144, 226, 0.05);
            }
        """)