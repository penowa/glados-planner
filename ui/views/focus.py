"""
Tela do Modo Foco (Pomodoro) com navegação
"""
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QFont, QPalette, QColor, QPainter, QPen
import logging

logger = logging.getLogger('GLaDOS.UI.FocusView')


class FocusView(QWidget):
    """Tela do modo foco com timer Pomodoro e navegação"""
    
    # Sinais
    session_started = pyqtSignal()
    session_paused = pyqtSignal()
    session_completed = pyqtSignal(dict)
    navigate_to = pyqtSignal(str)  # Novo sinal para navegação
    
    def __init__(self, controller=None):
        super().__init__()
        self.controller = controller
        self.timer = QTimer()
        self.time_left = 25 * 60  # 25 minutos em segundos
        self.is_running = False
        self.session_type = 'focus'  # focus, short_break, long_break
        
        self.setup_ui()
        self.setup_connections()
        
        logger.info("FocusView inicializada")
    
    def setup_ui(self):
        """Configura interface do modo foco com navegação"""
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(24, 24, 24, 24)
        main_layout.setSpacing(24)
        
        # Cabeçalho com navegação
        header_layout = QHBoxLayout()
        
        # Botão voltar
        back_button = QPushButton("← Voltar")
        back_button.setObjectName("navigation_button")
        back_button.clicked.connect(lambda: self.navigate_to.emit('dashboard'))
        
        # Título
        self.title_label = QLabel("🎯 Modo Foco Filosófico")
        self.title_label.setObjectName("view_title")
        self.title_label.setFont(QFont("FiraCode Nerd Font Propo", 18, QFont.Weight.Medium))
        
        header_layout.addWidget(back_button)
        header_layout.addStretch()
        header_layout.addWidget(self.title_label)
        header_layout.addStretch()
        
        main_layout.addLayout(header_layout)
        
        # Separador
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        separator.setStyleSheet("background-color: #252A32; height: 1px;")
        main_layout.addWidget(separator)
        
        # Timer circular
        self.timer_widget = CircularTimerWidget()
        main_layout.addWidget(self.timer_widget, 1, Qt.AlignmentFlag.AlignCenter)
        
        # Status da sessão
        self.status_label = QLabel("Pronto para começar sua sessão de foco")
        self.status_label.setObjectName("focus_status")
        self.status_label.setFont(QFont("FiraCode Nerd Font Propo", 12))
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(self.status_label)
        
        # Citação filosófica
        self.quote_label = QLabel('"A mente que se abre a uma nova ideia jamais voltará ao seu tamanho original."\n- Albert Einstein')
        self.quote_label.setObjectName("focus_quote")
        self.quote_label.setFont(QFont("FiraCode Nerd Font Propo", 10))
        self.quote_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.quote_label.setWordWrap(True)
        main_layout.addWidget(self.quote_label)
        
        # Controles
        controls_layout = QHBoxLayout()
        controls_layout.setSpacing(16)
        
        self.start_button = QPushButton("▶ Iniciar")
        self.start_button.setObjectName("focus_start_button")
        self.start_button.setFont(QFont("FiraCode Nerd Font Propo", 10))
        self.start_button.setFixedSize(100, 40)
        
        self.pause_button = QPushButton("⏸ Pausar")
        self.pause_button.setObjectName("focus_pause_button")
        self.pause_button.setFont(QFont("FiraCode Nerd Font Propo", 10))
        self.pause_button.setFixedSize(100, 40)
        self.pause_button.setEnabled(False)
        
        self.reset_button = QPushButton("↺ Reiniciar")
        self.reset_button.setObjectName("focus_reset_button")
        self.reset_button.setFont(QFont("FiraCode Nerd Font Propo", 10))
        self.reset_button.setFixedSize(100, 40)
        
        self.skip_button = QPushButton("⏭ Pular")
        self.skip_button.setObjectName("focus_skip_button")
        self.skip_button.setFont(QFont("FiraCode Nerd Font Propo", 10))
        self.skip_button.setFixedSize(100, 40)
        
        controls_layout.addStretch()
        controls_layout.addWidget(self.start_button)
        controls_layout.addWidget(self.pause_button)
        controls_layout.addWidget(self.reset_button)
        controls_layout.addWidget(self.skip_button)
        controls_layout.addStretch()
        
        main_layout.addLayout(controls_layout)
        
        # Navegação rápida
        nav_label = QLabel("🚀 Navegação Rápida")
        nav_label.setObjectName("section_title")
        nav_label.setFont(QFont("FiraCode Nerd Font Propo", 12, QFont.Weight.Medium))
        main_layout.addWidget(nav_label)
        
        nav_layout = QHBoxLayout()
        nav_layout.setSpacing(12)
        
        nav_buttons = [
            ("📚 Biblioteca", "library"),
            ("📅 Agenda", "agenda"),
            ("🧠 Conceitos", "concepts"),
            ("📊 Dashboard", "dashboard"),
        ]
        
        for text, target in nav_buttons:
            btn = QPushButton(text)
            btn.setObjectName("nav_quick_button")
            btn.setFont(QFont("FiraCode Nerd Font Propo", 9))
            btn.clicked.connect(lambda checked, t=target: self.navigate_to.emit(t))
            nav_layout.addWidget(btn)
        
        nav_layout.addStretch()
        main_layout.addLayout(nav_layout)
        
        # Estatísticas da sessão
        stats_frame = QFrame()
        stats_frame.setObjectName("focus_stats_frame")
        stats_layout = QHBoxLayout()
        
        self.sessions_label = QLabel("Sessões hoje: 0")
        self.sessions_label.setObjectName("focus_stats")
        self.sessions_label.setFont(QFont("FiraCode Nerd Font Propo", 9))
        
        self.total_time_label = QLabel("Tempo total: 0min")
        self.total_time_label.setObjectName("focus_stats")
        self.total_time_label.setFont(QFont("FiraCode Nerd Font Propo", 9))
        
        self.productivity_label = QLabel("Produtividade: 100%")
        self.productivity_label.setObjectName("focus_stats")
        self.productivity_label.setFont(QFont("FiraCode Nerd Font Propo", 9))
        
        stats_layout.addWidget(self.sessions_label)
        stats_layout.addWidget(self.total_time_label)
        stats_layout.addWidget(self.productivity_label)
        stats_frame.setLayout(stats_layout)
        
        main_layout.addWidget(stats_frame)
        
        # Botão tela cheia
        fullscreen_btn = QPushButton("🖥️ Tela Cheia")
        fullscreen_btn.setObjectName("secondary_button")
        fullscreen_btn.setFont(QFont("FiraCode Nerd Font Propo", 9))
        fullscreen_btn.clicked.connect(self.enter_fullscreen)
        main_layout.addWidget(fullscreen_btn, 0, Qt.AlignmentFlag.AlignCenter)
        
        self.setLayout(main_layout)
    
    def setup_connections(self):
        """Configura conexões de sinais"""
        self.start_button.clicked.connect(self.start_session)
        self.pause_button.clicked.connect(self.pause_session)
        self.reset_button.clicked.connect(self.reset_session)
        self.skip_button.clicked.connect(self.skip_session)
        
        self.timer.timeout.connect(self.update_timer)
        
        if self.controller and hasattr(self.controller, 'session_updated'):
            self.controller.session_updated.connect(self.on_session_updated)
    
    def start_session(self):
        """Inicia a sessão de foco"""
        if not self.is_running:
            self.is_running = True
            self.timer.start(1000)  # Atualizar a cada segundo
            
            self.start_button.setEnabled(False)
            self.pause_button.setEnabled(True)
            self.reset_button.setEnabled(True)
            
            self.status_label.setText("Foco ativo - Mantenha a concentração")
            self.session_started.emit()
            
            logger.info("Sessão de foco iniciada")
    
    def pause_session(self):
        """Pausa a sessão"""
        if self.is_running:
            self.is_running = False
            self.timer.stop()
            
            self.start_button.setEnabled(True)
            self.pause_button.setEnabled(False)
            
            self.status_label.setText("Sessão pausada")
            self.session_paused.emit()
            
            logger.info("Sessão de foco pausada")
    
    def reset_session(self):
        """Reinicia a sessão"""
        self.is_running = False
        self.timer.stop()
        
        if self.session_type == 'focus':
            self.time_left = 25 * 60
        elif self.session_type == 'short_break':
            self.time_left = 5 * 60
        elif self.session_type == 'long_break':
            self.time_left = 15 * 60
        
        self.update_display()
        
        self.start_button.setEnabled(True)
        self.pause_button.setEnabled(False)
        
        self.status_label.setText("Sessão reiniciada - Pronto para começar")
        
        logger.info("Sessão de foco reiniciada")
    
    def skip_session(self):
        """Pula para a próxima sessão"""
        # Alternar entre foco e intervalos
        if self.session_type == 'focus':
            self.session_type = 'short_break'
            self.time_left = 5 * 60
        elif self.session_type == 'short_break':
            self.session_type = 'focus'
            self.time_left = 25 * 60
        # Nota: Implementar lógica para intervalos longos após várias sessões
        
        self.reset_session()
        self.start_session()
        
        logger.info(f"Sessão pulada, novo tipo: {self.session_type}")
    
    def update_timer(self):
        """Atualiza o timer a cada segundo"""
        if self.time_left > 0:
            self.time_left -= 1
            self.update_display()
        else:
            self.complete_session()
    
    def update_display(self):
        """Atualiza a exibição do timer"""
        minutes = self.time_left // 60
        seconds = self.time_left % 60
        
        self.timer_widget.set_time(minutes, seconds)
        
        # Atualizar título baseado no tipo de sessão
        if self.session_type == 'focus':
            session_name = "Foco Filosófico"
        elif self.session_type == 'short_break':
            session_name = "Intervalo Curto"
        else:
            session_name = "Intervalo Longo"
        
        self.title_label.setText(f"🎯 Modo {session_name}")
    
    def complete_session(self):
        """Completa a sessão atual"""
        self.is_running = False
        self.timer.stop()
        
        # Coletar estatísticas
        stats = {
            'type': self.session_type,
            'duration': 25 if self.session_type == 'focus' else 5,
            'completed_at': self.get_current_timestamp()
        }
        
        self.session_completed.emit(stats)
        
        # Preparar próxima sessão
        if self.session_type == 'focus':
            self.status_label.setText("Sessão completada! Hora de um intervalo.")
            # Mudar para intervalo curto
            self.session_type = 'short_break'
            self.time_left = 5 * 60
        else:
            self.status_label.setText("Intervalo finalizado! Volte ao foco.")
            # Mudar para foco
            self.session_type = 'focus'
            self.time_left = 25 * 60
        
        self.update_display()
        
        self.start_button.setEnabled(True)
        self.pause_button.setEnabled(False)
        
        logger.info(f"Sessão {self.session_type} completada")
    
    def on_session_updated(self, data):
        """Atualiza com dados do controller"""
        # Atualizar estatísticas
        if 'sessions_today' in data:
            self.sessions_label.setText(f"Sessões hoje: {data['sessions_today']}")
        
        if 'total_time' in data:
            self.total_time_label.setText(f"Tempo total: {data['total_time']}min")
        
        if 'productivity' in data:
            self.productivity_label.setText(f"Produtividade: {data['productivity']}%")
    
    def get_current_timestamp(self):
        """Retorna timestamp atual formatado"""
        from datetime import datetime
        return datetime.now().isoformat()
    
    def enter_fullscreen(self):
        """Ativa modo tela cheia"""
        self.showFullScreen()
        logger.info("Modo foco em tela cheia")
    
    def exit_fullscreen(self):
        """Sai do modo tela cheia"""
        self.showNormal()
        logger.info("Modo foco saiu da tela cheia")
    
    def start_fullscreen_session(self):
        """Inicia sessão em tela cheia"""
        self.enter_fullscreen()
        self.start_session()
    
    def on_view_activated(self):
        """Chamado quando a view é ativada"""
        # Atualizar estatísticas
        if self.controller and hasattr(self.controller, 'get_session_stats'):
            stats = self.controller.get_session_stats()
            self.on_session_updated(stats)
    
    def refresh(self):
        """Atualiza a view"""
        self.on_view_activated()
    
    def cleanup(self):
        """Limpeza antes de fechar"""
        if self.is_running:
            self.pause_session()


