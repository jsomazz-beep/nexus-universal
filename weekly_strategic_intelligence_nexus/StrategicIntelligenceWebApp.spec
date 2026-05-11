# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['packaged_webapp_launcher.py'],
    pathex=['src'],
    binaries=[],
    datas=[('src\\news_reporter\\templates', 'news_reporter\\templates'), ('config\\config.example.yaml', 'config'), ('.env.example', '.')],
    hiddenimports=[],
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
    a.binaries,
    a.datas,
    [],
    name='StrategicIntelligenceWebApp',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
