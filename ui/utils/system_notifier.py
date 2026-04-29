"""
Notificacoes nativas do sistema operacional.
"""
from __future__ import annotations

import logging
import shutil
import subprocess
import sys

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QFont, QIcon, QPainter, QPixmap
from PyQt6.QtWidgets import QApplication, QSystemTrayIcon, QWidget
from ui.utils.nerd_icons import NerdIcons, nerd_font

logger = logging.getLogger("GLaDOS.UI.SystemNotifier")


class SystemNotifier:
    """Encapsula notificacoes nativas com fallback via Qt."""

    DEFAULT_TIMEOUT_MS = 5000

    def __init__(self, parent: QWidget | None = None, app_name: str = "GLaDOS's Planner"):
        self._parent = parent
        self._app_name = str(app_name or "GLaDOS's Planner").strip() or "GLaDOS's Planner"
        self._tray_icon: QSystemTrayIcon | None = None
        self._icon = self._resolve_icon(parent)

    def icon(self) -> QIcon:
        """Retorna o icone usado pelas notificacoes nativas."""
        return self._icon

    def set_tray_icon(self, tray_icon: QSystemTrayIcon | None) -> None:
        """Permite compartilhar um unico QSystemTrayIcon com a janela principal."""
        self._tray_icon = tray_icon

    def notify(
        self,
        notif_type: str,
        title: str,
        message: str,
        timeout_ms: int | None = None,
    ) -> bool:
        """Dispara uma notificacao nativa do sistema operacional."""
        normalized_type = self._normalize_type(notif_type)
        clean_title = self._compact_text(title, fallback=self._app_name, max_len=80)
        clean_message = self._compact_text(message, fallback="", max_len=240)
        timeout = max(1000, int(timeout_ms or self.DEFAULT_TIMEOUT_MS))

        command = self._build_platform_command(
            platform_name=sys.platform,
            app_name=self._app_name,
            notif_type=normalized_type,
            title=clean_title,
            message=clean_message,
            timeout_ms=timeout,
        )

        if command:
            try:
                subprocess.Popen(
                    command,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    start_new_session=True,
                )
                return True
            except Exception as exc:
                logger.warning("Falha ao enviar notificacao nativa via comando do SO: %s", exc)

        tray_icon = self._ensure_tray_icon()
        if tray_icon:
            try:
                tray_icon.showMessage(
                    clean_title,
                    clean_message,
                    self._qt_message_icon(normalized_type),
                    timeout,
                )
                return True
            except Exception as exc:
                logger.warning("Falha ao enviar notificacao via QSystemTrayIcon: %s", exc)

        logger.warning("Nenhum backend de notificacao nativa ficou disponivel.")
        return False

    def _ensure_tray_icon(self) -> QSystemTrayIcon | None:
        if self._tray_icon is not None:
            return self._tray_icon
        if not QSystemTrayIcon.isSystemTrayAvailable():
            return None

        tray_icon = QSystemTrayIcon(self._icon, self._parent)
        tray_icon.setToolTip(self._app_name)
        tray_icon.show()
        self._tray_icon = tray_icon
        return tray_icon

    def _resolve_icon(self, parent: QWidget | None) -> QIcon:
        if parent is not None and not parent.windowIcon().isNull():
            return parent.windowIcon()

        app = QApplication.instance()
        if app is not None:
            app_icon = app.windowIcon()
            if not app_icon.isNull():
                return app_icon

        return self._build_fallback_icon()

    @classmethod
    def _build_platform_command(
        cls,
        platform_name: str,
        app_name: str,
        notif_type: str,
        title: str,
        message: str,
        timeout_ms: int,
    ) -> list[str] | None:
        if platform_name.startswith("linux"):
            executable = shutil.which("notify-send")
            if not executable:
                return None
            return [
                executable,
                "-a",
                app_name,
                "-u",
                cls._linux_urgency(notif_type),
                "-t",
                str(timeout_ms),
                "-i",
                cls._linux_icon_name(notif_type),
                title,
                message or " ",
            ]

        if platform_name == "darwin":
            executable = shutil.which("osascript")
            if not executable:
                return None
            body = cls._escape_applescript(message or title)
            clean_title = cls._escape_applescript(title)
            clean_app_name = cls._escape_applescript(app_name)
            script = (
                f'display notification "{body}" '
                f'with title "{clean_title}" '
                f'subtitle "{clean_app_name}"'
            )
            return [executable, "-e", script]

        return None

    @staticmethod
    def _qt_message_icon(notif_type: str) -> QSystemTrayIcon.MessageIcon:
        mapping = {
            "error": QSystemTrayIcon.MessageIcon.Critical,
            "warning": QSystemTrayIcon.MessageIcon.Warning,
            "success": QSystemTrayIcon.MessageIcon.Information,
            "info": QSystemTrayIcon.MessageIcon.Information,
        }
        return mapping.get(notif_type, QSystemTrayIcon.MessageIcon.NoIcon)

    @staticmethod
    def _linux_urgency(notif_type: str) -> str:
        return {
            "error": "critical",
            "warning": "normal",
            "success": "low",
            "info": "low",
        }.get(notif_type, "normal")

    @staticmethod
    def _linux_icon_name(notif_type: str) -> str:
        return {
            "error": "dialog-error",
            "warning": "dialog-warning",
            "success": "dialog-information",
            "info": "dialog-information",
        }.get(notif_type, "dialog-information")

    @staticmethod
    def _normalize_type(notif_type: str) -> str:
        value = str(notif_type or "info").strip().lower()
        return value if value in {"error", "warning", "success", "info"} else "info"

    @staticmethod
    def _compact_text(value: str, fallback: str, max_len: int) -> str:
        text = " ".join(str(value or "").split()).strip()
        if not text:
            text = str(fallback or "").strip()
        if len(text) > max_len:
            return text[: max_len - 3].rstrip() + "..."
        return text

    @staticmethod
    def _escape_applescript(value: str) -> str:
        return str(value or "").replace("\\", "\\\\").replace('"', '\\"')

    @staticmethod
    def _build_fallback_icon() -> QIcon:
        icon = QIcon()
        glyph = NerdIcons.CALENDAR

        for size in (16, 18, 20, 22, 24, 32, 48, 64):
            pixmap = QPixmap(size, size)
            pixmap.fill(Qt.GlobalColor.transparent)

            painter = QPainter(pixmap)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
            painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)

            # Leve sombra para manter contraste em trays claras.
            shadow_font = nerd_font(
                max(9, int(size * 0.72)),
                weight=QFont.Weight.Bold,
            )
            painter.setFont(shadow_font)
            painter.setPen(QColor(10, 36, 64, 90))
            shadow_rect = pixmap.rect().adjusted(1, 1, 0, 0)
            painter.drawText(shadow_rect, Qt.AlignmentFlag.AlignCenter, glyph)

            painter.setPen(QColor("#69B9FF"))
            painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, glyph)
            painter.end()

            icon.addPixmap(pixmap)

        return icon
