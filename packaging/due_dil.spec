# PyInstaller — build from repo root:
#   pyinstaller packaging/due_dil.spec
#
# Produces dist/DueDiligenceTool/DueDiligenceTool.exe (onedir) with web/ bundled.

import sys
from pathlib import Path

block_cipher = None

# PyInstaller sets SPEC to this file's path.
ROOT = Path(SPEC).resolve().parents[1]

a = Analysis(
    [str(ROOT / "app" / "__main__.py")],
    pathex=[str(ROOT)],
    binaries=[],
    datas=[
        (str(ROOT / "web"), "web"),
    ],
    hiddenimports=["zeep", "reportlab", "eel", "appdirs"],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="DueDiligenceTool",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="DueDiligenceTool",
)
