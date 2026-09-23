# -*- mode: python ; coding: utf-8 -*-
"""发票打印独立版 — 单文件版打包配置：InvPrint_onefile.exe（供与目录版做启动速度对比）"""
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

# onefile 模式：EXE 直接包含所有运行库，启动时解压到临时目录
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='InvPrint_onefile',
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