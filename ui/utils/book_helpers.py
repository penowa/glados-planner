"""Helper utilities for locating book directories, metadata and covers.

These are lightweight helpers used by DynamicEventCard.
"""
from pathlib import Path
import json
import logging
import re
import unicodedata
from typing import Optional, List, Dict

logger = logging.getLogger("GLaDOS.UI.BookHelpers")


def _find_book_dir_by_book_id_in_vault(vault_root: Path, book_id: str) -> Optional[Path]:
    if not vault_root.exists() or not book_id:
        return None
    book_id_pattern = re.compile(rf'(?mi)^(?:book_id|id):\s*["\']?{re.escape(str(book_id).strip())}["\']?\s*$')
    for md_file in vault_root.rglob("*.md"):
        if not md_file.is_file():
            continue
        try:
            content = md_file.read_text(encoding='utf8', errors='ignore')
        except Exception:
            continue
        if book_id_pattern.search(content):
            return md_file.parent
    return None


def _directory_has_book_marker(book_dir: Path, book_id: str = "") -> bool:
    if not book_dir.exists() or not book_dir.is_dir():
        return False

    # cover or capa file in root is a strong signal that this is the book folder
    for name in ("cover.jpg", "cover.jpeg", "cover.png", "cover.webp", "capa.jpg", "capa.jpeg", "capa.png", "capa.webp"):
        if (book_dir / name).is_file():
            return True

    # a local note with the requested book_id is a strong signal
    if book_id:
        book_id_pattern = re.compile(rf'(?mi)^(?:book_id|id):\s*["\']?{re.escape(str(book_id).strip())}["\']?\s*$')
    else:
        book_id_pattern = None

    for md_file in book_dir.glob('*.md'):
        if not md_file.is_file():
            continue
        if book_id_pattern:
            try:
                content = md_file.read_text(encoding='utf8', errors='ignore')
                if book_id_pattern.search(content):
                    return True
            except Exception:
                pass
        else:
            return True
    return False


def _normalize_string(value: str) -> str:
    clean = unicodedata.normalize('NFKD', str(value or "")).encode('ascii', 'ignore').decode('ascii')
    clean = clean.lower()
    clean = re.sub(r'[^a-z0-9]+', '', clean)
    return clean


def _find_book_root_from_source_path(source_path: Path, book_id: str = "") -> Optional[Path]:
    if not source_path.exists():
        return None
    path = source_path if source_path.is_dir() else source_path.parent
    while path.exists():
        if _directory_has_book_marker(path, book_id=book_id):
            return path
        if path == path.parent:
            break
        path = path.parent
    return None


def _find_book_dir_by_title_author(vault_root: Path, title: str, author: str) -> Optional[Path]:
    if not vault_root.exists() or not title or not author:
        return None
    title_key = _normalize_string(title)
    author_key = _normalize_string(author)
    root = vault_root / "01-LEITURAS"
    if not root.exists():
        root = vault_root

    # first pass: exact author/book match
    for author_dir in sorted(root.iterdir(), key=lambda p: p.name.lower() if p.is_dir() else ''):
        if not author_dir.is_dir():
            continue
        if _normalize_string(author_dir.name) != author_key:
            continue
        for book_dir in sorted(author_dir.iterdir(), key=lambda p: p.name.lower() if p.is_dir() else ''):
            if not book_dir.is_dir():
                continue
            if _normalize_string(book_dir.name) == title_key:
                return book_dir

    # second pass: partial match in directory names
    for author_dir in sorted(root.iterdir(), key=lambda p: p.name.lower() if p.is_dir() else ''):
        if not author_dir.is_dir():
            continue
        for book_dir in sorted(author_dir.iterdir(), key=lambda p: p.name.lower() if p.is_dir() else ''):
            if not book_dir.is_dir():
                continue
            if author_key in _normalize_string(author_dir.name) and title_key in _normalize_string(book_dir.name):
                return book_dir

    return None


def find_book_directory(reading_manager, book_id, title: str = "", author: str = "") -> Optional[Path]:
    try:
        book_id_str = str(book_id or "").strip()
        title = str(title or "").strip()
        author = str(author or "").strip()
        if not book_id_str and not title and not author:
            return None

        # Prefer reading manager helper if available
        if reading_manager and hasattr(reading_manager, 'find_book_directory'):
            p = reading_manager.find_book_directory(book_id_str)
            if p:
                return Path(p)

        # Prefer a source path from the reading manager
        source_candidate = None
        if reading_manager and hasattr(reading_manager, 'get_book_source_path'):
            try:
                source = reading_manager.get_book_source_path(book_id_str)
                if source:
                    source_path = Path(source)
                    if source_path.exists():
                        root_dir = _find_book_root_from_source_path(source_path, book_id=book_id_str)
                        if root_dir:
                            return root_dir
                        source_candidate = source_path.parent if source_path.is_file() else source_path
                        if _directory_has_book_marker(source_candidate, book_id=book_id_str):
                            return source_candidate
            except Exception:
                pass

        if reading_manager and hasattr(reading_manager, 'readings'):
            progress = getattr(reading_manager, 'readings', {}).get(book_id_str)
            if progress:
                if not title:
                    title = getattr(progress, 'title', '') or title
                if not author:
                    author = getattr(progress, 'author', '') or author
                source_file = getattr(progress, 'source_file', None) or getattr(progress, 'source_path', None)
                if source_file:
                    source_path = Path(source_file)
                    if source_path.exists():
                        root_dir = _find_book_root_from_source_path(source_path, book_id=book_id_str)
                        if root_dir:
                            return root_dir
                        source_candidate = source_path.parent if source_path.is_file() else source_path
                        if _directory_has_book_marker(source_candidate, book_id=book_id_str):
                            return source_candidate

        vault = getattr(reading_manager, 'vault_path', None)
        if vault:
            vault_p = Path(vault)
            if vault_p.exists():
                search_root = vault_p / "01-LEITURAS"
                if not search_root.exists():
                    search_root = vault_p
                candidate = _find_book_dir_by_book_id_in_vault(search_root, book_id_str)
                if candidate:
                    return candidate
                # fallback by folder name match under vault when book_id is provided
                if book_id_str:
                    for p in search_root.rglob('*'):
                        if p.is_dir() and book_id_str in p.name:
                            return p
                # fallback by normalized title/author in vault
                candidate = _find_book_dir_by_title_author(vault_p, title or "", author or "")
                if candidate:
                    return candidate
    except Exception:
        logger.exception('find_book_directory failed')
    return None


