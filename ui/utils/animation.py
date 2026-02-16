"""
Sistema de animações para interface PyQt6
"""
from PyQt6.QtCore import QPropertyAnimation, QEasingCurve, QParallelAnimationGroup, QSequentialAnimationGroup, QTimer, pyqtSignal
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QProgressBar
from PyQt6.QtGui import QFont, QColor, QPainter, QPen, QBrush, QPixmap
from PyQt6.QtCore import Qt, QPoint, pyqtProperty, QRect
from typing import List, Optional, Union
import logging

logger = logging.getLogger('GLaDOS.UI.Animations')


class LoadingSplash(QWidget):
    """Tela de carregamento com animação personalizada"""
    
    # Sinais
    fade_finished = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        # Configurações
        self.animation_timer = QTimer()
        self.animation_timer.timeout.connect(self.update_animation)
        self.animation_step = 0
        self.dots_count = 0
        self.max_dots = 3
        self.loading_texts = [
            "Inicializando o núcleo da GLaDOS",
            "Validando configurações locais",
            "Preparando interface e tema",
            "Conectando módulos principais"
        ]
        self.current_text_index = 0
        
        self.setup_ui()
        self.setup_animations()
        
        logger.info("LoadingSplash inicializada")
    
    def setup_ui(self):
        """Configura interface da splash screen"""
        # Layout principal
        layout = QVBoxLayout()
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(20)
        
        # Título principal
        self.title_label = QLabel("GLaDOS Philosophy Planner")
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_font = QFont("Georgia", 28, QFont.Weight.Bold)
        self.title_label.setFont(title_font)
        self.title_label.setStyleSheet("color: #F5F5DC;")
        layout.addWidget(self.title_label)

        # Separador
        separator = QWidget()
        separator.setFixedHeight(2)
        separator.setStyleSheet("background-color: #8B7355;")
        layout.addWidget(separator)

        self.welcome_label = QLabel(
            "Bem-vindo ao seu planner diario. A GLaDOS esta preparando seu dia."
        )
        self.welcome_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.welcome_label.setWordWrap(True)
        self.welcome_label.setStyleSheet("color: #D8CBB5; font-size: 12px;")
        layout.addWidget(self.welcome_label)
        
        # Texto de carregamento
        self.loading_label = QLabel()
        self.loading_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        loading_font = QFont("Arial", 12)
        self.loading_label.setFont(loading_font)
        self.loading_label.setStyleSheet("color: #C9BAA6;")
        layout.addWidget(self.loading_label)
        
        # Indicador de progresso (animação customizada)
        self.progress_widget = QWidget()
        self.progress_widget.setFixedHeight(20)
        layout.addWidget(self.progress_widget)

        self.progress_label = QLabel("Boot em andamento")
        self.progress_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.progress_label.setStyleSheet("color: #B6A68D; font-size: 10px;")
        layout.addWidget(self.progress_label)
        
        # Versão e copyright
        self.version_label = QLabel("GLaDOS Planner · Vault lazy-load ativo")
        self.version_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        version_font = QFont("Arial", 9)
        self.version_label.setFont(version_font)
        self.version_label.setStyleSheet("color: #8B7355;")
        layout.addWidget(self.version_label)
        
        self.setLayout(layout)
        
        # Definir tamanho fixo
        self.setFixedSize(600, 400)
        
        # Definir texto inicial
        self.update_loading_text()
    
    def setup_animations(self):
        """Configura animações da splash screen"""
        # Timer para animação dos pontos
        self.animation_timer.start(80)  # Atualiza com mais fluidez
        
        # Fade in ao mostrar
        self.setWindowOpacity(0)
        self.fade_in_animation = QPropertyAnimation(self, b"windowOpacity")
        self.fade_in_animation.setDuration(500)
        self.fade_in_animation.setStartValue(0)
        self.fade_in_animation.setEndValue(1)
        self.fade_in_animation.setEasingCurve(QEasingCurve.Type.InOutQuad)
    
    def update_animation(self):
        """Atualiza animação dos pontos de carregamento"""
        self.animation_step += 1
        self.dots_count = (self.dots_count + 1) % (self.max_dots + 1)
        
        # Atualizar texto periodicamente
        if self.animation_step % 18 == 0:
            self.current_text_index = (self.current_text_index + 1) % len(self.loading_texts)
            self.update_loading_text()
        
        self.update()  # Forçar repaint para progresso personalizado
    
    def update_loading_text(self):
        """Atualiza texto de carregamento com pontos animados"""
        base_text = self.loading_texts[self.current_text_index]
        dots = "." * self.dots_count
        self.loading_label.setText(f"{base_text}{dots}")
        phase = (self.animation_step % 120) / 120
        self.progress_label.setText(f"Boot em andamento {int(phase * 100)}%")
    
    def paintEvent(self, event):
        """Desenha indicador de progresso personalizado"""
        super().paintEvent(event)
        
        # Desenhar progresso circular
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Posicionar no centro do widget de progresso
        progress_rect = self.progress_widget.geometry()
        center_x = progress_rect.x() + progress_rect.width() // 2
        center_y = progress_rect.y() + progress_rect.height() // 2
        radius = min(progress_rect.width(), progress_rect.height()) // 3
        
        # Fundo do círculo
        painter.setPen(QPen(QColor(50, 50, 50), 3))
        painter.setBrush(QBrush(QColor(30, 30, 30)))
        painter.drawEllipse(QPoint(center_x, center_y), radius, radius)
        
        # Arco de progresso animado
        angle = (self.animation_step * 6) % 360
        pen = QPen(QColor(85, 107, 47), 4)  # Verde oliva
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        
        # Desenhar arco
        painter.drawArc(
            center_x - radius,
            center_y - radius,
            radius * 2,
            radius * 2,
            90 * 16,  # Iniciar no topo
            -angle * 16  # Arco animado
        )
        
        # Pontos orbitais
        dot_radius = 4
        dot_count = 3
        for i in range(dot_count):
            dot_angle = angle + (i * 120)  # 3 pontos igualmente espaçados
            rad = dot_angle * 3.14159 / 180
            
            dot_x = center_x + int((radius + 10) * (1 + 0.3 * i) * math.cos(rad))
            dot_y = center_y - int((radius + 10) * (1 + 0.3 * i) * math.sin(rad))
            
            painter.setBrush(QBrush(QColor(139, 115, 85)))  # Bronze
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(QPoint(dot_x, dot_y), dot_radius, dot_radius)
    
    def show_message(self, message: str):
        """Atualiza mensagem de carregamento"""
        self.loading_texts.append(message.strip())
        self.loading_texts = self.loading_texts[-8:]
        self.current_text_index = len(self.loading_texts) - 1
        self.update_loading_text()
        self.progress_label.setText(message.strip())
        logger.debug(f"Splash message: {message}")

    def set_identity(self, user_name: str, assistant_name: str):
        """Atualiza identidade visual e texto de boas-vindas."""
        user = (user_name or "").strip() or "Usuario"
        assistant = (assistant_name or "").strip() or "GLaDOS"
        self.title_label.setText(f"{assistant} Philosophy Planner")
        self.welcome_label.setText(
            f"Bem-vindo, {user}. {assistant} esta organizando seu planner diario."
        )
    
    def show(self):
        """Mostra a splash screen com animação de fade in"""
        super().show()
        
        # Centralizar na tela
        screen = self.screen().availableGeometry()
        x = (screen.width() - self.width()) // 2
        y = (screen.height() - self.height()) // 2
        self.move(x, y)
        
        # Iniciar fade in
        self.fade_in_animation.start()
    
    def fade_out_and_close(self):
        """Animação de fade out antes de fechar"""
        self.fade_out_animation = QPropertyAnimation(self, b"windowOpacity")
        self.fade_out_animation.setDuration(500)
        self.fade_out_animation.setStartValue(1)
        self.fade_out_animation.setEndValue(0)
        self.fade_out_animation.setEasingCurve(QEasingCurve.Type.InOutQuad)
        self.fade_out_animation.finished.connect(self.close)
        self.fade_out_animation.start()
        
        self.fade_finished.emit()
    
    def close(self):
        """Fecha a splash screen"""
        self.animation_timer.stop()
        super().close()
    
    def set_progress(self, percent: int):
        """Define progresso (opcional, para compatibilidade)"""
        # Esta splash screen usa animação indeterminada
        pass


