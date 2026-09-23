#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF转换工具 - 统一入口
集成注册验证和完整用户流程
"""

import os
import sys
import argparse
import subprocess
from datetime import datetime

# 设置UTF-8输出
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# 添加当前脚本目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 导入许可验证
from license_checker import PDFConverterLicense


def print_welcome():
    """打印欢迎信息"""
    print("=" * 60)
    print("PDF转换器 v1.0")
    print("=" * 60)
    print()
    print("智能转换PDF、Word、Excel文档")
    print("支持格式: PDF <-> Word <-> Excel")
    print()


def print_registration_guide(machine_code=None):
    """打印注册引导信息"""
    print("-" * 60)
    print("【注册说明】")
    print("-" * 60)
    print()

    if machine_code:
        print(f"  您的机器码: {machine_code}")
        print()
    else:
        print("  步骤 1: 获取机器码")
        licensing_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'licensing', 'scripts')
        get_code_script = os.path.join(licensing_dir, 'get_machine_code.py')
        if os.path.exists(get_code_script):
            print(f"     运行: python \"{get_code_script}\"")
        else:
            print(f"     路径: {get_code_script}")
        print()

    print("  步骤 2: 发送机器码给开发者")
    print("     开发者将根据机器码生成许可码")
    print()

    print("  步骤 3: 使用许可码注册")
    print("     命令: python converter.py --register <机器码> <许可码>")
    print()

    print("-" * 60)


def print_usage_stats(license_checker):
    """打印使用统计"""
    registered = license_checker.is_registered()
    license_info = license_checker.get_license_info()

    if registered:
        usage = license_checker.get_usage()
        limit = usage.get('limit', 20)
        used = usage.get('files_used', 0)
        remaining = usage.get('files_remaining', 0)

        print()
        print("-" * 60)
        print(f"【注册状态】✓ 已注册")
        print(f"  机器码: {usage.get('machine_code', '未知')}")
        print(f"  已使用: {used} / {limit} 个文件")
        print(f"  剩余配额: {remaining} 个文件")
        print("-" * 60)
    else:
        print()
        print("-" * 60)
        print("【注册状态】✗ 未注册")
        print("-" * 60)


def find_script(script_name):
    """查找脚本文件"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    script_path = os.path.join(script_dir, script_name)
    if os.path.exists(script_path):
        return script_path
    return None


def run_script(script_name, args):
    """运行指定的转换脚本"""
    script_path = find_script(script_name)
    if not script_path:
        print(f"错误: 找不到脚本 {script_name}")
        sys.exit(1)

    # 参数清理：None 值（如未指定输出路径）应连同其前置 flag 一并移除，
    # 否则会残留孤立的 "--output" 导致 argparse 报"expected one argument"
    clean = []
    i = 0
    n = len(args)
    while i < n:
        a = args[i]
        s = str(a)
        # 若为 "--flag" 且紧邻的下一个值是 None，则跳过这一对
        if s.startswith('-') and i + 1 < n and args[i + 1] is None:
            i += 2
            continue
        if a is not None:
            clean.append(s)
        i += 1
    cmd = [sys.executable, script_path] + clean
    result = subprocess.run(cmd)
    return result.returncode


IMAGE_EXTS = {'.png', '.jpg', '.jpeg', '.bmp', '.gif', '.webp', '.tif', '.tiff'}


def detect_pdf_recommendation(pdf_path):
    """运行类型检测脚本并解析推荐格式"""
    script_path = find_script('detect_pdf_type.py')
    try:
        result = subprocess.run(
            [sys.executable, script_path, '--input', pdf_path],
            capture_output=True, text=True
        )
        for line in (result.stdout or '').splitlines():
            if '推荐格式' in line and ':' in line:
                rec = line.split(':', 1)[1].strip().upper()
                if rec == 'EXCEL':
                    return 'excel'
                if rec == 'OCR':
                    return 'ocr'
                return 'word'
    except Exception:
        pass
    return 'word'


