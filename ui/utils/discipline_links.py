"""Utilitários para notas de disciplina no diretório 05-DISCIPLINAS."""
from __future__ import annotations

import re
import unicodedata
from pathlib import Path
from typing import Iterable, Optional


DISCIPLINE_DIR = "05-DISCIPLINAS"
AGENDA_SECTION_HEADER = "## Agenda"
BOOKS_SECTION_HEADER = "## Obras"
LEGACY_BOOKS_SECTION_HEADER = "## Livro processado"


def _normalize_token(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", str(value or "").strip())
    normalized = "".join(ch for ch in normalized if not unicodedata.combining(ch))
    normalized = re.sub(r"[^a-zA-Z0-9]+", "-", normalized).strip("-").lower()
    return normalized


def _safe_filename(value: str) -> str:
    text = re.sub(r'[<>:"/\\|?*]+', "_", str(value or "").strip())
    text = re.sub(r"\s+", " ", text).strip()
    return text[:100] or "disciplina"


def resolve_vault_root(*candidates: object) -> Optional[Path]:
    for candidate in candidates:
        raw = str(candidate or "").strip()
        if not raw:
            continue
        path = Path(raw).expanduser().resolve(strict=False)
        if path.exists():
            return path
    return None


def _discipline_dir(vault_root: Path) -> Path:
    target = Path(vault_root) / DISCIPLINE_DIR
    target.mkdir(parents=True, exist_ok=True)
    return target


def _extract_display_name(note_path: Path) -> str:
    try:
        text = note_path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return note_path.stem
    for line in text.splitlines():
        cleaned = line.strip()
        if cleaned.lower().startswith("# disciplina:"):
            return cleaned.split(":", 1)[1].strip() or note_path.stem
    return note_path.stem


def list_disciplines(vault_root: Path) -> list[str]:
    names: list[str] = []
    for note_path in sorted(_discipline_dir(vault_root).glob("*.md"), key=lambda p: p.name.lower()):
        if note_path.stem.lower() == "readme":
            continue
        names.append(_extract_display_name(note_path))
    return names


def _find_discipline_note(vault_root: Path, discipline: str) -> Optional[Path]:
    target_norm = _normalize_token(discipline)
    if not target_norm:
        return None
    for note_path in _discipline_dir(vault_root).glob("*.md"):
        if note_path.stem.lower() == "readme":
            continue
        if _normalize_token(note_path.stem) == target_norm:
            return note_path
        if _normalize_token(_extract_display_name(note_path)) == target_norm:
            return note_path
    return None


def ensure_discipline_note(vault_root: Path, discipline: str) -> Optional[Path]:
    name = str(discipline or "").strip()
    if not name:
        return None
    existing = _find_discipline_note(vault_root, name)
    if existing:
        return existing

    note_name = _safe_filename(name)
    note_path = _discipline_dir(vault_root) / f"{note_name}.md"
    content = (
        f"# Disciplina: {name}\n\n"
        "A assistente está organizando os conteúdos desta disciplina.\n\n"
        f"{AGENDA_SECTION_HEADER}\n\n"
        f"{BOOKS_SECTION_HEADER}\n"
    )
    note_path.write_text(content, encoding="utf-8")
    return note_path


def _read_note_text(note_path: Path) -> str:
    try:
        return note_path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""


def _count_page_markers(content: str) -> int:
    return len(re.findall(r"(?m)^---\s*Página\s+\d+\s*---\s*$", str(content or "")))


def find_primary_book_note(book_dir: Path, *, title: str = "", book_id: str = "") -> Optional[Path]:
    if not book_dir.exists() or not book_dir.is_dir():
        return None

    files = sorted(path for path in book_dir.rglob("*.md") if path.is_file())
    best: Optional[Path] = None
    best_score = -1
    title_norm = str(title or "").strip().lower()
    book_id_norm = str(book_id or "").strip()

    for file_path in files:
        content = _read_note_text(file_path)
        if not content:
            continue

        name_lower = file_path.name.lower()
        stem_lower = file_path.stem.lower()
        score = 0

        if file_path.name.startswith("📖 "):
            score += 700
        if file_path.parent == book_dir:
            score += 80
        if "completo" in name_lower:
            score += 250
        if "capitulo" in stem_lower or "capítulo" in stem_lower:
            score -= 250
        if "pre-texto" in stem_lower or "pré-texto" in stem_lower or "pre texto" in stem_lower:
            score -= 300
        if re.search(r"(?mi)^type:\s*(book|livro)\s*$", content):
            score += 180
        if re.search(r"(?mi)^total_pages:\s*\d+\s*$", content):
            score += 120

        page_count = _count_page_markers(content)
        if page_count > 0:
            score += page_count

        if book_id_norm and re.search(rf"(?mi)^book_id:\s*{re.escape(book_id_norm)}\s*$", content):
            score += 500
        if title_norm and title_norm in content.lower():
            score += 40

        if score > best_score:
            best_score = score
            best = file_path

    return best


def _resolve_book_note_candidate(vault_root: Path, raw_path: object) -> Optional[Path]:
    raw = str(raw_path or "").strip().replace("\\", "/")
    if not raw:
        return None

    candidate = Path(raw)
    if not candidate.is_absolute():
        candidate = vault_root / candidate
    candidate = candidate.resolve(strict=False)
    if not candidate.exists() or not candidate.is_file() or candidate.suffix.lower() != ".md":
        return None
    return candidate


def _book_link_target(vault_root: Path, note_path: Path) -> str:
    try:
        return str(note_path.relative_to(vault_root).with_suffix("")).replace("\\", "/")
    except Exception:
        return ""


def _book_root_for_note(vault_root: Path, note_path: Path) -> Optional[Path]:
    try:
        relative = note_path.relative_to(vault_root)
    except Exception:
        return None

    parts = relative.parts
    if len(parts) < 3 or parts[0] != "01-LEITURAS":
        return None
    return vault_root / parts[0] / parts[1] / parts[2]


def _split_sections(content: str) -> tuple[list[str], list[tuple[str, list[str]]]]:
    lines = str(content or "").splitlines()
    headers: list[tuple[int, str]] = []
    for idx, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("## "):
            headers.append((idx, stripped))

    if not headers:
        return lines, []

    prefix = lines[: headers[0][0]]
    sections: list[tuple[str, list[str]]] = []
    for pos, (start_idx, header) in enumerate(headers):
        end_idx = headers[pos + 1][0] if pos + 1 < len(headers) else len(lines)
        sections.append((header, lines[start_idx + 1 : end_idx]))
    return prefix, sections


def _join_note_parts(prefix: list[str], sections: list[tuple[str, list[str]]]) -> str:
    parts: list[str] = []
    prefix_text = "\n".join(prefix).rstrip()
    if prefix_text:
        parts.append(prefix_text)
    for header, body_lines in sections:
        if parts:
            parts.append("")
        parts.append(header)
        body_text = "\n".join(body_lines).strip()
        if body_text:
            parts.append(body_text)
    return "\n".join(parts).rstrip() + "\n"


def _normalize_discipline_note_structure(content: str, discipline: str) -> tuple[list[str], list[tuple[str, list[str]]]]:
    prefix, raw_sections = _split_sections(content)
    if not prefix:
        prefix = [
            f"# Disciplina: {discipline}",
            "",
            "A assistente está organizando os conteúdos desta disciplina.",
        ]

    agenda_lines: list[str] = []
    books_lines: list[str] = []
    other_sections: list[tuple[str, list[str]]] = []
    for header, body_lines in raw_sections:
        normalized_header = BOOKS_SECTION_HEADER if header == LEGACY_BOOKS_SECTION_HEADER else header
        if normalized_header == AGENDA_SECTION_HEADER:
            agenda_lines.extend(body_lines)
            continue
        if normalized_header == BOOKS_SECTION_HEADER:
            books_lines.extend(body_lines)
            continue
        other_sections.append((normalized_header, body_lines))

    normalized_sections = [
        (AGENDA_SECTION_HEADER, agenda_lines),
        (BOOKS_SECTION_HEADER, books_lines),
        *other_sections,
    ]
    return prefix, normalized_sections


def _update_section_lines(
    content: str,
    discipline: str,
    header_name: str,
    updater,
) -> str:
    prefix, sections = _normalize_discipline_note_structure(content, discipline)
    updated_sections: list[tuple[str, list[str]]] = []
    for header, body_lines in sections:
        if header == header_name:
            updated_sections.append((header, updater(list(body_lines))))
        else:
            updated_sections.append((header, body_lines))
    return _join_note_parts(prefix, updated_sections)


def append_book_note_links(
    vault_root: Path,
    discipline: str,
    note_paths: Iterable[object],
    *,
    note_path: Optional[Path] = None,
) -> dict[str, object]:
    target_note = note_path or ensure_discipline_note(vault_root, discipline)
    if not target_note:
        return {"added_links": 0, "note_path": ""}

    content = _read_note_text(target_note)

    existing_targets: set[str] = set()
    for token in re.findall(r"\[\[([^\]]+)\]\]", content):
        normalized = token.split("|", 1)[0].strip().replace("\\", "/")
        if normalized:
            existing_targets.add(normalized)

    new_lines: list[str] = []
    for raw in note_paths:
        candidate = _resolve_book_note_candidate(vault_root, raw)
        if candidate is None:
            continue
        book_root = _book_root_for_note(vault_root, candidate)
        if book_root is not None:
            primary = find_primary_book_note(book_root)
            if primary is None or primary.resolve(strict=False) != candidate.resolve(strict=False):
                continue
        target = _book_link_target(vault_root, candidate)
        if not target or target in existing_targets:
            continue
        existing_targets.add(target)
        new_lines.append(f"- [[{target}|{candidate.stem}]]")

    if not new_lines:
        return {"added_links": 0, "note_path": str(target_note)}

    updated = _update_section_lines(
        content,
        discipline,
        BOOKS_SECTION_HEADER,
        lambda lines: list(lines) + new_lines,
    )
    target_note.write_text(updated, encoding="utf-8")
    return {"added_links": len(new_lines), "note_path": str(target_note)}


def append_event_link(
    vault_root: Path,
    discipline: str,
    *,
    title: str,
    start: str,
    end: str,
    event_id: str = "",
) -> Optional[Path]:
    note_path = ensure_discipline_note(vault_root, discipline)
    if not note_path:
        return None
    text = _read_note_text(note_path)

    marker = f"{start} · {title}"
    if marker not in text:
        suffix = f" (`{event_id}`)" if event_id else ""
        text = _update_section_lines(
            text,
            discipline,
            AGENDA_SECTION_HEADER,
            lambda lines: list(lines) + [f"- {start} - {end} · {title}{suffix}"],
        )
        note_path.write_text(text, encoding="utf-8")
    return note_path
