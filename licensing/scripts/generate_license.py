#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
许可码生成工具（开发者使用）
根据机器码生成注册许可码
许可码格式: PDF-{机器码前8位}-{序列号}-{校验位}
"""

import sys
import hashlib
import hmac
import re


# 开发者密钥（实际项目中应安全存储）
DEVELOPER_SECRET = "PDFConverter2026_SecretKey_v1.0"
MAX_FILE_LIMIT = 20


def validate_machine_code(machine_code):
    """验证机器码格式"""
    # 格式: XXXX-XXXX-XXXX-XXXX (每组4个字符)
    pattern = r'^[A-F0-9]{4}-[A-F0-9]{4}-[A-F0-9]{4}-[A-F0-9]{4}$'
    return re.match(pattern, machine_code.upper()) is not None


def extract_machine_code_hash(machine_code):
    """从机器码中提取原始哈希"""
    # 移除连字符
    clean_code = machine_code.replace("-", "")
    return clean_code


def generate_license_code(machine_code, serial_number=1):
    """
    生成许可码

    参数:
        machine_code: 用户的机器码 (格式: XXXX-XXXX-XXXX-XXXX)
        serial_number: 序列号，用于区分同一机器的多次授权

    返回:
        许可码字符串
    """
    if not validate_machine_code(machine_code):
        raise ValueError(f"无效的机器码格式: {machine_code}")

    machine_code = machine_code.upper()

    # 提取机器码哈希
    code_hash = extract_machine_code_hash(machine_code)

    # 生成许可码主体
    license_prefix = "PDF"
    machine_prefix = code_hash[:8]  # 取前8位
    serial_str = f"{serial_number:04d}"  # 4位序列号

    # 计算校验位（HMAC-SHA256）
    message = f"{license_prefix}-{machine_prefix}-{serial_str}"
    signature = hmac.new(
        DEVELOPER_SECRET.encode('utf-8'),
        message.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()[:8].upper()

    # 组装许可码
    license_code = f"{license_prefix}-{machine_prefix}-{serial_str}-{signature}"

    return license_code


def verify_license_code(license_code, machine_code):
    """
    验证许可码是否有效

    参数:
        license_code: 要验证的许可码
        machine_code: 对应的机器码

    返回:
        (是否有效, 错误信息)
    """
    # 验证许可码格式
    pattern = r'^PDF-[A-F0-9]{8}-\d{4}-[A-F0-9]{8}$'
    if not re.match(pattern, license_code.upper()):
        return False, "许可码格式无效"

    license_code = license_code.upper()

    # 验证机器码格式
    if not validate_machine_code(machine_code):
        return False, "机器码格式无效"

    machine_code = machine_code.upper()

    # 校验机器码前缀与许可码一致
    machine_prefix = machine_code.replace("-", "")[:8]
    if license_code[4:12] != machine_prefix:
        return False, "许可码与机器码不匹配"

    # 按许可码内嵌的序列号重算校验位，以支持续期（序列号>=2）
    serial_str = license_code[13:17]
    message = f"PDF-{machine_prefix}-{serial_str}"
    signature = hmac.new(
        DEVELOPER_SECRET.encode('utf-8'),
        message.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()[:8].upper()

    # 比较校验位
    if license_code[18:] == signature:
        return True, "许可码有效"
    else:
        return False, "许可码与机器码不匹配"


def get_license_info(license_code):
    """从许可码中提取信息"""
    pattern = r'^PDF-([A-F0-9]{8})-(\d{4})-([A-F0-9]{8})$'
    match = re.match(pattern, license_code.upper())

    if match:
        return {
            "machine_prefix": match.group(1),
            "serial_number": int(match.group(2)),
            "signature": match.group(3),
            "max_files": MAX_FILE_LIMIT
        }
    return None


def _print_license(machine_code, serial, license_code):
    print("=" * 60)
    print("PDF转换器 - 许可码生成工具")
    print("=" * 60)
    print()
    print(f"机器码:   {machine_code}")
    print(f"序列号:   {serial}")
    print(f"文件限制: {MAX_FILE_LIMIT} 个文件")
    print()
    print("=" * 60)
    print("许可码:")
    print(f"  {license_code}")
    print("=" * 60)
    print()
    print("请将此许可码提供给用户进行注册。")


def _safe_input(prompt=""):
    """读取一行输入；stdin关闭或被中断时返回空串，避免闪退崩溃。"""
    try:
        return input(prompt)
    except (EOFError, KeyboardInterrupt):
        return ""


def _interactive_main():
    """无参数时进入交互模式（双击运行时使用），结束前驻留以便查看结果。"""
    print("=" * 60)
    print("PDF转换器 - 许可码生成工具（交互模式）")
    print("=" * 60)
    print()
    while True:
        machine_code = _safe_input(
            "请输入机器码 (格式 XXXX-XXXX-XXXX-XXXX，直接回车退出): ").strip().upper()
        if not machine_code:
            print("已退出。")
            break
        if not validate_machine_code(machine_code):
            print("  机器码格式无效，请重新输入。")
            print()
            continue
        serial_str = _safe_input("请输入序列号 (默认1): ").strip() or "1"
        try:
            serial = int(serial_str)
        except ValueError:
            print("  序列号无效，已使用默认值1。")
            serial = 1
        license_code = generate_license_code(machine_code, serial)
        print()
        _print_license(machine_code, serial, license_code)
        print()
    _safe_input("\n按回车键退出...")


def main():
    # 控制台输出统一使用UTF-8，避免中文乱码
    for _stream in (sys.stdout, sys.stderr):
        try:
            _stream.reconfigure(encoding="utf-8")
        except Exception:
            pass

    if len(sys.argv) < 2:
        _interactive_main()
        return

    machine_code = sys.argv[1].upper()
    serial = int(sys.argv[2]) if len(sys.argv) > 2 else 1

    try:
        license_code = generate_license_code(machine_code, serial)
        _print_license(machine_code, serial, license_code)

    except ValueError as e:
        print(f"错误: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
