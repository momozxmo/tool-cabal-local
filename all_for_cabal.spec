# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec — build "All for Cabal.exe" (รวม Item Finder + Create Bundle)
# build:  pyinstaller all_for_cabal.spec
import os
from PyInstaller.utils.hooks import collect_all

datas, binaries, hiddenimports = [], [], []

# ไอคอนแอป — ฝังใน .exe (icon=) และแนบเป็นไฟล์ (datas) ให้ runtime หาเจอ (title bar / taskbar)
_ICON = os.path.join(os.path.dirname(os.path.abspath(SPEC)), 'icon.ico')
if os.path.exists(_ICON):
    datas.append((_ICON, '.'))

# รวม playwright driver (ตัวขับ browser) + openpyxl เข้า exe
for pkg in ('playwright', 'openpyxl'):
    try:
        d, b, h = collect_all(pkg)
        datas += d
        binaries += b
        hiddenimports += h
    except Exception:
        pass

hiddenimports += ['tkinter', 'tkinter.ttk', 'tkinter.scrolledtext',
                  'tkinter.messagebox', 'tkinter.filedialog',
                  # โมดูลเครื่องมือ + ของกลาง (ui_common/aztek_core/config/tool_registry)
                  'item_finder', 'new_tool', 'itemcode_tool', 'event_tool',
                  'aztek_core', 'ui_common', 'config', 'tool_registry']

a = Analysis(
    ['all_for_cabal.py'],   # entry point — import item_finder + new_tool อัตโนมัติ
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='All for Cabal',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,          # ไม่มีหน้าต่าง console (GUI app)
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=_ICON if os.path.exists(_ICON) else None,
)
