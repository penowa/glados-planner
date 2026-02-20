"""
View de biblioteca com visual superficial de livros (título + capa).
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, Optional
from datetime import datetime, timedelta

import yaml
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QAction, QColor, QFont, QLinearGradient, QPainter, QPixmap, QPen
from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMenu,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSpinBox,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from ui.widgets.cards.add_book_card import AddBookCard

logger = logging.getLogger("GLaDOS.UI.LibraryView")

try:
    from core.config.settings import settings as core_settings
except Exception:
    core_settings = None


class MetadataEditDialog(QDialog):
    """Diálogo simples para editar metadados de livro."""

    def __init__(self, metadata: Dict[str, Any], parent=None):
        super().__init__(parent)
        self.setWindowTitle("Editar metadados do livro")
        self.setModal(True)
        self.resize(460, 340)

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.title_input = QLineEdit(str(metadata.get("title", "")))
        self.author_input = QLineEdit(str(metadata.get("author", "")))
        self.pages_input = QSpinBox()
        self.pages_input.setRange(0, 100000)
        self.pages_input.setValue(int(metadata.get("total_pages", 0) or 0))
        self.year_input = QLineEdit(str(metadata.get("year", "")))
        self.publisher_input = QLineEdit(str(metadata.get("publisher", "")))
        self.isbn_input = QLineEdit(str(metadata.get("isbn", "")))
        self.language_input = QLineEdit(str(metadata.get("language", "")))
        self.genre_input = QLineEdit(str(metadata.get("genre", "")))
        tags = metadata.get("tags", [])
        self.tags_input = QLineEdit(", ".join(tags) if isinstance(tags, list) else str(tags or ""))

        form.addRow("Título:", self.title_input)
        form.addRow("Autor:", self.author_input)
        form.addRow("Páginas:", self.pages_input)
        form.addRow("Ano:", self.year_input)
        form.addRow("Editora:", self.publisher_input)
        form.addRow("ISBN:", self.isbn_input)
        form.addRow("Idioma:", self.language_input)
        form.addRow("Gênero:", self.genre_input)
        form.addRow("Tags:", self.tags_input)
        layout.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def get_data(self) -> Dict[str, Any]:
        return {
            "title": self.title_input.text().strip(),
            "author": self.author_input.text().strip(),
            "total_pages": self.pages_input.value(),
            "year": self.year_input.text().strip(),
            "publisher": self.publisher_input.text().strip(),
            "isbn": self.isbn_input.text().strip(),
            "language": self.language_input.text().strip(),
            "genre": self.genre_input.text().strip(),
            "tags": [t.strip() for t in self.tags_input.text().split(",") if t.strip()],
        }


class ScheduleDialog(QDialog):
    """Diálogo para iniciar agendamento de sessões de leitura."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Agendar sessões de leitura")
        self.setModal(True)
        self.resize(360, 180)

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.pages_per_day = QSpinBox()
        self.pages_per_day.setRange(1, 200)
        self.pages_per_day.setValue(20)

        self.strategy_combo = QComboBox()
        self.strategy_combo.addItem("Equilibrado", "balanced")
        self.strategy_combo.addItem("Intensivo", "intensive")
        self.strategy_combo.addItem("Leve", "light")

        form.addRow("Páginas por dia:", self.pages_per_day)
        form.addRow("Estratégia:", self.strategy_combo)
        layout.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def values(self) -> tuple[int, str]:
        return int(self.pages_per_day.value()), str(self.strategy_combo.currentData())