# Adicionar import de math que é usado no paintEvent
import math

# ============ CLASSES EXISTENTES (mantidas do arquivo original) ============

class FadeAnimation:
    """Animação de fade in/out"""
    
    def __init__(self, widget: QWidget, start_opacity: float, end_opacity: float, duration: int = 300):
        self.widget = widget
        self.start_opacity = start_opacity
        self.end_opacity = end_opacity
        self.duration = duration
        self.animation = None
        
    def start(self):
        """Inicia a animação"""
        self.animation = QPropertyAnimation(self.widget, b"windowOpacity")
        self.animation.setDuration(self.duration)
        self.animation.setStartValue(self.start_opacity)
        self.animation.setEndValue(self.end_opacity)
        self.animation.setEasingCurve(QEasingCurve.Type.InOutQuad)
        self.animation.start()
        
        logger.debug(f"Fade animation started: {self.start_opacity} -> {self.end_opacity}")


class SlideAnimation:
    """Animação de deslizamento entre widgets"""
    
    def __init__(self, stacked_widget, direction: str = "right_to_left"):
        self.stacked_widget = stacked_widget
        self.direction = direction
        self.animation_group = None
        
        # Mapear direções para offsets
        self.direction_offsets = {
            "right_to_left": (100, 0),
            "left_to_right": (-100, 0),
            "bottom_to_top": (0, 100),
            "top_to_bottom": (0, -100)
        }
    
    def transition_to(self, widget_name: str):
        """Transição para widget específico"""
        target_index = -1
        for i in range(self.stacked_widget.count()):
            widget = self.stacked_widget.widget(i)
            if widget.objectName() == widget_name or widget.__class__.__name__.lower() == widget_name.lower():
                target_index = i
                break
        
        if target_index == -1 or target_index == self.stacked_widget.currentIndex():
            return
        
        # Criar animação paralela
        self.animation_group = QParallelAnimationGroup()
        
        # Widget atual saindo
        current_widget = self.stacked_widget.currentWidget()
        current_pos = current_widget.pos()
        current_anim = QPropertyAnimation(current_widget, b"pos")
        
        # Widget entrando
        target_widget = self.stacked_widget.widget(target_index)
        target_widget.show()
        target_pos = target_widget.pos()
        target_anim = QPropertyAnimation(target_widget, b"pos")
        
        # Configurar animações baseadas na direção
        offset_x, offset_y = self.direction_offsets.get(self.direction, (100, 0))
        
        # Widget atual sai
        current_anim.setDuration(300)
        current_anim.setStartValue(current_pos)
        current_anim.setEndValue(QPoint(current_pos.x() - offset_x, current_pos.y() - offset_y))
        current_anim.setEasingCurve(QEasingCurve.Type.InOutQuad)
        
        # Widget alvo entra
        target_widget.move(current_pos.x() + offset_x, current_pos.y() + offset_y)
        target_anim.setDuration(300)
        target_anim.setStartValue(QPoint(current_pos.x() + offset_x, current_pos.y() + offset_y))
        target_anim.setEndValue(current_pos)
        target_anim.setEasingCurve(QEasingCurve.Type.InOutQuad)
        
        # Adicionar ao grupo
        self.animation_group.addAnimation(current_anim)
        self.animation_group.addAnimation(target_anim)
        
        # Conectar finalização
        self.animation_group.finished.connect(
            lambda: self._on_animation_finished(target_index)
        )
        
        # Iniciar animação
        self.animation_group.start()
        
        logger.debug(f"Slide animation: {self.stacked_widget.currentIndex()} -> {target_index} ({self.direction})")
    
    def _on_animation_finished(self, target_index: int):
        """Callback quando animação termina"""
        self.stacked_widget.setCurrentIndex(target_index)
        
        # Resetar posição do widget atual
        current_widget = self.stacked_widget.currentWidget()
        if current_widget:
            current_widget.move(0, 0)
        
        logger.debug(f"Slide animation finished, current index: {target_index}")