def convert_pdf_file(pdf_path, output_path=None, fmt='auto', use_ocr=False):
    """对PDF执行实际转换；auto模式按内容自动路由到 word/excel"""
    output_args = ['--input', pdf_path]
    if output_path:
        output_args += ['--output', output_path]

    if fmt == 'word':
        return run_script('pdf_to_word.py', output_args)
    if fmt == 'excel':
        return run_script('pdf_to_excel.py', output_args)

    # auto / --use-ocr：自动检测并真实转换
    rec = detect_pdf_recommendation(pdf_path)
    if use_ocr:
        print(f"\n  检测到推荐格式: {rec.upper()}")
        print("  注意: OCR 文字识别仅 GUI 版本可用，本次按 Word 转换（扫描件文字层可能为空）。")
        return run_script('pdf_to_word.py', output_args)

    print(f"\n  推荐格式: {rec.upper()}，开始转换...")
    if rec == 'excel':
        return run_script('pdf_to_excel.py', output_args)
    return run_script('pdf_to_word.py', output_args)


def main():
    parser = argparse.ArgumentParser(
        description='PDF转换工具 - 统一入口',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  # 首次使用 - 查看注册说明
  python converter.py

  # 获取机器码
  python converter.py --get-machine-code

  # 注册（需要机器码和许可码）
  python converter.py --register D060-9F8C-3317-EC14 PDF-D0609F8C-0001-E4F1990B

  # 查看注册状态
  python converter.py --status

  # PDF转Word
  python converter.py --input doc.pdf --format word

  # PDF转Excel
  python converter.py --input data.pdf --format excel

  # Word转PDF
  python converter.py --input report.docx --format pdf

  # 批量转换
  python converter.py --batch-dir ./documents --format pdf

  # 跳过注册检查（仅测试用）
  python converter.py --input doc.pdf --no-check
        """
    )

    # 注册相关参数
    parser.add_argument('--register', '-r', nargs=2, metavar=('MACHINE', 'LICENSE'),
                       help='注册: --register <机器码> <许可码>')
    parser.add_argument('--get-machine-code', action='store_true',
                       help='显示机器码和注册说明')
    parser.add_argument('--status', '-s', action='store_true',
                       help='查看注册状态和使用统计')

    # 转换相关参数
    parser.add_argument('--input', '-i', help='输入文件路径')
    parser.add_argument('--output', '-o', help='输出文件路径（默认同目录）')
    parser.add_argument('--format', '-f',
                       choices=['word', 'excel', 'pdf', 'auto'],
                       default='auto',
                       help='输出格式（默认auto自动检测）')
    parser.add_argument('--auto', action='store_true',
                       help='使用自动检测模式（等同于 --format auto）')
    parser.add_argument('--batch-dir', '-b',
                       help='批量转换目录（转换目录下所有匹配文件）')
    parser.add_argument('--use-ocr', action='store_true',
                       help='强制使用OCR模式（适用于扫描PDF）')
    parser.add_argument('--no-check', action='store_true',
                       help='跳过注册检查（仅供测试使用）')

    args = parser.parse_args()

    # 初始化
    license_checker = PDFConverterLicense()
    license_checker.init()

    # ========== 注册相关命令 ==========

    if args.get_machine_code:
        print_welcome()
        print_registration_guide()
        print()
        print("正在获取机器码...")
        print()

        # 调用机器码获取脚本 - 计算正确路径
        converter_dir = os.path.dirname(os.path.abspath(__file__))
        # converter/scripts -> pdf-converter -> pdf2pdf -> licensing/scripts
        licensing_dir = os.path.join(converter_dir, '..', '..', 'licensing', 'scripts')
        licensing_dir = os.path.abspath(licensing_dir)
        get_code_script = os.path.join(licensing_dir, 'get_machine_code.py')

        print(f"转换器目录: {converter_dir}")
        print(f"许可目录: {licensing_dir}")
        print(f"脚本路径: {get_code_script}")
        print(f"文件存在: {os.path.exists(get_code_script)}")
        print()

        if os.path.exists(get_code_script):
            result = subprocess.run(
                [sys.executable, get_code_script],
                capture_output=True, text=True
            )
            # 提取机器码 - 匹配 "  D060-9F8C-3317-EC14" 格式
            output_lines = result.stdout.split('\n')
            machine_code = None
            for line in output_lines:
                line_stripped = line.strip()
                # 匹配格式: XXXX-XXXX-XXXX-XXXX
                if len(line_stripped) == 19 and line_stripped.count('-') == 3:
                    import re
                    if re.match(r'^[A-F0-9]{4}-[A-F0-9]{4}-[A-F0-9]{4}-[A-F0-9]{4}$', line_stripped.upper()):
                        machine_code = line_stripped.upper()
                        break

            if machine_code:
                print("=" * 60)
                print(f"您的机器码: {machine_code}")
                print("=" * 60)
                print()
                print_registration_guide(machine_code)
            else:
                print("无法解析机器码")
                print("输出内容:")
                print(result.stdout)
                if result.stderr:
                    print("错误:")
                    print(result.stderr)
        else:
            print("错误: 找不到licensing/scripts/get_machine_code.py")
            print(f"期望路径: {get_code_script}")

        return

    if args.register:
        machine_code, license_code = args.register
        print("正在注册...")
        print()

        # 验证机器码格式
        import re
        if not re.match(r'^[A-F0-9]{4}-[A-F0-9]{4}-[A-F0-9]{4}-[A-F0-9]{4}$', machine_code.upper()):
            print("✗ 错误: 机器码格式无效")
            print("  正确格式: XXXX-XXXX-XXXX-XXXX (十六进制)")
            sys.exit(1)

        # 执行注册
        success, message = license_checker.register(machine_code, license_code)
        print(message)

        if success:
            print()
            print("注册成功！您现在可以使用PDF转换器。")
            print()
            print("-" * 60)
            print("快速开始:")
            print("-" * 60)
            print("  python converter.py --input document.pdf --format word")
            print("  python converter.py --input document.pdf --format excel")
            print("  python converter.py --input document.pdf --auto")
            print("-" * 60)
        sys.exit(0 if success else 1)

    if args.status:
        print_welcome()
        print_usage_stats(license_checker)
        return

    # ========== 转换命令 ==========

    # 检查注册状态（除非禁用），不扣减配额（成功后才扣）
    if not args.no_check:
        allowed, message = license_checker.check_conversion_allowed("conversion_check")
        if not allowed:
            print(f"✗ {message}")
            print()
            print_registration_guide()
            sys.exit(1)
        else:
            print(f"✓ {message}")
            print_usage_stats(license_checker)

    # 检查输入
    if not args.input and not args.batch_dir:
        print_welcome()
        print_usage_stats(license_checker)
        print()
        print("使用方法:")
        print("  python converter.py --input document.pdf --format word")
        print("  python converter.py --input document.pdf --auto")
        print("  python converter.py --help")
        sys.exit(1)

    # 处理批量转换
    if args.batch_dir:
        if not os.path.isdir(args.batch_dir):
            print(f"错误: 目录不存在 {args.batch_dir}")
            sys.exit(1)

        print(f"批量转换目录: {args.batch_dir}")
        print("=" * 60)

        # 查找文件
        pdf_files = []
        doc_files = []
        xlsx_files = []
        image_files = []

        for file in os.listdir(args.batch_dir):
            full_path = os.path.join(args.batch_dir, file)
            ext = os.path.splitext(file)[1].lower()
            if ext == '.pdf':
                pdf_files.append(full_path)
            elif ext in ('.docx', '.doc'):
                doc_files.append(full_path)
            elif ext in ('.xlsx', '.xls'):
                xlsx_files.append(full_path)
            elif ext in IMAGE_EXTS:
                image_files.append(full_path)

        total_files = len(pdf_files) + len(doc_files) + len(xlsx_files) + len(image_files)
        print(f"发现 {total_files} 个文件待转换")
        print()

        # 转换PDF文件
        for pdf_file in pdf_files:
            filename = os.path.basename(pdf_file)
            allowed, message = license_checker.check_conversion_allowed(filename)
            if not allowed:
                print(f"\n✗ {message}")
                print("批量转换已停止。")
                sys.exit(1)
            print(f"  ✓ {message}")
            print(f"\n处理PDF: {filename}")
            if args.format == 'pdf':
                print("  跳过：输入已是PDF格式")
            else:
                ok = convert_pdf_file(pdf_file, None, args.format, args.use_ocr) == 0
                if ok:
                    if not args.no_check:
                        allowed, message = license_checker.check_and_increment(filename)
                        print(f"  {message}")
                else:
                    print("  转换失败，本次未扣除配额。")

        # 转换Word文件
        for doc_file in doc_files:
            filename = os.path.basename(doc_file)
            allowed, message = license_checker.check_conversion_allowed(filename)
            if not allowed:
                print(f"\n✗ {message}")
                print("批量转换已停止。")
                sys.exit(1)
            print(f"  ✓ {message}")
            print(f"\n处理Word: {filename}")
            ok = run_script('doc_to_pdf.py', ['--input', doc_file]) == 0
            if ok:
                if not args.no_check:
                    allowed, message = license_checker.check_and_increment(filename)
                    print(f"  {message}")
            else:
                print("  转换失败，本次未扣除配额。")

        # 转换Excel文件
        for xlsx_file in xlsx_files:
            filename = os.path.basename(xlsx_file)
            allowed, message = license_checker.check_conversion_allowed(filename)
            if not allowed:
                print(f"\n✗ {message}")
                print("批量转换已停止。")
                sys.exit(1)
            print(f"  ✓ {message}")
            print(f"\n处理Excel: {filename}")
            ok = run_script('excel_to_pdf.py', ['--input', xlsx_file]) == 0
            if ok:
                if not args.no_check:
                    allowed, message = license_checker.check_and_increment(filename)
                    print(f"  {message}")
            else:
                print("  转换失败，本次未扣除配额。")

        # 转换图片文件
        if image_files:
            filename = "图片合集"
            allowed, message = license_checker.check_conversion_allowed(filename)
            if not allowed:
                print(f"\n✗ {message}")
                print("批量转换已停止。")
                sys.exit(1)
            print(f"  ✓ {message}")
            print(f"\n处理图片: {len(image_files)} 张")
            ok = run_script('image_to_pdf.py',
                           ['--input'] + image_files) == 0
            if ok:
                if not args.no_check:
                    allowed, message = license_checker.check_and_increment(filename)
                    print(f"  {message}")
            else:
                print("  转换失败，本次未扣除配额。")

        print("\n" + "=" * 60)
        print("批量转换完成！")
        return

    # 单文件转换
    if not args.input:
        parser.print_help()
        sys.exit(1)

    if not os.path.exists(args.input):
        print(f"错误: 文件不存在 {args.input}")
        sys.exit(1)

    file_ext = os.path.splitext(args.input)[1].lower()
    filename = os.path.basename(args.input)

    print("=" * 60)
    print("PDF转换器")
    print("=" * 60)
    print(f"输入文件: {args.input}")
    print(f"输出格式: {args.format}")
    print()

    # 根据文件扩展名选择转换策略
    ok = True
    if file_ext == '.pdf':
        if args.format == 'word':
            ok = run_script('pdf_to_word.py',
                           ['--input', args.input, '--output', args.output]) == 0
        elif args.format == 'excel':
            ok = run_script('pdf_to_excel.py',
                           ['--input', args.input, '--output', args.output]) == 0
        else:
            # auto / --use-ocr / --format pdf：自动检测并实际转换
            print("正在分析PDF类型...")
            run_script('detect_pdf_type.py', ['--input', args.input])
            if args.use_ocr:
                print("\n强制使用OCR模式...")
            ok = convert_pdf_file(args.input, args.output, args.format,
                                  args.use_ocr) == 0

    elif file_ext in ['.docx', '.doc']:
        ok = run_script('doc_to_pdf.py',
                       ['--input', args.input, '--output', args.output]) == 0

    elif file_ext in ['.xlsx', '.xls']:
        ok = run_script('excel_to_pdf.py',
                       ['--input', args.input, '--output', args.output]) == 0

    elif file_ext in IMAGE_EXTS:
        # 图片 → PDF
        if args.format not in ('pdf', 'auto'):
            print(f"提示: 图片输入固定转换为PDF（忽略格式 {args.format}）")
        ok = run_script('image_to_pdf.py',
                       ['--input', args.input, '--output', args.output]) == 0

    else:
        print(f"错误: 不支持的文件格式 {file_ext}")
        print("支持格式: .pdf, .docx, .doc, .xlsx, .xls " + ",".join(sorted(IMAGE_EXTS)))
        sys.exit(1)

    if not ok:
        print(f"\n❌ 转换失败，本次未扣除配额。请检查错误日志。")
        sys.exit(1)

    # 转换成功后才扣除配额
    if not args.no_check:
        license_checker.check_and_increment(filename)
        print_usage_stats(license_checker)

    print("\n" + "=" * 60)
    print("转换完成！")
    print("=" * 60)


if __name__ == '__main__':
    main()
