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
from PyQt6.QtGui import QAction, QColor, QFont, QLinearGradient, QPainter, QPixmap
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

    def __init__(
        self,
        book_dir: Path,
        title: str,
        author: str,
        cover_path: Optional[Path],
        badge_text: Optional[str] = None,
        parent=None
    ):
        super().__init__(parent)
        self.book_dir = book_dir
        self.title = title
        self.author = author
        self.cover_path = cover_path
        self.badge_text = badge_text
        self._setup_ui()

    def _setup_ui(self):
        self.setObjectName("library_book_tile")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedWidth(190)
        self.setFrameShape(QFrame.Shape.StyledPanel)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        self.cover_label = QLabel()
        self.cover_label.setFixedSize(170, 230)
        self.cover_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.cover_label.setStyleSheet("border: 1px solid #2E3440; border-radius: 8px;")
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

        title_label = QLabel(self.title)
        title_label.setWordWrap(True)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("font-weight: 700;")
        layout.addWidget(title_label)

        author_label = QLabel(self.author)
        author_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        author_label.setStyleSheet("color: #8A94A6; font-size: 11px;")
        layout.addWidget(author_label)

    def _show_options_menu(self):
        menu = QMenu(self)
        edit_action = menu.addAction("Editar metadados")
        schedule_action = menu.addAction("Agendar sessões")
        selected = menu.exec(self.options_button.mapToGlobal(self.options_button.rect().bottomLeft()))
        if selected == edit_action:
            self.metadata_requested.emit(self.book_dir)
        elif selected == schedule_action:
            self.schedule_requested.emit(self.book_dir)

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

    def resizeEvent(self, event):
        super().resizeEvent(event)
        x = self.cover_label.width() - self.options_button.width() - 6
        self.options_button.move(max(0, x), 6)
        self.badge_label.move(6, 6)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.open_requested.emit(self.book_dir)
        super().mousePressEvent(event)


class LibraryView(QWidget):
    """Tela da biblioteca com itens superficiais e card de adição."""

    navigate_to = pyqtSignal(str)
    open_book_requested = pyqtSignal(object)  # Path

    def __init__(self, controllers: Optional[Dict[str, Any]] = None, parent=None):
        super().__init__(parent)
        self.controllers = controllers or {}
        self.book_controller = self.controllers.get("book")
        self.reading_controller = self.controllers.get("reading")
        self.agenda_controller = self.controllers.get("agenda")
        self.add_book_card: Optional[AddBookCard] = None
        self.books_grid: Optional[QGridLayout] = None
        self.books_scroll: Optional[QScrollArea] = None
        self.empty_label: Optional[QLabel] = None
        self._books_cache: list[Dict[str, Any]] = []
        self._schedule_feedback: Dict[str, Dict[str, Any]] = {}
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
        header_layout.addLayout(left)
        header_layout.addStretch()
        header_layout.addWidget(refresh_button)
        content_layout.addWidget(header)

        row = QHBoxLayout()
        row.setSpacing(12)

        books_panel = QFrame()
        books_panel.setObjectName("dashboard_card")
        books_panel_layout = QVBoxLayout(books_panel)
        books_panel_layout.setContentsMargins(12, 12, 12, 12)
        books_panel_layout.setSpacing(10)

        self.books_scroll = QScrollArea()
        self.books_scroll.setWidgetResizable(True)
        self.books_scroll.setFrameShape(QFrame.Shape.NoFrame)
        books_widget = QWidget()
        self.books_grid = QGridLayout(books_widget)
        self.books_grid.setContentsMargins(0, 0, 0, 0)
        self.books_grid.setHorizontalSpacing(10)
        self.books_grid.setVerticalSpacing(10)
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
                                "cover_path": self._find_cover_file(book_dir),
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

    def _render_books_grid(self):
        if not self.books_grid:
            return
        while self.books_grid.count():
            item = self.books_grid.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        has_books = len(self._books_cache) > 0
        if self.empty_label:
            self.empty_label.setVisible(not has_books)
        if self.books_scroll:
            self.books_scroll.setVisible(True)
        logger.info(
            "Render books grid | has_books=%s | total=%d | viewport_width=%d",
            has_books,
            len(self._books_cache),
            self.books_scroll.viewport().width() if self.books_scroll else -1,
        )

        viewport_width = self.books_scroll.viewport().width() if self.books_scroll else 900
        tile_width = 210
        columns = max(1, viewport_width // tile_width)

        for idx, book in enumerate(self._books_cache):
            row = idx // columns
            col = idx % columns
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
                badge_text=badge_text,
            )
            tile.open_requested.connect(self.open_book_requested.emit)
            tile.metadata_requested.connect(self._open_metadata_editor)
            tile.schedule_requested.connect(self._open_schedule_dialog)
            self.books_grid.addWidget(tile, row, col)

        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.books_grid.addWidget(spacer, max(len(self._books_cache) // max(columns, 1), 1), columns + 1)

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
            return
        quality_map = {
            "Rápido (Rascunho)": "draft",
            "Padrão": "standard",
            "Alta Qualidade": "high",
            "Acadêmico": "academic",
        }
        settings = {
            "file_path": config["file_path"],
            "quality": quality_map.get(config["quality"], "standard"),
            "use_llm": config["use_llm"],
            "auto_schedule": config["auto_schedule"],
            "metadata": {
                "title": config["title"],
                "author": config["author"],
                "year": config["year"],
                "publisher": config["publisher"],
                "isbn": config["isbn"],
                "language": config["language"],
                "genre": config["genre"],
                "tags": config["tags"],
            },
            "notes_config": {
                "structure": config["note_structure"],
                "template": config["note_template"],
                "vault_location": config["vault_location"],
            },
            "scheduling_config": {
                "pages_per_day": config["pages_per_day"],
                "start_date": config["start_date"],
                "preferred_time": config["preferred_time"],
                "strategy": config["strategy"],
            },
        }
        self.book_controller.process_book_with_config(settings)
