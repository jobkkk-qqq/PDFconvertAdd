#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF转换器 - 打包脚本
使用PyInstaller打包为可执行文件
"""

import os
import sys
import subprocess
import shutil


def run_command(cmd, description):
    """运行命令并显示进度"""
    print(f"\n{'='*60}")
    print(f"  {description}")
    print(f"{'='*60}")
    print(f"命令: {cmd}")
    print()

    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)

    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print(result.stderr)

    return result.returncode == 0


def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    dist_dir = os.path.join(base_dir, 'dist')

    # 创建dist目录
    if os.path.exists(dist_dir):
        shutil.rmtree(dist_dir)
    os.makedirs(dist_dir, exist_ok=True)

    print()
    print("=" * 60)
    print("  PDF转换器 - 打包工具")
    print("=" * 60)
    print(f"工作目录: {base_dir}")
    print(f"输出目录: {dist_dir}")

    # 检查PyInstaller
    print("\n检查PyInstaller...")
    try:
        import PyInstaller
        print(f"  ✓ PyInstaller已安装: {PyInstaller.__version__}")
    except ImportError:
        print("  ✗ PyInstaller未安装，正在安装...")
        run_command("pip install pyinstaller", "安装PyInstaller")

    # 打包PDF转换器
    print("\n[1/1] 打包PDF转换器...")
    cmd1 = f'pyinstaller --onefile --console --name PDFConverter --distpath "{dist_dir}" --workpath "{os.path.join(dist_dir, "build")}" "pdf-converter/scripts/converter.py"'
    success1 = run_command(cmd1, "打包PDF转换器")

    # 复制辅助脚本到dist目录
    print("\n复制辅助文件...")
    scripts_dir = os.path.join(dist_dir, 'scripts')
    os.makedirs(scripts_dir, exist_ok=True)

    source_scripts = [
        ('pdf-converter/scripts/pdf_to_word.py', 'pdf_to_word.py'),
        ('pdf-converter/scripts/pdf_to_excel.py', 'pdf_to_excel.py'),
        ('pdf-converter/scripts/detect_pdf_type.py', 'detect_pdf_type.py'),
        ('pdf-converter/scripts/doc_to_pdf.py', 'doc_to_pdf.py'),
        ('pdf-converter/scripts/excel_to_pdf.py', 'excel_to_pdf.py'),
        ('pdf-converter/scripts/license_checker.py', 'license_checker.py'),
        ('pdf-converter/scripts/ed25519.py', 'ed25519.py'),
        ('licensing/scripts/get_machine_code.py', 'get_machine_code.py'),
        ('licensing/scripts/verify_license.py', 'verify_license.py'),
        ('licensing/scripts/license_verify.py', 'license_verify.py'),
        ('licensing/scripts/register.py', 'register.py'),
    ]

    copied = 0
    for src, dst in source_scripts:
        src_path = os.path.join(base_dir, src)
        dst_path = os.path.join(scripts_dir, dst)
        if os.path.exists(src_path):
            shutil.copy2(src_path, dst_path)
            copied += 1
            print(f"  ✓ {dst}")
        else:
            print(f"  ✗ {dst} (文件不存在)")

    # 复制文档
    docs = [
        ('README.md', 'README.md'),
        ('PROJECT.md', 'PROJECT.md'),
        ('REGISTRATION_GUIDE.md', 'REGISTRATION_GUIDE.md'),
        ('USAGE.md', 'USAGE.md'),
    ]

    print("\n复制文档...")
    for src, dst in docs:
        src_path = os.path.join(base_dir, src)
        dst_path = os.path.join(dist_dir, dst)
        if os.path.exists(src_path):
            shutil.copy2(src_path, dst_path)
            print(f"  ✓ {dst}")

    # 创建启动脚本
    print("\n创建启动脚本...")
    startup_script = '''@echo off
chcp 65001 >nul
echo ============================================
echo   PDF转换器 v1.0
echo ============================================
echo.
"%~dp0PDFConverter.exe" %*
pause
'''
    startup_path = os.path.join(dist_dir, '启动PDF转换器.bat')
    with open(startup_path, 'w', encoding='utf-8') as f:
        f.write(startup_script)
    print(f"  ✓ 启动脚本: 启动PDF转换器.bat")

    # 最终结果
    print("\n" + "=" * 60)
    print("  打包完成！")
    print("=" * 60)
    print(f"\n输出目录: {dist_dir}")
    print()

    if success1:
        print("  ✓ PDF转换器: PDFConverter.exe")
        print("  ✓ 辅助脚本: scripts/ 目录")
        print("  ✓ 启动脚本: 启动PDF转换器.bat")
        print()
        print("所有文件已准备就绪，可以分发给用户！")
    else:
        print("  ✗ 打包过程中出现错误，请检查以上输出")

    print("=" * 60)
    print()


if __name__ == '__main__':
    main()
