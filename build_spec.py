# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller 配置文件
用于打包PDF转换器和注册系统
"""

block_cipher = None

# PDF转换器主程序
a = Analysis(
    ['pdf-converter/scripts/converter.py'],
    pathex=['D:\\python\\pdf2pdf'],
    binaries=[],
    datas=[
        ('pdf-converter/scripts/pdf_to_word.py', 'scripts'),
        ('pdf-converter/scripts/pdf_to_excel.py', 'scripts'),
        ('pdf-converter/scripts/detect_pdf_type.py', 'scripts'),
        ('pdf-converter/scripts/doc_to_pdf.py', 'scripts'),
        ('pdf-converter/scripts/excel_to_pdf.py', 'scripts'),
        ('pdf-converter/scripts/license_checker.py', 'scripts'),
        ('pdf-converter/scripts/ed25519.py', 'scripts'),
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
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'matplotlib',
        'numpy',
        'scipy',
        'pandas',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='PDFConverter',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,  # 保持控制台窗口
    windowed=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)

# 创建单文件可执行文件
exe_single = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='PDFConverter',
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

# 许可码生成工具
a_license = Analysis(
    ['licensing/scripts/generate_license.py'],
    pathex=['D:\\python\\pdf2pdf'],
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
