"""Helpers para montar contexto semantico de uma disciplina a partir do vault."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import math
import re
import unicodedata
from collections import Counter
from typing import Any, Iterable, Optional

from ui.utils.class_notes import WorkMaterial, load_discipline_works


_STOPWORDS = {
    "que", "com", "para", "por", "uma", "um", "as", "os", "do", "da",
    "de", "em", "no", "na", "nos", "nas", "o", "a", "e", "eh", "se",
    "mas", "como", "mais", "isso", "isto", "aquilo", "ser", "estar",
    "ter", "ha", "muito", "pouco", "nao", "sim", "ainda", "ja", "ao",
    "aos", "das", "dos", "ou", "sobre", "entre", "pela", "pelas",
    "pelo", "pelos", "sua", "seu", "suas", "seus", "minha", "meu",
    "minhas", "meus", "num", "numa", "porque", "quando", "onde",
}

_CATEGORY_LABELS = {
    "discipline": "DISCIPLINA",
    "book_primary": "OBRA_COMPLETA",
    "book_note": "NOTA_DE_OBRA",
    "annotation": "ANOTACAO",
    "canvas": "MAPA",
}

_CATEGORY_BOOSTS = {
    "discipline": 1.15,
    "book_primary": 1.35,
    "book_note": 1.0,
    "annotation": 1.1,
    "canvas": 0.95,
}


@dataclass(frozen=True)
class ScopedVaultNote:
    path: Path
    relative_path: str
    title: str
    content: str
    frontmatter: dict[str, Any]
    tags: tuple[str, ...]
    category: str


@dataclass(frozen=True)
class DisciplineAnnotationCandidate:
    path: Path
    relative_path: str
    title: str
    related_by_link: bool
    already_linked_in_discipline: bool


def build_discipline_semantic_context(
    vault_root: Path,
    discipline: str,
    query: str,
    *,
    extra_note_paths: Optional[Iterable[Path]] = None,
    max_results: int = 8,
    max_excerpt_chars: int = 2200,
) -> str:
    """Monta contexto textual da disciplina com busca semantica scoped."""
    discipline_name = str(discipline or "").strip()
    if not discipline_name:
        return "Disciplina invalida para contexto."

    works = load_discipline_works(vault_root, discipline_name)
    scoped_notes = collect_discipline_scoped_notes(
        vault_root,
        discipline_name,
        extra_note_paths=extra_note_paths,
    )

    if not scoped_notes:
        return f"Sem notas encontradas no escopo da disciplina '{discipline_name}'."

    ranked = rank_scoped_notes(scoped_notes, query, max_results=max_results)
    if not ranked:
        ranked = scoped_notes[:max_results]

    lines = [
        f"DISCIPLINA: {discipline_name}",
        f"OBRAS_IDENTIFICADAS: {len(works)}",
    ]

    if works:
        for work in works[:20]:
            lines.append(
                f"- {work.title} | principal={work.primary_target} | notas_relacionadas={len(work.note_targets)}"
            )
    else:
        lines.append("- Nenhuma obra vinculada na nota da disciplina.")

    lines.extend(
        [
            "",
            f"NOTAS_NO_ESCOPO: {len(scoped_notes)}",
            "RESULTADOS_SEMANTICOS_PRIORIZADOS:",
        ]
    )

    for index, note in enumerate(ranked, start=1):
        label = _CATEGORY_LABELS.get(note.category, note.category.upper())
        excerpt = _build_excerpt(note.content, query, max_chars=max_excerpt_chars)
        lines.append(f"[NOTA {index}] [{label}] {note.relative_path}")
        lines.append(f"Titulo: {note.title}")
        if note.tags:
            lines.append(f"Tags: {', '.join(note.tags[:12])}")
        lines.append(excerpt)
        lines.append("")

    return "\n".join(lines).strip()


def collect_discipline_scoped_notes(
    vault_root: Path,
    discipline: str,
    *,
    extra_note_paths: Optional[Iterable[Path]] = None,
) -> list[ScopedVaultNote]:
    """Coleta notas candidatas da disciplina: disciplina, obras, notas e anotacoes."""
    notes: list[ScopedVaultNote] = []
    seen: set[str] = set()

    def append_note(path: Optional[Path], category: str) -> None:
        if path is None:
            return
        note = _load_scoped_note(vault_root, path, category)
        if note is None:
            return
        key = str(note.path.resolve(strict=False)).lower()
        if key in seen:
            return
        seen.add(key)
        notes.append(note)

    discipline_note = _resolve_discipline_note(vault_root, discipline)
    append_note(discipline_note, "discipline")

    works = load_discipline_works(vault_root, discipline)
    work_targets: set[str] = set()

    for work in works:
        append_note(work.primary_note_abs, "book_primary")
        if work.primary_target:
            work_targets.add(_normalize_target(work.primary_target))
        for target in work.note_targets:
            work_targets.add(_normalize_target(target))
            append_note(_resolve_target_path(vault_root, target), "book_note")

    for annotation_path in _collect_related_annotation_paths(vault_root, discipline, work_targets):
        append_note(annotation_path, "annotation")

    for extra_path in extra_note_paths or []:
        append_note(extra_path, "canvas")

    notes.sort(key=lambda item: (item.category, item.relative_path.lower()))
    return notes


def list_discipline_annotation_candidates(
    vault_root: Path,
    discipline: str,
) -> list[DisciplineAnnotationCandidate]:
    """Lista anotações de 02-ANOTAÇÕES com status de vínculo automático com a disciplina."""
    discipline_name = str(discipline or "").strip()
    if not discipline_name:
        return []

    notes_dir = _annotation_notes_dir(vault_root)
    if notes_dir is None or not notes_dir.exists():
        return []

    discipline_note = _resolve_discipline_note(vault_root, discipline_name)
    discipline_norm = _normalize_token(discipline_name)
    discipline_targets: set[str] = set()
    if discipline_note is not None:
        try:
            discipline_targets.add(
                str(discipline_note.relative_to(vault_root).with_suffix("")).replace("\\", "/")
            )
        except Exception:
            pass

    work_targets: set[str] = set()
    for work in load_discipline_works(vault_root, discipline_name):
        if work.primary_target:
            work_targets.add(_normalize_target(work.primary_target))
        for target in work.note_targets:
            work_targets.add(_normalize_target(target))

    discipline_note_links: set[str] = set()
    if discipline_note is not None:
        discipline_note_links = _normalized_target_aliases(
            _extract_wikilink_targets(_read_text(discipline_note))
        )

    candidates: list[DisciplineAnnotationCandidate] = []
    for note_path in sorted(notes_dir.rglob("*.md"), key=lambda path: str(path).lower()):
        if not note_path.is_file():
            continue

        try:
            raw_text = note_path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            raw_text = ""

        frontmatter, body = _split_frontmatter(raw_text)
        title = str(frontmatter.get("title") or "").strip()
        if not title:
            title = _extract_heading(body) or note_path.stem

        try:
            relative_path = str(note_path.relative_to(vault_root)).replace("\\", "/")
        except Exception:
            continue

        note_target = str(Path(relative_path).with_suffix("")).replace("\\", "/")
        related_by_link = _annotation_has_scope_link(
            frontmatter=frontmatter,
            body=body,
            discipline_norm=discipline_norm,
            discipline_targets=discipline_targets,
            work_targets=work_targets,
        )
        already_linked = bool(
            _normalized_target_aliases([note_target]) & discipline_note_links
        )

        candidates.append(
            DisciplineAnnotationCandidate(
                path=note_path.resolve(strict=False),
                relative_path=relative_path,
                title=title,
                related_by_link=related_by_link,
                already_linked_in_discipline=already_linked,
            )
        )

    candidates.sort(
        key=lambda item: (
            not item.related_by_link,
            item.already_linked_in_discipline,
            item.title.lower(),
            item.relative_path.lower(),
        )
    )
    return candidates


def rank_scoped_notes(
    notes: list[ScopedVaultNote],
    query: str,
    *,
    max_results: int = 8,
) -> list[ScopedVaultNote]:
    """Ordena notas do escopo por relevancia textual/semantica leve."""
    if not notes:
        return []

    query_terms = _tokenize(query)
    if not query_terms:
        ordered = sorted(
            notes,
            key=lambda item: (-_CATEGORY_BOOSTS.get(item.category, 1.0), item.relative_path.lower()),
        )
        return ordered[:max_results]

    doc_freq = Counter()
    note_term_counts: dict[str, Counter[str]] = {}
    note_lengths: dict[str, int] = {}

    for note in notes:
        note_id = str(note.path.resolve(strict=False))
        text = _searchable_text(note)
        counts = Counter(_tokenize(text))
        note_term_counts[note_id] = counts
        note_lengths[note_id] = max(sum(counts.values()), 1)
        for term in counts:
            doc_freq[term] += 1

    total_docs = max(len(notes), 1)
    query_counts = Counter(query_terms)
    ranked: list[tuple[float, ScopedVaultNote]] = []
    normalized_query = _normalize_text(query)

    for note in notes:
        note_id = str(note.path.resolve(strict=False))
        counts = note_term_counts.get(note_id, Counter())
        if not counts:
            continue

        score = 0.0
        note_text = _searchable_text(note)
        normalized_note_text = _normalize_text(note_text)
        normalized_title = _normalize_text(note.title)

        for term, q_count in query_counts.items():
            tf = counts.get(term, 0) / note_lengths[note_id]
            if tf <= 0:
                continue
            idf = math.log((1 + total_docs) / (1 + doc_freq.get(term, 0))) + 1.0
            score += (tf * idf) * q_count

            if term in normalized_title:
                score += 0.45

        if normalized_query and normalized_query in normalized_title:
            score += 2.0
        elif normalized_query and normalized_query in normalized_note_text:
            score += 1.0

        overlap = len(set(query_terms) & set(counts.keys()))
        if overlap:
            score += overlap * 0.15

        score *= _CATEGORY_BOOSTS.get(note.category, 1.0)
        if score > 0:
            ranked.append((score, note))

    ranked.sort(key=lambda item: (-item[0], item[1].relative_path.lower()))
    return [note for _, note in ranked[:max_results]]


def _collect_related_annotation_paths(
    vault_root: Path,
    discipline: str,
    work_targets: set[str],
) -> list[Path]:
    notes_dir = _annotation_notes_dir(vault_root)
    if notes_dir is None or not notes_dir.exists():
        return []

    discipline_norm = _normalize_token(discipline)
    discipline_targets: set[str] = set()
    discipline_note = _resolve_discipline_note(vault_root, discipline)
    if discipline_note is not None:
        try:
            discipline_targets.add(str(discipline_note.relative_to(vault_root).with_suffix("")).replace("\\", "/"))
        except Exception:
            pass
    found: list[Path] = []

    for note_path in sorted(notes_dir.rglob("*.md")):
        raw_text = _read_text(note_path)
        if not raw_text:
            continue
        frontmatter, body = _split_frontmatter(raw_text)

        if _annotation_matches_scope(
            note_path=note_path,
            frontmatter=frontmatter,
            body=body,
            discipline_norm=discipline_norm,
            discipline_targets=discipline_targets,
            work_targets=work_targets,
        ):
            found.append(note_path)

    return found


def _annotation_matches_scope(
    *,
    note_path: Path,
    frontmatter: dict[str, Any],
    body: str,
    discipline_norm: str,
    discipline_targets: set[str],
    work_targets: set[str],
) -> bool:
    if _annotation_has_scope_link(
        frontmatter=frontmatter,
        body=body,
        discipline_norm=discipline_norm,
        discipline_targets=discipline_targets,
        work_targets=work_targets,
    ):
        return True

    note_text = _normalize_text(body)
    return bool(discipline_norm and discipline_norm in note_text)


def _annotation_has_scope_link(
    *,
    frontmatter: dict[str, Any],
    body: str,
    discipline_norm: str,
    discipline_targets: set[str],
    work_targets: set[str],
) -> bool:
    fm_discipline = _normalize_token(str(frontmatter.get("discipline") or ""))
    if discipline_norm and fm_discipline and fm_discipline == discipline_norm:
        return True

    linked_targets = _collect_annotation_link_targets(frontmatter, body)
    linked_aliases = _normalized_target_aliases(linked_targets)
    scope_aliases = _normalized_target_aliases({*discipline_targets, *work_targets})
    if scope_aliases and (linked_aliases & scope_aliases):
        return True

    return False


def _collect_annotation_link_targets(frontmatter: dict[str, Any], body: str) -> set[str]:
    linked_targets: set[str] = set()
    for key in ("works", "work_notes"):
        value = frontmatter.get(key)
        if isinstance(value, (list, tuple, set)):
            for item in value:
                normalized = _normalize_target(str(item or ""))
                if normalized:
                    linked_targets.add(normalized)
        elif isinstance(value, str):
            normalized = _normalize_target(value)
            if normalized:
                linked_targets.add(normalized)

    linked_targets.update(_extract_wikilink_targets(body))
    return linked_targets


def _extract_wikilink_targets(text: str) -> set[str]:
    targets: set[str] = set()
    for token in re.findall(r"\[\[([^\]]+)\]\]", str(text or "")):
        target = token.split("|", 1)[0].strip()
        normalized = _normalize_target(target)
        if normalized:
            targets.add(normalized)
    return targets


def _normalized_target_aliases(targets: Iterable[str]) -> set[str]:
    aliases: set[str] = set()
    for target in targets:
        normalized = _normalize_target(target)
        if not normalized:
            continue
        aliases.add(normalized)
        path = Path(normalized)
        name = str(path.name or "").strip().lower()
        stem = str(path.stem or "").strip().lower()
        if name:
            aliases.add(name)
        if stem:
            aliases.add(stem)
    return aliases


def _annotation_notes_dir(vault_root: Path) -> Optional[Path]:
    canonical_dir = vault_root / "02-ANOTAÇÕES"
    if canonical_dir.exists():
        return canonical_dir

    fallback_dir = vault_root / "02-ANOTACOES"
    if fallback_dir.exists():
        return fallback_dir
    return canonical_dir


def _load_scoped_note(vault_root: Path, path: Path, category: str) -> Optional[ScopedVaultNote]:
    try:
        resolved = path.resolve(strict=False)
        relative = str(resolved.relative_to(vault_root)).replace("\\", "/")
    except Exception:
        return None

    raw_text = _read_text(path)
    if not raw_text:
        return None

    frontmatter, body = _split_frontmatter(raw_text)
    title = str(frontmatter.get("title") or "").strip()
    if not title:
        title = _extract_heading(body) or path.stem

    tags = _coerce_tags(frontmatter.get("tags"))

    return ScopedVaultNote(
        path=resolved,
        relative_path=relative,
        title=title,
        content=body.strip(),
        frontmatter=frontmatter,
        tags=tags,
        category=category,
    )


def _split_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    raw = str(text or "")
    if not raw.startswith("---"):
        return {}, raw

    parts = raw.split("---", 2)
    if len(parts) < 3:
        return {}, raw

    parsed = _parse_simple_frontmatter(parts[1])
    return parsed, parts[2].lstrip("\n")


def _parse_simple_frontmatter(raw: str) -> dict[str, Any]:
    parsed: dict[str, Any] = {}
    current_list_key = ""

    for line in str(raw or "").splitlines():
        if not line.strip():
            continue
        if line.startswith("  - ") or line.startswith("- "):
            if current_list_key:
                parsed.setdefault(current_list_key, [])
                parsed[current_list_key].append(line.split("-", 1)[1].strip().strip("'\""))
            continue

        if ":" not in line:
            current_list_key = ""
            continue

        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip()
        current_list_key = ""

        if not key:
            continue
        if not value:
            parsed[key] = []
            current_list_key = key
            continue
        if value.startswith("[") and value.endswith("]"):
            items = [
                item.strip().strip("'\"")
                for item in value[1:-1].split(",")
                if item.strip()
            ]
            parsed[key] = items
            continue

        parsed[key] = value.strip("'\"")

    return parsed


def _extract_heading(content: str) -> str:
    for line in str(content or "").splitlines():
        cleaned = line.strip()
        if cleaned.startswith("#"):
            return cleaned.lstrip("#").strip()
    return ""


def _coerce_tags(raw_value: Any) -> tuple[str, ...]:
    if isinstance(raw_value, str):
        values = [raw_value]
    elif isinstance(raw_value, (list, tuple, set)):
        values = [str(item or "").strip() for item in raw_value]
    else:
        values = []
    clean = [value for value in values if value]
    return tuple(dict.fromkeys(clean))


def _resolve_discipline_note(vault_root: Path, discipline: str) -> Optional[Path]:
    discipline_dir = vault_root / "05-DISCIPLINAS"
    if not discipline_dir.exists():
        return None

    expected = _normalize_token(discipline)
    for candidate in discipline_dir.glob("*.md"):
        if _normalize_token(candidate.stem) == expected:
            return candidate
        text = _read_text(candidate)
        for line in text.splitlines():
            stripped = line.strip()
            if stripped.lower().startswith("# disciplina:"):
                display_name = stripped.split(":", 1)[1].strip()
                if _normalize_token(display_name) == expected:
                    return candidate
    return None


def _resolve_target_path(vault_root: Path, target: str) -> Optional[Path]:
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


def _searchable_text(note: ScopedVaultNote) -> str:
    fields: list[str] = [note.title, " ".join(note.tags), note.content]
    for key in ("discipline", "author", "book", "type"):
        value = str(note.frontmatter.get(key) or "").strip()
        if value:
            fields.append(value)
    return "\n".join(fields)


def _build_excerpt(content: str, query: str, *, max_chars: int) -> str:
    raw = str(content or "").strip()
    if not raw:
        return "(sem conteudo textual)"

    compact = re.sub(r"\n{3,}", "\n\n", raw)
    normalized_query = _normalize_text(query)
    normalized_content = _normalize_text(compact)

    if normalized_query:
        index = normalized_content.find(normalized_query)
        if index >= 0:
            start = max(0, index - max_chars // 4)
            end = min(len(compact), start + max_chars)
            excerpt = compact[start:end].strip()
            if start > 0:
                excerpt = "[...] " + excerpt
            if end < len(compact):
                excerpt = excerpt + " [...]"
            return excerpt

    if len(compact) > max_chars:
        return compact[:max_chars].rstrip() + "\n[...]"
    return compact


def _tokenize(text: str) -> list[str]:
    normalized = _normalize_text(text)
    words = re.findall(r"[a-z0-9]{3,}", normalized)
    return [word for word in words if word not in _STOPWORDS]


def _normalize_text(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", str(text or "").strip().lower())
    normalized = "".join(ch for ch in normalized if not unicodedata.combining(ch))
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized


def _normalize_target(target: str) -> str:
    cleaned = str(target or "").strip().replace("\\", "/")
    if not cleaned:
        return ""
    path = Path(cleaned)
    without_suffix = str(path.with_suffix("")) if path.suffix else cleaned
    return without_suffix.replace("\\", "/").strip().lower()


def _normalize_token(value: str) -> str:
    normalized = _normalize_text(value)
    return re.sub(r"[^a-z0-9]+", "-", normalized).strip("-")


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""
