# -*- mode: python ; coding: utf-8 -*-
"""发票打印独立版打包配置：InvPrint/ 目录版（onedir，启动更快，免每次解压）"""
import os

# 在 inv-print 目录内运行打包，cwd 即脚本根目录
_base = os.getcwd()

a = Analysis(
    [os.path.join(_base, 'inv_print.py')],
    pathex=[_base],
    binaries=[],
    datas=[],
    hiddenimports=[
        'fitz',
        'pymupdf',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['matplotlib', 'scipy'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=None)

# onedir 模式：EXE 仅含启动器（exclude_binaries），运行库由下方 COLLECT 放到旁边目录
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='InvPrint',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,          # 图形界面程序，不弹控制台
    windowed=True,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='InvPrint',
)