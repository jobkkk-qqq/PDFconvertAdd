#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF转换器 - GUI版本打包脚本
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
    print("  PDF转换器 - GUI版本打包")
    print("=" * 60)
    print(f"工作目录: {base_dir}")
    print(f"输出目录: {dist_dir}")

    # 打包GUI版本
    print("\n[1/2] 打包GUI版本...")
    cmd1 = 'pyinstaller --noconfirm --clean "build_gui_spec.spec"'
    success1 = run_command(cmd1, "打包PDF转换器GUI版本")

    # 打包许可码生成工具（开发者自用，必须带私钥才能发码）
    print("\n[2/3] 打包许可码生成工具（GUI 版）...")
    work_license = os.path.join(dist_dir, "build_license")
    cmd2 = (
        f'pyinstaller --noconfirm --clean --onefile --windowed --name LicenseGenerator '
        f'--distpath "{dist_dir}" --workpath "{os.path.join(work_license, "gui")}" '
        f'--specpath "{work_license}" "licensing/scripts/license_generator_gui.py"'
    )
    success2 = run_command(cmd2, "打包许可码生成工具（GUI 版）")

    print("\n[3/3] 打包许可码生成工具（命令行版）...")
    cmd3 = (
        f'pyinstaller --noconfirm --clean --onefile --console --name LicenseGenerator-cli '
        f'--distpath "{dist_dir}" --workpath "{os.path.join(work_license, "cli")}" '
        f'--specpath "{work_license}" "licensing/scripts/generate_license.py"'
    )
    success3 = run_command(cmd3, "打包许可码生成工具（命令行版）")

    # 整理文件（onedir 输出为 dist/PDFConverter_gui/）
    gui_ok = False
    print("\n整理输出文件...")
    gui_exe = os.path.join(dist_dir, 'PDFConverter_gui', 'PDFConverter_gui.exe')
    if os.path.exists(gui_exe):
        gui_ok = True
        print("  ✓ GUI版本: PDFConverter_gui/PDFConverter_gui.exe")
    else:
        print("  ✗ GUI版本打包失败，未找到 PDFConverter_gui.exe")

    license_gui = os.path.join(dist_dir, 'LicenseGenerator.exe')
    license_cli = os.path.join(dist_dir, 'LicenseGenerator-cli.exe')
    license_ok = os.path.exists(license_gui) and os.path.exists(license_cli)
    if license_ok:
        print("  ✓ 许可码生成器(GUI): LicenseGenerator.exe")
        print("  ✓ 许可码生成器(命令行): LicenseGenerator-cli.exe")
    else:
        print("  ✗ 许可码生成工具打包失败，未找到 LicenseGenerator.exe / LicenseGenerator-cli.exe")

    # 复制辅助脚本
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
        ('pdf-converter/scripts/invoice_print_layout.py', 'invoice_print_layout.py'),
        ('pdf-converter/scripts/invoice_recognizer.py', 'invoice_recognizer.py'),
        ('pdf-converter/scripts/converter_gui.py', 'converter_gui.py'),
        ('licensing/scripts/get_machine_code.py', 'get_machine_code.py'),
        ('licensing/scripts/verify_license.py', 'verify_license.py'),
        ('licensing/scripts/register.py', 'register.py'),
    ]

    for src, dst in source_scripts:
        src_path = os.path.join(base_dir, src)
        dst_path = os.path.join(scripts_dir, dst)
        if os.path.exists(src_path):
            shutil.copy2(src_path, dst_path)
            print(f"  ✓ {dst}")

    # 复制文档
    docs = [
        ('README.md', 'README.md'),
        ('PROJECT.md', 'PROJECT.md'),
        ('REGISTRATION_GUIDE.md', 'REGISTRATION_GUIDE.md'),
        ('USAGE.md', 'USAGE.md'),
        ('DISTRIBUTION.md', '使用说明.md'),
    ]

    for src, dst in docs:
        src_path = os.path.join(base_dir, src)
        dst_path = os.path.join(dist_dir, dst)
        if os.path.exists(src_path):
            shutil.copy2(src_path, dst_path)

    # 创建启动脚本
    startup_script = '''@echo off
chcp 65001 >nul
echo ============================================
echo   PDF转换器 v1.0 (GUI版本)
echo ============================================
echo.
"%~dp0PDFConverter_gui\PDFConverter_gui.exe"
pause
'''
    with open(os.path.join(dist_dir, '启动PDF转换器.bat'), 'w', encoding='utf-8') as f:
        f.write(startup_script)
    print("  ✓ 启动脚本: 启动PDF转换器.bat")

    # 最终结果
    print("\n" + "=" * 60)
    print("  打包完成！")
    print("=" * 60)
    print(f"\n输出目录: {dist_dir}")
    print()

    overall_ok = gui_ok and license_ok
    if overall_ok:
        success1 = True
        print("  ✓ PDF转换器(GUI): PDFConverter_gui/PDFConverter_gui.exe")
        print("  ✓ 许可码生成器(GUI): LicenseGenerator.exe")
        print("  ✓ 许可码生成器(命令行): LicenseGenerator-cli.exe")
        print("  ✓ 辅助脚本: scripts/ 目录")
        print("  ✓ 启动脚本: 启动PDF转换器.bat")
        print()
        print("发码工具需要私钥才能签发许可码（私钥不进 exe）：")
        default_key = os.path.join(os.path.dirname(base_dir), 'license-keys', 'license-private-key.json')
        if os.path.exists(default_key):
            print(f"  ✓ 已找到私钥: {default_key}")
        else:
            print(f"  ! 未找到私钥（按约定应放在仓库上一级）: {default_key}")
            print("    也可放到 exe 同级目录，或用 LICENSE_PRIVATE_KEY 环境变量指定")
        print()
        print("注意：发给客户前请把 LicenseGenerator*.exe 从 dist 移走，只发客户需要的程序。")
    else:
        print("  ✗ 打包过程中出现错误，请检查以上输出（GUI=%s, License=%s）"
              % ("OK" if gui_ok else "FAIL", "OK" if (license_ok and success3) else "FAIL"))

    print("=" * 60)
    print()


if __name__ == '__main__':
    main()
