"""Agrupamento de eventos da agenda em compromissos consolidados."""

from __future__ import annotations

import re
from typing import Any, Dict, Iterable, Optional, Tuple

CommitmentGroupKey = Tuple[str, str, str]

SKIP_EVENT_TYPES = {"sono", "refeicao"}


def _strip_title_prefix(title: str, prefixes: Iterable[str]) -> str:
    cleaned = re.sub(r"\s+", " ", str(title or "").strip())
    lowered = cleaned.lower()
    for prefix in prefixes:
        normalized_prefix = str(prefix).strip().lower()
        if lowered.startswith(normalized_prefix):
            cleaned = cleaned[len(normalized_prefix) :].strip()
            if cleaned.startswith(":"):
                cleaned = cleaned[1:].strip()
            break
    return cleaned or "Sem título"


def normalize_event_type(raw_type: Any) -> str:
    event_type = str(raw_type or "casual").strip().lower()
    if event_type == "producao":
        return "dissertacao"
    return event_type


def event_group_key_from_mapping(event: Dict[str, Any]) -> Optional[CommitmentGroupKey]:
    event_type = normalize_event_type(event.get("type") or event.get("event_type"))
    if event_type in SKIP_EVENT_TYPES:
        return None
    if event.get("_fixed_virtual"):
        return None
    if bool(event.get("completed", False)):
        return None

    metadata = event.get("metadata") or {}
    book_id = str(event.get("book_id") or metadata.get("book_id") or "").strip()
    if book_id:
        return (event_type, "book", book_id)

    project_id = str(
        metadata.get("writing_project")
        or metadata.get("project_id")
        or metadata.get("dissertation_id")
        or ""
    ).strip()
    if project_id:
        return (event_type, "project", project_id)

    title = _strip_title_prefix(
        event.get("title", ""),
        ("Leitura:", "Revisão:", "Dissertação:", "Produção:"),
    )
    normalized_title = re.sub(r"\s+", " ", title).strip().lower()
    if not normalized_title:
        normalized_title = str(event.get("id") or event.get("title") or "sem-titulo").lower()
    return (event_type, "title", normalized_title)


def event_group_key_from_object(event: Any) -> Optional[CommitmentGroupKey]:
    if event is None:
        return None

    metadata = getattr(event, "metadata", None) or {}
    event_type = normalize_event_type(getattr(getattr(event, "type", None), "value", None) or getattr(event, "type", "casual"))
    if event_type in SKIP_EVENT_TYPES:
        return None
    if bool(getattr(event, "completed", False)):
        return None

    book_id = str(getattr(event, "book_id", None) or metadata.get("book_id") or "").strip()
    if book_id:
        return (event_type, "book", book_id)

    project_id = str(
        metadata.get("writing_project")
        or metadata.get("project_id")
        or metadata.get("dissertation_id")
        or ""
    ).strip()
    if project_id:
        return (event_type, "project", project_id)

    title = _strip_title_prefix(
        getattr(event, "title", ""),
        ("Leitura:", "Revisão:", "Dissertação:", "Produção:"),
    )
    normalized_title = re.sub(r"\s+", " ", title).strip().lower()
    if not normalized_title:
        normalized_title = str(getattr(event, "id", None) or getattr(event, "title", "") or "sem-titulo").lower()
    return (event_type, "title", normalized_title)


def matches_group_key(event: Any, group_key: CommitmentGroupKey) -> bool:
    return event_group_key_from_object(event) == group_key
