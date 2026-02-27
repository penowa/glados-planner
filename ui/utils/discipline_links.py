"""Utilitários para notas de disciplina no diretório 05-DISCIPLINAS."""
from __future__ import annotations

import re
import unicodedata
from pathlib import Path
from typing import Optional


DISCIPLINE_DIR = "05-DISCIPLINAS"


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
        "## Livro processado\n\n"
        "## Agenda\n"
    )
    note_path.write_text(content, encoding="utf-8")
    return note_path


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
    text = note_path.read_text(encoding="utf-8", errors="ignore")
    if "## Agenda" not in text:
        text = text.rstrip() + "\n\n## Agenda\n"

    marker = f"{start} · {title}"
    if marker not in text:
        suffix = f" (`{event_id}`)" if event_id else ""
        text = text.rstrip() + f"\n- {start} - {end} · {title}{suffix}\n"
        note_path.write_text(text, encoding="utf-8")
    return note_path
