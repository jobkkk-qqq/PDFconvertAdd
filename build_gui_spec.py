# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller 配置文件 - GUI版本
用于打包PDF转换器图形界面
"""

block_cipher = None

# GUI版本
a_gui = Analysis(
    ['pdf-converter/scripts/converter_gui.py'],
    pathex=['D:\\python\\pdf2pdf'],
    binaries=[],
    datas=[
        ('pdf-converter/scripts/pdf_to_word.py', 'scripts'),
        ('pdf-converter/scripts/pdf_to_excel.py', 'scripts'),
        ('pdf-converter/scripts/detect_pdf_type.py', 'scripts'),
        ('pdf-converter/scripts/doc_to_pdf.py', 'scripts'),
        ('pdf-converter/scripts/excel_to_pdf.py', 'scripts'),
        ('pdf-converter/scripts/license_checker.py', 'scripts'),
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
    ['licensing/scripts/generate_license.py'],
    pathex=['D:\\python\\pdf2pdf'],
    binaries=[],
    datas=[],
    hiddenimports=[],
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
