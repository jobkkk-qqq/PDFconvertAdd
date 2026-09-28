#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
注册管理器
管理用户注册状态、许可验证和文件计数
"""

import os
import json
import hashlib
from datetime import datetime


class LicenseManager:
    """许可管理器"""

    def __init__(self, config_dir=None):
        """初始化许可管理器"""
        if config_dir is None:
            config_dir = os.path.join(os.path.expanduser("~"), ".pdf_converter")

        self.config_dir = config_dir
        self.config_file = os.path.join(config_dir, "license_config.json")
        self.license_file = os.path.join(config_dir, "license.json")
        self.usage_file = os.path.join(config_dir, "usage.json")

        # 确保配置目录存在
        os.makedirs(config_dir, exist_ok=True)

        # 默认配置：改用 Ed25519 非对称验签后，客户端**不再需要任何签名密钥**
        self.default_config = {
            "version": "2.0.0",
            "max_files_per_license": 20,
            "license_prefix": "PDF",
        }

    def init_config(self):
        """初始化配置文件"""
        if not os.path.exists(self.config_file):
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.default_config, f, indent=2)
            return True
        return False

    def load_config(self):
        """加载配置（丢弃旧文件里残留的对称密钥字段）"""
        if os.path.exists(self.config_file):
            with open(self.config_file, 'r', encoding='utf-8') as f:
                cfg = json.load(f)
            if isinstance(cfg, dict):
                cfg.pop("developer_key", None)
                return cfg
        return self.default_config.copy()

    def save_config(self, config):
        """保存配置"""
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2)

    def load_license(self):
        """加载许可信息"""
        if os.path.exists(self.license_file):
            with open(self.license_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return None

    def save_license(self, license_data):
        """保存许可信息"""
        with open(self.license_file, 'w', encoding='utf-8') as f:
            json.dump(license_data, f, indent=2)

    def load_usage(self):
        """加载使用记录"""
        if os.path.exists(self.usage_file):
            with open(self.usage_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {"total_files": 0, "files": [], "last_reset": None}

    def save_usage(self, usage_data):
        """保存使用记录"""
        with open(self.usage_file, 'w', encoding='utf-8') as f:
            json.dump(usage_data, f, indent=2)

    def register(self, machine_code, license_code):
        """
        注册 / 续期许可

        参数:
            machine_code: 机器码
            license_code: 许可码

        返回:
            (成功标志, 消息)

        续期规则：同一台机器必须用**序列号更大**的新许可码，旧码不能重复使用。
        （旧版本直接拒绝"已注册机器"，导致过期后无法续期，这里已修正。）
        """
        # 验证许可码（复用只读验签模块，本仓库不含发码能力）
        from license_verify import verify_license_code, get_license_info

        machine_code = str(machine_code).strip().upper()
        license_code = str(license_code).strip().upper()

        is_valid, message = verify_license_code(license_code, machine_code)
        if not is_valid:
            return False, message

        info = get_license_info(license_code) or {}
        serial = int(info.get("serial_number") or 0)

        # 加载现有许可：同机续期要求序列号递增
        existing_license = self.load_license()
        prev_serial = 0
        if existing_license:
            if existing_license.get('machine_code') != machine_code:
                return False, "此许可码已注册到另一台机器 (机器码: %s)" % existing_license.get('machine_code')
            prev_serial = int(existing_license.get('max_serial') or 0)
            if not prev_serial:
                old = get_license_info(existing_license.get('license_code', '')) or {}
                prev_serial = int(old.get("serial_number") or 0)
            if serial <= prev_serial:
                return False, (
                    "这是第 %d 次授权，本机已用到第 %d 次。"
                    "请使用序列号大于 %d 的新许可码续期" % (serial, prev_serial, prev_serial)
                )

        limit = self.load_config().get("max_files_per_license", 20)
        license_info = {
            "machine_code": machine_code,
            "license_code": license_code,
            "serial": serial,
            "max_serial": max(serial, prev_serial),
            "registered_at": datetime.now().isoformat(),
            "status": "active",
        }

        self.save_license(license_info)

        # 换了新授权，计数归零（新的一份名额）
        self.save_usage({"total_files": 0, "files": [], "last_reset": None})

        return True, "注册成功！本次授权可转换 %d 个文件（第 %d 次授权）。" % (limit, serial)

    def check_license(self):
        """
        检查当前许可状态

        返回:
            (是否已注册, 许可信息)
        """
        license_info = self.load_license()
        if license_info:
            return True, license_info
        return False, None

    def get_usage(self):
        """获取使用统计"""
        usage = self.load_usage()
        license_info = self.load_license()

        if not license_info:
            return {
                "registered": False,
                "files_used": 0,
                "files_remaining": 0,
                "limit": 20
            }

        config = self.load_config()
        limit = config.get("max_files_per_license", 20)

        return {
            "registered": True,
            "machine_code": license_info.get("machine_code"),
            "files_used": usage.get("total_files", 0),
            "files_remaining": max(0, limit - usage.get("total_files", 0)),
            "limit": limit,
            "registered_at": license_info.get("registered_at")
        }

    def increment_usage(self, filename):
        """
        增加使用计数

        参数:
            filename: 文件名

        返回:
            (成功标志, 消息)
        """
        # 检查是否已注册
        registered, license_info = self.check_license()
        if not registered:
            return False, "未注册，请先注册"

        # 检查是否还有配额
        usage = self.load_usage()
        limit = self.load_config().get("max_files_per_license", 20)

        if usage.get("total_files", 0) >= limit:
            return False, f"已用完配额 ({limit}/{limit})，请联系开发者获取新许可码"

        # 更新使用记录
        usage["total_files"] = usage.get("total_files", 0) + 1
        usage["files"].append({
            "filename": filename,
            "timestamp": datetime.now().isoformat()
        })

        self.save_usage(usage)

        remaining = limit - usage["total_files"]
        return True, f"转换成功！剩余配额: {remaining} 个文件"

    def show_status(self):
        """显示注册状态和使用情况"""
        registered, license_info = self.check_license()

        print("=" * 60)
        print("PDF转换器 - 注册状态")
        print("=" * 60)

        if registered:
            usage = self.get_usage()
            print(f"\n✓ 已注册")
            print(f"  机器码:   {usage['machine_code']}")
            print(f"  注册时间: {usage.get('registered_at', '未知')}")
            print(f"  已使用:   {usage['files_used']} / {usage['limit']} 个文件")
            print(f"  剩余配额: {usage['files_remaining']} 个文件")
        else:
            print(f"\n✗ 未注册")
            print(f"\n请先运行注册流程:")
            print(f"  1. 获取机器码: python get_machine_code.py")
            print(f"  2. 联系开发者获取许可码")
            print(f"  3. 注册: python register.py --machine <机器码> --license <许可码>")

        print("=" * 60)

    def reset_usage(self):
        """重置使用计数（仅用于测试）"""
        if not os.path.exists(self.license_file):
            return False, "未注册，无法重置"

        # 清空使用记录
        usage = {
            "total_files": 0,
            "files": [],
            "last_reset": datetime.now().isoformat()
        }
        self.save_usage(usage)

        return True, "使用计数已重置"


def main():
    import argparse

    parser = argparse.ArgumentParser(description='PDF转换器注册管理')
    parser.add_argument('--register', '-r', nargs=2, metavar=('MACHINE', 'LICENSE'),
                       help='注册: --register <机器码> <许可码>')
    parser.add_argument('--status', '-s', action='store_true',
                       help='查看注册状态')
    parser.add_argument('--usage', '-u', action='store_true',
                       help='查看使用统计')
    parser.add_argument('--reset', action='store_true',
                       help='重置使用计数（仅用于测试）')
    parser.add_argument('--filename', '-f', help='记录转换的文件名')

    args = parser.parse_args()

    manager = LicenseManager()
    manager.init_config()

    if args.register:
        machine_code, license_code = args.register
        success, message = manager.register(machine_code, license_code)
        print(message)
        sys.exit(0 if success else 1)

    elif args.status or args.usage:
        manager.show_status()
        if args.usage:
            usage = manager.get_usage()
            print(f"\n详细使用统计:")
            print(f"  已转换文件数: {usage['files_used']}")
            print(f"  剩余配额:     {usage['files_remaining']}")
            print(f"  总配额:       {usage['limit']}")

    elif args.reset:
        success, message = manager.reset_usage()
        print(message)

    elif args.filename:
        # 增加使用计数
        success, message = manager.increment_usage(args.filename)
        print(message)
        sys.exit(0 if success else 1)

    else:
        parser.print_help()


if __name__ == '__main__':
    import sys
    main()
