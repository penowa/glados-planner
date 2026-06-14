"""
Sistema de animações para interface PyQt6
"""
import logging
import math
from typing import List, Optional, Union

from PyQt6.QtCore import (
    QEasingCurve,
    QParallelAnimationGroup,
    QPoint,
    QPointF,
    QPropertyAnimation,
    QRect,
    QRectF,
    QSequentialAnimationGroup,
    QTimer,
    Qt,
    pyqtProperty,
    pyqtSignal,
)
from PyQt6.QtGui import (
    QColor,
    QBrush,
    QFont,
    QLinearGradient,
    QPainter,
    QPen,
    QPixmap,
    QPolygonF,
    QRadialGradient,
)
from PyQt6.QtWidgets import QLabel, QVBoxLayout, QWidget

logger = logging.getLogger('GLaDOS.UI.Animations')


class PortalSpinner(QWidget):
    """Animacao inspirada em Portal para a splash screen."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._phase = 0.0
        self._rotation = 0.0
        self.setFixedSize(420, 96)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setStyleSheet("background: transparent;")

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._advance_frame)
        self._timer.start(16)

    def _advance_frame(self) -> None:
        self._phase = (self._phase + 0.065) % (math.tau)
        self._rotation = (self._rotation + 3.6) % 360.0
        self.update()

    def stop_animation(self) -> None:
        if self._timer.isActive():
            self._timer.stop()

    def paintEvent(self, event):
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = QRectF(self.rect()).adjusted(12.0, 12.0, -12.0, -12.0)
        center_y = rect.center().y()
        left_portal = QPointF(rect.left() + 58.0, center_y)
        right_portal = QPointF(rect.right() - 58.0, center_y)
        travel_start = left_portal.x()
        travel_end = right_portal.x()
        motion = (math.sin(self._phase) + 1.0) / 2.0
        core_x = travel_start + ((travel_end - travel_start) * motion)
        core_center = QPointF(core_x, center_y)

        marker_pen = QPen(QColor(210, 216, 224, 65))
        marker_pen.setWidthF(1.4)
        painter.setPen(marker_pen)
        for index in range(1, 8):
            marker_x = rect.left() + ((rect.width() / 8.0) * index)
            painter.drawLine(QPointF(marker_x, center_y - 5.0), QPointF(marker_x, center_y + 5.0))

        self._draw_portal(painter, left_portal, QColor(80, 168, 255), 0.7)
        self._draw_portal(painter, right_portal, QColor(255, 148, 54), -0.7)

        for step in range(1, 5):
            trail_motion = (math.sin(self._phase - (step * 0.18)) + 1.0) / 2.0
            trail_x = travel_start + ((travel_end - travel_start) * trail_motion)
            trail_alpha = max(0, 110 - (step * 22))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(216, 222, 228, trail_alpha))
            painter.drawEllipse(QPointF(trail_x, center_y), 5.5 - step, 5.5 - step)

        portal_pull = max(
            math.exp(-((core_x - left_portal.x()) / 28.0) ** 2),
            math.exp(-((core_x - right_portal.x()) / 28.0) ** 2),
        )
        book_width = 24.0 - (portal_pull * 4.5) + (math.sin(self._phase * 2.4) * 0.5)
        book_height = 32.0 - (portal_pull * 5.5)

        shadow = QRadialGradient(core_center, book_height * 1.3)
        shadow.setColorAt(0.0, QColor(115, 173, 219, 55))
        shadow.setColorAt(0.55, QColor(255, 150, 70, 35))
        shadow.setColorAt(1.0, QColor(20, 24, 30, 0))
        painter.setBrush(shadow)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(core_center, book_width * 0.95, book_height * 0.95)

        painter.save()
        painter.translate(core_center)
        painter.rotate(math.sin(self._phase * 1.8) * 12.0)

        book_rect = QRectF(-book_width * 0.5, -book_height * 0.5, book_width, book_height)
        cover_gradient = QLinearGradient(book_rect.topLeft(), book_rect.topRight())
        cover_gradient.setColorAt(0.0, QColor(201, 140, 78, 245))
        cover_gradient.setColorAt(0.5, QColor(126, 79, 42, 250))
        cover_gradient.setColorAt(1.0, QColor(74, 45, 24, 250))
        painter.setBrush(cover_gradient)
        painter.setPen(QPen(QColor(244, 224, 192, 210), 1.4))
        painter.drawRoundedRect(book_rect, 4.0, 4.0)

        spine_rect = QRectF(book_rect.left(), book_rect.top(), book_width * 0.18, book_height)
        painter.setBrush(QColor(96, 58, 30, 250))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(spine_rect, 3.0, 3.0)

        page_rect = QRectF(book_rect.left() + (book_width * 0.18), book_rect.top() + 2.6, book_width * 0.72, book_height - 5.2)
        page_gradient = QLinearGradient(page_rect.topLeft(), page_rect.bottomRight())
        page_gradient.setColorAt(0.0, QColor(245, 239, 224, 245))
        page_gradient.setColorAt(1.0, QColor(216, 205, 181, 235))
        painter.setBrush(page_gradient)
        painter.drawRoundedRect(page_rect, 2.5, 2.5)

        line_pen = QPen(QColor(133, 112, 84, 125), 1.0)
        painter.setPen(line_pen)
        for idx in range(3):
            y = page_rect.top() + 6.0 + (idx * 6.0)
            painter.drawLine(QPointF(page_rect.left() + 3.0, y), QPointF(page_rect.right() - 3.0, y))

        bookmark = QPolygonF(
            [
                QPointF(book_rect.right() - 5.0, book_rect.top() + 1.8),
                QPointF(book_rect.right() - 1.8, book_rect.top() + 1.8),
                QPointF(book_rect.right() - 1.8, book_rect.top() + 11.0),
                QPointF(book_rect.right() - 3.4, book_rect.top() + 8.4),
                QPointF(book_rect.right() - 5.0, book_rect.top() + 11.0),
            ]
        )
        painter.setBrush(QColor(84, 159, 216, 235))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawPolygon(bookmark)
        painter.restore()

        highlight = QRadialGradient(
            QPointF(core_center.x() - (book_width * 0.12), core_center.y() - (book_height * 0.18)),
            book_height * 0.7,
        )
        highlight.setColorAt(0.0, QColor(255, 255, 255, 170))
        highlight.setColorAt(1.0, QColor(255, 255, 255, 0))
        painter.setBrush(highlight)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(core_center, book_width * 0.65, book_height * 0.68)

    def _draw_portal(self, painter: QPainter, center: QPointF, color: QColor, tilt: float) -> None:
        painter.save()
        painter.translate(center)
        painter.rotate(tilt * 11.0)

        outer_rect = QRectF(-24.0, -17.0, 48.0, 34.0)
        glow_pen = QPen(QColor(color.red(), color.green(), color.blue(), 70), 10.0)
        painter.setPen(glow_pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(outer_rect)

        portal_pen = QPen(color, 4.0)
        painter.setPen(portal_pen)
        painter.drawEllipse(outer_rect)

        portal_fill = QRadialGradient(QPointF(0.0, 0.0), 21.0)
        portal_fill.setColorAt(0.0, QColor(10, 14, 19, 225))
        portal_fill.setColorAt(0.72, QColor(25, 33, 42, 170))
        portal_fill.setColorAt(1.0, QColor(color.red(), color.green(), color.blue(), 35))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(portal_fill)
        painter.drawEllipse(QRectF(-17.0, -11.0, 34.0, 22.0))

        painter.restore()


class LoadingSplash(QWidget):
    """Tela de carregamento minimalista."""

    fade_finished = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setStyleSheet("background: transparent;")
        self.assistant_name = "GLaDOS"
        self._current_status_message = "Preparando ambiente..."

        self.setup_ui()
        self.setup_animations()

        logger.info("LoadingSplash inicializada")

    def setup_ui(self):
        """Configura interface da splash screen"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(34, 26, 34, 26)
        layout.setSpacing(14)
        layout.addStretch(1)

        self.portal_spinner = PortalSpinner(self)
        layout.addWidget(self.portal_spinner, 0, Qt.AlignmentFlag.AlignHCenter)

        self.title_label = QLabel()
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title_label.setWordWrap(True)
        self.title_label.setStyleSheet(
            "background: transparent; border: none; color: #E7DBC7; "
            "font-size: 15px; font-weight: 700; letter-spacing: 0.8px;"
        )
        layout.addWidget(self.title_label)
        layout.addStretch(1)

        self.setFixedSize(560, 210)
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
        self.title_label.setText(f"{self.assistant_name} esta configurando seu planner")

    def show_message(self, message: str):
        """Mantem compatibilidade com chamadas legadas sem alterar a UI."""
        cleaned_message = str(message or "").strip()
        if cleaned_message:
            self._current_status_message = cleaned_message
        logger.debug("Splash status atualizado: %s", self._current_status_message)

    def set_identity(self, user_name: str, assistant_name: str):
        """Atualiza nome do assistente na mensagem fixa."""
        del user_name
        assistant = (assistant_name or "").strip() or "GLaDOS"
        self.assistant_name = assistant
        self._apply_fixed_message()

    def paintEvent(self, event):
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        panel_rect = QRectF(self.rect()).adjusted(7.0, 7.0, -7.0, -7.0)
        shadow_rect = panel_rect.adjusted(0.0, 6.0, 0.0, 6.0)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(4, 8, 12, 48))
        painter.drawRoundedRect(shadow_rect, 28.0, 28.0)

        glow_left = QRadialGradient(
            QPointF(panel_rect.left() + 90.0, panel_rect.top() + 72.0),
            panel_rect.width() * 0.56,
        )
        glow_left.setColorAt(0.0, QColor(80, 168, 255, 52))
        glow_left.setColorAt(1.0, QColor(80, 168, 255, 0))
        painter.setBrush(glow_left)
        painter.drawRoundedRect(panel_rect, 28.0, 28.0)

        glow_right = QRadialGradient(
            QPointF(panel_rect.right() - 90.0, panel_rect.top() + 72.0),
            panel_rect.width() * 0.56,
        )
        glow_right.setColorAt(0.0, QColor(255, 148, 54, 56))
        glow_right.setColorAt(1.0, QColor(255, 148, 54, 0))
        painter.setBrush(glow_right)
        painter.drawRoundedRect(panel_rect, 28.0, 28.0)

        panel_fill = QLinearGradient(panel_rect.topLeft(), panel_rect.bottomRight())
        panel_fill.setColorAt(0.0, QColor(23, 30, 38, 210))
        panel_fill.setColorAt(0.5, QColor(14, 19, 26, 194))
        panel_fill.setColorAt(1.0, QColor(10, 15, 21, 204))
        painter.setBrush(panel_fill)
        painter.drawRoundedRect(panel_rect, 28.0, 28.0)

        sheen_rect = QRectF(
            panel_rect.left() + 18.0,
            panel_rect.top() + 16.0,
            panel_rect.width() - 36.0,
            26.0,
        )
        sheen = QLinearGradient(sheen_rect.topLeft(), sheen_rect.bottomRight())
        sheen.setColorAt(0.0, QColor(255, 255, 255, 55))
        sheen.setColorAt(1.0, QColor(255, 255, 255, 0))
        painter.setBrush(sheen)
        painter.drawRoundedRect(sheen_rect, 13.0, 13.0)

        border = QLinearGradient(panel_rect.topLeft(), panel_rect.bottomRight())
        border.setColorAt(0.0, QColor(80, 168, 255, 148))
        border.setColorAt(0.45, QColor(228, 232, 236, 68))
        border.setColorAt(1.0, QColor(255, 148, 54, 152))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QPen(QBrush(border), 1.3))
        painter.drawRoundedRect(panel_rect, 28.0, 28.0)

    def show(self):
        """Mostra a splash screen com animação de fade in"""
        super().show()
        self.raise_()
        self.activateWindow()

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

    def set_progress(self, percent: int):
        """Mantem compatibilidade com o fluxo legado da splash."""
        del percent

    def closeEvent(self, event):
        self.portal_spinner.stop_animation()
        super().closeEvent(event)

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
