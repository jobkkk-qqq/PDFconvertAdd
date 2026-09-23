#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Excel转PDF脚本
使用LibreOffice进行转换
"""

import os
import sys
import argparse
import subprocess
import platform


def find_libreoffice():
    """查找LibreOffice可执行文件"""
    system = platform.system()

    if system == "Windows":
        possible_paths = [
            r"C:\Program Files\LibreOffice\program\soffice.exe",
            r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
        ]
        for path in possible_paths:
            if os.path.exists(path):
                return path

        try:
            result = subprocess.run(['where', 'soffice'], capture_output=True, text=True)
            if result.returncode == 0:
                return result.stdout.strip().split('\n')[0]
        except Exception:
            pass

    elif system == "Linux":
        possible_paths = [
            "/usr/bin/libreoffice",
            "/usr/bin/soffice",
        ]
        for path in possible_paths:
            if os.path.exists(path):
                return path

    elif system == "Darwin":
        possible_paths = [
            "/Applications/LibreOffice.app/Contents/MacOS/soffice",
        ]
        for path in possible_paths:
            if os.path.exists(path):
                return path

    return None


def excel_to_pdf(excel_path, output_path=None):
    """将Excel文档转换为PDF"""
    libreoffice = find_libreoffice()

    if not libreoffice:
        print("错误: 未找到LibreOffice")
        sys.exit(1)

    if not os.path.exists(excel_path):
        print(f"错误: 文件不存在 {excel_path}")
        sys.exit(1)

    # 默认输出路径
    if not output_path:
        base_name = os.path.splitext(excel_path)[0]
        output_path = f"{base_name}.pdf"

    # 确保输出目录存在
    output_dir = os.path.dirname(output_path)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)

    print(f"正在转换: {excel_path}")
    print(f"LibreOffice路径: {libreoffice}")
    print()

    # 使用LibreOffice转换
    cmd = [
        libreoffice,
        '--headless',
        '--convert-to', 'pdf',
        '--outdir', os.path.dirname(output_path) or '.',
        excel_path
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)

        if result.returncode == 0:
            # LibreOffice 输出文件名固定为“输入文件同名.pdf”，需校正到目标路径
            real_output = os.path.join(
                os.path.dirname(output_path) or '.',
                os.path.splitext(os.path.basename(excel_path))[0] + '.pdf')
            if os.path.abspath(real_output) != os.path.abspath(output_path):
                if os.path.exists(output_path):
                    os.remove(output_path)
                os.replace(real_output, output_path)
                real_output = output_path

            print("✓ 转换成功！")
            print(f"输出文件: {real_output}")

            if os.path.exists(real_output):
                file_size = os.path.getsize(real_output)
                print(f"文件大小: {file_size / 1024:.1f} KB")
            return real_output
        else:
            print("✗ 转换失败")
            print(f"错误信息: {result.stderr}")
            sys.exit(1)

    except subprocess.TimeoutExpired:
        print("✗ 转换超时（超过120秒）")
        sys.exit(1)
    except Exception as e:
        print(f"✗ 转换出错: {e}")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description='Excel转PDF工具')
    parser.add_argument('--input', '-i', required=True, help='输入Excel文件路径')
    parser.add_argument('--output', '-o', help='输出PDF文件路径（默认同目录）')

    args = parser.parse_args()
    excel_to_pdf(args.input, args.output)


if __name__ == '__main__':
    main()
