# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller 配置文件 - GUI版本（旧版，保留作参考）
用于打包PDF转换器图形界面

注意：日常打包请用仓库根目录下维护中的 spec：build_gui_spec.spec
本文件里的 excludes 含 numpy 与 tkinter.ttk，且未收集 RapidOCR/onnxruntime，
直接使用会导致界面/OCR 相关功能不可用。
"""

import os

block_cipher = None

# 文件所在目录（即仓库根）；不再依赖任何本机绝对路径
_base_dir = os.path.dirname(os.path.abspath(__file__))

# GUI版本
a_gui = Analysis(
    [os.path.join(_base_dir, 'pdf-converter', 'scripts', 'converter_gui.py')],
    pathex=[_base_dir],
    binaries=[],
    datas=[
        ('pdf-converter/scripts/pdf_to_word.py', 'scripts'),
        ('pdf-converter/scripts/pdf_to_excel.py', 'scripts'),
        ('pdf-converter/scripts/detect_pdf_type.py', 'scripts'),
        ('pdf-converter/scripts/doc_to_pdf.py', 'scripts'),
        ('pdf-converter/scripts/excel_to_pdf.py', 'scripts'),
        ('pdf-converter/scripts/license_checker.py', 'scripts'),
        ('pdf-converter/scripts/ed25519.py', 'scripts'),
        ('pdf-converter/scripts/invoice_print_layout.py', 'scripts'),
        ('pdf-converter/scripts/invoice_recognizer.py', 'scripts'),
        ('pdf-converter/scripts/pdf_page_editor.py', 'scripts'),
        ('licensing/scripts/get_machine_code.py', 'scripts'),
        ('licensing/scripts/generate_license.py', 'scripts'),
        ('licensing/scripts/verify_license.py', 'scripts'),
        ('licensing/scripts/register.py', 'scripts'),
    ],
    hiddenimports=[
        'fitz',
        'pymupdf',
        'pdfplumber',
        'docx',
        'openpyxl',
        'PIL',
        'generate_license',
        'verify_license',
        'get_machine_code',
        'register',
        'license_checker',
        'ed25519',
        'invoice_print_layout',
        'invoice_recognizer',
        'pdf_page_editor',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'matplotlib',
        'numpy',
        'scipy',
        'pandas',
        'tkinter.ttk',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz_gui = PYZ(a_gui.pure, a_gui.zipped_data, cipher=block_cipher)

exe_gui = EXE(
    pyz_gui,
    a_gui.scripts,
    [],
    exclude_binaries=True,
    name='PDFConverter',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # 无控制台窗口
    windowed=True,  # 窗口模式
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)

# 许可码生成工具（保持命令行版本）
a_license = Analysis(
    [os.path.join(_base_dir, 'licensing', 'scripts', 'generate_license.py')],
    pathex=[_base_dir],
    binaries=[],
    datas=[('licensing/scripts/ed25519.py', '.')],
    hiddenimports=['ed25519'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

exe_license = EXE(
    a_license.pure,
    a_license.scripts,
    a_license.binaries,
    a_license.zipfiles,
    a_license.datas,
    [],
    name='LicenseGenerator',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    windowed=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)
