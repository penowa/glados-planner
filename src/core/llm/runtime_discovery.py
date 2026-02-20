"""
Descoberta de runtime para LLM local.
- Modelos GGUF disponíveis em diretórios configurados
- GPUs NVIDIA disponíveis via nvidia-smi
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional
import subprocess


@dataclass
class GgufModelInfo:
    name: str
    path: str
    size_mb: int
    modified_ts: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "path": self.path,
            "size_mb": self.size_mb,
            "modified_ts": self.modified_ts,
        }


def resolve_project_root() -> Path:
    # src/core/llm/runtime_discovery.py -> projeto na raiz
    return Path(__file__).resolve().parents[3]


def resolve_models_dir(models_dir: str) -> Path:
    root = resolve_project_root()
    path = Path(models_dir).expanduser()
    if not path.is_absolute():
        path = root / path
    return path


def discover_gguf_models(models_dir: str, recursive: bool = True) -> List[Dict[str, Any]]:
    base = resolve_models_dir(models_dir)
    if not base.exists():
        return []

    globber = base.rglob("*.gguf") if recursive else base.glob("*.gguf")
    models: List[GgufModelInfo] = []
    for file in globber:
        try:
            stat = file.stat()
            models.append(
                GgufModelInfo(
                    name=file.name,
                    path=str(file),
                    size_mb=int(stat.st_size / (1024 * 1024)),
                    modified_ts=float(stat.st_mtime),
                )
            )
        except OSError:
            continue

    models.sort(key=lambda m: (m.name.lower(), -m.modified_ts))
    return [m.to_dict() for m in models]


def detect_nvidia_gpus() -> List[Dict[str, Any]]:
    """
    Detecta GPUs NVIDIA instaladas.
    Retorna lista vazia se nvidia-smi não existir ou falhar.
    """
    cmd = [
        "nvidia-smi",
        "--query-gpu=index,name,memory.total,driver_version",
        "--format=csv,noheader,nounits",
    ]
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=2.0,
            check=False,
        )
    except Exception:
        return []

    if proc.returncode != 0 or not proc.stdout.strip():
        return []

    gpus: List[Dict[str, Any]] = []
    for line in proc.stdout.splitlines():
        parts = [p.strip() for p in line.split(",")]
        if len(parts) < 4:
            continue
        idx_text, name, mem_text, driver = parts[0], parts[1], parts[2], parts[3]
        try:
            idx = int(idx_text)
        except ValueError:
            continue
        try:
            mem_mb = int(mem_text)
        except ValueError:
            mem_mb = 0
        gpus.append(
            {
                "index": idx,
                "name": name,
                "memory_total_mb": mem_mb,
                "driver_version": driver,
            }
        )

    return gpus


def pick_model_path(
    explicit_model_path: str,
    models_dir: str,
    model_name: str = "",
) -> tuple[Optional[str], List[Dict[str, Any]]]:
    """
    Resolve caminho de modelo:
    1) model_path explícito se arquivo existir
    2) match por model_name em models_dir
    3) primeiro .gguf encontrado
    """
    root = resolve_project_root()
    explicit = Path(explicit_model_path).expanduser() if explicit_model_path else Path()
    if explicit_model_path:
        if not explicit.is_absolute():
            explicit = root / explicit
        if explicit.exists() and explicit.is_file():
            return str(explicit), discover_gguf_models(models_dir)

    models = discover_gguf_models(models_dir)
    if not models:
        return None, []

    wanted = (model_name or "").strip().lower()
    if wanted:
        for item in models:
            if wanted in str(item.get("name", "")).lower():
                return str(item["path"]), models

    return str(models[0]["path"]), models
