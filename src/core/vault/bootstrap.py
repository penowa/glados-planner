"""
Bootstrap do vault Obsidian usado pelo GLaDOS Planner.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable


DEFAULT_VAULT_STRUCTURE = (
    "00-META",
    "01-LEITURAS",
    "02-ANOTAÇÕES",
    "03-REVISÃO",
    "04-MAPAS MENTAIS",
    "06-RECURSOS",
)

README_DESCRIPTIONS = {
    "00-META": "Metadados, índices e organização do sistema.",
    "01-LEITURAS": "Obras por autor e progresso de leitura.",
    "02-ANOTAÇÕES": "Anotações do usuário durante estudo/leitura.",
    "03-REVISÃO": "Materiais de revisão gerados com LLM.",
    "04-MAPAS MENTAIS": "Mapas mentais e estruturas visuais (Canva).",
    "06-RECURSOS": "Recursos de apoio, caches e registros.",
}


def bootstrap_vault(vault_path: str, vault_structure: Iterable[str] | None = None) -> Path:
    """
    Garante existência do vault e estrutura mínima esperada pelo sistema.

    Returns:
        Path absoluto para o vault.
    """
    resolved_vault = Path(str(vault_path or "").strip()).expanduser().resolve()
    if not str(resolved_vault).strip():
        raise ValueError("Caminho do vault inválido.")

    structure = [str(item).strip() for item in (vault_structure or DEFAULT_VAULT_STRUCTURE) if str(item).strip()]
    if not structure:
        structure = list(DEFAULT_VAULT_STRUCTURE)

    resolved_vault.mkdir(parents=True, exist_ok=True)
    for folder in structure:
        folder_path = resolved_vault / folder
        folder_path.mkdir(parents=True, exist_ok=True)
        _ensure_readme(folder_path, folder)

    _ensure_obsidian_config(resolved_vault)
    _ensure_index_file(resolved_vault)
    _ensure_expected_json_files(resolved_vault)
    return resolved_vault


def _ensure_readme(folder_path: Path, folder_name: str) -> None:
    readme_path = folder_path / "README.md"
    if readme_path.exists():
        return
    description = README_DESCRIPTIONS.get(folder_name, "Diretório de trabalho do vault.")
    readme_path.write_text(
        f"# {folder_name}\n\n{description}\n\n*Gerenciado por GLaDOS Planner*\n",
        encoding="utf-8",
    )


def _ensure_obsidian_config(vault_path: Path) -> None:
    obsidian_dir = vault_path / ".obsidian"
    obsidian_dir.mkdir(parents=True, exist_ok=True)

    core_plugins = {
        "corePlugins": {
            "file-explorer": True,
            "global-search": True,
            "graph": True,
            "backlink": True,
            "templates": True,
        }
    }
    templates = {
        "folder": "06-RECURSOS/templates",
        "dateFormat": "YYYY-MM-DD",
    }
    _ensure_json(obsidian_dir / "core-plugins.json", core_plugins)
    _ensure_json(obsidian_dir / "templates.json", templates)


def _ensure_index_file(vault_path: Path) -> None:
    index_path = vault_path / "Índice Principal.md"
    if index_path.exists():
        return

    content = (
        "# 🧠 Cérebro Digital - Filosofia\n\n"
        "Bem-vindo ao seu vault gerenciado pelo **GLaDOS Planner**.\n\n"
        "## Estrutura\n"
        "- **00-META**: Metadados e organização\n"
        "- **01-LEITURAS**: Obras por autor e sessão de leitura\n"
        "- **02-ANOTAÇÕES**: Notas do usuário\n"
        "- **03-REVISÃO**: Resumos, flashcards e perguntas de revisão\n"
        "- **04-MAPAS MENTAIS**: Materiais visuais\n"
        "- **06-RECURSOS**: Arquivos de suporte e registros\n"
    )
    index_path.write_text(content, encoding="utf-8")


def _ensure_expected_json_files(vault_path: Path) -> None:
    resource_dir = vault_path / "06-RECURSOS"
    resource_dir.mkdir(parents=True, exist_ok=True)

    # Estruturas consumidas pelos módulos de agenda, revisão e pomodoro.
    _ensure_json(resource_dir / "agenda.json", {})
    _ensure_json(resource_dir / "preferences.json", {})
    _ensure_json(resource_dir / "pomodoro_stats.json", {})
    _ensure_json(resource_dir / "flashcards.json", {})
    _ensure_json(resource_dir / "quizzes.json", {})
    _ensure_json(resource_dir / "review_stats.json", {})
    _ensure_json(resource_dir / "review_questions.json", {})
    _ensure_json(resource_dir / "review_chapter_difficulty.json", {})
    _ensure_json(resource_dir / "review_runtime.json", {"question_interval_minutes": 10})


def _ensure_json(path: Path, default_payload: dict) -> None:
    if path.exists():
        return
    path.write_text(json.dumps(default_payload, indent=2, ensure_ascii=False), encoding="utf-8")
