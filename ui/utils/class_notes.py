"""Utilitários para criação de notas de aula em 03-PRODUÇÃO."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import re
import unicodedata
from typing import Any, Optional

from ui.utils.discipline_links import find_primary_book_note


PRODUCTION_DIR = "03-PRODUÇÃO"
DISCIPLINE_DIR = "05-DISCIPLINAS"
ANNOTATIONS_HEADER = "## Anotações da aula"


@dataclass(frozen=True)
class WorkMaterial:
    """Representa uma obra selecionável para uma aula."""

    title: str
    primary_note_abs: Path
    work_dir_abs: Path
    primary_target: str
    note_targets: tuple[str, ...]


def _normalize_token(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", str(value or "").strip())
    normalized = "".join(ch for ch in normalized if not unicodedata.combining(ch))
    normalized = re.sub(r"[^a-zA-Z0-9]+", "-", normalized).strip("-").lower()
    return normalized


def _safe_filename(value: str) -> str:
    text = re.sub(r'[<>:"/\\|?*]+', "-", str(value or "").strip())
    text = re.sub(r"\s+", " ", text).strip().rstrip(".")
    return text or "nota"


def _format_display_date(event_dt: datetime) -> str:
    return event_dt.strftime("%d/%m/%Y")


def _format_file_date(event_dt: datetime) -> str:
    return event_dt.strftime("%d-%m-%Y")


def _event_datetime(event_data: dict[str, Any]) -> datetime:
    for key in ("start", "start_time"):
        raw = str(event_data.get(key) or "").strip()
        if not raw:
            continue
        try:
            return datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except Exception:
            continue
    raise ValueError("Evento sem data/hora de início válida.")


def _resolve_discipline_note_path(vault_root: Path, discipline: str) -> Optional[Path]:
    discipline_dir = vault_root / DISCIPLINE_DIR
    if not discipline_dir.exists():
        return None

    direct = discipline_dir / f"{_safe_filename(discipline)}.md"
    if direct.exists():
        return direct

    expected = _normalize_token(discipline)
    for candidate in discipline_dir.glob("*.md"):
        if _normalize_token(candidate.stem) == expected:
            return candidate
        try:
            text = candidate.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        for line in text.splitlines():
            stripped = line.strip()
            if stripped.lower().startswith("# disciplina:"):
                display_name = stripped.split(":", 1)[1].strip()
                if _normalize_token(display_name) == expected:
                    return candidate
    return None


def _resolve_obsidian_target(vault_root: Path, target: str) -> Optional[Path]:
    cleaned = str(target or "").strip().replace("\\", "/")
    if not cleaned:
        return None

    candidate = Path(cleaned)
    options = [candidate]
    if candidate.suffix.lower() != ".md":
        options.append(candidate.with_suffix(".md"))

    for option in options:
        full = option if option.is_absolute() else (vault_root / option)
        full = full.resolve(strict=False)
        if full.exists() and full.is_file():
            return full
    return None


def _vault_target(vault_root: Path, note_abs: Path) -> str:
    return str(note_abs.relative_to(vault_root).with_suffix("")).replace("\\", "/")


def _collect_work_note_targets(vault_root: Path, work_dir_abs: Path, primary_note_abs: Path) -> tuple[str, ...]:
    targets: list[str] = []
    seen: set[str] = set()
    for candidate in sorted(work_dir_abs.rglob("*.md")):
        if not candidate.is_file() or candidate.resolve(strict=False) == primary_note_abs.resolve(strict=False):
            continue
        target = _vault_target(vault_root, candidate)
        if not target or target in seen:
            continue
        seen.add(target)
        targets.append(target)
    return tuple(targets)


def load_discipline_works(vault_root: Path, discipline: str) -> list[WorkMaterial]:
    """Lista obras vinculadas a uma disciplina a partir da nota da disciplina."""
    note_path = _resolve_discipline_note_path(vault_root, discipline)
    if not note_path or not note_path.exists():
        return []

    try:
        content = note_path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return []

    works: list[WorkMaterial] = []
    seen: set[str] = set()
    for token in re.findall(r"\[\[([^\]]+)\]\]", content):
        target = token.split("|", 1)[0].strip().replace("\\", "/")
        resolved = _resolve_obsidian_target(vault_root, target)
        if not resolved or resolved.suffix.lower() != ".md":
            continue

        try:
            relative = resolved.relative_to(vault_root)
        except Exception:
            continue
        if len(relative.parts) < 3 or relative.parts[0] != "01-LEITURAS":
            continue

        work_dir_abs = vault_root / relative.parts[0] / relative.parts[1] / relative.parts[2]
        primary_note_abs = find_primary_book_note(work_dir_abs) or resolved
        work_key = str(primary_note_abs.resolve(strict=False))
        if work_key in seen:
            continue
        seen.add(work_key)

        works.append(
            WorkMaterial(
                title=primary_note_abs.stem.removeprefix("📖 ").strip() or work_dir_abs.name,
                primary_note_abs=primary_note_abs,
                work_dir_abs=work_dir_abs,
                primary_target=_vault_target(vault_root, primary_note_abs),
                note_targets=_collect_work_note_targets(vault_root, work_dir_abs, primary_note_abs),
            )
        )

    works.sort(key=lambda item: item.title.lower())
    return works


def build_class_note_filename(discipline: str, event_dt: datetime) -> str:
    return _safe_filename(f"Aula de {discipline} do dia {_format_file_date(event_dt)}")


def build_class_note_relative_path(discipline: str, event_data: dict[str, Any]) -> str:
    event_dt = _event_datetime(event_data)
    return f"{PRODUCTION_DIR}/{build_class_note_filename(discipline, event_dt)}.md"


def _extract_existing_annotations(existing_content: str) -> str:
    text = str(existing_content or "")
    if not text.strip():
        return ""

    marker = f"\n{ANNOTATIONS_HEADER}\n"
    if marker in text:
        return text.split(marker, 1)[1].strip()

    if text.startswith(f"{ANNOTATIONS_HEADER}\n"):
        return text.split(f"{ANNOTATIONS_HEADER}\n", 1)[1].strip()

    return text.strip()


def _link_line(target: str) -> str:
    label = Path(target).name
    return f"- [[{target}|{label}]]"


def build_class_note_content(
    *,
    discipline: str,
    event_data: dict[str, Any],
    selected_works: list[WorkMaterial],
    existing_content: str = "",
) -> tuple[dict[str, Any], str]:
    """Monta frontmatter e corpo padronizados para a nota de aula."""
    event_dt = _event_datetime(event_data)
    title = f"Aula de {discipline} do dia {_format_file_date(event_dt)}"
    event_id = str(event_data.get("id") or "").strip()
    annotations = _extract_existing_annotations(existing_content)

    unique_work_targets: list[str] = []
    seen_work_targets: set[str] = set()
    note_targets_by_work: list[tuple[str, tuple[str, ...]]] = []
    aggregated_note_targets: list[str] = []
    seen_note_targets: set[str] = set()

    for work in selected_works:
        if work.primary_target and work.primary_target not in seen_work_targets:
            seen_work_targets.add(work.primary_target)
            unique_work_targets.append(work.primary_target)

        scoped_targets: list[str] = []
        for target in work.note_targets:
            if not target or target in seen_note_targets:
                continue
            seen_note_targets.add(target)
            aggregated_note_targets.append(target)
            scoped_targets.append(target)
        note_targets_by_work.append((work.title, tuple(scoped_targets)))

    frontmatter = {
        "title": title,
        "type": "class_note",
        "discipline": discipline,
        "event_id": event_id,
        "event_date": event_dt.date().isoformat(),
        "event_start": event_dt.isoformat(),
        "tags": [
            "aula",
            "class_note",
            "anotacoes-em-aula",
            _normalize_token(discipline) or "disciplina",
        ],
        "works": unique_work_targets,
        "work_notes": aggregated_note_targets,
    }

    lines: list[str] = [
        f"# {title}",
        "",
        f"**Disciplina:** {discipline}",
        f"**Data:** {_format_display_date(event_dt)}",
        f"**Horário:** {event_dt.strftime('%H:%M')}",
        "",
        "## Obras da aula",
    ]

    if unique_work_targets:
        lines.extend(_link_line(target) for target in unique_work_targets)
    else:
        lines.append("- Nenhuma obra selecionada.")

    lines.extend(["", "## Notas das obras"])
    if note_targets_by_work:
        for work_title, note_targets in note_targets_by_work:
            lines.append(f"### {work_title}")
            if note_targets:
                lines.extend(_link_line(target) for target in note_targets)
            else:
                lines.append("- Nenhuma nota complementar encontrada.")
            lines.append("")
        while lines and not lines[-1].strip():
            lines.pop()
    else:
        lines.append("- Nenhuma nota complementar encontrada.")

    lines.extend(["", ANNOTATIONS_HEADER, ""])
    if annotations:
        lines.append(annotations)
    else:
        lines.append("<!-- Espaço livre para anotar o conteúdo da aula. -->")

    return frontmatter, "\n".join(lines).rstrip() + "\n"
