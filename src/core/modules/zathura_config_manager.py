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

    def status(self) -> Dict[str, Any]:
        binary = str(self.config.binary or "zathura").strip() or "zathura"
        generator = str(self.config.pywal_generator or "genzathurarc").strip() or "genzathurarc"
        colors_file = self.resolve_path(self.config.pywal_colors_file)
        binary_resolved = shutil.which(binary)
        generator_resolved = shutil.which(generator)
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

        if self.config.keymaps:
            lines.append("")
            lines.append("# Keymaps customizados")
            for mapping in self.config.keymaps:
                clean = str(mapping or "").strip()
                if clean:
                    lines.append(clean)

        extra = str(self.config.extra_config or "").strip()
        if extra:
            lines.append("")
            lines.append("# Configuracao extra")
            lines.append(extra)

        return "\n".join(lines).rstrip() + "\n"

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
