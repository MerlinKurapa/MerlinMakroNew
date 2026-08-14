# -*- mode: python ; coding: utf-8 -*-
import os

block_cipher = None
root = os.path.abspath('.')

a = Analysis(
    ['MerlinMakro_GUI.py'],
    pathex=[root],
    binaries=[],
    datas=[
        ('ui/macro', 'ui/macro'),
        ('MerlinMakro.ico', '.'),
        ('merlinmakroauth-firebase-adminsdk-fbsvc-df7571c065.json', '.'),
    ],
    hiddenimports=[
        'webview',
        'clr',
        'firebase_admin',
        'google.cloud.firestore',
        'pydirectinput',
        'keyboard',
        'psutil',
    ],
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
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='MerlinMakro',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='MerlinMakro.ico',
)
