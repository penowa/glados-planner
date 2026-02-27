from __future__ import annotations

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from core.vault.bootstrap import bootstrap_vault


def test_bootstrap_seeds_meta_docs_for_new_vault(tmp_path):
    vault_path = tmp_path / "planner-vault"

    bootstrap_vault(str(vault_path))

    meta_dir = vault_path / "00-META"
    assert meta_dir.exists()
    assert (meta_dir / "00-LLM-HELP-POLICY.md").exists()
    assert (meta_dir / "01-UI-MAPA-GERAL.md").exists()
    assert (meta_dir / "11-DIALOG-ONBOARDING.md").exists()


def test_bootstrap_seeds_meta_docs_when_only_readme_exists(tmp_path):
    vault_path = tmp_path / "planner-vault"
    meta_dir = vault_path / "00-META"
    meta_dir.mkdir(parents=True, exist_ok=True)
    (meta_dir / "README.md").write_text("# 00-META\n", encoding="utf-8")

    bootstrap_vault(str(vault_path))

    assert (meta_dir / "00-LLM-HELP-POLICY.md").exists()
    assert (meta_dir / "09-VIEW-WEEKLY-REVIEW.md").exists()


def test_bootstrap_preserves_existing_meta_content(tmp_path):
    vault_path = tmp_path / "planner-vault"
    meta_dir = vault_path / "00-META"
    meta_dir.mkdir(parents=True, exist_ok=True)
    custom_file = meta_dir / "custom-note.md"
    custom_file.write_text("manual content", encoding="utf-8")

    bootstrap_vault(str(vault_path))

    assert custom_file.read_text(encoding="utf-8") == "manual content"
    assert not (meta_dir / "00-LLM-HELP-POLICY.md").exists()

