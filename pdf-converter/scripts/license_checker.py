#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF转换器注册验证模块
集成到转换流程中，验证注册状态并使用计数
"""

import os
import sys
import json
from datetime import datetime


class PDFConverterLicense:
    """PDF转换器许可验证"""

    def __init__(self, config_dir=None):
        """初始化许可验证器"""
        if config_dir is None:
            config_dir = os.path.join(os.path.expanduser("~"), ".pdf_converter")

        self.config_dir = config_dir
        self.config_file = os.path.join(config_dir, "license_config.json")
        self.license_file = os.path.join(config_dir, "license.json")
        self.usage_file = os.path.join(config_dir, "usage.json")

        # 默认配置
        self.default_config = {
            "version": "1.0.0",
            "max_files_per_license": 20,
            "license_prefix": "PDF",
            "developer_key": "PDFConverter2026_SecretKey_v1.0"
        }

    def init(self):
        """初始化配置文件"""
        os.makedirs(self.config_dir, exist_ok=True)
        if not os.path.exists(self.config_file):
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.default_config, f, indent=2)

    def save_license(self, license_info):
        """保存许可信息"""
        with open(self.license_file, 'w', encoding='utf-8') as f:
            json.dump(license_info, f, indent=2)

    def save_usage(self, usage_data):
        """保存使用记录"""
        with open(self.usage_file, 'w', encoding='utf-8') as f:
            json.dump(usage_data, f, indent=2)

    def load_license(self):
        """加载许可信息"""
        if os.path.exists(self.license_file):
            with open(self.license_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return None

    def load_usage(self):
        """加载使用记录"""
        if os.path.exists(self.usage_file):
            with open(self.usage_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {"total_files": 0, "files": [], "last_reset": None}

    def is_registered(self):
        """检查是否已注册"""
        return os.path.exists(self.license_file)

    def get_license_info(self):
        """获取许可信息"""
        return self.load_license()

    def get_usage(self):
        """获取使用统计"""
        usage = self.load_usage()
        config = self.get_config()
        limit = config.get("max_files_per_license", 20)
        used = usage.get("total_files", 0)

        license_info = self.get_license_info()
        machine_code = license_info.get("machine_code", "未知") if license_info else "未知"

        return {
            "total_files": used,
            "files": usage.get("files", []),
            "last_reset": usage.get("last_reset"),
            "limit": limit,
            "files_used": used,
            "files_remaining": max(0, limit - used),
            "machine_code": machine_code
        }

    def get_config(self):
        """获取配置"""
        if os.path.exists(self.config_file):
            with open(self.config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return self.default_config.copy()

    def register(self, machine_code, license_code):
        """
        注册用户许可

        参数:
            machine_code: 机器码
            license_code: 许可码

        返回:
            (成功标志, 消息)
        """

        # 导入许可码生成模块进行验证
        script_dir = os.path.dirname(os.path.abspath(__file__))
        licensing_path = os.path.join(script_dir, '..', '..', 'licensing', 'scripts')
        licensing_path = os.path.abspath(licensing_path)

        if licensing_path not in sys.path:
            sys.path.insert(0, licensing_path)

        try:
            from generate_license import verify_license_code
        except ImportError:
            # 本地验证逻辑
            return self._local_verify(machine_code, license_code)

        is_valid, message = verify_license_code(license_code, machine_code)

        if not is_valid:
            return False, message

        # 检查是否已注册
        existing = self.get_license_info()
        if existing:
            if existing.get('machine_code') == machine_code:
                return False, "此机器已注册，无需重复注册"
            else:
                return False, f"此许可码已注册到另一台机器"

        # 保存许可信息
        license_info = {
            "machine_code": machine_code,
            "license_code": license_code,
            "registered_at": datetime.now().isoformat(),
            "status": "active"
        }

        self.save_license(license_info)

        # 初始化使用记录
        usage = {"total_files": 0, "files": [], "last_reset": None}
        self.save_usage(usage)

        return True, "注册成功！您现在可以转换20个文件。"

    def _local_verify(self, machine_code, license_code):
        """本地验证许可码（备用方案）：用开发者密钥做 HMAC 校验，避免绕过后放行"""
        import re
        import hmac
        import hashlib

        config = self.get_config()
        secret = config.get("developer_key", "PDFConverter2026_SecretKey_v1.0")

        if not re.match(r'^[A-F0-9]{4}-[A-F0-9]{4}-[A-F0-9]{4}-[A-F0-9]{4}$',
                        machine_code.upper()):
            return False, "机器码格式无效"
        if not re.match(r'^PDF-[A-F0-9]{8}-\d{4}-[A-F0-9]{8}$',
                        license_code.upper()):
            return False, "许可码格式无效"

        m = re.match(r'^PDF-([A-F0-9]{8})-(\d{4})-([A-F0-9]{8})$',
                     license_code.upper())
        machine_prefix = machine_code.replace('-', '').upper()[:8]
        if m.group(1) != machine_prefix:
            return False, "许可码与机器码不匹配"

        message = f"PDF-{machine_prefix}-{m.group(2)}"
        expected = hmac.new(secret.encode('utf-8'),
                            message.encode('utf-8'),
                            hashlib.sha256).hexdigest()[:8].upper()
        if m.group(3) == expected:
            return True, "许可码有效（本地验证）"
        return False, "许可码校验失败"

    def check_and_increment(self, filename):
        """
        检查注册状态并增加使用计数

        参数:
            filename: 处理的文件名

        返回:
            (允许转换, 消息)
        """
        # 检查是否注册
        if not self.is_registered():
            return False, "请先注册PDF转换器\n\n" + \
                         "注册方法:\n" + \
                         "  1. 运行: python get_machine_code.py 获取机器码\n" + \
                         "  2. 联系开发者获取许可码\n" + \
                         "  3. 运行: python register.py --register <机器码> <许可码>"

        # 检查配额
        usage = self.get_usage()
        config = self.get_config()
        limit = config.get("max_files_per_license", 20)
        used = usage.get("total_files", 0)

        if used >= limit:
            return False, f"已用完配额 ({used}/{limit})\n\n" + \
                         "请联系开发者获取新的许可码。"

        # 增加使用计数
        usage["total_files"] = used + 1
        usage["files"].append({
            "filename": filename,
            "timestamp": datetime.now().isoformat()
        })

        self.save_usage(usage)

        remaining = limit - usage["total_files"]
        return True, f"转换成功！剩余配额: {remaining} 个文件"

    def check_conversion_allowed(self, filename):
        """
        检查是否允许转换（不扣除配额）

        参数:
            filename: 处理的文件名

        返回:
            (是否允许, 消息)
        """
        if not self.is_registered():
            return False, "请先注册PDF转换器\n\n" + \
                         "注册方法:\n" + \
                         "  1. 运行: python get_machine_code.py 获取机器码\n" + \
                         "  2. 联系开发者获取许可码\n" + \
                         "  3. 运行: python register.py --register <机器码> <许可码>"

        usage = self.get_usage()
        config = self.get_config()
        limit = config.get("max_files_per_license", 20)
        used = usage.get("total_files", 0)

        if used >= limit:
            return False, f"已用完配额 ({used}/{limit})\n\n" + \
                         "请联系开发者获取新的许可码。"

        return True, f"可以转换，剩余配额: {limit - used} 个文件"

    def show_status(self):
        """显示注册状态"""
        print("=" * 60)
        print("PDF转换器 - 注册状态")
        print("=" * 60)

        if self.is_registered():
            usage = self.get_usage()
            print(f"\n✓ 已注册")
            print(f"  机器码:   {usage['machine_code']}")
            print(f"  已使用:   {usage['files_used']} / {usage['limit']} 个文件")
            print(f"  剩余配额: {usage['files_remaining']} 个文件")
        else:
            print(f"\n✗ 未注册")
            print(f"\n请先完成注册:")
            print(f"  1. python get_machine_code.py")
            print(f"  2. 联系开发者获取许可码")
            print(f"  3. python converter.py --register <机器码> <许可码>")

        print("=" * 60)


def check_conversion_allowed(filename):
    """
    检查是否允许转换（供转换脚本调用）

    参数:
        filename: 处理的文件名

    返回:
        (是否允许, 消息)
    """
    license_checker = PDFConverterLicense()
    return license_checker.check_and_increment(filename)


def get_registration_status():
    """获取注册状态（供展示使用）"""
    license_checker = PDFConverterLicense()
    return license_checker.show_status()


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='PDF转换器许可验证')
    parser.add_argument('--register', '-r', nargs=2, metavar=('MACHINE', 'LICENSE'),
                       help='注册: --register <机器码> <许可码>')
    parser.add_argument('--status', '-s', action='store_true',
                       help='查看注册状态')
    parser.add_argument('--check', '-c', metavar='FILENAME',
                       help='检查单个文件转换权限')

    args = parser.parse_args()

    checker = PDFConverterLicense()
    checker.init()

    if args.register:
        machine_code, license_code = args.register
        success, message = checker.register(machine_code, license_code)
        print(message)
        sys.exit(0 if success else 1)

    elif args.status:
        checker.show_status()

    elif args.check:
        allowed, message = checker.check_and_increment(args.check)
        print(message)
        sys.exit(0 if allowed else 1)

    else:
        parser.print_help()
