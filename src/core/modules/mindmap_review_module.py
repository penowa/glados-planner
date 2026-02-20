"""
Módulo dedicado para geração de mapas mentais.

Observação:
- Este módulo foi criado para separar o fluxo de mapas mentais do pipeline
  de revisão padrão (resumo/flashcards/perguntas).
- Integração com dialog e botão próprios da SessionView ficará para etapa futura.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
import re
from pathlib import Path
from typing import Any, Dict, Optional


@dataclass
class MindmapBaseSources:
    """Arquivos usados para construir o canvas base da obra."""

    book_note: Optional[Path]
    pretext_note: Optional[Path]


@dataclass
class MindmapIncrementalResult:
    """Resultado da atualização incremental local do canvas."""

    payload: Dict[str, Any]
    added_nodes: int
    added_edges: int


class MindmapReviewModule:
    """Serviço isolado para fluxo de mapa mental."""
    COLOR_BOOK = "4"
    COLOR_BOOK_NOTE = "2"
    COLOR_PRETEXT = "3"
    COLOR_CHAPTER = "5"
    COLOR_USER_NOTE = "6"
    COLOR_SUMMARY = "1"

    EDGE_COLOR_BOOK_NOTE = "2"
    EDGE_COLOR_PRETEXT = "3"
    EDGE_COLOR_CHAPTER = "5"
    EDGE_COLOR_USER_NOTE = "6"
    EDGE_COLOR_SUMMARY = "1"

    def find_base_sources(
        self,
        book_dir: Optional[Path],
        preferred_book_note: Optional[Path] = None,
    ) -> MindmapBaseSources:
        if not book_dir or not book_dir.exists() or not book_dir.is_dir():
            return MindmapBaseSources(
                book_note=preferred_book_note if preferred_book_note and preferred_book_note.exists() else None,
                pretext_note=None,
            )

        md_files = sorted([p for p in book_dir.glob("*.md") if p.is_file()])
        if not md_files:
            return MindmapBaseSources(
                book_note=preferred_book_note if preferred_book_note and preferred_book_note.exists() else None,
                pretext_note=None,
            )

        pretext_note: Optional[Path] = None
        for note in md_files:
            name = self._normalize_text(note.stem)
            if any(token in name for token in ("pre-texto", "pre texto", "pretexto", "pré-texto", "pré texto")):
                pretext_note = note
                break

        book_note: Optional[Path] = preferred_book_note if preferred_book_note and preferred_book_note.exists() else None
        if not book_note:
            scored: list[tuple[int, Path]] = []
            for note in md_files:
                name = self._normalize_text(note.stem)
                score = 0
                if note.name.startswith("📖"):
                    score += 10
                if "capitulo" in name or "capítulo" in name:
                    score -= 5
                if any(token in name for token in ("livro", "obra", "ficha", "resumo geral", "introducao", "introdução")):
                    score += 5
                scored.append((score, note))
            scored.sort(key=lambda item: (-item[0], str(item[1]).lower()))
            if scored:
                book_note = scored[0][1]

        return MindmapBaseSources(book_note=book_note, pretext_note=pretext_note)

    def build_base_canvas(
        self,
        vault_root: Path,
        book_title: str,
        book_note: Optional[Path],
        pretext_note: Optional[Path],
    ) -> Dict[str, Any]:
        title_w, title_h = self._card_dimensions_for_title(f"Mapa base da obra {book_title}", is_text=True)
        nodes: list[Dict[str, Any]] = [
            {
                "id": "node-livro",
                "type": "text",
                "text": f"Mapa base da obra\n{book_title}",
                "x": 0,
                "y": 0,
                "width": title_w,
                "height": title_h,
                "color": self.COLOR_BOOK,
            }
        ]
        edges: list[Dict[str, Any]] = []

        if book_note:
            relative = self._to_relative_vault_path(book_note, vault_root)
            card_w, card_h = self._card_dimensions_for_title(Path(relative).stem)
            nodes.append(
                {
                    "id": "node-nota-livro",
                    "type": "file",
                    "file": relative,
                    "x": 430,
                    "y": -110,
                    "width": card_w,
                    "height": card_h,
                    "color": self.COLOR_BOOK_NOTE,
                }
            )
            edges.append(
                {
                    "id": "edge-livro-nota",
                    "fromNode": "node-livro",
                    "toNode": "node-nota-livro",
                    "fromSide": "right",
                    "toSide": "left",
                    "label": "informações básicas",
                    "color": self.EDGE_COLOR_BOOK_NOTE,
                }
            )

        if pretext_note:
            relative = self._to_relative_vault_path(pretext_note, vault_root)
            card_w, card_h = self._card_dimensions_for_title(Path(relative).stem)
            nodes.append(
                {
                    "id": "node-pre-texto",
                    "type": "file",
                    "file": relative,
                    "x": 430,
                    "y": 90,
                    "width": card_w,
                    "height": card_h,
                    "color": self.COLOR_PRETEXT,
                }
            )
            edges.append(
                {
                    "id": "edge-livro-pretexto",
                    "fromNode": "node-livro",
                    "toNode": "node-pre-texto",
                    "fromSide": "right",
                    "toSide": "left",
                    "label": "pré-texto",
                    "color": self.EDGE_COLOR_PRETEXT,
                }
            )

        return {"nodes": nodes, "edges": edges}

    def dump_canvas_json(self, payload: Dict[str, Any]) -> str:
        return json.dumps(payload, ensure_ascii=False, indent=2)

    def load_canvas_payload(self, canvas_path: Path) -> Dict[str, Any]:
        try:
            raw = canvas_path.read_text(encoding="utf-8", errors="ignore")
            parsed = json.loads(raw)
        except Exception:
            return {"nodes": [], "edges": []}
        if not isinstance(parsed, dict):
            return {"nodes": [], "edges": []}
        nodes = parsed.get("nodes")
        edges = parsed.get("edges")
        if not isinstance(nodes, list) or not isinstance(edges, list):
            return {"nodes": [], "edges": []}
        return {"nodes": nodes, "edges": edges}

    def merge_incremental_canvas(
        self,
        payload: Dict[str, Any],
        vault_root: Path,
        book_title: str,
        chapter_path: Optional[Path],
        user_notes: list[dict[str, str]],
        summary_path: Optional[Path],
    ) -> MindmapIncrementalResult:
        nodes = payload.get("nodes")
        edges = payload.get("edges")
        if not isinstance(nodes, list):
            nodes = []
        if not isinstance(edges, list):
            edges = []

        existing_ids = {str(item.get("id")) for item in nodes if isinstance(item, dict) and item.get("id")}
        existing_edge_ids = {str(item.get("id")) for item in edges if isinstance(item, dict) and item.get("id")}

        anchor_id = self._ensure_anchor_node(nodes, existing_ids, book_title)
        anchor_node = self._find_node_by_id(nodes, anchor_id) or {}
        anchor_x = int(anchor_node.get("x", 0) or 0)
        anchor_y = int(anchor_node.get("y", 0) or 0)

        file_node_by_path: dict[str, str] = {}
        for node in nodes:
            if not isinstance(node, dict):
                continue
            if str(node.get("type") or "") != "file":
                continue
            file_path = str(node.get("file") or "").replace("\\", "/").strip()
            node_id = str(node.get("id") or "").strip()
            if file_path and node_id:
                file_node_by_path[file_path] = node_id

        added_nodes = 0
        added_edges = 0

        chapter_node_id: Optional[str] = None
        if chapter_path and chapter_path.exists():
            chapter_file = self._to_relative_vault_path(chapter_path, vault_root)
            chapter_node_id = file_node_by_path.get(chapter_file)
            if not chapter_node_id:
                chapter_node_id = self._unique_id("node-capitulo", existing_ids)
                card_w, card_h = self._card_dimensions_for_title(Path(chapter_file).stem)
                nodes.append(
                    {
                        "id": chapter_node_id,
                        "type": "file",
                        "file": chapter_file,
                        "x": anchor_x + 460,
                        "y": anchor_y + 180,
                        "width": card_w,
                        "height": card_h,
                        "color": self.COLOR_CHAPTER,
                    }
                )
                file_node_by_path[chapter_file] = chapter_node_id
                added_nodes += 1
            if self._ensure_edge(
                edges,
                existing_edge_ids,
                from_node=anchor_id,
                to_node=chapter_node_id,
                label="capítulo atual",
                color=self.EDGE_COLOR_CHAPTER,
            ):
                added_edges += 1

        notes_base_y = anchor_y - 120
        note_step_y = 110
        notes_added_so_far = 0
        source_id_for_children = chapter_node_id or anchor_id

        for note in user_notes:
            note_path_str = str(note.get("path") or "").strip()
            if not note_path_str:
                continue
            note_abs = Path(note_path_str)
            if not note_abs.exists():
                candidate = vault_root / note_path_str
                if candidate.exists():
                    note_abs = candidate
            if not note_abs.exists() or not note_abs.is_file():
                continue

            note_file = self._to_relative_vault_path(note_abs, vault_root)
            note_node_id = file_node_by_path.get(note_file)
            if not note_node_id:
                note_node_id = self._unique_id("node-nota-usuario", existing_ids)
                card_w, card_h = self._card_dimensions_for_title(Path(note_file).stem)
                nodes.append(
                    {
                        "id": note_node_id,
                        "type": "file",
                        "file": note_file,
                        "x": anchor_x + 920,
                        "y": notes_base_y + (notes_added_so_far * note_step_y),
                        "width": card_w,
                        "height": card_h,
                        "color": self.COLOR_USER_NOTE,
                    }
                )
                file_node_by_path[note_file] = note_node_id
                notes_added_so_far += 1
                added_nodes += 1

            if self._ensure_edge(
                edges,
                existing_edge_ids,
                from_node=source_id_for_children,
                to_node=note_node_id,
                label="nota do usuário",
                color=self.EDGE_COLOR_USER_NOTE,
            ):
                added_edges += 1

        if summary_path and summary_path.exists():
            summary_file = self._to_relative_vault_path(summary_path, vault_root)
            summary_node_id = file_node_by_path.get(summary_file)
            if not summary_node_id:
                summary_node_id = self._unique_id("node-resumo-llm", existing_ids)
                card_w, card_h = self._card_dimensions_for_title(Path(summary_file).stem)
                nodes.append(
                    {
                        "id": summary_node_id,
                        "type": "file",
                        "file": summary_file,
                        "x": anchor_x + 920,
                        "y": anchor_y + 260,
                        "width": card_w,
                        "height": card_h,
                        "color": self.COLOR_SUMMARY,
                    }
                )
                file_node_by_path[summary_file] = summary_node_id
                added_nodes += 1
            if self._ensure_edge(
                edges,
                existing_edge_ids,
                from_node=source_id_for_children,
                to_node=summary_node_id,
                label="resumo",
                color=self.EDGE_COLOR_SUMMARY,
            ):
                added_edges += 1

        return MindmapIncrementalResult(
            payload={"nodes": nodes, "edges": edges},
            added_nodes=added_nodes,
            added_edges=added_edges,
        )

    def _to_relative_vault_path(self, file_path: Path, vault_root: Path) -> str:
        try:
            relative = file_path.relative_to(vault_root)
        except Exception:
            relative = file_path
        return str(relative).replace("\\", "/")

    def _normalize_text(self, value: str) -> str:
        lowered = value.strip().lower()
        lowered = re.sub(r"\s+", " ", lowered)
        return lowered

    def _find_node_by_id(self, nodes: list[Dict[str, Any]], node_id: str) -> Optional[Dict[str, Any]]:
        for node in nodes:
            if isinstance(node, dict) and str(node.get("id") or "") == node_id:
                return node
        return None

    def _ensure_anchor_node(
        self,
        nodes: list[Dict[str, Any]],
        existing_ids: set[str],
        book_title: str,
    ) -> str:
        for node in nodes:
            if not isinstance(node, dict):
                continue
            node_id = str(node.get("id") or "").strip()
            if not node_id:
                continue
            node_type = str(node.get("type") or "").strip().lower()
            if node_type == "text":
                text = str(node.get("text") or "")
                text_norm = self._normalize_text(text)
                if "mapa base da obra" in text_norm or self._normalize_text(book_title) in text_norm:
                    return node_id
            if node_id == "node-livro":
                return node_id

        node_id = self._unique_id("node-livro", existing_ids)
        card_w, card_h = self._card_dimensions_for_title(f"Mapa base da obra {book_title}", is_text=True)
        nodes.append(
            {
                "id": node_id,
                "type": "text",
                "text": f"Mapa base da obra\n{book_title}",
                "x": 0,
                "y": 0,
                "width": card_w,
                "height": card_h,
                "color": self.COLOR_BOOK,
            }
        )
        return node_id

    def _unique_id(self, prefix: str, existing_ids: set[str]) -> str:
        if prefix not in existing_ids:
            existing_ids.add(prefix)
            return prefix
        index = 2
        while True:
            candidate = f"{prefix}-{index}"
            if candidate not in existing_ids:
                existing_ids.add(candidate)
                return candidate
            index += 1

    def _ensure_edge(
        self,
        edges: list[Dict[str, Any]],
        existing_edge_ids: set[str],
        from_node: str,
        to_node: str,
        label: str,
        color: Optional[str] = None,
    ) -> bool:
        normalized_label = (label or "").strip().lower()
        for edge in edges:
            if not isinstance(edge, dict):
                continue
            if str(edge.get("fromNode") or "") != from_node:
                continue
            if str(edge.get("toNode") or "") != to_node:
                continue
            edge_label = str(edge.get("label") or "").strip().lower()
            if edge_label == normalized_label:
                return False

        edge_id = self._unique_id("edge", existing_edge_ids)
        edge_payload: Dict[str, Any] = {
            "id": edge_id,
            "fromNode": from_node,
            "toNode": to_node,
            "fromSide": "right",
            "toSide": "left",
        }
        if label:
            edge_payload["label"] = label
        if color:
            edge_payload["color"] = color
        edges.append(edge_payload)
        return True

    def _card_dimensions_for_title(self, title: str, is_text: bool = False) -> tuple[int, int]:
        clean = re.sub(r"\s+", " ", (title or "").strip())
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
