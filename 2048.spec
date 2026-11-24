# -*- mode: python ; coding: utf-8 -*-
# 2048.spec —— onefile 单文件构建配置
# 用法：pyinstaller 2048.spec --clean --noconfirm

block_cipher = None

datas = [
    ("assets", "assets"),          # 整个 assets 目录原样复制到包的根级 assets/
]

a = Analysis(
    ["main.py"],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter", "pytest"],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="2048",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,                      # 关掉 UPX，降低杀软误报
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,                  # True 会带黑窗
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=["assets/icon.ico"],
    version="version_info.txt",     # 可选，见 docs/06 §5.3
)