def load_book_metadata(book_dir: str or Path) -> Dict:
    bd = Path(book_dir)
    if not bd.exists():
        return {}
    # look for metadata.json or info.json
    for name in ('metadata.json', 'info.json', 'book.json'):
        p = bd / name
        if p.exists():
            try:
                return json.loads(p.read_text(encoding='utf8'))
            except Exception:
                logger.exception('failed parsing %s', p)
    # fallback: use directory name
    return {'title': bd.name}


def find_cover_file(book_dir: str or Path) -> Optional[str]:
    bd = Path(book_dir)
    if not bd.exists():
        return None
    if bd.is_file():
        return str(bd) if bd.suffix.lower() in {'.jpg', '.jpeg', '.png', '.webp'} else None

    candidates = [
        'cover.jpg',
        'cover.jpeg',
        'cover.png',
        'cover.webp',
        'capa.jpg',
        'capa.jpeg',
        'capa.png',
        'capa.webp',
    ]
    for name in candidates:
        p = bd / name
        if p.exists() and p.is_file():
            return str(p)

    # search recursively for image files under the book directory
    image_files = [
        p for p in bd.rglob('*')
        if p.is_file() and p.suffix.lower() in {'.jpg', '.jpeg', '.png', '.webp'}
    ]
    for p in image_files:
        lower_name = p.name.lower()
        if 'cover' in lower_name or 'capa' in lower_name:
            return str(p)
    if image_files:
        return str(image_files[0])
    return None


def load_book_note_properties(book_dir: str or Path, book_id: str = "", title: str = "") -> Dict:
    bd = Path(book_dir)
    if not bd.exists():
        return {}
    try:
        from ui.utils.citation_notes import _read_text, _parse_frontmatter
        from ui.utils.discipline_links import find_primary_book_note

        note_path = None
        if bd.is_file() and bd.suffix.lower() == '.md':
            note_path = bd
        else:
            note_path = _find_completo_note_in_book_dir(bd)
            if not note_path:
                note_path = find_primary_book_note(bd, title=title, book_id=book_id)

        if not note_path or not note_path.exists():
            return {}
        content = _read_text(note_path)
        if not content:
            return {}
        props = _parse_frontmatter(content)
        if not isinstance(props, dict):
            return {}

        # normalize numeric metadata fields into native types
        for key in ('total_pages', 'pages_planned', 'current_page', 'current_pages', 'year'):
            value = props.get(key)
            if isinstance(value, str) and value.isdigit():
                props[key] = int(value)

        # normalize boolean-like fields
        for key in ('completed', 'finished'):
            value = props.get(key)
            if isinstance(value, str):
                lower = value.strip().lower()
                if lower in ('true', 'yes', 'sim', '1'):
                    props[key] = True
                elif lower in ('false', 'no', 'não', 'nao', '0'):
                    props[key] = False

        return props
    except Exception:
        logger.exception('load_book_note_properties failed')
        return {}


def _find_completo_note_in_book_dir(book_dir: Path) -> Optional[Path]:
    if not book_dir.exists() or not book_dir.is_dir():
        return None
    for child in book_dir.iterdir():
        if child.is_file() and child.suffix.lower() == '.md':
            name = child.stem
            if name.endswith(' - Completo') or name.endswith(' - completo'):
                return child
    return None


def load_discipline_books(vault_root: str or Path, discipline: str) -> List[Dict]:
    vault = Path(vault_root)
    results = []
    try:
        # If ui.utils.class_notes provides loader, prefer it
        try:
            from ui.utils.class_notes import load_discipline_works
            works = load_discipline_works(vault, discipline)
            for w in works:
                work_dir = Path(w.get('work_dir_abs') or w.get('path') or w.get('work_dir'))
                metadata = load_book_metadata(work_dir)
                cover = find_cover_file(work_dir)
                results.append({
                    'title': metadata.get('title') or w.get('title') or work_dir.name,
                    'work_dir_abs': str(work_dir),
                    'cover_path': cover,
                })
            return results
        except Exception:
            logger.debug('load_discipline_works not available or failed')

        # Fallback: look for folders under vault_root/01-LEITURAS or vault_root/discipline
        candidates = []
        for sub in ('01-LEITURAS', discipline, ''):
            base = vault / sub if sub else vault
            if base.exists():
                for p in base.iterdir():
                    if p.is_dir():
                        candidates.append(p)

        for p in candidates:
            metadata = load_book_metadata(p)
            cover = find_cover_file(p)
            results.append({'title': metadata.get('title') or p.name, 'work_dir_abs': str(p), 'cover_path': cover})
    except Exception:
        logger.exception('load_discipline_books failed')
    return results