class LibraryBookTile(QFrame):
    """Card leve de livro para biblioteca."""

    open_requested = pyqtSignal(Path)
    metadata_requested = pyqtSignal(Path)
    schedule_requested = pyqtSignal(Path)
    review_requested = pyqtSignal(Path)

    def __init__(
        self,
        book_dir: Path,
        title: str,
        author: str,
        cover_path: Optional[Path],
        progress_percent: float = 0.0,
        completed: bool = False,
        progress_current: int = 0,
        progress_total: int = 0,
        badge_text: Optional[str] = None,
        parent=None
    ):
        super().__init__(parent)
        self.book_dir = book_dir
        self.title = title
        self.author = author
        self.cover_path = cover_path
        self.progress_percent = max(0.0, min(100.0, float(progress_percent or 0.0)))
        self.completed = bool(completed)
        self.progress_current = max(0, int(progress_current or 0))
        self.progress_total = max(0, int(progress_total or 0))
        self.badge_text = badge_text
        self._setup_ui()

    def _setup_ui(self):
        self.setObjectName("library_book_tile")
        self.setCursor(Qt.CursorShape.ArrowCursor)
        self.setFixedWidth(190)
        self.setFrameShape(QFrame.Shape.StyledPanel)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        self.cover_label = QLabel()
        self.cover_label.setFixedSize(170, 230)
        self.cover_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.cover_label.setCursor(Qt.CursorShape.PointingHandCursor)
        self.cover_label.setStyleSheet("border: 1px solid #2E3440; border-radius: 8px;")
        self.cover_label.mousePressEvent = self._on_cover_clicked
        self._render_cover()
        layout.addWidget(self.cover_label, alignment=Qt.AlignmentFlag.AlignHCenter)

        self.options_button = QToolButton(self.cover_label)
        self.options_button.setText("...")
        self.options_button.setFixedSize(24, 20)
        self.options_button.setStyleSheet(
            "QToolButton { background: rgba(20,20,20,0.75); color: #ECEFF4; border: 1px solid #4C566A; border-radius: 6px; font-weight: 700; }"
        )
        self.options_button.clicked.connect(self._show_options_menu)

        self.badge_label = QLabel(self.cover_label)
        self.badge_label.setStyleSheet(
            "background: rgba(46, 125, 50, 0.88); color: #ECFDF3; "
            "border: 1px solid rgba(236, 253, 243, 0.25); border-radius: 6px; "
            "font-size: 9px; font-weight: 700; padding: 1px 6px;"
        )
        self.badge_label.setVisible(False)
        if self.badge_text:
            self.badge_label.setText(self.badge_text)
            self.badge_label.adjustSize()
            self.badge_label.setVisible(True)

        self.progress_label = QLabel(self.cover_label)
        self.progress_label.setFixedSize(36, 36)
        self.progress_label.setFrameShape(QFrame.Shape.NoFrame)
        self.progress_label.setStyleSheet("background: transparent; border: none;")
        self._render_progress_indicator()

        title_label = QLabel(self.title)
        title_label.setWordWrap(True)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("font-weight: 700;")
        layout.addWidget(title_label)

        progress_text = (
            f"{self.progress_current}/{self.progress_total} páginas"
            if self.progress_total > 0
            else "0/? páginas"
        )
        progress_info_label = QLabel(progress_text)
        progress_info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        progress_info_label.setStyleSheet("color: #A7B1C2; font-size: 10px;")
        layout.addWidget(progress_info_label)

        author_label = QLabel(self.author)
        author_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        author_label.setStyleSheet("color: #8A94A6; font-size: 11px;")
        layout.addWidget(author_label)

    def _show_options_menu(self):
        menu = QMenu(self)
        edit_action = menu.addAction("Editar metadados")
        schedule_action = menu.addAction("Agendar sessões")
        review_action = menu.addAction("Abrir revisão")
        selected = menu.exec(self.options_button.mapToGlobal(self.options_button.rect().bottomLeft()))
        if selected == edit_action:
            self.metadata_requested.emit(self.book_dir)
        elif selected == schedule_action:
            self.schedule_requested.emit(self.book_dir)
        elif selected == review_action:
            self.review_requested.emit(self.book_dir)

    def _placeholder_cover(self) -> QPixmap:
        pixmap = QPixmap(self.cover_label.size())
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = pixmap.rect().adjusted(1, 1, -1, -1)
        grad = QLinearGradient(0, 0, rect.width(), rect.height())
        grad.setColorAt(0.0, QColor("#2E3440"))
        grad.setColorAt(1.0, QColor("#3B4252"))
        painter.setBrush(grad)
        painter.setPen(QColor("#4C566A"))
        painter.drawRoundedRect(rect, 8, 8)

        initials = "".join([part[0] for part in self.title.split()[:2] if part]).upper() or "BK"
        painter.setPen(QColor("#ECEFF4"))
        painter.setFont(QFont("Georgia", 24, QFont.Weight.Bold))
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, initials)
        painter.end()
        return pixmap

    def _render_cover(self):
        if self.cover_path and self.cover_path.exists():
            pixmap = QPixmap(str(self.cover_path))
            if not pixmap.isNull():
                scaled = pixmap.scaled(
                    self.cover_label.size(),
                    Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                    Qt.TransformationMode.SmoothTransformation,
                )
                self.cover_label.setPixmap(scaled)
                self.cover_label.setText("")
                return
        self.cover_label.setPixmap(self._placeholder_cover())
        self.cover_label.setText("")

    def _render_progress_indicator(self):
        size = self.progress_label.size()
        pixmap = QPixmap(size)
        pixmap.fill(Qt.GlobalColor.transparent)

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = pixmap.rect().adjusted(2, 2, -2, -2)
        painter.setBrush(QColor(15, 23, 32, 220))
        painter.setPen(QPen(QColor("#6B7280"), 1))
        painter.drawEllipse(rect)

        if self.completed:
            painter.setBrush(QColor("#2E7D32"))
            painter.setPen(QPen(QColor("#A5D6A7"), 1))
            painter.drawEllipse(rect.adjusted(2, 2, -2, -2))
            painter.setPen(QPen(QColor("#ECFDF3"), 2))
            painter.drawLine(13, 18, 17, 22)
            painter.drawLine(17, 22, 24, 14)
        else:
            progress_rect = rect.adjusted(4, 4, -4, -4)
            painter.setPen(QPen(QColor("#4A90E2"), 4))
            span = int(360 * 16 * (self.progress_percent / 100.0))
            painter.drawArc(progress_rect, 90 * 16, -span)
            painter.setPen(QColor("#ECEFF4"))
            painter.setFont(QFont("Sans Serif", 7, QFont.Weight.Bold))
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, f"{int(self.progress_percent)}%")

        painter.end()
        self.progress_label.setPixmap(pixmap)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        x = self.cover_label.width() - self.options_button.width() - 6
        self.options_button.move(max(0, x), 6)
        self.badge_label.move(6, 6)
        self.progress_label.move(self.cover_label.width() - self.progress_label.width() - 6, self.cover_label.height() - self.progress_label.height() - 6)

    def _on_cover_clicked(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.open_requested.emit(self.book_dir)
        event.accept()


class LibraryView(QWidget):
    """Tela da biblioteca com itens superficiais e card de adição."""

    navigate_to = pyqtSignal(str)
    open_book_requested = pyqtSignal(object)  # Path
    review_workspace_requested = pyqtSignal(dict)

    def __init__(self, controllers: Optional[Dict[str, Any]] = None, parent=None):
        super().__init__(parent)
        self.controllers = controllers or {}
        self.book_controller = self.controllers.get("book")
        self.reading_controller = self.controllers.get("reading")
        self.agenda_controller = self.controllers.get("agenda")
        self.add_book_card: Optional[AddBookCard] = None
        self.books_container: Optional[QWidget] = None
        self.books_panel_layout: Optional[QVBoxLayout] = None
        self.books_shelves_layout: Optional[QVBoxLayout] = None
        self.books_scroll: Optional[QScrollArea] = None
        self.empty_label: Optional[QLabel] = None
        self._books_cache: list[Dict[str, Any]] = []
        self._schedule_feedback: Dict[str, Dict[str, Any]] = {}
        self.sort_mode = "recent"
        self.sort_toggle_button: Optional[QPushButton] = None
        self._render_retry_count = 0
        self._layout_timer = QTimer(self)
        self._layout_timer.setSingleShot(True)
        self._layout_timer.timeout.connect(self._render_books_grid)

        self._setup_ui()
        self._setup_connections()
        QTimer.singleShot(100, self.refresh_books)

    def _setup_ui(self):
        self.setObjectName("library_view")
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(20, 20, 20, 20)
        content_layout.setSpacing(16)

        header = QWidget()
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 0)
        title = QLabel("📚 Biblioteca")
        title.setStyleSheet("font-size: 20px; font-weight: 700;")
        subtitle = QLabel("Visual rápido de título + capa")
        subtitle.setStyleSheet("color: #8A94A6; font-size: 11px;")
        left = QVBoxLayout()
        left.setContentsMargins(0, 0, 0, 0)
        left.setSpacing(2)
        left.addWidget(title)
        left.addWidget(subtitle)
        refresh_button = QPushButton("🔄")
        refresh_button.setFixedSize(32, 32)
        refresh_button.setToolTip("Atualizar biblioteca")
        refresh_button.clicked.connect(self.refresh_books)
        self.sort_toggle_button = QPushButton(self._sort_button_text())
        self.sort_toggle_button.setToolTip("Alternar organização das prateleiras")
        self.sort_toggle_button.clicked.connect(self._cycle_sort_mode)
        self.sort_toggle_button.setMinimumHeight(32)
        header_layout.addLayout(left)
        header_layout.addStretch()
        header_layout.addWidget(self.sort_toggle_button)
        header_layout.addWidget(refresh_button)
        content_layout.addWidget(header)

        row = QHBoxLayout()
        row.setSpacing(12)

        books_panel = QFrame()
        books_panel.setObjectName("dashboard_card")
        books_panel_layout = QVBoxLayout(books_panel)
        self.books_panel_layout = books_panel_layout
        books_panel_layout.setContentsMargins(12, 12, 12, 12)
        books_panel_layout.setSpacing(10)

        self.books_scroll = QScrollArea()
        self.books_scroll.setWidgetResizable(True)
        self.books_scroll.setFrameShape(QFrame.Shape.NoFrame)
        books_widget = QWidget()
        self.books_container = books_widget
        self.books_shelves_layout = QVBoxLayout(books_widget)
        self.books_shelves_layout.setContentsMargins(0, 0, 0, 0)
        self.books_shelves_layout.setSpacing(12)
        self.books_scroll.setWidget(books_widget)

        self.empty_label = QLabel("Nenhum livro encontrado em `01-LEITURAS` ou `01- LEITURAS`.")
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_label.setStyleSheet("color: #8A94A6;")

        books_panel_layout.addWidget(self.empty_label)
        books_panel_layout.addWidget(self.books_scroll, 1)
        row.addWidget(books_panel, 75)

        self.add_book_card = AddBookCard(book_controller=self.book_controller)
        self.add_book_card.setObjectName("dashboard_card")
        self.add_book_card.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        row.addWidget(self.add_book_card, 25, alignment=Qt.AlignmentFlag.AlignTop)

        content_layout.addLayout(row)
        content_layout.addStretch()

        scroll_area.setWidget(content)
        root.addWidget(scroll_area)

    def _setup_connections(self):
        if self.add_book_card:
            self.add_book_card.import_config_requested.connect(self.show_import_dialog)

        if self.book_controller:
            self.book_controller.book_processing_started.connect(self.add_book_card.on_processing_started)
            self.book_controller.book_processing_progress.connect(self.add_book_card.on_processing_progress)
            self.book_controller.book_processing_completed.connect(self._on_processing_completed)
            self.book_controller.book_processing_failed.connect(self.add_book_card.on_processing_failed)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._layout_timer.start(100)

    def on_view_activated(self):
        self.refresh_books()

    def _books_root(self) -> Optional[Path]:
        candidates = self._books_roots()
        if not candidates:
            return None

        for candidate in candidates:
            if candidate.exists() and candidate.is_dir():
                return candidate

        # Fallback para manter comportamento previsível quando a pasta ainda não existe.
        return candidates[0]

    def _books_roots(self) -> list[Path]:
        roots: list[Path] = []
        roots_seen: set[Path] = set()
        vault_paths: list[Path] = []

        if self.reading_controller and getattr(self.reading_controller, "reading_manager", None):
            vault_paths.append(Path(self.reading_controller.reading_manager.vault_path))
        if self.book_controller and getattr(self.book_controller, "vault_manager", None):
            vault_paths.append(Path(self.book_controller.vault_manager.vault_path))
        if core_settings:
            settings_vault = str(getattr(getattr(core_settings, "paths", None), "vault", "") or "").strip()
            if settings_vault:
                vault_paths.append(Path(settings_vault).expanduser())
        vault_paths.append(Path.home() / "Documentos" / "Obsidian" / "Philosophy_Vault")
        vault_paths.append(Path.home() / "Documents" / "Obsidian" / "Philosophy_Vault")
        vault_paths.append(Path.home() / "Obsidian" / "Philosophy_Vault")

        unique_vault_paths: list[Path] = []
        seen_vaults: set[Path] = set()
        for vault_path in vault_paths:
            resolved = Path(vault_path).expanduser().resolve(strict=False)
            if resolved not in seen_vaults:
                seen_vaults.add(resolved)
                unique_vault_paths.append(resolved)

        folder_candidates = ("01-LEITURAS", "01- LEITURAS")
        for vault_path in unique_vault_paths:
            existing_roots: list[Path] = []
            for folder_name in folder_candidates:
                candidate = (vault_path / folder_name).resolve(strict=False)
                if candidate.exists() and candidate.is_dir():
                    existing_roots.append(candidate)

            if not existing_roots:
                existing_roots = [(vault_path / "01-LEITURAS").resolve(strict=False)]

            for candidate in existing_roots:
                if candidate not in roots_seen:
                    roots_seen.add(candidate)
                    roots.append(candidate)
        return roots

    def _vault_root(self) -> Optional[Path]:
        books_root = self._books_root()
        return books_root.parent if books_root else None

    def _find_cover_file(self, book_dir: Path) -> Optional[Path]:
        candidates = [
            "cover.jpg",
            "cover.jpeg",
            "cover.png",
            "cover.webp",
            "capa.jpg",
            "capa.jpeg",
            "capa.png",
            "capa.webp",
        ]
        for filename in candidates:
            path = book_dir / filename
            if path.exists() and path.is_file():
                return path
        return None

    def _create_blank_cover(self, cover_path: Path, title: str):
        pixmap = QPixmap(680, 920)
        pixmap.fill(QColor("#FFFFFF"))
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        frame_rect = pixmap.rect().adjusted(18, 18, -18, -18)
        painter.setPen(QColor("#C6CDD6"))
        painter.drawRoundedRect(frame_rect, 20, 20)

        title_rect = frame_rect.adjusted(50, 80, -50, -80)
        painter.setPen(QColor("#1F2933"))
        painter.setFont(QFont("Georgia", 44, QFont.Weight.Bold))
        text_flags = int(Qt.AlignmentFlag.AlignCenter) | int(Qt.TextFlag.TextWordWrap)
        painter.drawText(
            title_rect,
            text_flags,
            str(title or "Livro"),
        )
        painter.end()
        pixmap.save(str(cover_path), "PNG")

    def _ensure_cover_file(self, book_dir: Path, title: str) -> Optional[Path]:
        cover_path = self._find_cover_file(book_dir)
        if cover_path:
            return cover_path

        generated_cover = book_dir / "cover.png"
        try:
            self._create_blank_cover(generated_cover, title)
            if generated_cover.exists() and generated_cover.is_file():
                return generated_cover
        except Exception as exc:
            logger.warning("Falha ao gerar capa placeholder para %s: %s", book_dir, exc)
        return None

    def _find_index_note(self, book_dir: Path) -> Optional[Path]:
        for pattern in ("📖 *.md", "📚 *.md", "*.md"):
            matches = sorted(book_dir.glob(pattern), key=lambda p: p.name.lower())
            if matches:
                return matches[0]
        return None

    def _read_frontmatter(self, note_path: Path) -> Dict[str, Any]:
        try:
            content = note_path.read_text(encoding="utf-8")
            if not content.startswith("---"):
                return {}
            parts = content.split("---", 2)
            if len(parts) < 3:
                return {}
            return yaml.safe_load(parts[1]) or {}
        except Exception:
            return {}

    def _resolve_book_id(self, title: str, author: str, book_dir: Path, frontmatter: Dict[str, Any]) -> Optional[str]:
        if frontmatter.get("book_id"):
            return str(frontmatter.get("book_id"))
        if not self.reading_controller or not getattr(self.reading_controller, "reading_manager", None):
            return None
        manager = self.reading_controller.reading_manager
        for bid, progress in manager.readings.items():
            if progress.title.strip().lower() == title.strip().lower() and progress.author.strip().lower() == author.strip().lower():
                return str(bid)
        return None

    def _load_book_metadata(self, book_dir: Path) -> Dict[str, Any]:
        title = book_dir.name
        author = book_dir.parent.name if book_dir.parent else "Desconhecido"
        index_note = self._find_index_note(book_dir)
        frontmatter = self._read_frontmatter(index_note) if index_note else {}
        metadata = {
            "title": frontmatter.get("title", title),
            "author": frontmatter.get("author", author),
            "total_pages": int(frontmatter.get("total_pages", 0) or 0),
            "year": frontmatter.get("year", ""),
            "publisher": frontmatter.get("publisher", ""),
            "isbn": frontmatter.get("isbn", ""),
            "language": frontmatter.get("language", ""),
            "genre": frontmatter.get("genre", ""),
            "tags": frontmatter.get("tags", []),
            "book_id": None,
            "index_note_path": index_note,
            "frontmatter": frontmatter,
        }

        metadata["book_id"] = self._resolve_book_id(
            metadata["title"],
            metadata["author"],
            book_dir,
            frontmatter,
        )
        return metadata

    def _sync_reading_manager_metadata(self, book_id: str, data: Dict[str, Any]):
        if not self.reading_controller or not getattr(self.reading_controller, "reading_manager", None):
            return
        manager = self.reading_controller.reading_manager
        if book_id not in manager.readings:
            return
        entry = manager.readings[book_id]
        entry.title = data["title"]
        entry.author = data["author"]
        entry.total_pages = int(data.get("total_pages", 0) or entry.total_pages or 0)
        manager._save_progress()

    def _ensure_book_in_reading_manager(self, metadata: Dict[str, Any]) -> str:
        manager = self.reading_controller.reading_manager
        existing = metadata.get("book_id")
        if existing and existing in manager.readings:
            return str(existing)
        return str(
            manager.add_book(
                title=metadata.get("title", "Livro sem título"),
                author=metadata.get("author", "Desconhecido"),
                total_pages=max(int(metadata.get("total_pages", 0) or 0), 1),
                book_id=existing if existing else None,
            )
        )

    def _update_book_notes_metadata(self, book_dir: Path, metadata: Dict[str, Any]):
        if not self.book_controller or not getattr(self.book_controller, "vault_manager", None):
            return
        vault_manager = self.book_controller.vault_manager
        vault_root = self._vault_root()
        if not vault_root:
            return

        for note_path in book_dir.glob("*.md"):
            try:
                relative = note_path.relative_to(vault_root).as_posix()
                note = vault_manager.get_note_by_path(relative)
                if note is None:
                    continue

                fm_update = {
                    "author": metadata["author"],
                    "publisher": metadata["publisher"],
                    "year": metadata["year"],
                    "isbn": metadata["isbn"],
                    "language": metadata["language"],
                    "genre": metadata["genre"],
                    "tags": metadata["tags"],
                }
                if "book" in note.frontmatter:
                    fm_update["book"] = metadata["title"]
                if note_path == metadata.get("index_note_path"):
                    fm_update["title"] = metadata["title"]
                    fm_update["total_pages"] = int(metadata.get("total_pages", 0) or 0)
                if metadata.get("book_id"):
                    fm_update["book_id"] = metadata["book_id"]

                vault_manager.update_note(relative, frontmatter=fm_update)
            except Exception as exc:
                logger.debug("Falha ao atualizar metadados da nota %s: %s", note_path, exc)

    def _sort_button_text(self) -> str:
        labels = {
            "author": "Organizar: Autor",
            "alphabetical": "Organizar: A-Z",
            "recent": "Organizar: Recentes",
        }
        return labels.get(self.sort_mode, "Organizar")

    def _cycle_sort_mode(self):
        modes = ["author", "alphabetical", "recent"]
        current_idx = modes.index(self.sort_mode) if self.sort_mode in modes else 0
        self.sort_mode = modes[(current_idx + 1) % len(modes)]
        if self.sort_toggle_button:
            self.sort_toggle_button.setText(self._sort_button_text())
        self._render_books_grid()

    def _parse_iso_datetime(self, value: str) -> Optional[datetime]:
        if not value:
            return None
        try:
            return datetime.fromisoformat(str(value))
        except Exception:
            return None

    def _reading_progress_for_book(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        progress_data = {
            "percent": 0.0,
            "completed": False,
            "current_page": 0,
            "total_pages": 0,
            "last_activity": None,
            "registered_at": None,
        }
        if not self.reading_controller or not getattr(self.reading_controller, "reading_manager", None):
            return progress_data

        manager = self.reading_controller.reading_manager
        book_id = metadata.get("book_id")
        if not book_id:
            return progress_data

        entry = manager.readings.get(str(book_id))
        if not entry:
            return progress_data

        total_pages = max(int(getattr(entry, "total_pages", 0) or 0), 1)
        current_page = max(int(getattr(entry, "current_page", 0) or 0), 0)
        percent = max(0.0, min(100.0, (current_page / total_pages) * 100.0))
        progress_data["percent"] = percent
        progress_data["completed"] = current_page >= total_pages and total_pages > 0
        progress_data["current_page"] = current_page
        progress_data["total_pages"] = total_pages
        progress_data["last_activity"] = self._parse_iso_datetime(getattr(entry, "last_read", "") or "")
        progress_data["registered_at"] = self._parse_iso_datetime(getattr(entry, "start_date", "") or "")
        return progress_data

    def refresh_books(self):
        books = []
        seen_book_dirs: set[Path] = set()
        checked_roots: list[str] = []
        logger.info("Library refresh iniciado")
        for root in self._books_roots():
            checked_roots.append(str(root))
            if not root.exists() or not root.is_dir():
                logger.debug("Library root ignorado (inexistente ou não-diretório): %s", root)
                continue
            try:
                authors_count = 0
                books_before = len(books)
                for author_dir in sorted(root.iterdir(), key=lambda p: p.name.lower()):
                    if not author_dir.is_dir():
                        continue
                    authors_count += 1
                    for book_dir in sorted(author_dir.iterdir(), key=lambda p: p.name.lower()):
                        canonical_book_dir = book_dir.resolve(strict=False)
                        if not book_dir.is_dir() or canonical_book_dir in seen_book_dirs:
                            continue
                        seen_book_dirs.add(canonical_book_dir)
                        books.append(
                            {
                                "title": str(book_dir.name),
                                "author": str(author_dir.name),
                                "book_dir": book_dir,
                                "cover_path": self._ensure_cover_file(book_dir, str(book_dir.name)),
                            }
                        )
                logger.info(
                    "Library root processado: %s | autores=%d | livros_novos=%d",
                    root,
                    authors_count,
                    len(books) - books_before,
                )
            except Exception as exc:
                logger.error("Falha ao carregar biblioteca em %s: %s", root, exc)
        self._books_cache = books
        logger.info("Library refresh concluído | livros_total=%d | roots=%s", len(books), checked_roots)
        if self.empty_label:
            if books:
                self.empty_label.setText("Nenhum livro encontrado em `01-LEITURAS` ou `01- LEITURAS`.")
                self.empty_label.setToolTip("")
                self.empty_label.hide()
            else:
                roots_text = " | ".join(checked_roots) if checked_roots else "nenhum root detectado"
                self.empty_label.setText(
                    "Nenhum livro encontrado.\n"
                    f"Roots verificados: {roots_text}"
                )
                self.empty_label.setToolTip(roots_text)
                self.empty_label.show()
        self._render_books_grid()

    def _sorted_books(self) -> list[Dict[str, Any]]:
        books: list[Dict[str, Any]] = []
        for book in self._books_cache:
            metadata = self._load_book_metadata(book["book_dir"])
            progress = self._reading_progress_for_book(metadata)
            books.append(
                {
                    **book,
                    "book_id": metadata.get("book_id"),
                    "progress_percent": progress["percent"],
                    "progress_completed": progress["completed"],
                    "progress_current": progress["current_page"],
                    "progress_total": progress["total_pages"],
                    "last_activity": progress["last_activity"],
                    "registered_at": progress["registered_at"],
                }
            )

        if self.sort_mode == "alphabetical":
            return sorted(books, key=lambda b: str(b["title"]).lower())
        if self.sort_mode == "recent":
            def recent_key(item: Dict[str, Any]):
                activity = item.get("last_activity") or item.get("registered_at") or datetime.min
                return (activity, str(item["title"]).lower())
            return sorted(books, key=recent_key, reverse=True)
        return sorted(books, key=lambda b: (str(b["author"]).lower(), str(b["title"]).lower()))

    def _render_books_grid(self):
        try:
            shelves_layout = self._ensure_books_shelves_layout()
            if shelves_layout is None:
                self._render_retry_count += 1
                logger.warning(
                    "Render prateleiras adiado: layout indisponível (tentativa=%d, books_scroll=%s, panel_layout=%s)",
                    self._render_retry_count,
                    self.books_scroll is not None,
                    self.books_panel_layout is not None,
                )
                if self._render_retry_count <= 8:
                    QTimer.singleShot(120, self._render_books_grid)
                return
            self._render_retry_count = 0
            while shelves_layout.count():
                item = shelves_layout.takeAt(0)
                widget = item.widget()
                if widget:
                    widget.deleteLater()

            has_books = len(self._books_cache) > 0
            if self.empty_label:
                self.empty_label.setVisible(not has_books)
            if self.books_scroll:
                self.books_scroll.setVisible(True)
            logger.info("Render prateleiras | has_books=%s | total=%d", has_books, len(self._books_cache))

            sorted_books = self._sorted_books()

            if self.sort_mode == "author":
                grouped: Dict[str, list[Dict[str, Any]]] = {}
                for book in sorted_books:
                    grouped.setdefault(str(book["author"]), []).append(book)
                groups = list(grouped.items())
            else:
                title = "Ordem alfabética" if self.sort_mode == "alphabetical" else "Últimas leituras e registros"
                groups = [(title, sorted_books)]

            for author, author_books in groups:
                shelf = QFrame()
                shelf_layout = QVBoxLayout(shelf)
                shelf_layout.setContentsMargins(0, 0, 0, 0)
                shelf_layout.setSpacing(8)

                author_label = QLabel(author)
                author_label.setStyleSheet("font-size: 13px; font-weight: 700; color: #D8DEE9;")
                shelf_layout.addWidget(author_label)

                if self.sort_mode == "author":
                    shelf_scroll = QScrollArea()
                    shelf_scroll.setWidgetResizable(False)
                    shelf_scroll.setFrameShape(QFrame.Shape.NoFrame)
                    shelf_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
                    shelf_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
                    shelf_scroll.setFixedHeight(305)
                    shelf_scroll.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

                    books_row = QWidget()
                    books_row_layout = QHBoxLayout(books_row)
                    books_row_layout.setContentsMargins(0, 0, 0, 0)
                    books_row_layout.setSpacing(10)
                    rows_to_render = [books_row_layout]
                else:
                    wrap_widget = QWidget()
                    wrap_grid = QGridLayout(wrap_widget)
                    wrap_grid.setContentsMargins(0, 0, 0, 0)
                    wrap_grid.setHorizontalSpacing(10)
                    wrap_grid.setVerticalSpacing(12)
                    viewport_width = self.books_scroll.viewport().width() if self.books_scroll else 900
                    columns = max(1, viewport_width // 220)
                    rows_to_render = [wrap_grid, columns]

                for idx, book in enumerate(author_books):
                    badge_text = None
                    feedback = self._schedule_feedback.get(str(book["book_dir"]))
                    if feedback:
                        expires_at = feedback.get("expires_at")
                        if isinstance(expires_at, datetime) and expires_at > datetime.now():
                            badge_text = str(feedback.get("text") or "")
                        else:
                            self._schedule_feedback.pop(str(book["book_dir"]), None)

                    tile = LibraryBookTile(
                        book_dir=book["book_dir"],
                        title=book["title"],
                        author=book["author"],
                        cover_path=book["cover_path"],
                        progress_percent=float(book.get("progress_percent", 0.0) or 0.0),
                        completed=bool(book.get("progress_completed", False)),
                        progress_current=int(book.get("progress_current", 0) or 0),
                        progress_total=int(book.get("progress_total", 0) or 0),
                        badge_text=badge_text,
                    )
                    tile.open_requested.connect(self._open_book_from_tile)
                    tile.metadata_requested.connect(self._open_metadata_editor)
                    tile.schedule_requested.connect(self._open_schedule_dialog)
                    tile.review_requested.connect(self._open_review_dialog)

                    if self.sort_mode == "author":
                        rows_to_render[0].addWidget(tile)
                    else:
                        columns = rows_to_render[1]
                        row = idx // columns
                        col = idx % columns
                        rows_to_render[0].addWidget(tile, row, col)

                if self.sort_mode == "author":
                    row_width = (200 * len(author_books)) + (10 * max(0, len(author_books) - 1)) + 20
                    books_row.setFixedSize(max(row_width, 220), 285)
                    shelf_scroll.setWidget(books_row)
                    shelf_layout.addWidget(shelf_scroll)
                else:
                    shelf_layout.addWidget(wrap_widget)

                shelf_line = QFrame()
                shelf_line.setFixedHeight(8)
                shelf_line.setStyleSheet(
                    "background-color: #2B3341; border: 1px solid #4A90E2; border-radius: 4px;"
                )
                shelf_layout.addWidget(shelf_line)

                shelves_layout.addWidget(shelf)

            spacer = QWidget()
            spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
            shelves_layout.addWidget(spacer)

            if self.books_scroll and self.books_scroll.widget():
                self.books_scroll.widget().adjustSize()
                self.books_scroll.viewport().update()
        except Exception as exc:
            logger.exception("Falha ao renderizar prateleiras: %s", exc)

    def _ensure_books_shelves_layout(self) -> Optional[QVBoxLayout]:
        """Recupera/cria layout de prateleiras de forma robusta no container do scroll."""
        if self.books_scroll is None:
            if self.books_panel_layout is None:
                return None
            self.books_scroll = QScrollArea()
            self.books_scroll.setWidgetResizable(True)
            self.books_scroll.setFrameShape(QFrame.Shape.NoFrame)
            self.books_panel_layout.addWidget(self.books_scroll, 1)

        container = self.books_scroll.widget()
        if container is None:
            container = QWidget()
            self.books_scroll.setWidget(container)
            self.books_container = container
        else:
            self.books_container = container

        existing_layout = container.layout()
        if isinstance(existing_layout, QVBoxLayout):
            self.books_shelves_layout = existing_layout
            return existing_layout

        shelves_layout = QVBoxLayout(container)
        shelves_layout.setContentsMargins(0, 0, 0, 0)
        shelves_layout.setSpacing(12)
        self.books_shelves_layout = shelves_layout
        return shelves_layout

    def _open_book_from_tile(self, book_dir: Path):
        metadata = self._load_book_metadata(book_dir)
        if self.reading_controller and getattr(self.reading_controller, "reading_manager", None):
            try:
                book_id = metadata.get("book_id")
                if not book_id:
                    metadata["book_id"] = self._ensure_book_in_reading_manager(metadata)
            except Exception as exc:
                logger.warning("Falha ao registrar livro no ReadingManager (%s): %s", book_dir, exc)
        self.open_book_requested.emit(book_dir)

    def _open_metadata_editor(self, book_dir: Path):
        metadata = self._load_book_metadata(book_dir)
        dialog = MetadataEditDialog(metadata, self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        updated = dialog.get_data()
        updated["book_id"] = metadata.get("book_id")
        updated["index_note_path"] = metadata.get("index_note_path")

        # Garante registro no ReadingManager para persistência local.
        if self.reading_controller and getattr(self.reading_controller, "reading_manager", None):
            book_id = updated.get("book_id")
            if not book_id:
                temp = dict(updated)
                temp["book_id"] = metadata.get("book_id")
                updated["book_id"] = self._ensure_book_in_reading_manager(temp)
            self._sync_reading_manager_metadata(str(updated["book_id"]), updated)

        self._update_book_notes_metadata(book_dir, updated)
        self.refresh_books()
        QMessageBox.information(self, "Metadados", "Metadados atualizados com sucesso.")

    def _open_schedule_dialog(self, book_dir: Path):
        if not self.reading_controller or not getattr(self.reading_controller, "reading_manager", None):
            QMessageBox.warning(self, "Agendamento", "ReadingManager não disponível.")
            return

        metadata = self._load_book_metadata(book_dir)
        dialog = ScheduleDialog(self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        pages_per_day, strategy = dialog.values()
        book_id = self._ensure_book_in_reading_manager(metadata)

        if self.agenda_controller and hasattr(self.agenda_controller, "schedule_reading"):
            self.agenda_controller.schedule_reading(str(book_id), float(pages_per_day), strategy)
            self._set_schedule_feedback(book_dir, "Agendamento iniciado")
            QMessageBox.information(self, "Agendamento", "Agendamento iniciado com sucesso.")
            return

        if self.book_controller and hasattr(self.book_controller, "schedule_book_reading"):
            result = self.book_controller.schedule_book_reading(
                book_id=str(book_id),
                title=metadata.get("title"),
                total_pages=int(metadata.get("total_pages", 0) or 0),
            )
            if result.get("success"):
                self._set_schedule_feedback(book_dir, "Agendado")
                QMessageBox.information(self, "Agendamento", "Sessões agendadas com sucesso.")
            else:
                QMessageBox.warning(
                    self,
                    "Agendamento",
                    f"Não foi possível agendar: {result.get('error', 'erro desconhecido')}",
                )
            return

        QMessageBox.warning(self, "Agendamento", "AgendaController não disponível.")

    def _open_review_dialog(self, book_dir: Path):
        if not self.reading_controller or not getattr(self.reading_controller, "reading_manager", None):
            QMessageBox.warning(self, "Revisão", "ReadingManager não disponível.")
            return

        metadata = self._load_book_metadata(book_dir)
        book_id = self._ensure_book_in_reading_manager(metadata)
        book_title = str(metadata.get("title", "Livro")).strip() or "Livro"
        self.review_workspace_requested.emit(
            {
                "source": "library",
                "book_id": str(book_id),
                "book_title": book_title,
                "book_dir": str(book_dir),
            }
        )

    def _set_schedule_feedback(self, book_dir: Path, text: str):
        self._schedule_feedback[str(book_dir)] = {
            "text": text,
            "expires_at": datetime.now() + timedelta(seconds=8),
        }
        self._render_books_grid()

    def _on_processing_completed(self, pipeline_id, result):
        self.add_book_card.on_processing_completed(pipeline_id, result)
        self.refresh_books()

    def show_import_dialog(self, file_path, initial_metadata):
        from ui.widgets.dialogs.book_import_dialog import BookImportDialog

        dialog = BookImportDialog(file_path, initial_metadata, self)
        dialog.import_confirmed.connect(lambda config: self.start_book_processing(config))
        dialog.import_cancelled.connect(self.add_book_card.reset_to_idle)
        dialog.exec()

    def start_book_processing(self, config):
        if not self.book_controller:
            if self.add_book_card:
                self.add_book_card.show_error("BookController não disponível")
            return
        quality_map = {
            "Rápido (Rascunho)": "draft",
            "Padrão": "standard",
            "Alta Qualidade": "high",
            "Acadêmico": "academic",
        }
        file_path = str(config.get("file_path") or "").strip()
        if not file_path:
            if self.add_book_card:
                self.add_book_card.show_error("Arquivo inválido para importação")
            return

        settings = {
            "file_path": file_path,
            "quality": quality_map.get(config.get("quality"), "standard"),
            "use_llm": bool(config.get("use_llm", True)),
            "auto_schedule": bool(config.get("auto_schedule", True)),
            "metadata": {
                "title": config.get("title", ""),
                "author": config.get("author", ""),
                "year": config.get("year", ""),
                "publisher": config.get("publisher", ""),
                "isbn": config.get("isbn", ""),
                "language": config.get("language", ""),
                "genre": config.get("genre", ""),
                "tags": config.get("tags", []),
            },
            "notes_config": {
                "structure": config.get("note_structure", ""),
                "template": config.get("note_template", ""),
                "vault_location": config.get("vault_location", ""),
            },
            "scheduling_config": {
                "pages_per_day": config.get("pages_per_day", 20),
                "start_date": config.get("start_date", ""),
                "preferred_time": config.get("preferred_time", ""),
                "strategy": config.get("strategy", ""),
            },
        }
        try:
            pipeline_id = self.book_controller.process_book_with_config(settings)
            if self.add_book_card and pipeline_id and self.add_book_card.current_state != "processing":
                self.add_book_card.start_processing(
                    pipeline_id,
                    {"file_path": file_path, "quality": settings["quality"]},
                )
        except Exception as exc:
            logger.error("Falha ao iniciar processamento do livro '%s': %s", file_path, exc)
            if self.add_book_card:
                self.add_book_card.show_error(f"Falha ao iniciar importação: {exc}")
            QMessageBox.warning(
                self,
                "Importação",
                f"Não foi possível iniciar o processamento.\n\nErro: {exc}",
            )