class CircularTimerWidget(QWidget):
    """Widget de timer circular customizado"""
    
    def __init__(self, size=300):
        super().__init__()
        self.size = size
        self.minutes = 25
        self.seconds = 0
        self.setFixedSize(size, size)
        
        # Cores
        self.bg_color = QColor(37, 42, 50)  # #252A32
        self.progress_color = QColor(99, 102, 241)  # #6366F1 (índigo)
        self.text_color = QColor(228, 231, 235)     # #E4E7EB
    
    def set_time(self, minutes: int, seconds: int):
        """Define o tempo atual"""
        self.minutes = minutes
        self.seconds = seconds
        self.update()  # Forçar repaint
    
    def paintEvent(self, event):
        """Desenha o timer circular"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Calcular geometria
        center = self.rect().center()
        radius = min(self.width(), self.height()) // 2 - 10
        
        # Desenhar fundo do círculo
        painter.setPen(QPen(self.bg_color, 8))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(center, radius, radius)
        
        # Calcular ângulo do progresso
        if self.minutes >= 25:  # Sessão de foco
            total_seconds = 25 * 60
            current_seconds = 25 * 60
        elif self.minutes >= 5:  # Intervalo curto
            total_seconds = 5 * 60
            current_seconds = self.minutes * 60 + self.seconds
        else:  # Intervalo longo
            total_seconds = 15 * 60
            current_seconds = self.minutes * 60 + self.seconds
        
        if total_seconds > 0:
            progress = current_seconds / total_seconds
            angle = int(progress * 360 * 16)
        else:
            angle = 0
        
        # Desenhar arco de progresso
        pen = QPen(self.progress_color, 8)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        painter.drawArc(
            center.x() - radius,
            center.y() - radius,
            radius * 2,
            radius * 2,
            90 * 16,  # Começar do topo (90 graus)
            -angle    # Sentido horário
        )
        
        # Texto do tempo
        painter.setPen(self.text_color)
        font = QFont("FiraCode Nerd Font Propo", 32, QFont.Weight.Medium)
        painter.setFont(font)
        
        time_text = f"{self.minutes:02d}:{self.seconds:02d}"
        painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, time_text)
        
        # Texto secundário
        font_small = QFont("FiraCode Nerd Font Propo", 14)
        painter.setFont(font_small)
        
        if self.minutes >= 25:
            session_text = "Foco"
        elif self.minutes >= 5:
            session_text = "Intervalo"
        else:
            session_text = "Intervalo Longo"
        
        painter.drawText(
            self.rect().adjusted(0, 60, 0, 0),
            Qt.AlignmentFlag.AlignCenter,
            session_text
        )