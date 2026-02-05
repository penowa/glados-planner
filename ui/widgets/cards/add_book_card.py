# ui/widgets/cards/add_book_card.py
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                            QPushButton, QSizePolicy, QFrame, QFileDialog,
                            QProgressBar, QMenu, QToolButton)
from PyQt6.QtCore import Qt, pyqtSignal, QSize, QPoint, QTimer, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import (QPixmap, QPainter, QColor, QLinearGradient, QFont, 
                        QBrush, QPen, QIcon, QPainterPath)
import hashlib
import os

from .base_card import PhilosophyCard

class AddBookCard(PhilosophyCard):
    """Card especializado para adicionar novos livros ao sistema"""
    
    # Sinais
    file_selected = pyqtSignal(str)  # Caminho do arquivo selecionado
    processing_started = pyqtSignal(str)  # Início do processamento
    processing_progress = pyqtSignal(int, str)  # Progresso do processamento
    processing_completed = pyqtSignal(dict)  # Processamento concluído
    processing_failed = pyqtSignal(str)  # Falha no processamento
    import_mode_changed = pyqtSignal(str)  # Modo de importação alterado
    
    def __init__(self, parent=None):
        # Inicializar estado antes de chamar a classe base
        self.is_dragging = False
        self.drag_position = QPoint()
        self.current_state = "idle"  # idle, selecting, processing, success, error
        self.processing_steps = []
        self.current_step = 0
        self.total_steps = 5
        
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
        
        # Chamar classe base (que configurará as animações base)
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
        
        # Status label
        self.status_label = QLabel()
        self.status_label.setWordWrap(True)
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setStyleSheet("""
            QLabel {
                font-size: 11px;
                color: #888888;
                padding: 2px;
            }
        """)
        content_layout.addWidget(self.status_label)
        
        # Adicionar ao layout principal (substituindo conteúdo existente)
        if hasattr(self, 'content_widget'):
            # Remover widget de conteúdo existente
            self.content_widget.hide()
            self.main_layout.removeWidget(self.content_widget)
            self.content_widget.deleteLater()
        
        # Atualizar referências para os layouts
        self.content_widget = content_widget
        self.content_layout = content_layout
        
        # Adicionar ao layout principal
        self.main_layout.addWidget(self.content_widget)
        
        # Atualizar texto baseado no estado
        self.update_help_text()
        
    def setup_footer(self):
        """Configurar rodapé com botões de ação"""
        # Layout horizontal para botões
        button_layout = QHBoxLayout()
        button_layout.setSpacing(8)
        
        # Botão de selecionar arquivo
        self.select_file_button = QPushButton("📁 Selecionar Arquivo")
        self.select_file_button.setObjectName("primary_button")
        self.select_file_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.select_file_button.setIcon(QIcon.fromTheme("document-open"))
        button_layout.addWidget(self.select_file_button)
        
        # Botão de opções avançadas
        self.options_button = QToolButton()
        self.options_button.setText("⋯")
        self.options_button.setObjectName("icon_button")
        self.options_button.setFixedSize(30, 30)
        self.options_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.options_button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        
        # Menu de opções
        self.options_menu = QMenu(self.options_button)
        self.setup_options_menu()
        self.options_button.setMenu(self.options_menu)
        
        button_layout.addWidget(self.options_button)
        
        # Criar novo widget de rodapé (substituindo existente)
        if hasattr(self, 'footer_widget'):
            self.footer_widget.hide()
            self.main_layout.removeWidget(self.footer_widget)
            self.footer_widget.deleteLater()
        
        self.footer_widget = QWidget()
        self.footer_layout = QHBoxLayout(self.footer_widget)
        self.footer_layout.setContentsMargins(0, 0, 0, 0)
        self.footer_layout.addLayout(button_layout)
        
        self.main_layout.addWidget(self.footer_widget)
        
    def setup_options_menu(self):
        """Configurar menu de opções"""
        # Ação de digitalizar diretório
        scan_action = self.options_menu.addAction("📂 Escanear Diretório")
        scan_action.triggered.connect(self.scan_directory)
        
        # Ação de importar de URL
        url_action = self.options_menu.addAction("🌐 Importar de URL")
        url_action.triggered.connect(self.import_from_url)
        
        # Separador
        self.options_menu.addSeparator()
        
        # Ação de configurações de importação
        settings_action = self.options_menu.addAction("⚙ Configurações de Importação")
        settings_action.triggered.connect(self.show_import_settings)
        
        # Ação de histórico de importações
        history_action = self.options_menu.addAction("📋 Histórico de Importações")
        history_action.triggered.connect(self.show_import_history)
        
    def setup_connections(self):
        """Conectar sinais e slots"""
        if self.select_file_button:
            self.select_file_button.clicked.connect(self.select_file)
        
        if self.drop_area:
            self.drop_area.file_dropped.connect(self.handle_dropped_file)
        
        # Timer para animação de idle
        self.idle_timer = QTimer()
        self.idle_timer.timeout.connect(self.animate_idle_state)
        self.idle_timer.start(3000)  # Animar a cada 3 segundos
        
    def setup_animations(self):
        """Configurar animações para feedback visual"""
        # Primeiro, configurar animações da classe base
        super().setup_animations()
        
        # Depois, configurar animações específicas deste card
        # A animação de pulso será configurada quando o central_icon existir
        # Ela será configurada em update_visual_state
        
    def select_file(self):
        """Abrir diálogo para selecionar arquivo"""
        if self.current_state == "processing":
            return
            
        file_dialog = QFileDialog()
        file_dialog.setFileMode(QFileDialog.FileMode.ExistingFile)
        file_dialog.setNameFilter("Documentos (*.pdf *.epub *.mobi *.djvu *.txt);;Todos os arquivos (*)")
        
        if file_dialog.exec():
            files = file_dialog.selectedFiles()
            if files:
                self.process_file(files[0])
                
    def scan_directory(self):
        """Escanear diretório para múltiplos arquivos"""
        directory = QFileDialog.getExistingDirectory(self, "Selecionar Diretório")
        if directory:
            self.status_label.setText(f"Diretório selecionado: {directory}")
            self.set_state("selecting")
            
    def import_from_url(self):
        """Importar livro de URL"""
        self.status_label.setText("Funcionalidade de URL em desenvolvimento")
        
    def show_import_settings(self):
        """Mostrar configurações de importação"""
        self.status_label.setText("Configurações de importação")
        
    def show_import_history(self):
        """Mostrar histórico de importações"""
        self.status_label.setText("Histórico de importações")
        
    def process_file(self, file_path):
        """Processar arquivo selecionado"""
        if not os.path.exists(file_path):
            self.status_label.setText(f"Arquivo não encontrado: {file_path}")
            self.set_state("error")
            return
            
        file_name = os.path.basename(file_path)
        valid_extensions = ['.pdf', '.epub', '.mobi', '.djvu', '.txt']
        file_ext = os.path.splitext(file_path)[1].lower()
        
        if file_ext not in valid_extensions:
            self.status_label.setText(f"Formato não suportado: {file_ext}")
            self.set_state("error")
            return
            
        self.file_selected.emit(file_path)
        self.set_state("processing")
        self.status_label.setText(f"Processando: {file_name}")
        self.progress_bar.setVisible(True)
        self.simulate_processing(file_path)

    def handle_dropped_file(self, file_path):
        """Lidar com arquivo solto via drag and drop"""
        self.process_file(file_path)

    def set_state(self, state):
        """Alterar estado do card"""
        self.current_state = state
        self.update_visual_state()
        self.update_help_text()

    def update_visual_state(self):
        """Atualizar interface baseada no estado atual"""
        if not self.central_icon:
            return
            
        self.central_icon.set_state(self.current_state)
        
        if self.current_state == "idle":
            self.central_icon.set_color("#4A90E2")
            self.drop_area.setVisible(False)
            self.progress_bar.setVisible(False)
            
            # Configurar e iniciar animação de pulso se não existir
            if not self.pulse_animation:
                self.pulse_animation = QPropertyAnimation(self.central_icon, b"scale")
                self.pulse_animation.setDuration(1500)
                self.pulse_animation.setStartValue(1.0)
                self.pulse_animation.setEndValue(1.1)
                self.pulse_animation.setEasingCurve(QEasingCurve.Type.InOutSine)
                self.pulse_animation.setLoopCount(-1)  # Loop infinito
                self.pulse_animation.start()
            elif self.pulse_animation.state() != QPropertyAnimation.State.Running:
                self.pulse_animation.start()
                
        elif self.current_state == "selecting":
            self.central_icon.set_color("#F5A623")
            self.drop_area.setVisible(True)
            self.progress_bar.setVisible(False)
            if self.pulse_animation and self.pulse_animation.state() == QPropertyAnimation.State.Running:
                self.pulse_animation.stop()
                
        elif self.current_state == "processing":
            self.central_icon.set_color("#4A90E2")
            self.drop_area.setVisible(False)
            self.progress_bar.setVisible(True)
            if self.pulse_animation and self.pulse_animation.state() == QPropertyAnimation.State.Running:
                self.pulse_animation.stop()
                
        elif self.current_state == "success":
            self.central_icon.set_color("#7ED321")
            self.drop_area.setVisible(False)
            self.progress_bar.setVisible(False)
            if self.pulse_animation and self.pulse_animation.state() == QPropertyAnimation.State.Running:
                self.pulse_animation.stop()
                
        elif self.current_state == "error":
            self.central_icon.set_color("#D0021B")
            self.drop_area.setVisible(False)
            self.progress_bar.setVisible(False)
            if self.pulse_animation and self.pulse_animation.state() == QPropertyAnimation.State.Running:
                self.pulse_animation.stop()

    def update_help_text(self):
        """Atualizar texto de ajuda baseado no estado"""
        if not self.help_text:
            return
        
        texts = {
            "idle": "Arraste um livro aqui ou clique em selecionar",
            "selecting": "Solte para iniciar a importação",
            "processing": "Analisando metadados e conteúdo...",
            "success": "Livro adicionado com sucesso!",
            "error": "Ocorreu um erro ao processar o arquivo"
        }
        self.help_text.setText(texts.get(self.current_state, ""))

    def animate_idle_state(self):
        """Animação sutil para o estado idle"""
        if self.current_state == "idle" and self.central_icon:
            # Alternar entre dois estados sutilmente
            current_scale = self.central_icon.scale
            if abs(current_scale - 1.0) < 0.01:
                # Criar animação temporária para sutil "respiração"
                breath_anim = QPropertyAnimation(self.central_icon, b"scale")
                breath_anim.setDuration(2000)
                breath_anim.setStartValue(1.0)
                breath_anim.setEndValue(1.02)
                breath_anim.setEasingCurve(QEasingCurve.Type.InOutSine)
                breath_anim.start()
            elif abs(current_scale - 1.02) < 0.01:
                breath_anim = QPropertyAnimation(self.central_icon, b"scale")
                breath_anim.setDuration(2000)
                breath_anim.setStartValue(1.02)
                breath_anim.setEndValue(1.0)
                breath_anim.setEasingCurve(QEasingCurve.Type.InOutSine)
                breath_anim.start()

    def simulate_processing(self, file_path):
        """Simular o fluxo de processamento"""
        self.current_step = 0
        self.processing_timer = QTimer()
        self.processing_timer.timeout.connect(self._processing_step)
        self.processing_timer.start(800)

    def _processing_step(self):
        """Executar um passo da simulação de processamento"""
        self.current_step += 1
        progress = int((self.current_step / self.total_steps) * 100)
        if self.progress_bar:
            self.progress_bar.setValue(progress)
        
        steps = [
            "Lendo arquivo...",
            "Extraindo metadados...",
            "Gerando capa...",
            "Indexando conteúdo...",
            "Finalizando..."
        ]
        
        if self.current_step <= len(steps) and self.status_label:
            self.status_label.setText(steps[self.current_step-1])
            self.processing_progress.emit(progress, steps[self.current_step-1])
        
        if self.current_step >= self.total_steps:
            if self.processing_timer:
                self.processing_timer.stop()
            self.set_state("success")
            self.processing_completed.emit({"status": "ok", "path": ""})
            QTimer.singleShot(2000, self.reset_to_idle)

    def reset_to_idle(self):
        """Resetar o card para o estado inicial"""
        self.current_state = "idle"
        if self.progress_bar:
            self.progress_bar.setValue(0)
        if self.status_label:
            self.status_label.clear()
        self.update_visual_state()
        self.update_help_text()
        
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            if urls and os.path.isfile(urls[0].toLocalFile()):
                event.acceptProposedAction()
                self.set_state("selecting")
                
    def dragLeaveEvent(self, event):
        if self.current_state == "selecting":
            self.set_state("idle")
            
    def dropEvent(self, event):
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            if urls:
                file_path = urls[0].toLocalFile()
                self.process_file(file_path)
                event.acceptProposedAction()
                
    def cleanup(self):
        """Limpar recursos e animações"""
        if self.idle_timer:
            self.idle_timer.stop()
        if self.processing_timer:
            self.processing_timer.stop()
        if self.pulse_animation:
            self.pulse_animation.stop()
        
        # Limpar animações da classe base
        if hasattr(self, 'hover_animation'):
            self.hover_animation.stop()
        if hasattr(self, 'click_animation'):
            self.click_animation.stop()

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