class PulseAnimation:
    """Animação de pulsação para chamar atenção"""
    
    def __init__(self, widget: QWidget, scale_factor: float = 1.1, duration: int = 500):
        self.widget = widget
        self.scale_factor = scale_factor
        self.duration = duration
        self.animation_group = QSequentialAnimationGroup()
        
        # Criar propriedade de escala personalizada
        self._scale = 1.0
        
    def start(self):
        """Inicia animação de pulsação"""
        # Animação de crescimento
        grow_anim = QPropertyAnimation(self, b"scale")
        grow_anim.setDuration(self.duration // 2)
        grow_anim.setStartValue(1.0)
        grow_anim.setEndValue(self.scale_factor)
        grow_anim.setEasingCurve(QEasingCurve.Type.OutQuad)
        
        # Animação de redução
        shrink_anim = QPropertyAnimation(self, b"scale")
        shrink_anim.setDuration(self.duration // 2)
        shrink_anim.setStartValue(self.scale_factor)
        shrink_anim.setEndValue(1.0)
        shrink_anim.setEasingCurve(QEasingCurve.Type.InQuad)
        
        # Adicionar ao grupo sequencial
        self.animation_group.addAnimation(grow_anim)
        self.animation_group.addAnimation(shrink_anim)
        
        # Conectar sinal de atualização
        self.scaleChanged.connect(self._update_widget_scale)
        
        self.animation_group.start()
        
        logger.debug(f"Pulse animation started on {self.widget.objectName()}")
    
    def stop(self):
        """Para a animação"""
        if self.animation_group:
            self.animation_group.stop()
    
    scaleChanged = pyqtProperty(float, fset=lambda self, value: setattr(self, '_scale', value))
    
    @pyqtProperty(float)
    def scale(self):
        return self._scale
    
    @scale.setter
    def scale(self, value):
        self._scale = value
        self.scaleChanged.emit(value)
    
    def _update_widget_scale(self, scale: float):
        """Atualiza escala do widget"""
        # Implementar transformação de escala
        # Nota: Para implementação completa, seria necessário usar QGraphicsTransform
        pass


class ShakeAnimation:
    """Animação de tremer (para indicar erro)"""
    
    def __init__(self, widget: QWidget, intensity: int = 10, duration: int = 400):
        self.widget = widget
        self.intensity = intensity
        self.duration = duration
        self.animation_group = QSequentialAnimationGroup()
        self.original_pos = widget.pos()
    
    def start(self):
        """Inicia animação de tremor"""
        positions = [
            QPoint(self.original_pos.x() + self.intensity, self.original_pos.y()),
            QPoint(self.original_pos.x() - self.intensity, self.original_pos.y()),
            QPoint(self.original_pos.x() + self.intensity//2, self.original_pos.y()),
            QPoint(self.original_pos.x() - self.intensity//2, self.original_pos.y()),
            self.original_pos
        ]
        
        for i, pos in enumerate(positions):
            anim = QPropertyAnimation(self.widget, b"pos")
            anim.setDuration(self.duration // len(positions))
            anim.setStartValue(self.widget.pos() if i == 0 else positions[i-1])
            anim.setEndValue(pos)
            anim.setEasingCurve(QEasingCurve.Type.InOutSine)
            self.animation_group.addAnimation(anim)
        
        self.animation_group.start()
        
        logger.debug(f"Shake animation started on {self.widget.objectName()}")
    
    def stop(self):
        """Para a animação e retorna à posição original"""
        if self.animation_group:
            self.animation_group.stop()
        
        self.widget.move(self.original_pos)


class ColorTransitionAnimation:
    """Animação de transição de cor"""
    
    def __init__(self, widget: QWidget, start_color: str, end_color: str, duration: int = 500):
        self.widget = widget
        self.start_color = start_color
        self.end_color = end_color
        self.duration = duration
        self.animation = None
    
    def start(self):
        """Inicia animação de transição de cor"""
        # Implementação simplificada
        # Para implementação completa, seria necessário criar uma propriedade
        # de cor personalizada e animá-la
        logger.debug(f"Color transition: {self.start_color} -> {self.end_color}")


class AnimationManager:
    """Gerencia todas as animações do sistema"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not hasattr(self, 'initialized'):
            self.animations = []
            self.enabled = True
            self.initialized = True
            
            logger.info("AnimationManager inicializado")
    
    def fade_in(self, widget: QWidget, duration: int = 300) -> FadeAnimation:
        """Animação de fade in"""
        if not self.enabled or widget is None:
            return None
        
        widget.setWindowOpacity(0)
        widget.show()
        
        animation = FadeAnimation(widget, 0, 1, duration)
        animation.start()
        self.animations.append(animation)
        
        return animation
    
    def fade_out(self, widget: QWidget, duration: int = 300) -> FadeAnimation:
        """Animação de fade out"""
        if not self.enabled or widget is None:
            return None
        
        animation = FadeAnimation(widget, 1, 0, duration)
        animation.start()
        self.animations.append(animation)
        
        return animation
    
    def pulse(self, widget: QWidget, scale: float = 1.1, duration: int = 500) -> PulseAnimation:
        """Animação de pulsação"""
        if not self.enabled or widget is None:
            return None
        
        animation = PulseAnimation(widget, scale, duration)
        animation.start()
        self.animations.append(animation)
        
        return animation
    
    def shake(self, widget: QWidget, intensity: int = 10, duration: int = 400) -> ShakeAnimation:
        """Animação de tremor"""
        if not self.enabled or widget is None:
            return None
        
        animation = ShakeAnimation(widget, intensity, duration)
        animation.start()
        self.animations.append(animation)
        
        return animation
    
    def enable_animations(self, enabled: bool = True):
        """Habilita ou desabilita todas as animações"""
        self.enabled = enabled
        status = "habilitadas" if enabled else "desabilitadas"
        logger.info(f"Animações {status}")
    
    def stop_all_animations(self):
        """Para todas as animações em execução"""
        for animation in self.animations:
            if hasattr(animation, 'stop'):
                animation.stop()
        
        self.animations.clear()
        logger.info("Todas as animações paradas")
    
    def get_animation_count(self) -> int:
        """Retorna número de animações ativas"""
        return len(self.animations)
