#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF转换器 - 注册说明
"""

import os
import sys


def main():
    print("=" * 60)
    print("PDF转换器 - 注册说明")
    print("=" * 60)
    print()
    print("PDF转换器需要注册后才能使用，每个许可可转换20个文件。")
    print()
    print("注册步骤:")
    print()
    print("  1. 获取机器码")
    print(f"     python {os.path.join('..', 'licensing', 'scripts', 'get_machine_code.py')}")
    print()
    print("  2. 联系开发者获取许可码")
    print("     将机器码发送给开发者，获取许可码")
    print()
    print("  3. 注册")
    print(f"     python {os.path.join('..', 'licensing', 'scripts', 'register.py')} --register <机器码> <许可码>")
    print()
    print("  4. 开始转换")
    print(f"     python {os.path.join('scripts', 'converter.py')} --input your_file.pdf --auto")
    print()
    print("=" * 60)
    print("示例:")
    print("=" * 60)
    print()
    print("  $ python get_machine_code.py")
    print("  您的机器码: D060-9F8C-3317-EC14")
    print()
    print("  $ python register.py --register D060-9F8C-3317-EC14 PDF-D0609F8C-0001-ABCDEF01")
    print("  注册成功！您现在可以转换20个文件。")
    print()
    print("  $ python converter.py --input report.pdf --format word")
    print("  ✓ 转换成功！剩余配额: 19 个文件")
    print()


if __name__ == '__main__':
    main()
