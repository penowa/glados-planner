# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import (
    collect_data_files,
    collect_submodules,
)

import os
import sys


def _filter_problematic_qt_binaries(collected_entries):
    """Remove plugins opcionais que trazem dependências nativas ausentes na release Linux."""
    filtered_entries = []
    for entry in collected_entries:
        dest_name = str(entry[0]) if len(entry) > 0 else ""
        src_name = str(entry[1]) if len(entry) > 1 else ""
        if "libqtiff.so" in dest_name or "libqtiff.so" in src_name:
            continue
        filtered_entries.append(entry)
    return filtered_entries


hiddenimports = []
hiddenimports += collect_submodules("sentence_transformers")
hiddenimports += collect_submodules("transformers")
hiddenimports += collect_submodules("litellm")
hiddenimports += collect_submodules("litellm.litellm_core_utils.tokenizers")
hiddenimports += collect_submodules("core")
hiddenimports += collect_submodules("ui")

binaries = []

# Encontrar o caminho real do litellm no site-packages do virtualenv
litellm_path = None
for path in sys.path:
    test_path = os.path.join(path, 'litellm')
    if os.path.exists(test_path):
        litellm_path = test_path
        break

datas = [
    ("config/templates", "config/templates"),
    ("config/settings.release.yaml", "config"),
    ("requirements-llm.txt", "."),
    ("ui/themes", "ui/themes"),
    ("ui/resources", "ui/resources"),
    ("src/cli/interactive/screens/glados_templates", "src/cli/interactive/screens/glados_templates"),
    ("scripts/setup_ollama.py", "scripts"),
]
datas += collect_data_files("litellm", includes=["*.json"])
if litellm_path:
    containers_dir = os.path.join(litellm_path, "containers")
    if os.path.exists(containers_dir):
        datas.append((containers_dir, "litellm/containers"))
        print(f"✓ Added containers directory: {containers_dir}")
    else:
        print(f"⚠ Warning: containers directory not found at {containers_dir}")
    
    # Também garantir o diretório tokenizers
    tokenizers_dir = os.path.join(litellm_path, "litellm_core_utils", "tokenizers")
    if os.path.exists(tokenizers_dir):
        datas.append((tokenizers_dir, "litellm/litellm_core_utils/tokenizers"))
        print(f"✓ Added tokenizers directory: {tokenizers_dir}")
else:
    print("⚠ Warning: Could not locate litellm installation")


a = Analysis(
    ["run.py"],
    pathex=[".", "./src", "./ui"],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
a.binaries = _filter_problematic_qt_binaries(a.binaries)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="glados-planner",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="glados-planner",
)
