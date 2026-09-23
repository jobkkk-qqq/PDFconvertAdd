#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
机器码提取工具
从用户机器提取唯一标识符（机器码）
"""

import os
import sys
import platform
import hashlib
import subprocess


def get_cpu_id():
    """获取CPU ID"""
    system = platform.system()

    if system == "Windows":
        try:
            import winreg
            key = winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                r"HARDWARE\DESCRIPTION\System\CentralProcessor\0"
            )
            cpu_id, _ = winreg.QueryValueEx(key, "ProcessorId")
            winreg.CloseKey(key)
            return str(cpu_id).strip()
        except Exception:
            pass

        # 备用：通过WMIC获取
        try:
            result = subprocess.run(
                ['wmic', 'cpu', 'get', 'ProcessorId'],
                capture_output=True, text=True, timeout=10
            )
            lines = result.stdout.strip().split('\n')
            for line in lines:
                if line.strip() and line.strip() != 'ProcessorId':
                    return line.strip()
        except Exception:
            pass

    elif system == "Linux":
        try:
            with open('/proc/cpuinfo', 'r') as f:
                for line in f:
                    if line.startswith('processor id'):
                        return line.split(':')[1].strip().upper()
        except Exception:
            pass

        try:
            result = subprocess.run(
                ['sudo', 'dmidecode', '-t', 'processor'],
                capture_output=True, text=True, timeout=10
            )
            for line in result.stdout.split('\n'):
                if 'ID:' in line:
                    return line.split(':')[1].strip().upper()
        except Exception:
            pass

    elif system == "Darwin":  # macOS
        try:
            result = subprocess.run(
                ['sysctl', 'machdep.cpu.brand_string'],
                capture_output=True, text=True
            )
            return hashlib.sha256(result.stdout.encode()).hexdigest()[:16].upper()
        except Exception:
            pass

    return None


def get_board_id():
    """获取主板序列号"""
    system = platform.system()

    if system == "Windows":
        try:
            import winreg
            key = winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                r"HARDWARE\DESCRIPTION\System\BIOS"
            )
            board_id, _ = winreg.QueryValueEx(key, "BaseBoardProduct")
            winreg.CloseKey(key)
            if board_id:
                return str(board_id).strip()
        except Exception:
            pass

        # 备用：通过WMIC获取
        try:
            result = subprocess.run(
                ['wmic', 'baseboard', 'get', 'Product'],
                capture_output=True, text=True, timeout=10
            )
            lines = result.stdout.strip().split('\n')
            for line in lines:
                if line.strip() and line.strip() != 'Product':
                    return line.strip()
        except Exception:
            pass

        # 再备用：获取系统序列号
        try:
            result = subprocess.run(
                ['wmic', 'computersystem', 'get', 'UUID'],
                capture_output=True, text=True, timeout=10
            )
            lines = result.stdout.strip().split('\n')
            for line in lines:
                if line.strip() and line.strip() != 'UUID':
                    return line.strip()
        except Exception:
            pass

    elif system == "Linux":
        try:
            with open('/sys/class/dmi/id/board_serial', 'r') as f:
                return f.read().strip().upper()
        except Exception:
            pass

        try:
            with open('/sys/class/dmi/id/product_serial', 'r') as f:
                return f.read().strip().upper()
        except Exception:
            pass

    elif system == "Darwin":
        try:
            result = subprocess.run(
                ['system_profiler', 'SPHardwareDataType'],
                capture_output=True, text=True
            )
            for line in result.stdout.split('\n'):
                if 'Serial Number (system)' in line:
                    return line.split(':')[1].strip().upper()
        except Exception:
            pass

    return None


def get_mac_address():
    """获取网卡MAC地址"""
    try:
        mac = uuid_get_mac()
        if mac:
            return mac
    except Exception:
        pass

    system = platform.system()

    if system == "Windows":
        try:
            result = subprocess.run(
                ['getmac', '/fo', 'csv'],
                capture_output=True, text=True, timeout=10
            )
            lines = result.stdout.strip().split('\n')
            for line in lines[1:]:  # 跳过标题行
                if line.strip():
                    parts = line.split(',')
                    if parts:
                        mac = parts[0].strip().replace('-', ':')
                        if mac:
                            return mac.upper()
        except Exception:
            pass

    elif system == "Linux":
        try:
            with open('/sys/class/net/eth0/address', 'r') as f:
                return f.read().strip().upper()
        except Exception:
            try:
                with open('/sys/class/net/wlan0/address', 'r') as f:
                    return f.read().strip().upper()
            except Exception:
                pass

    elif system == "Darwin":
        try:
            result = subprocess.run(
                ['ifconfig', 'en0'],
                capture_output=True, text=True
            )
            for line in result.stdout.split('\n'):
                if 'ether' in line:
                    return line.split()[1].upper()
        except Exception:
            pass

    return None


def uuid_get_mac():
    """使用uuid模块获取MAC地址（跨平台）"""
    import uuid
    mac = uuid.getnode()
    if mac:
        return ':'.join(
            ('%012x' % mac)[i:i+2] for i in range(0, 12, 2)
        ).upper()
    return None


def get_hdd_serial():
    """获取硬盘序列号（Windows专用）"""
    system = platform.system()

    if system == "Windows":
        try:
            result = subprocess.run(
                ['wmic', 'diskdrive', 'get', 'SerialNumber'],
                capture_output=True, text=True, timeout=10
            )
            lines = result.stdout.strip().split('\n')
            for line in lines:
                if line.strip() and line.strip() != 'SerialNumber':
                    return line.strip()
        except Exception:
            pass

    return None


def generate_machine_code():
    """生成机器码"""
    components = []

    # 收集硬件信息
    cpu_id = get_cpu_id()
    board_id = get_board_id()
    mac_addr = get_mac_address()
    hdd_serial = get_hdd_serial()

    # 添加到组件列表（非空则添加）
    if cpu_id:
        components.append(f"CPU:{cpu_id}")
    if board_id:
        components.append(f"BOARD:{board_id}")
    if mac_addr:
        components.append(f"MAC:{mac_addr}")
    if hdd_serial:
        components.append(f"HDD:{hdd_serial}")

    if not components:
        # 兜底：使用主机名+用户目录（与GUI端一致，保证总能生成机器码）
        raw = f"HOST:{platform.node()}|USER:{os.path.expanduser('~')}"
        components.append(f"FALLBACK:{platform.node()}")

    # 组合并生成机器码
    raw_string = "|".join(components)

    # 使用SHA256生成机器码
    hash_obj = hashlib.sha256(raw_string.encode('utf-8'))
    machine_code = hash_obj.hexdigest().upper()

    # 格式化为易读的机器码格式
    formatted_code = format_machine_code(machine_code)

    return formatted_code, components


def format_machine_code(full_hash):
    """将哈希值格式化为易读的机器码"""
    # 取前32位，分成4组
    code_part = full_hash[:32]
    groups = [code_part[i:i+4] for i in range(0, 16, 4)]
    return "-".join(groups)


def main():
    print("=" * 60)
    print("PDF转换器 - 机器码提取工具")
    print("=" * 60)
    print()

    print("正在提取硬件信息...")
    machine_code, components = generate_machine_code()

    print()
    print("已检测到的硬件组件:")
    for comp in components:
        print(f"  ✓ {comp}")
    print()
    print("=" * 60)
    print("您的机器码:")
    print(f"  {machine_code}")
    print("=" * 60)
    print()
    print("请将此机器码发送给开发者以获取注册许可码。")
    print("机器码是唯一的，请勿分享。")


if __name__ == '__main__':
    main()
