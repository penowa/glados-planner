# ui/widgets/cards/next_reading_session_card.py
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                            QPushButton, QSizePolicy, QProgressBar)
from PyQt6.QtCore import Qt, pyqtSignal, QSize, QTimer, QPropertyAnimation, QEasingCurve, QRect
from PyQt6.QtGui import QPixmap, QPainter, QColor, QLinearGradient, QFont, QBrush, QPen
import hashlib
from datetime import datetime, timedelta

from .base_card import PhilosophyCard

class NextReadingSessionCard(PhilosophyCard):
    """Card para exibir apenas a próxima sessão de leitura agendada com animações"""
    
    # Sinais específicos para sessão
    start_session = pyqtSignal(dict)      # Iniciar sessão
    pause_session = pyqtSignal(dict)      # Pausar sessão
    edit_session = pyqtSignal(dict)       # Editar sessão
    skip_session = pyqtSignal(dict)       # Pular sessão
    
    def __init__(self, session_data: dict = None, parent=None):
        # Inicializar animações específicas como None
        self.progress_animation = None
        self.status_pulse_animation = None
        self.button_pulse_animation = None
        self.timer_fade_animation = None
        self.highlight_animation = None
        
        # Inicializar estado
        self.session_data = session_data or self._get_default_session()
        self.is_active = False
        self.time_elapsed = 0  # segundos
        self._timer_opacity = 1.0
        
        # Inicializar base
        super().__init__(parent)
        
        # Timers e estado
        self.session_timer = QTimer()
        self.session_timer.timeout.connect(self._update_timer_display)
        
        # Configurar UI e animações
        self.setup_ui()
        self.setup_connections()
        
        # Atualizar estado inicial
        self._update_session_state()

    def setup_ui(self):
        """Configurar interface do card de sessão"""
        # Tamanho fixo para consistência
        self.setFixedSize(320, 240)
        
        # Título da sessão com indicador de status
        title_widget = QWidget()
        title_layout = QHBoxLayout(title_widget)
        title_layout.setContentsMargins(0, 0, 0, 0)
        
        # Indicador de status (círculo colorido)
        self.status_indicator = QLabel()
        self.status_indicator.setFixedSize(12, 12)
        title_layout.addWidget(self.status_indicator)
        
        title = self._get_session_title()
        self.title_label.setText(title)
        self.title_label.setObjectName("session_title")
        title_layout.addWidget(self.title_label)
        title_layout.addStretch()
        
        # Remover widgets existentes do layout de conteúdo
        while self.content_layout.count():
            child = self.content_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        
        self.content_layout.addWidget(title_widget)
        
        # Área de conteúdo específica da sessão
        self.setup_session_content()
        
        # Rodapé com botões de ação
        self.setup_session_footer()
        
    def setup_session_content(self):
        """Configurar conteúdo específico da sessão"""
        content_widget = QWidget()
        layout = QVBoxLayout(content_widget)
        layout.setSpacing(10)
        
        # Container do livro com efeito de elevação
        book_container = QWidget()
        book_container.setObjectName("book_container")
        book_container.setFixedHeight(60)
        book_layout = QVBoxLayout(book_container)
        book_layout.setContentsMargins(12, 8, 12, 8)
        
        # Informações do livro
        self.book_info_label = QLabel(self._get_book_info())
        self.book_info_label.setObjectName("book_info")
        self.book_info_label.setWordWrap(True)
        book_layout.addWidget(self.book_info_label)
        
        layout.addWidget(book_container)
        
        # Informações da sessão em grid
        info_widget = QWidget()
        info_layout = QHBoxLayout(info_widget)
        info_layout.setContentsMargins(0, 5, 0, 5)
        
        # Tempo
        time_widget = QWidget()
        time_layout = QVBoxLayout(time_widget)
        time_layout.setContentsMargins(0, 0, 0, 0)
        time_icon = QLabel("⏰")
        time_icon.setObjectName("info_icon")
        self.time_info_label = QLabel(self._get_time_info())
        self.time_info_label.setObjectName("time_info")
        time_layout.addWidget(time_icon)
        time_layout.addWidget(self.time_info_label)
        info_layout.addWidget(time_widget)
        
        # Separador
        separator = QLabel("•")
        separator.setObjectName("separator")
        info_layout.addWidget(separator)
        
        # Progresso
        progress_widget = QWidget()
        progress_layout = QVBoxLayout(progress_widget)
        progress_layout.setContentsMargins(0, 0, 0, 0)
        progress_icon = QLabel("📖")
        progress_icon.setObjectName("info_icon")
        self.progress_label = QLabel(self._get_progress_info())
        self.progress_label.setObjectName("progress_info")
        progress_layout.addWidget(progress_icon)
        progress_layout.addWidget(self.progress_label)
        info_layout.addWidget(progress_widget)
        
        layout.addWidget(info_widget)
        
        # Barra de progresso da sessão com animação
        progress_container = QWidget()
        progress_container_layout = QVBoxLayout(progress_container)
        progress_container_layout.setContentsMargins(0, 5, 0, 5)
        
        self.session_progress = QProgressBar()
        self.session_progress.setTextVisible(True)
        self.session_progress.setFormat("📄 %v/%m páginas")
        self.session_progress.setValue(self.session_data.get('pages_read', 0))
        self.session_progress.setMaximum(self.session_data.get('target_pages', 30))
        self.session_progress.setObjectName("session_progress")
        progress_container_layout.addWidget(self.session_progress)
        
        layout.addWidget(progress_container)
        
        # Timer de sessão (visível apenas quando ativa)
        timer_container = QWidget()
        timer_layout = QVBoxLayout(timer_container)
        timer_layout.setContentsMargins(0, 5, 0, 0)
        
        self.timer_label = QLabel("00:00")
        self.timer_label.setObjectName("timer_display")
        self.timer_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.timer_label.setVisible(False)
        timer_layout.addWidget(self.timer_label)
        
        layout.addWidget(timer_container)
        
        self.content_layout.addWidget(content_widget)
        
    def setup_session_footer(self):
        """Configurar rodapé com botões de ação da sessão"""
        # Botão de iniciar/pausar
        self.start_pause_button = QPushButton("▶ Iniciar")
        self.start_pause_button.setObjectName("primary_action_button")
        self.start_pause_button.setFixedHeight(32)
        self.start_pause_button.setCursor(Qt.CursorShape.PointingHandCursor)
        
        # Botão de editar
        self.edit_button = QPushButton("✏")
        self.edit_button.setObjectName("icon_button")
        self.edit_button.setFixedSize(32, 32)
        self.edit_button.setToolTip("Editar sessão")
        self.edit_button.setCursor(Qt.CursorShape.PointingHandCursor)
        
        # Botão de pular
        self.skip_button = QPushButton("⏭")
        self.skip_button.setObjectName("icon_button")
        self.skip_button.setFixedSize(32, 32)
        self.skip_button.setToolTip("Pular sessão")
        self.skip_button.setCursor(Qt.CursorShape.PointingHandCursor)
        
        # Remover botões existentes do rodapé
        while self.footer_layout.count():
            child = self.footer_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        
        # Adicionar ao layout
        self.footer_layout.addWidget(self.start_pause_button)
        self.footer_layout.addWidget(self.edit_button)
        self.footer_layout.addWidget(self.skip_button)
        
    def setup_animations(self):
        """Configurar animações do card"""
        # Chamar animações da classe base primeiro
        super().setup_animations()
        
        # Só configurar animações específicas se os widgets existirem
        if hasattr(self, 'status_indicator'):
            # Animação de pulsação para sessão ativa
            self.status_pulse_animation = QPropertyAnimation(self.status_indicator, b"geometry")
            if self.status_pulse_animation:
                self.status_pulse_animation.setDuration(1000)
                self.status_pulse_animation.setLoopCount(-1)  # Loop infinito
        
        if hasattr(self, 'session_progress'):
            # Animação de progresso suave
            self.progress_animation = QPropertyAnimation(self.session_progress, b"value")
            if self.progress_animation:
                self.progress_animation.setDuration(500)
                self.progress_animation.setEasingCurve(QEasingCurve.Type.OutQuad)
        
        if hasattr(self, 'timer_label'):
            # Animação de fade in/out do timer
            self.timer_fade_animation = QPropertyAnimation(self.timer_label, b"windowOpacity")
            if self.timer_fade_animation:
                self.timer_fade_animation.setDuration(300)
        
    def setup_connections(self):
        """Conectar sinais dos botões"""
        if hasattr(self, 'start_pause_button'):
            self.start_pause_button.clicked.connect(self._toggle_session)
        if hasattr(self, 'edit_button'):
            self.edit_button.clicked.connect(lambda: self.edit_session.emit(self.session_data))
        if hasattr(self, 'skip_button'):
            self.skip_button.clicked.connect(lambda: self.skip_session.emit(self.session_data))
        
    def update_session_data(self, new_data: dict):
        """Atualizar dados da sessão com animação"""
        old_pages = self.session_data.get('pages_read', 0)
        new_pages = new_data.get('pages_read', old_pages)
        
        # Animar transição de progresso
        if old_pages != new_pages and self.progress_animation:
            self.progress_animation.setStartValue(old_pages)
            self.progress_animation.setEndValue(new_pages)
            self.progress_animation.start()
        
        self.session_data.update(new_data)
        self._update_display()
        self._update_session_state()
        
        # Feedback visual para atualização
        self._animate_update_feedback()
        
    def set_session_data(self, session_data: dict):
        """Definir novos dados de sessão com animação"""
        old_status = self.session_data.get('status')
        new_status = session_data.get('status')
        
        # Animar transição de status
        if old_status != new_status:
            self._animate_status_transition(old_status, new_status)
        
        self.session_data = session_data
        self._update_display()
        self._update_session_state()
        
    def _update_display(self):
        """Atualizar todos os elementos visuais"""
        if hasattr(self, 'title_label'):
            self.title_label.setText(self._get_session_title())
        if hasattr(self, 'book_info_label'):
            self.book_info_label.setText(self._get_book_info())
        if hasattr(self, 'time_info_label'):
            self.time_info_label.setText(self._get_time_info())
        if hasattr(self, 'progress_label'):
            self.progress_label.setText(self._get_progress_info())
        
        # Atualizar indicador de status
        self._update_status_indicator()
        
        # Atualizar barra de progresso (sem animação imediata)
        if hasattr(self, 'session_progress'):
            pages_read = self.session_data.get('pages_read', 0)
            target_pages = self.session_data.get('target_pages', 30)
            self.session_progress.setValue(pages_read)
            self.session_progress.setMaximum(target_pages)
        
    def _update_session_state(self):
        """Atualizar estado da sessão com animações"""
        self.is_active = self.session_data.get('status') == 'active'
        status = self.session_data.get('status', 'scheduled')
        
        if self.is_active:
            # Sessão ativa
            if hasattr(self, 'start_pause_button'):
                self.start_pause_button.setText("⏸ Pausar")
                self.start_pause_button.setObjectName("warning_action_button")
            
            # Mostrar timer com fade in
            if hasattr(self, 'timer_label') and not self.timer_label.isVisible():
                self.timer_label.setWindowOpacity(0)
                self.timer_label.setVisible(True)
                if self.timer_fade_animation:
                    self.timer_fade_animation.setStartValue(0)
                    self.timer_fade_animation.setEndValue(1)
                    self.timer_fade_animation.start()
            
            # Iniciar animação de pulsação do status
            self._start_status_pulse()
            
            # Iniciar timer se ainda não estiver rodando
            if self.session_timer and not self.session_timer.isActive():
                self.time_elapsed = self.session_data.get('time_elapsed', 0)
                self.session_timer.start(1000)
                
        elif status == 'completed':
            # Sessão concluída
            if hasattr(self, 'start_pause_button'):
                self.start_pause_button.setText("✓ Concluída")
                self.start_pause_button.setObjectName("success_action_button")
                self.start_pause_button.setEnabled(False)
            
            if hasattr(self, 'timer_label'):
                self.timer_label.setVisible(False)
            
            if self.session_timer:
                self.session_timer.stop()
            self._stop_status_pulse()
            
        elif status == 'paused':
            # Sessão pausada
            if hasattr(self, 'start_pause_button'):
                self.start_pause_button.setText("▶ Continuar")
                self.start_pause_button.setObjectName("primary_action_button")
            
            if hasattr(self, 'timer_label'):
                self.timer_label.setVisible(True)
            
            if self.session_timer:
                self.session_timer.stop()
            self._stop_status_pulse()
            
        else:
            # Sessão agendada
            if hasattr(self, 'start_pause_button'):
                self.start_pause_button.setText("▶ Iniciar")
                self.start_pause_button.setObjectName("primary_action_button")
                self.start_pause_button.setEnabled(True)
            
            if hasattr(self, 'timer_label'):
                self.timer_label.setVisible(False)
            
            if self.session_timer:
                self.session_timer.stop()
            self._stop_status_pulse()
            
        # Atualizar estilo dos botões
        if hasattr(self, 'start_pause_button'):
            self.start_pause_button.style().polish(self.start_pause_button)
        
    def _update_status_indicator(self):
        """Atualizar cor do indicador de status"""
        if not hasattr(self, 'status_indicator'):
            return
            
        status = self.session_data.get('status', 'scheduled')
        
        # Cores baseadas no status
        colors = {
            'scheduled': '#FFA726',  # Laranja
            'active': '#4CAF50',      # Verde
            'paused': '#2196F3',      # Azul
            'completed': '#9C27B0',   # Roxo
            'empty': '#757575'        # Cinza
        }
        
        color = colors.get(status, '#757575')
        
        # Criar pixmap com círculo colorido
        pixmap = QPixmap(12, 12)
        pixmap.fill(Qt.GlobalColor.transparent)
        
        painter = QPainter(pixmap)
        try:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter.setBrush(QColor(color))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(0, 0, 12, 12)
        finally:
            painter.end()
        
        self.status_indicator.setPixmap(pixmap)
        
    def _start_status_pulse(self):
        """Iniciar animação de pulsação do status"""
        if not hasattr(self, 'status_indicator') or not self.status_pulse_animation:
            return
            
        # Parar animação atual se estiver rodando
        if self.status_pulse_animation.state() == QPropertyAnimation.State.Running:
            self.status_pulse_animation.stop()
        
        # Configurar animação de pulsação
        current_geom = self.status_indicator.geometry()
        self.status_pulse_animation.setStartValue(current_geom)
        
        # Criar geometria expandida
        expanded = current_geom.adjusted(-2, -2, 2, 2)
        self.status_pulse_animation.setEndValue(expanded)
        
        # Adicionar keyframes para criar efeito de pulsação
        self.status_pulse_animation.setKeyValueAt(0.5, expanded)
        self.status_pulse_animation.setKeyValueAt(1, current_geom)
        
        self.status_pulse_animation.start()
        
    def _stop_status_pulse(self):
        """Parar animação de pulsação do status"""
        if self.status_pulse_animation and self.status_pulse_animation.state() == QPropertyAnimation.State.Running:
            self.status_pulse_animation.stop()
            # Restaurar tamanho original
            if hasattr(self, 'status_indicator'):
                current_geom = self.status_indicator.geometry()
                self.status_indicator.setGeometry(
                    current_geom.adjusted(2, 2, -2, -2) if current_geom.width() > 12 else current_geom
                )
                
    def _toggle_session(self):
        """Alternar entre iniciar/pausar sessão"""
        if self.session_data.get('id') == 'no_session':
            return
            
        if self.is_active:
            # Pausar sessão
            self.session_data['status'] = 'paused'
            self.session_data['time_elapsed'] = self.time_elapsed
            self.pause_session.emit(self.session_data)
            
        else:
            # Iniciar sessão
            self.session_data['status'] = 'active'
            self.session_data['start_time'] = datetime.now().isoformat()
            self.start_session.emit(self.session_data)
            
        self._update_session_state()
        
    def _update_timer_display(self):
        """Atualizar display do timer"""
        if self.is_active:
            self.time_elapsed += 1
            
            # Formatar tempo (MM:SS)
            minutes = self.time_elapsed // 60
            seconds = self.time_elapsed % 60
            
            # Animar transição do timer
            if hasattr(self, 'timer_label'):
                new_text = f"{minutes:02d}:{seconds:02d}"
                self.timer_label.setText(new_text)
            
            # Atualizar páginas lidas automaticamente (simulação)
            # Em produção, isso viria do controller
            pages_per_minute = 0.2  # Páginas por minuto (mais realista)
            if minutes > 0 and minutes % 5 == 0:  # A cada 5 minutos
                new_pages = self.session_data.get('pages_read', 0) + pages_per_minute
                if new_pages <= self.session_data.get('target_pages', 30):
                    self.session_data['pages_read'] = round(new_pages, 1)
                    
                    # Animar atualização de progresso
                    if self.progress_animation and hasattr(self, 'session_progress'):
                        self.progress_animation.setStartValue(self.session_progress.value())
                        self.progress_animation.setEndValue(new_pages)
                        self.progress_animation.start()
                        
    def _animate_update_feedback(self):
        """Animar feedback de atualização"""
        # Efeito sutil de highlight
        self.highlight_animation = QPropertyAnimation(self, b"windowOpacity")
        if self.highlight_animation:
            self.highlight_animation.setDuration(300)
            self.highlight_animation.setStartValue(0.95)
            self.highlight_animation.setEndValue(1.0)
            self.highlight_animation.setEasingCurve(QEasingCurve.Type.OutQuad)
            self.highlight_animation.start()
        
    def _animate_status_transition(self, old_status: str, new_status: str):
        """Animar transição entre status"""
        # Para transições importantes, podemos adicionar uma animação de escala
        if old_status == 'scheduled' and new_status == 'active':
            # Animação de escala para início
            start_animation = QPropertyAnimation(self, b"scale")
            start_animation.setDuration(400)
            start_animation.setStartValue(1.0)
            start_animation.setKeyValueAt(0.5, 1.05)
            start_animation.setEndValue(1.0)
            start_animation.setEasingCurve(QEasingCurve.Type.OutQuad)
            start_animation.start()
            
        elif new_status == 'completed':
            # Animação de conclusão
            complete_animation = QPropertyAnimation(self, b"scale")
            complete_animation.setDuration(600)
            complete_animation.setStartValue(1.0)
            complete_animation.setKeyValueAt(0.3, 1.08)
            complete_animation.setEndValue(1.0)
            complete_animation.setEasingCurve(QEasingCurve.Type.OutQuad)
            complete_animation.start()
            
    def _get_session_title(self):
        """Obter título da sessão"""
        status = self.session_data.get('status', 'scheduled')
        status_map = {
            'scheduled': 'Próxima Sessão',
            'active': 'Sessão em Andamento',
            'paused': 'Sessão Pausada',
            'completed': 'Sessão Concluída',
            'empty': 'Agendar Sessão'
        }
        return status_map.get(status, 'Sessão de Leitura')
        
    def _get_book_info(self):
        """Obter informações do livro formatadas"""
        title = self.session_data.get('book_title', 'Livro não especificado')
        author = self.session_data.get('book_author', 'Autor desconhecido')
        
        if self.session_data.get('id') == 'no_session':
            return "<span style='color: #888; font-style: italic;'>Nenhuma sessão agendada</span>"
        
        return f"<b>{self._truncate_text(title, 25)}</b><br><span style='color: #666;'>por {author}</span>"
        
    def _get_time_info(self):
        """Obter informações de tempo formatadas"""
        start_str = self.session_data.get('start_time')
        duration = self.session_data.get('duration_minutes', 30)
        
        if self.session_data.get('id') == 'no_session':
            return "<span style='color: #888;'>--:--</span>"
        
        if start_str:
            try:
                start_time = datetime.fromisoformat(start_str)
                time_str = start_time.strftime("%H:%M")
                return f"<b>{time_str}</b> ({duration}min)"
            except:
                return f"<b>Agendada</b> ({duration}min)"
        else:
            return "<b>Flexível</b>"
            
    def _get_progress_info(self):
        """Obter informações de progresso formatadas"""
        current = self.session_data.get('current_page', 0)
        total = self.session_data.get('total_pages', 100)
        pages_read = self.session_data.get('pages_read', 0)
        target = self.session_data.get('target_pages', 30)
        
        if self.session_data.get('id') == 'no_session':
            return "<span style='color: #888;'>--/--</span>"
        
        return f"Pág. <b>{current}/{total}</b>"
        
    def _get_default_session(self):
        """Obter dados padrão para sessão vazia"""
        return {
            'id': 'no_session',
            'book_title': 'Nenhuma sessão agendada',
            'book_author': '',
            'status': 'empty',
            'duration_minutes': 0,
            'target_pages': 0,
            'pages_read': 0,
            'current_page': 0,
            'total_pages': 0
        }
        
    def _truncate_text(self, text: str, max_length: int) -> str:
        """Truncar texto se for muito longo"""
        if len(text) > max_length:
            return text[:max_length-3] + "..."
        return text
        
    def cleanup(self):
        """Limpar recursos"""
        # Parar timers
        if hasattr(self, 'session_timer'):
            self.session_timer.stop()
        
        # Parar todas as animações específicas
        if self.status_pulse_animation:
            self.status_pulse_animation.stop()
        if self.progress_animation:
            self.progress_animation.stop()
        if self.timer_fade_animation:
            self.timer_fade_animation.stop()
        if self.highlight_animation:
            self.highlight_animation.stop()
        
        # Chamar cleanup da classe base
        super().cleanup()
            
    def paintEvent(self, event):
        """Custom paint event para efeitos visuais"""
        # Primeiro, chamar o paintEvent da classe base
        super().paintEvent(event)
        
        # Adicionar efeito de glow para sessão ativa
        if self.is_active:
            painter = QPainter(self)
            try:
                painter.setRenderHint(QPainter.RenderHint.Antialiasing)
                painter.setPen(Qt.PenStyle.NoPen)
                
                # Gradiente sutil de glow
                gradient = QLinearGradient(0, 0, self.width(), 0)
                gradient.setColorAt(0, QColor(76, 175, 80, 10))
                gradient.setColorAt(0.5, QColor(76, 175, 80, 5))
                gradient.setColorAt(1, QColor(76, 175, 80, 10))
                
                painter.setBrush(gradient)
                painter.drawRoundedRect(self.rect().adjusted(2, 2, -2, -2), 8, 8)
            finally:
                painter.end()