# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_dynamic_libs, collect_submodules


hiddenimports = []
hiddenimports += collect_submodules("sentence_transformers")
hiddenimports += collect_submodules("transformers")

binaries = []
binaries += collect_dynamic_libs("llama_cpp")

datas = [
    ("config", "config"),
    ("ui/themes", "ui/themes"),
    ("ui/resources", "ui/resources"),
    ("src/cli/interactive/screens/glados_templates", "src/cli/interactive/screens/glados_templates"),
    ("data/database/.keep", "data/database"),
    ("data/cache/.keep", "data/cache"),
    ("data/exports/.keep", "data/exports"),
    ("data/history/book_processing_history.json", "data/history"),
]


a = Analysis(
    ["run.py"],
    pathex=["."],
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
