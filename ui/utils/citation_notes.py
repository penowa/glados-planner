"""Utilitários para notas de citações por livro em 02-ANOTAÇÕES."""
from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import re
import unicodedata
import uuid
from typing import Any, Dict, Iterable, Optional

from ui.utils.class_notes import load_discipline_works
from ui.utils.discipline_links import (
    append_annotation_note_links,
    ensure_discipline_note,
    find_primary_book_note,
    list_disciplines,
)


ANNOTATIONS_DIR = "02-ANOTAÇÕES"
DISCIPLINE_DIR = "05-DISCIPLINAS"
READINGS_DIR = "01-LEITURAS"
MINDMAPS_DIR = "04-MAPAS MENTAIS"


@dataclass(frozen=True)
class CitationNoteContext:
    """Contexto mínimo para materializar a nota de citações de uma obra."""

    vault_root: Path
    title: str
    author: str
    book_note_path: Path
    book_dir_path: Path
    book_id: str = ""
    discipline: str = ""
    discipline_note_path: Optional[Path] = None
    source_pdf_path: Optional[Path] = None


def _normalize_token(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", str(value or "").strip())
    normalized = "".join(ch for ch in normalized if not unicodedata.combining(ch))
    normalized = re.sub(r"[^a-zA-Z0-9]+", "-", normalized).strip("-").lower()
    return normalized


def _sanitize_obsidian_title(value: str) -> str:
    cleaned = str(value or "").strip().replace("\n", " ")
    cleaned = re.sub(r'[\\/:*?"<>|]+', "-", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip(". ").strip()
    return cleaned or "Citações"


def _sanitize_canvas_filename(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9._-]+", "-", str(value or "").strip()).strip("-").lower() or "review"


def _card_dimensions_for_title(title: str, is_text: bool = False) -> tuple[int, int]:
    clean = re.sub(r"\s+", " ", str(title or "").strip())
    if not clean:
        clean = "Sem título"
    per_char = 8 if is_text else 7
    base = 170 if is_text else 150
    min_w = 240 if is_text else 180
    max_w = 460 if is_text else 340
    width = base + (len(clean[:48]) * per_char)
    bounded_width = max(min_w, min(max_w, width))
    height = 96 if is_text else 64
    return bounded_width, height


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""


def _strip_quotes(value: str) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    if len(text) >= 2 and text[0] == text[-1] and text[0] in {"'", '"'}:
        return text[1:-1].strip()
    return text


def _parse_frontmatter(text: str) -> Dict[str, Any]:
    raw = str(text or "")
    if not raw.startswith("---"):
        return {}

    lines = raw.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}

    frontmatter: Dict[str, Any] = {}
    current_key = ""
    current_list: list[str] = []
    current_scalar_key = ""
    current_scalar_lines: list[str] = []

    def flush_list() -> None:
        nonlocal current_key, current_list
        if current_key:
            frontmatter[current_key] = list(current_list)
        current_key = ""
        current_list = []

    def flush_scalar() -> None:
        nonlocal current_scalar_key, current_scalar_lines
        if current_scalar_key:
            merged = " ".join(part.strip() for part in current_scalar_lines if part.strip())
            frontmatter[current_scalar_key] = _strip_quotes(merged)
        current_scalar_key = ""
        current_scalar_lines = []

    for line in lines[1:]:
        stripped = line.strip()
        if stripped == "---":
            flush_list()
            flush_scalar()
            break

        if current_key and stripped.startswith("- "):
            current_list.append(_strip_quotes(stripped[2:].strip()))
            continue

        if current_scalar_key and (line[:1].isspace() or stripped == "") and not stripped.startswith("- "):
            current_scalar_lines.append(stripped)
            continue

        flush_list()
        flush_scalar()

        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip()
        if not key:
            continue
        if value == "":
            current_key = key
            current_list = []
            continue
        current_scalar_key = key
        current_scalar_lines = [value]

    flush_list()
    flush_scalar()

    return frontmatter


def _relative_target(vault_root: Path, path: Path, *, keep_suffix: bool = False) -> str:
    try:
        relative = path.resolve(strict=False).relative_to(vault_root.resolve(strict=False))
    except Exception:
        return ""
    target = str(relative).replace("\\", "/")
    if keep_suffix:
        return target
    return str(relative.with_suffix("")).replace("\\", "/")


def _wikilink(vault_root: Path, path: Optional[Path], *, alias: str = "") -> str:
    if path is None:
        return "-"
    target = _relative_target(vault_root, path, keep_suffix=False)
    if not target:
        return path.stem
    if alias:
        return f"[[{target}|{alias}]]"
    return f"[[{target}]]"


def build_citations_note_path(vault_root: Path, title: str) -> Path:
    safe = _sanitize_obsidian_title(f"Citações {title}")
    return Path(vault_root) / ANNOTATIONS_DIR / f"{safe}.md"


def _discipline_note_path(vault_root: Path, discipline: str) -> Optional[Path]:
    name = str(discipline or "").strip()
    if not name:
        return None
    note = ensure_discipline_note(vault_root, name)
    if note and note.exists():
        return note
    return None


def _build_discipline_book_index(vault_root: Path) -> Dict[str, tuple[str, Path]]:
    index: Dict[str, tuple[str, Path]] = {}
    for discipline in list_disciplines(vault_root):
        note_path = _discipline_note_path(vault_root, discipline)
        if note_path is None:
            continue
        for work in load_discipline_works(vault_root, discipline):
            key = str(work.primary_note_abs.resolve(strict=False))
            index[key] = (discipline, note_path)
    return index


def _source_pdf_from_registry(vault_root: Path, book_id: str) -> Optional[Path]:
    normalized = str(book_id or "").strip()
    if not normalized:
        return None
    registry_path = Path(vault_root) / "06-RECURSOS" / "registros_livros" / f"{normalized}.json"
    if not registry_path.exists():
        return None
    try:
        data = json.loads(registry_path.read_text(encoding="utf-8", errors="ignore"))
    except Exception:
        return None
    if not isinstance(data, dict):
        return None
    raw = str(data.get("file_path") or "").strip()
    if not raw:
        return None
    path = Path(raw).expanduser()
    return path if path.exists() else path


def resolve_citation_note_context(
    vault_root: Path,
    *,
    book_note_path: Optional[Path] = None,
    book_dir_path: Optional[Path] = None,
    discipline: str = "",
    discipline_note_path: Optional[Path] = None,
    source_pdf_path: Optional[Path] = None,
    discipline_index: Optional[Dict[str, tuple[str, Path]]] = None,
) -> Optional[CitationNoteContext]:
    root = Path(vault_root).expanduser().resolve(strict=False)
    book_dir = Path(book_dir_path).expanduser().resolve(strict=False) if book_dir_path else None
    book_note = Path(book_note_path).expanduser().resolve(strict=False) if book_note_path else None

    if book_note is None and book_dir is not None:
        book_note = find_primary_book_note(book_dir)
    if book_note is None or not book_note.exists():
        return None

    if book_dir is None:
        book_dir = book_note.parent

    frontmatter = _parse_frontmatter(_read_text(book_note))
    title = str(frontmatter.get("title") or book_note.stem.removeprefix("📖 ").removeprefix("📚 ").strip()).strip()
    author = str(frontmatter.get("author") or book_dir.parent.name or "Autor Desconhecido").strip()
    book_id = str(frontmatter.get("book_id") or "").strip()

    note_lookup = discipline_index or {}
    matched = note_lookup.get(str(book_note.resolve(strict=False)))
    resolved_discipline = str(discipline or (matched[0] if matched else "")).strip()
    resolved_discipline_note = discipline_note_path
    if resolved_discipline_note is None and matched:
        resolved_discipline_note = matched[1]
    if resolved_discipline_note is None and resolved_discipline:
        resolved_discipline_note = _discipline_note_path(root, resolved_discipline)

    resolved_source = Path(source_pdf_path).expanduser() if source_pdf_path else None
    if resolved_source is None:
        resolved_source = _source_pdf_from_registry(root, book_id)

    return CitationNoteContext(
        vault_root=root,
        title=title or book_dir.name,
        author=author or "Autor Desconhecido",
        book_note_path=book_note,
        book_dir_path=book_dir,
        book_id=book_id,
        discipline=resolved_discipline,
        discipline_note_path=resolved_discipline_note,
        source_pdf_path=resolved_source,
    )


def build_citations_note_header(context: CitationNoteContext) -> str:
    title = f"Citações {context.title}".strip()
    lines = [f"# {title}", "", "## Referências"]
    lines.append(f"- Livro: {_wikilink(context.vault_root, context.book_note_path, alias=context.book_note_path.stem)}")

    if context.discipline_note_path:
        lines.append(
            f"- Disciplina: {_wikilink(context.vault_root, context.discipline_note_path, alias=context.discipline_note_path.stem)}"
        )

    if context.book_note_path.exists():
        lines.append(f"- Nota base: {_wikilink(context.vault_root, context.book_note_path, alias=context.book_note_path.stem)}")

    if context.source_pdf_path is not None:
        lines.append(f"- PDF original: `{context.source_pdf_path}`")

    lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _ensure_citations_note_header(note_path: Path, header: str) -> tuple[bool, str]:
    existing = _read_text(note_path)
    if not existing.strip():
        return True, header

    stripped = existing.lstrip()
    if "## Referências" in stripped:
        return False, existing

    updated = header.rstrip() + "\n\n" + stripped.strip() + "\n"
    return updated != existing, updated


def _load_canvas_payload(canvas_path: Path) -> Dict[str, Any]:
    if not canvas_path.exists():
        return {"nodes": [], "edges": []}
    try:
        loaded = json.loads(canvas_path.read_text(encoding="utf-8", errors="ignore"))
    except Exception:
        return {"nodes": [], "edges": []}
    nodes = loaded.get("nodes") if isinstance(loaded, dict) else None
    edges = loaded.get("edges") if isinstance(loaded, dict) else None
    return {
        "nodes": nodes if isinstance(nodes, list) else [],
        "edges": edges if isinstance(edges, list) else [],
    }


def _dump_canvas_payload(canvas_path: Path, payload: Dict[str, Any]) -> None:
    canvas_path.parent.mkdir(parents=True, exist_ok=True)
    canvas_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _ensure_canvas_root(nodes: list[Dict[str, Any]], discipline: str) -> str:
    for node in nodes:
        if isinstance(node, dict) and str(node.get("id") or "").strip() == "node-disciplina":
            return "node-disciplina"

    root_title = f"Mapa da disciplina\n{discipline}"
    width, height = _card_dimensions_for_title(root_title, is_text=True)
    nodes.insert(
        0,
        {
            "id": "node-disciplina",
            "type": "text",
            "text": root_title,
            "x": 0.0,
            "y": 0.0,
            "width": width,
            "height": height,
            "color": "4",
        },
    )
    return "node-disciplina"


def _node_position(node: Dict[str, Any]) -> tuple[float, float]:
    try:
        x = float(node.get("x", 0) or 0)
    except Exception:
        x = 0.0
    try:
        y = float(node.get("y", 0) or 0)
    except Exception:
        y = 0.0
    return x, y


def _node_right_edge(node: Dict[str, Any]) -> float:
    x, _ = _node_position(node)
    try:
        width = float(node.get("width", 220) or 220)
    except Exception:
        width = 220.0
    return x + width


def _generate_unique_node_id(nodes: Iterable[Dict[str, Any]], prefix: str) -> str:
    existing = {
        str(node.get("id") or "").strip()
        for node in nodes
        if isinstance(node, dict) and str(node.get("id") or "").strip()
    }
    base = f"{prefix}-{uuid.uuid4().hex[:8]}"
    if base not in existing:
        return base
    counter = 2
    while True:
        candidate = f"{base}-{counter}"
        if candidate not in existing:
            return candidate
        counter += 1


def _generate_unique_edge_id(edges: Iterable[Dict[str, Any]], prefix: str = "edge") -> str:
    existing = {
        str(edge.get("id") or "").strip()
        for edge in edges
        if isinstance(edge, dict) and str(edge.get("id") or "").strip()
    }
    base = f"{prefix}-{uuid.uuid4().hex[:8]}"
    if base not in existing:
        return base
    counter = 2
    while True:
        candidate = f"{base}-{counter}"
        if candidate not in existing:
            return candidate
        counter += 1


def _has_edge(
    edges: Iterable[Dict[str, Any]],
    *,
    from_node: str,
    to_node: str,
    from_side: str = "right",
    to_side: str = "left",
) -> bool:
    from_id = str(from_node or "").strip()
    to_id = str(to_node or "").strip()
    for edge in edges:
        if not isinstance(edge, dict):
            continue
        if str(edge.get("fromNode") or "").strip() != from_id:
            continue
        if str(edge.get("toNode") or "").strip() != to_id:
            continue
        if str(edge.get("fromSide") or "right").strip().lower() != from_side:
            continue
        if str(edge.get("toSide") or "left").strip().lower() != to_side:
            continue
        return True
    return False


def _append_edge(
    edges: list[Dict[str, Any]],
    *,
    from_node: str,
    to_node: str,
    label: str,
    color: str,
    from_side: str = "right",
    to_side: str = "left",
) -> bool:
    if _has_edge(edges, from_node=from_node, to_node=to_node, from_side=from_side, to_side=to_side):
        return False
    edges.append(
        {
            "id": _generate_unique_edge_id(edges),
            "fromNode": from_node,
            "toNode": to_node,
            "fromSide": from_side,
            "toSide": to_side,
            "label": str(label or "").strip(),
            "color": str(color or "6"),
        }
    )
    return True


def _find_file_node(nodes: Iterable[Dict[str, Any]], relative_path: str) -> Optional[Dict[str, Any]]:
    target = str(relative_path or "").strip().replace("\\", "/")
    if not target:
        return None
    for node in nodes:
        if not isinstance(node, dict):
            continue
        if str(node.get("type") or "").strip().lower() != "file":
            continue
        if str(node.get("file") or "").strip().replace("\\", "/") == target:
            return node
    return None


def _find_work_anchor(
    nodes: Iterable[Dict[str, Any]],
    *,
    book_dir_rel: str,
    work_key: str,
    title: str,
) -> Optional[Dict[str, Any]]:
    normalized_title = _normalize_token(title)
    normalized_dir = str(book_dir_rel or "").strip().replace("\\", "/")
    normalized_key = str(work_key or "").strip()

    for node in nodes:
        if not isinstance(node, dict):
            continue
        anchor_flag = str(node.get("discipline_work_anchor") or "").strip().lower()
        if anchor_flag not in {"1", "true", "yes"}:
            continue
        if str(node.get("book_dir") or "").strip().replace("\\", "/") == normalized_dir:
            return node
        if normalized_key and str(node.get("work_key") or "").strip() == normalized_key:
            return node
        node_title = str(node.get("work_title") or node.get("text") or "").strip()
        if normalized_title and normalized_title in _normalize_token(node_title):
            return node
    return None


def _next_anchor_position(nodes: Iterable[Dict[str, Any]]) -> tuple[float, float]:
    anchor_nodes = [
        node
        for node in nodes
        if isinstance(node, dict)
        and str(node.get("discipline_work_anchor") or "").strip().lower() in {"1", "true", "yes"}
    ]
    if not anchor_nodes:
        return 650.0, 180.0
    max_y = max(_node_position(node)[1] for node in anchor_nodes)
    return 650.0, max_y + 220.0


def _ensure_work_anchor_and_book_note(
    payload: Dict[str, Any],
    *,
    context: CitationNoteContext,
) -> tuple[str, str, bool]:
    nodes = payload["nodes"]
    edges = payload["edges"]
    root_id = _ensure_canvas_root(nodes, context.discipline)
    book_dir_rel = _relative_target(context.vault_root, context.book_dir_path, keep_suffix=True)
    book_rel = _relative_target(context.vault_root, context.book_note_path, keep_suffix=True)
    work_key = _normalize_token(f"{context.book_dir_path.parent.name}/{context.book_dir_path.name}")

    anchor_node = _find_work_anchor(
        nodes,
        book_dir_rel=book_dir_rel,
        work_key=work_key,
        title=context.title,
    )
    book_node = _find_file_node(nodes, book_rel)
    changed = False

    if anchor_node is None:
        x, y = _next_anchor_position(nodes)
        anchor_id = _generate_unique_node_id(nodes, "node-obra")
        width, height = _card_dimensions_for_title(f"Obra\n{context.title}", is_text=True)
        anchor_node = {
            "id": anchor_id,
            "type": "text",
            "text": f"Obra\n{context.title}",
            "x": round(x, 2),
            "y": round(y, 2),
            "width": width,
            "height": height,
            "color": "4",
            "discipline_work_anchor": True,
            "work_key": work_key,
            "work_title": context.title,
            "author_name": context.book_dir_path.parent.name,
            "book_dir": book_dir_rel,
        }
        nodes.append(anchor_node)
        changed = True
        changed |= _append_edge(
            edges,
            from_node=root_id,
            to_node=anchor_id,
            label=f"obra: {context.book_dir_path.parent.name}/{context.title}",
            color="2",
        )

    anchor_id = str(anchor_node.get("id") or "").strip()
    anchor_x, anchor_y = _node_position(anchor_node)

    if book_node is None:
        width, height = _card_dimensions_for_title(context.book_note_path.stem)
        book_id = _generate_unique_node_id(nodes, "node-livro-nota")
        book_node = {
            "id": book_id,
            "type": "file",
            "file": book_rel,
            "x": round(anchor_x + 650.0, 2),
            "y": round(anchor_y, 2),
            "width": width,
            "height": height,
            "color": "2",
            "work_key": work_key,
            "work_title": context.title,
            "author_name": context.book_dir_path.parent.name,
        }
        nodes.append(book_node)
        changed = True

    book_node_id = str(book_node.get("id") or "").strip()
    if book_node_id:
        changed |= _append_edge(
            edges,
            from_node=anchor_id,
            to_node=book_node_id,
            label="material da obra",
            color="2",
        )

    return anchor_id, book_node_id, changed


def ensure_citations_note_in_discipline_canvas(context: CitationNoteContext, note_path: Path) -> Dict[str, Any]:
    if not context.discipline:
        return {"updated": False, "canvas_path": "", "annotation_node_created": False}

    canvas_name = f"{_sanitize_canvas_filename(f'disciplina-{context.discipline}')}.mapa-mental.canvas"
    canvas_path = context.vault_root / MINDMAPS_DIR / canvas_name
    payload = _load_canvas_payload(canvas_path)
    nodes = payload["nodes"]
    edges = payload["edges"]
    changed = False

    anchor_id, book_node_id, anchor_changed = _ensure_work_anchor_and_book_note(payload, context=context)
    changed |= anchor_changed

    note_rel = _relative_target(context.vault_root, note_path, keep_suffix=True)
    note_node = _find_file_node(nodes, note_rel)
    created_note_node = False

    if note_node is None:
        anchor_node = next(
            (node for node in nodes if isinstance(node, dict) and str(node.get("id") or "").strip() == anchor_id),
            {},
        )
        anchor_x, anchor_y = _node_position(anchor_node)
        note_label = note_path.stem
        width, height = _card_dimensions_for_title(note_label)
        note_id = _generate_unique_node_id(nodes, "node-disciplina-citacoes")
        note_node = {
            "id": note_id,
            "type": "file",
            "file": note_rel,
            "x": round(anchor_x + 650.0, 2),
            "y": round(anchor_y + 110.0, 2),
            "width": width,
            "height": height,
            "color": "6",
            "note_kind": "annotation",
            "citation_note": True,
            "work_key": _normalize_token(f"{context.book_dir_path.parent.name}/{context.book_dir_path.name}"),
            "work_title": context.title,
            "author_name": context.book_dir_path.parent.name,
        }
        nodes.append(note_node)
        changed = True
        created_note_node = True

    note_id = str(note_node.get("id") or "").strip()
    parent_id = anchor_id or book_node_id or "node-disciplina"
    if parent_id and note_id:
        changed |= _append_edge(
            edges,
            from_node=parent_id,
            to_node=note_id,
            label="citações",
            color="6",
        )

    if changed:
        _dump_canvas_payload(canvas_path, payload)

    return {
        "updated": changed,
        "canvas_path": str(canvas_path),
        "annotation_node_created": created_note_node,
        "anchor_node_id": anchor_id,
        "book_node_id": book_node_id,
        "citation_node_id": note_id,
    }


def ensure_citations_note_for_book(
    vault_root: Path,
    *,
    book_note_path: Optional[Path] = None,
    book_dir_path: Optional[Path] = None,
    discipline: str = "",
    discipline_note_path: Optional[Path] = None,
    source_pdf_path: Optional[Path] = None,
    discipline_index: Optional[Dict[str, tuple[str, Path]]] = None,
) -> Dict[str, Any]:
    context = resolve_citation_note_context(
        vault_root,
        book_note_path=book_note_path,
        book_dir_path=book_dir_path,
        discipline=discipline,
        discipline_note_path=discipline_note_path,
        source_pdf_path=source_pdf_path,
        discipline_index=discipline_index,
    )
    if context is None:
        return {
            "created": False,
            "updated": False,
            "linked_in_discipline": False,
            "linked_in_canvas": False,
            "note_path": "",
            "discipline_note_path": "",
            "canvas_path": "",
        }

    note_path = build_citations_note_path(context.vault_root, context.title)
    existed_before = note_path.exists()
    note_path.parent.mkdir(parents=True, exist_ok=True)
    changed, content = _ensure_citations_note_header(note_path, build_citations_note_header(context))
    if changed:
        note_path.write_text(content.rstrip() + "\n", encoding="utf-8")

    discipline_linked = False
    discipline_note_result_path = ""
    if context.discipline:
        try:
            result = append_annotation_note_links(
                context.vault_root,
                context.discipline,
                [str(note_path)],
                note_path=context.discipline_note_path,
            )
            discipline_linked = bool(str(result.get("note_path") or "").strip())
            discipline_note_result_path = str(result.get("note_path") or "")
        except Exception:
            discipline_linked = False

    canvas_result = {"updated": False, "canvas_path": ""}
    if context.discipline:
        canvas_result = ensure_citations_note_in_discipline_canvas(context, note_path)

    return {
        "created": not existed_before,
        "updated": changed,
        "linked_in_discipline": discipline_linked,
        "linked_in_canvas": bool(str(canvas_result.get("canvas_path") or "").strip()),
        "note_path": str(note_path),
        "discipline_note_path": discipline_note_result_path or str(context.discipline_note_path or ""),
        "canvas_path": str(canvas_result.get("canvas_path") or ""),
        "discipline": context.discipline,
        "title": context.title,
        "author": context.author,
    }


def backfill_citation_notes(vault_root: Path) -> Dict[str, Any]:
    root = Path(vault_root).expanduser().resolve(strict=False)
    readings_dir = root / READINGS_DIR
    if not readings_dir.exists():
        return {"processed_books": 0, "created_notes": 0, "updated_notes": 0, "disciplines_linked": 0, "canvas_updates": 0}

    discipline_index = _build_discipline_book_index(root)
    processed_books = 0
    created_notes = 0
    updated_notes = 0
    disciplines_linked = 0
    canvas_updates = 0

    for author_dir in sorted(readings_dir.iterdir(), key=lambda path: path.name.lower()):
        if not author_dir.is_dir():
            continue
        for book_dir in sorted(author_dir.iterdir(), key=lambda path: path.name.lower()):
            if not book_dir.is_dir():
                continue
            primary = find_primary_book_note(book_dir)
            if primary is None or not primary.exists():
                continue

            processed_books += 1
            result = ensure_citations_note_for_book(
                root,
                book_note_path=primary,
                book_dir_path=book_dir,
                discipline_index=discipline_index,
            )
            if bool(result.get("created")):
                created_notes += 1
            if bool(result.get("updated")):
                updated_notes += 1
            if bool(result.get("linked_in_discipline")):
                disciplines_linked += 1
            if bool(result.get("linked_in_canvas")):
                canvas_updates += 1

    return {
        "processed_books": processed_books,
        "created_notes": created_notes,
        "updated_notes": updated_notes,
        "disciplines_linked": disciplines_linked,
        "canvas_updates": canvas_updates,
    }
