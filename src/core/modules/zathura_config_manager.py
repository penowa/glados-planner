"""
Gerenciador central de configuracao do Zathura.
"""
from __future__ import annotations

import re
import shlex
import shutil
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.config.settings import ZathuraConfig


class ZathuraConfigManager:
    """Lida com leitura, geracao e sincronizacao do zathurarc."""

    def __init__(self, config: Optional[ZathuraConfig] = None):
        if config is None:
            from core.config.settings import settings as runtime_settings
            config = runtime_settings.zathura
        self.config = config

    def refresh(self, config: Optional[ZathuraConfig] = None) -> None:
        if config is None:
            from core.config.settings import settings as runtime_settings
            config = runtime_settings.zathura
        self.config = config

    def resolve_path(self, raw_path: str) -> Path:
        return Path(str(raw_path or "").strip()).expanduser()

    @property
    def config_dir(self) -> Path:
        raw = str(self.config.config_dir or "").strip()
        if raw:
            configured = self.resolve_path(raw)
            return configured
        return self.resolve_path("~/.config/zathura")

    @property
    def config_file(self) -> Path:
        raw = str(self.config.config_file or "").strip()
        if raw:
            configured = self.resolve_path(raw)
            return configured
        return self.config_dir / "zathurarc"

    @property
    def data_dir(self) -> Path:
        raw = str(self.config.data_dir or "").strip()
        if raw:
            return self.resolve_path(raw)
        return self.resolve_path("~/.local/share/zathura")

    @property
    def cache_dir(self) -> Path:
        raw = str(self.config.cache_dir or "").strip()
        if raw:
            return self.resolve_path(raw)
        return self.resolve_path("~/.cache/zathura")

    @property
    def generated_theme_file(self) -> Path:
        raw = str(self.config.generated_theme_file or "").strip()
        if raw:
            return self.resolve_path(raw)
        return self.config_dir / "glados-theme.zathurarc"

    @property
    def custom_theme_include_file(self) -> Path:
        raw = str(self.config.custom_theme_include_file or "").strip()
        if raw:
            return self.resolve_path(raw)
        return Path()

    @property
    def capture_script_file(self) -> Path:
        raw = str(getattr(self.config, "capture_script_file", "") or "").strip()
        if raw:
            return self.resolve_path(raw)
        return self.data_dir / "glados-zathura-capture.sh"

    @property
    def capture_events_file(self) -> Path:
        raw = str(getattr(self.config, "capture_events_file", "") or "").strip()
        if raw:
            return self.resolve_path(raw)
        return self.data_dir / "glados-captures.jsonl"

    @property
    def capture_images_dir(self) -> Path:
        raw = str(getattr(self.config, "capture_images_dir", "") or "").strip()
        if raw:
            return self.resolve_path(raw)
        return self.data_dir / "glados-captures"

    def status(self) -> Dict[str, Any]:
        binary = str(self.config.binary or "zathura").strip() or "zathura"
        generator = str(self.config.pywal_generator or "genzathurarc").strip() or "genzathurarc"
        colors_file = self.resolve_path(self.config.pywal_colors_file)
        binary_resolved = shutil.which(binary)
        generator_resolved = shutil.which(generator)
        capture_script = self.capture_script_file
        capture_queue = self.capture_events_file
        return {
            "enabled": bool(self.config.enabled),
            "binary": binary,
            "binary_found": bool(binary_resolved),
            "binary_resolved": str(binary_resolved or ""),
            "config_dir": str(self.config_dir),
            "config_file": str(self.config_file),
            "config_exists": self.config_file.exists(),
            "data_dir": str(self.data_dir),
            "cache_dir": str(self.cache_dir),
            "generator": generator,
            "generator_found": bool(generator_resolved),
            "generator_resolved": str(generator_resolved or ""),
            "pywal_colors_file": str(colors_file),
            "pywal_colors_found": colors_file.exists(),
            "theme_mode": str(self.config.theme_mode or "plain"),
            "capture_enabled": bool(getattr(self.config, "capture_enabled", True)),
            "capture_keybinding": str(getattr(self.config, "capture_keybinding", "<C-g>") or "<C-g>"),
            "capture_script_file": str(capture_script),
            "capture_script_exists": capture_script.exists(),
            "capture_events_file": str(capture_queue),
            "capture_events_exists": capture_queue.exists(),
        }

    def load_existing_config(self) -> str:
        if not self.config_file.exists():
            return ""
        try:
            return self.config_file.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            return ""

    def build_open_command(
        self,
        file_path: str | Path,
        *,
        page: int = 1,
        mode: str = "",
        fork: Optional[bool] = None,
    ) -> List[str]:
        binary = str(self.config.binary or "zathura").strip() or "zathura"
        command: List[str] = [binary]

        if fork if fork is not None else bool(self.config.session_use_fork):
            command.append("--fork")

        config_dir = self.config_dir
        if str(config_dir):
            command.extend(["--config-dir", str(config_dir)])

        if str(self.data_dir):
            command.extend(["--data-dir", str(self.data_dir)])

        if str(self.cache_dir):
            command.extend(["--cache-dir", str(self.cache_dir)])

        plugin_path = str(self.config.plugin_path or "").strip()
        if plugin_path:
            command.extend(["--plugins-dir", plugin_path])

        page_number = max(1, int(page or 1))
        command.extend(["--page", str(page_number)])

        target_mode = str(mode or self.config.session_open_mode or "").strip().lower()
        if target_mode and target_mode != "normal":
            command.extend(["--mode", target_mode])

        command.append(str(Path(file_path).expanduser()))
        return command

    def apply(self) -> Dict[str, Any]:
        result = {
            "success": False,
            "config_file": str(self.config_file),
            "theme_file": str(self.generated_theme_file),
            "capture_script_file": str(self.capture_script_file),
            "warnings": [],
            "errors": [],
        }

        if not self.config.enabled:
            result["warnings"].append("Zathura desabilitado nas configuracoes.")
            return result

        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.config_file.parent.mkdir(parents=True, exist_ok=True)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        if bool(getattr(self.config, "capture_enabled", True)):
            script_ok, script_message = self._ensure_capture_helper_script()
            if script_ok:
                result["warnings"].append(script_message)
            else:
                result["errors"].append(script_message)

        theme_mode = str(self.config.theme_mode or "plain").strip().lower()
        if theme_mode == "pywal_internal":
            ok, message = self._write_internal_pywal_theme()
            if not ok:
                result["errors"].append(message)
            else:
                result["warnings"].append(message)
        elif theme_mode == "pywal_generator":
            ok, message = self._write_generator_pywal_theme()
            if not ok:
                result["errors"].append(message)
            else:
                result["warnings"].append(message)

        rendered = self.render_config()
        try:
            self.config_file.write_text(rendered, encoding="utf-8")
        except Exception as exc:
            result["errors"].append(f"Falha ao salvar zathurarc: {exc}")
            return result

        result["success"] = len(result["errors"]) == 0
        return result

    def render_config(self) -> str:
        lines: List[str] = [
            "# Arquivo gerado pelo GLaDOS Planner",
            "# Edite via modulo/configuracoes do projeto para evitar drift.",
            "",
        ]

        include_paths = self._resolved_include_paths()
        for include_path in include_paths:
            lines.append(f"include {self._quote_path(include_path)}")

        if include_paths:
            lines.append("")

        base_options = {
            "selection-clipboard": self.config.selection_clipboard,
            "statusbar-basename": self.config.statusbar_basename,
            "window-title-home-tilde": self.config.window_title_home_tilde,
            "recolor": self.config.recolor,
        }
        base_options.update(dict(self.config.extra_options or {}))

        for option_name, option_value in base_options.items():
            rendered = self._render_set_option(option_name, option_value)
            if rendered:
                lines.append(rendered)

        effective_keymaps = self._effective_keymaps()
        if effective_keymaps:
            lines.append("")
            lines.append("# Keymaps customizados")
            for mapping in effective_keymaps:
                clean = str(mapping or "").strip()
                if clean:
                    lines.append(clean)

        extra = str(self.config.extra_config or "").strip()
        if extra:
            lines.append("")
            lines.append("# Configuracao extra")
            lines.append(extra)

        return "\n".join(lines).rstrip() + "\n"

    def _effective_keymaps(self) -> List[str]:
        keymaps: List[str] = []
        seen: set[str] = set()
        for raw in self.config.keymaps or []:
            line = str(raw or "").strip()
            if not line or line in seen:
                continue
            keymaps.append(line)
            seen.add(line)

        if bool(getattr(self.config, "capture_enabled", True)):
            capture_binding = str(getattr(self.config, "capture_keybinding", "<C-g>") or "<C-g>").strip() or "<C-g>"
            keymaps = [line for line in keymaps if not self._keymap_uses_binding(line, capture_binding)]
            capture_line = self._default_capture_keymap_line(capture_binding)
            line = capture_line.strip()
            if line:
                keymaps.insert(0, line)

        deduped: List[str] = []
        dedup_seen: set[str] = set()
        for line in keymaps:
            if line in dedup_seen:
                continue
            dedup_seen.add(line)
            deduped.append(line)
        return deduped

    def _default_capture_keymap_line(self, binding: str) -> str:
        safe_binding = str(binding or "<C-g>").strip() or "<C-g>"
        raw_script = str(getattr(self.config, "capture_script_file", "") or "").strip()
        script_path = raw_script or "~/.local/share/zathura/glados-zathura-capture.sh"
        script_path = script_path.replace(" ", "\\ ")
        return f"map {safe_binding} exec {script_path} $PAGE $FILE"

    def _keymap_uses_binding(self, line: str, binding: str) -> bool:
        normalized_line = str(line or "").strip()
        normalized_binding = str(binding or "").strip()
        if not normalized_line or not normalized_binding:
            return False
        pattern = re.compile(r"^map(?:\s+\[[^\]]+\])?\s+(\S+)\s+")
        match = pattern.match(normalized_line)
        if not match:
            return False
        return match.group(1).strip().lower() == normalized_binding.lower()

    def _ensure_capture_helper_script(self) -> tuple[bool, str]:
        script_path = self.capture_script_file
        queue_path = self.capture_events_file
        images_dir = self.capture_images_dir
        ocr_lang = str(getattr(self.config, "capture_ocr_language", "por+eng") or "por+eng").strip() or "por+eng"
        notify_enabled = bool(getattr(self.config, "capture_notify", True))

        try:
            script_path.parent.mkdir(parents=True, exist_ok=True)
            queue_path.parent.mkdir(parents=True, exist_ok=True)
            images_dir.mkdir(parents=True, exist_ok=True)
            script_path.write_text(
                self._render_capture_helper_script(
                    queue_path=queue_path,
                    images_dir=images_dir,
                    ocr_lang=ocr_lang,
                    notify_enabled=notify_enabled,
                ),
                encoding="utf-8",
            )
            script_path.chmod(0o755)
            return True, f"Helper de captura preparado em {script_path}."
        except Exception as exc:
            return False, f"Falha ao preparar helper de captura do Zathura: {exc}"

    def _render_capture_helper_script(
        self,
        *,
        queue_path: Path,
        images_dir: Path,
        ocr_lang: str,
        notify_enabled: bool,
    ) -> str:
        queue_q = shlex.quote(str(queue_path.expanduser()))
        images_q = shlex.quote(str(images_dir.expanduser()))
        ocr_lang_q = shlex.quote(str(ocr_lang or "por+eng"))
        notify_flag = "1" if notify_enabled else "0"
        return f"""#!/usr/bin/env bash
set -euo pipefail

PAGE_RAW="${{1:-0}}"
shift || true
PDF_PATH="${{*:-}}"

if [[ -z "$PDF_PATH" ]]; then
  exit 0
fi

QUEUE_FILE={queue_q}
IMAGES_DIR={images_q}
OCR_LANG={ocr_lang_q}
NOTIFY_ENABLED={notify_flag}
BOOKMARK_DB="$(dirname "$QUEUE_FILE")/bookmarks.sqlite"

mkdir -p "$(dirname "$QUEUE_FILE")" "$IMAGES_DIR"

page_num="$PAGE_RAW"
if ! [[ "$page_num" =~ ^[0-9]+$ ]]; then
  page_num="0"
fi
if [[ "$page_num" -le 0 ]]; then
  page_num="1"
fi

timestamp="$(date -Iseconds)"
event_id="$(python3 - "$PDF_PATH|$page_num|$timestamp" <<'PY'
import hashlib
import sys
print(hashlib.sha1(sys.argv[1].encode("utf-8", errors="ignore")).hexdigest())
PY
)"

image_path="$IMAGES_DIR/${{event_id}}.png"
region=""

notify() {{
  if [[ "$NOTIFY_ENABLED" != "1" ]]; then
    return 0
  fi
  if command -v notify-send >/dev/null 2>&1; then
    notify-send "$@" >/dev/null 2>&1 || true
  fi
}}

notify "GLaDOS capture" "Selecione uma area do PDF para OCR."

if [[ -n "${{WAYLAND_DISPLAY:-}}" ]] && command -v slurp >/dev/null 2>&1 && command -v grim >/dev/null 2>&1; then
  region="$(slurp 2>/dev/null || true)"
  if [[ -n "$region" ]]; then
    grim -g "$region" "$image_path" >/dev/null 2>&1 || true
  fi
fi

if [[ ! -s "$image_path" ]] && [[ -n "${{DISPLAY:-}}" ]] && command -v slop >/dev/null 2>&1 && command -v maim >/dev/null 2>&1; then
  region="$(slop -f "%wx%h+%x+%y" 2>/dev/null || true)"
  if [[ -n "$region" ]]; then
    maim -g "$region" "$image_path" >/dev/null 2>&1 || true
  fi
fi

excerpt=""
excerpt_source=""
olmocr_error=""

run_olmocr_on_image() {{
  local image_file="$1"
  local workdir
  workdir="$(mktemp -d "${{TMPDIR:-/tmp}}/glados-olmocr-XXXXXX")"
  local output=""

  if command -v olmocr >/dev/null 2>&1; then
    if output="$(olmocr "$workdir" --markdown --images "$image_file" --workers 1 --pages_per_group 1 2>/tmp/glados-olmocr.err || true)"; then
      :
    fi
  else
    echo "__OLMOCR_MISSING__"
    rm -rf "$workdir"
    return 0
  fi

  local md_file=""
  if [[ -d "$workdir/markdown" ]]; then
    md_file="$(ls -1t "$workdir"/markdown/*.md 2>/dev/null | head -n 1 || true)"
  fi
  if [[ -n "$md_file" && -f "$md_file" ]]; then
    cat "$md_file"
    rm -rf "$workdir"
    return 0
  fi

  # fallback: gera PDF de 1 página e usa modo --pdfs do olmOCR
  if command -v python3 >/dev/null 2>&1; then
    local tmp_pdf="$workdir/capture.pdf"
    if python3 - "$image_file" "$tmp_pdf" >/dev/null 2>&1 <<'PY'
import sys
from pathlib import Path
try:
    from PIL import Image
except Exception:
    raise SystemExit(1)
src = Path(sys.argv[1])
dst = Path(sys.argv[2])
img = Image.open(src).convert("RGB")
img.save(dst, "PDF", resolution=300.0)
PY
    then
      olmocr "$workdir" --markdown --pdfs "$tmp_pdf" --workers 1 --pages_per_group 1 >/tmp/glados-olmocr.out 2>/tmp/glados-olmocr.err || true
      md_file="$(ls -1t "$workdir"/markdown/*.md 2>/dev/null | head -n 1 || true)"
      if [[ -n "$md_file" && -f "$md_file" ]]; then
        cat "$md_file"
        rm -rf "$workdir"
        return 0
      fi
    fi
  fi

  if [[ -f /tmp/glados-olmocr.err ]]; then
    head -n 3 /tmp/glados-olmocr.err | tr '\n' ' '
  fi
  rm -rf "$workdir"
  return 0
}}

if [[ -s "$image_path" ]]; then
  excerpt="$(run_olmocr_on_image "$image_path" || true)"
  if [[ "$excerpt" == "__OLMOCR_MISSING__" ]]; then
    excerpt=""
    excerpt_source="olmocr_unavailable"
    olmocr_error="CLI olmocr não encontrada"
  elif [[ -n "${{excerpt//[[:space:]]/}}" ]]; then
    excerpt_source="ocr_area"
  else
    excerpt=""
    excerpt_source="olmocr_failed"
    olmocr_error="olmOCR não retornou texto"
  fi
fi

if [[ -z "$excerpt_source" ]]; then
  excerpt_source="empty"
fi

python3 - "$QUEUE_FILE" "$event_id" "$timestamp" "$PDF_PATH" "$page_num" "$excerpt_source" "$excerpt" "$image_path" "$region" "$olmocr_error" <<'PY'
import json
import os
import sys
from pathlib import Path

queue_path = Path(sys.argv[1]).expanduser()
event_id = sys.argv[2]
created_at = sys.argv[3]
pdf_path = sys.argv[4]
page = int(sys.argv[5] or 0)
source = sys.argv[6]
excerpt = sys.argv[7]
image_path = sys.argv[8]
region = sys.argv[9]
error = sys.argv[10]

queue_path.parent.mkdir(parents=True, exist_ok=True)
event = {{
    "id": event_id,
    "created_at": created_at,
    "pdf_path": str(Path(pdf_path).expanduser()),
    "page": max(1, page),
    "excerpt": str(excerpt or "").strip(),
    "source": source or "empty",
    "image_path": str(Path(image_path).expanduser()) if image_path else "",
    "region": str(region or "").strip(),
    "error": str(error or "").strip(),
}}
with queue_path.open("a", encoding="utf-8") as handle:
    handle.write(json.dumps(event, ensure_ascii=False) + "\\n")
PY

# cria bookmark da captura na página para feedback no próprio zathura
if [[ -f "$BOOKMARK_DB" ]] && command -v python3 >/dev/null 2>&1; then
  python3 - "$BOOKMARK_DB" "$PDF_PATH" "$page_num" "$event_id" >/dev/null 2>&1 <<'PY'
import sqlite3
import sys
db_path, pdf_path, page_raw, event_id = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
try:
    page = max(1, int(page_raw))
except Exception:
    page = 1
try:
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "INSERT OR REPLACE INTO bookmarks(file, id, page) VALUES (?, ?, ?)",
            (str(pdf_path), f"gcap-{event_id[:10]}", page),
        )
        conn.commit()
except Exception:
    pass
PY
fi

if [[ "$excerpt_source" == "ocr_area" ]]; then
  notify "GLaDOS capture" "Trecho OCR (olmOCR) enviado para a nota de citacoes."
elif [[ "$excerpt_source" == "olmocr_unavailable" ]]; then
  notify "GLaDOS capture" "olmOCR não encontrado. Instale o CLI para capturar citações."
elif [[ "$excerpt_source" == "olmocr_failed" ]]; then
  notify "GLaDOS capture" "olmOCR falhou no recorte. Tente selecionar uma área maior."
else
  notify "GLaDOS capture" "Recorte registrado, sem texto detectável."
fi
"""

    def _resolved_include_paths(self) -> List[Path]:
        includes: List[Path] = []
        theme_mode = str(self.config.theme_mode or "plain").strip().lower()

        if theme_mode in {"pywal_internal", "pywal_generator"}:
            includes.append(self.generated_theme_file)
        elif theme_mode == "custom_include" and str(self.config.custom_theme_include_file or "").strip():
            includes.append(self.custom_theme_include_file)

        for raw in self.config.include_files or []:
            value = str(raw or "").strip()
            if value:
                includes.append(self.resolve_path(value))

        unique: List[Path] = []
        seen: set[str] = set()
        for item in includes:
            key = str(item)
            if key in seen:
                continue
            seen.add(key)
            unique.append(item)
        return unique

    def _write_internal_pywal_theme(self) -> tuple[bool, str]:
        colors = self._read_pywal_colors(self.resolve_path(self.config.pywal_colors_file))
        if not colors:
            return False, "Pywal interno indisponivel: arquivo colors.sh nao encontrado ou invalido."

        self.generated_theme_file.parent.mkdir(parents=True, exist_ok=True)
        self.generated_theme_file.write_text(self._render_pywal_theme(colors), encoding="utf-8")
        return True, "Tema Pywal interno atualizado."

    def _write_generator_pywal_theme(self) -> tuple[bool, str]:
        generator = str(self.config.pywal_generator or "genzathurarc").strip() or "genzathurarc"
        if not shutil.which(generator):
            return False, f"Gerador Pywal nao encontrado: {generator}"

        colors_file = self.resolve_path(self.config.pywal_colors_file)
        if not colors_file.exists():
            return False, f"Arquivo de cores do Pywal nao encontrado: {colors_file}"

        try:
            completed = subprocess.run(
                [generator],
                check=True,
                capture_output=True,
                text=True,
            )
        except subprocess.CalledProcessError as exc:
            stderr = (exc.stderr or exc.stdout or "").strip()
            return False, f"Falha ao executar {generator}: {stderr or exc}"
        except Exception as exc:
            return False, f"Falha ao executar {generator}: {exc}"

        output = str(completed.stdout or "").strip()
        if not output:
            return False, f"{generator} nao retornou configuracao."

        self.generated_theme_file.parent.mkdir(parents=True, exist_ok=True)
        self.generated_theme_file.write_text(output.rstrip() + "\n", encoding="utf-8")
        return True, "Tema Pywal via gerador atualizado."

    def _read_pywal_colors(self, colors_file: Path) -> Dict[str, str]:
        if not colors_file.exists():
            return {}
        try:
            content = colors_file.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            return {}

        colors: Dict[str, str] = {}
        for line in content.splitlines():
            match = re.match(r"^\s*([A-Za-z0-9_]+)=['\"]?([^'\"]+)['\"]?\s*$", line.strip())
            if not match:
                continue
            colors[match.group(1)] = match.group(2)
        return colors

    def _render_pywal_theme(self, colors: Dict[str, str]) -> str:
        background = colors.get("background", "#000000")
        foreground = colors.get("foreground", "#FFFFFF")
        color1 = colors.get("color1", "#FF5555")
        color2 = colors.get("color2", "#50FA7B")
        lines = [
            "set recolor true",
            "",
            f'set completion-bg "{background}"',
            f'set completion-fg "{foreground}"',
            f'set completion-group-bg "{background}"',
            f'set completion-group-fg "{color2}"',
            f'set completion-highlight-bg "{foreground}"',
            f'set completion-highlight-fg "{background}"',
            "",
            f'set recolor-lightcolor "{background}"',
            f'set recolor-darkcolor "{foreground}"',
            f'set default-bg "{background}"',
            "",
            f'set inputbar-bg "{background}"',
            f'set inputbar-fg "{foreground}"',
            f'set notification-bg "{background}"',
            f'set notification-fg "{foreground}"',
            f'set notification-error-bg "{color1}"',
            f'set notification-error-fg "{foreground}"',
            f'set notification-warning-bg "{color1}"',
            f'set notification-warning-fg "{foreground}"',
            f'set statusbar-bg "{background}"',
            f'set statusbar-fg "{foreground}"',
            f'set index-bg "{background}"',
            f'set index-fg "{foreground}"',
            f'set index-active-bg "{foreground}"',
            f'set index-active-fg "{background}"',
            f'set render-loading-bg "{background}"',
            f'set render-loading-fg "{foreground}"',
        ]
        return "\n".join(lines).rstrip() + "\n"

    def _render_set_option(self, option_name: str, option_value: Any) -> str:
        name = str(option_name or "").strip()
        if not name:
            return ""
        return f"set {name} {self._format_value(option_value)}"

    def _format_value(self, value: Any) -> str:
        if isinstance(value, bool):
            return "true" if value else "false"
        if isinstance(value, (int, float)):
            return str(value)
        text = str(value or "").strip()
        if not text:
            return '""'
        if re.fullmatch(r"[A-Za-z0-9_./#:-]+", text):
            return text
        return shlex.quote(text)

    def _quote_path(self, path: Path) -> str:
        return shlex.quote(str(path.expanduser()))
