# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller 配置文件 - GUI版本
用于打包PDF转换器图形界面（onedir 布局: dist/PDFConverter_gui/）
"""

import os

# 项目根目录（PyInstaller 在项目根目录执行，cwd 即项目根）
_base_dir = os.getcwd()

# GUI版本（onedir）
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
        ('pdf-converter/scripts/image_to_pdf.py', 'scripts'),
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
        'pdf2docx',
        'pdf2docx.converter',
        'pdf2docx.main',
        'pdf2docx.common',
        'pdf2docx.common.docx',
        'pdf2docx.font',
        'pdf2docx.font.Fonts',
        'pdf2docx.image',
        'pdf2docx.image.Image',
        'pdf2docx.image.ImageBlock',
        'pdf2docx.layout',
        'pdf2docx.layout.Blocks',
        'pdf2docx.layout.Layout',
        'pdf2docx.layout.Sections',
        'pdf2docx.page',
        'pdf2docx.page.Page',
        'pdf2docx.page.Pages',
        'pdf2docx.page.RawPage',
        'pdf2docx.page.RawPageFitz',
        'pdf2docx.shape',
        'pdf2docx.shape.Shape',
        'pdf2docx.table',
        'pdf2docx.table.TableStructure',
        'pdf2docx.table.TablesConstructor',
        'pdf2docx.text',
        'pdf2docx.text.TextBlock',
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
        'image_to_pdf',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'matplotlib',
        'scipy',
        'pandas',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)

pyz_gui = PYZ(a_gui.pure, a_gui.zipped_data, cipher=None)

exe_gui = EXE(
    pyz_gui,
    a_gui.scripts,
    [],
    exclude_binaries=True,
    name='PDFConverter_gui',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    windowed=True,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)

coll_gui = COLLECT(
    exe_gui,
    a_gui.binaries,
    a_gui.zipfiles,
    a_gui.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='PDFConverter_gui',
)