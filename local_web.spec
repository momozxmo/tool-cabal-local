# -*- mode: python ; coding: utf-8 -*-
import os
from pathlib import Path

from PyInstaller.utils.hooks import collect_all, collect_submodules


ROOT = Path(SPEC).resolve().parent
ICON = ROOT / 'icon.ico'
BROWSER_CACHE = ROOT / 'build-cache' / 'ms-playwright'
if not BROWSER_CACHE.is_dir():
    raise SystemExit(
        'Bundled Chromium is missing. Run: '
        'python -m playwright install chromium'
    )

os.environ['PLAYWRIGHT_BROWSERS_PATH'] = str(BROWSER_CACHE)

datas = [
    (str(ROOT / 'web' / 'static'), 'web/static'),
    (str(ROOT / 'alembic'), 'alembic'),
    (str(ROOT / 'alembic.ini'), '.'),
    (str(ICON), '.'),
    (str(BROWSER_CACHE), 'ms-playwright'),
]
binaries = []
hiddenimports = [
    'tkinter',
    'tkinter.ttk',
    'tkinter.messagebox',
    'item_finder',
    'finder_core',
    'aztek_core',
    'ui_common',
]

for package in (
    'fastapi',
    'starlette',
    'uvicorn',
    'sqlalchemy',
    'alembic',
    'cryptography',
    'argon2',
    'openpyxl',
    'playwright',
    'pydantic',
    'pydantic_core',
    'multipart',
    'anyio',
    'greenlet',
):
    package_datas, package_binaries, package_hidden = collect_all(package)
    datas += package_datas
    binaries += package_binaries
    hiddenimports += package_hidden

hiddenimports += collect_submodules('web')
hiddenimports += collect_submodules('local_app')

a = Analysis(
    ['local_app/launcher.py'],
    pathex=[str(ROOT)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=['local_app/pyinstaller_runtime_hook.py'],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='All for Cabal Web',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    icon=str(ICON),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    name='All for Cabal Web',
)
