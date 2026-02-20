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
    """Tela de carregamento minimalista."""
    
    # Sinais
    fade_finished = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.assistant_name = "GLaDOS"
        
        self.setup_ui()
        self.setup_animations()
        
        logger.info("LoadingSplash inicializada")
    
    def setup_ui(self):
        """Configura interface da splash screen"""
        layout = QVBoxLayout()
        layout.setContentsMargins(36, 32, 36, 32)
        layout.setSpacing(14)

        self.progress_label = QLabel()
        self.progress_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.progress_label.setWordWrap(True)
        self.progress_label.setStyleSheet("color: #D8CBB5; font-size: 13px;")
        layout.addWidget(self.progress_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)  # modo indeterminado
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setFixedHeight(10)
        layout.addWidget(self.progress_bar)
        
        self.setLayout(layout)
        self.setFixedSize(520, 120)
        self._apply_fixed_message()
    
    def setup_animations(self):
        """Configura animações da splash screen"""
        self.setWindowOpacity(0)
        self.fade_in_animation = QPropertyAnimation(self, b"windowOpacity")
        self.fade_in_animation.setDuration(500)
        self.fade_in_animation.setStartValue(0)
        self.fade_in_animation.setEndValue(1)
        self.fade_in_animation.setEasingCurve(QEasingCurve.Type.InOutQuad)
    
    def _apply_fixed_message(self):
        self.progress_label.setText(f"{self.assistant_name} esta configurando seu planner")
    
    def show_message(self, message: str):
        """Mantém mensagem fixa para splash minimalista."""
        logger.debug(f"Splash message ignorada (layout fixo): {message}")
        self._apply_fixed_message()

    def set_identity(self, user_name: str, assistant_name: str):
        """Atualiza nome do assistente na mensagem fixa."""
        assistant = (assistant_name or "").strip() or "GLaDOS"
        self.assistant_name = assistant
        self._apply_fixed_message()
    
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
        super().close()
    
    def set_progress(self, percent: int):
        """Define progresso (opcional, para compatibilidade)"""
        # Esta splash screen usa animação indeterminada
        pass

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
