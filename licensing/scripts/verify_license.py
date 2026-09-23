#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
许可码验证工具
验证用户提供的许可码是否有效
"""

import sys
import os

# 添加licensing脚本路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from generate_license import (
    validate_machine_code,
    verify_license_code,
    get_license_info
)


def main():
    if len(sys.argv) < 3:
        print("用法: python verify_license.py <机器码> <许可码>")
        print()
        print("示例:")
        print("  python verify_license.py A1B2C3D4-E5F6G7H8-I9J0K1L2-M3N4O5P6 PDF-A1B2C3D4-0001-ABCDEF01")
        sys.exit(1)

    machine_code = sys.argv[1].upper()
    license_code = sys.argv[2].upper()

    print("=" * 60)
    print("PDF转换器 - 许可码验证工具")
    print("=" * 60)
    print()

    # 验证机器码
    if not validate_machine_code(machine_code):
        print(f"✗ 机器码格式无效: {machine_code}")
        print("  正确格式: XXXX-XXXX-XXXX-XXXX (十六进制)")
        sys.exit(1)

    print(f"机器码: {machine_code}")
    print(f"许可码: {license_code}")
    print()

    # 验证许可码
    is_valid, message = verify_license_code(license_code, machine_code)

    if is_valid:
        print("✓ 验证结果: 许可码有效")
        print()

        # 显示许可信息
        info = get_license_info(license_code)
        if info:
            print("许可信息:")
            print(f"  机器前缀: {info['machine_prefix']}")
            print(f"  序列号:   {info['serial_number']}")
            print(f"  文件限额: {info['max_files']} 个文件")
            print()
            print("恭喜！您可以开始使用PDF转换器。")
    else:
        print(f"✗ 验证结果: {message}")
        print()
        print("请检查机器码和许可码是否正确。")
        print("如果问题持续，请联系开发者重新生成许可码。")
        sys.exit(1)

    print("=" * 60)


if __name__ == '__main__':
    main()
