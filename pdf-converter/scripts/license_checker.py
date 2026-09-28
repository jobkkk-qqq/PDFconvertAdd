#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF转换器注册验证模块（Ed25519 非对称验签版）

许可码格式（与 PrintShare 通用）：
    PDF-{机器码前8位}-{序列号4位}-{Base32签名}
例：PDF-56BA91C4-0001-67LTR5...

签名算法 Ed25519（RFC 8032），程序内只内置**公钥**——只能验签、不能造码。

注意：打包成 exe 后 licensing/ 目录不会随包分发，所以本模块**不依赖**任何外部
许可模块，验签所需的公钥与 ed25519.py 都在本目录内自带（见同目录 ed25519.py）。
"""

import os
import sys
import json
import base64
from datetime import datetime

# 同目录自带的纯标准库 Ed25519（打包时需一并打进 scripts/）
try:
    from ed25519 import verify as _ed25519_verify
except ImportError:  # 极端情况下的兜底：宁可验不过，也不放行
    _ed25519_verify = None

# 公钥：公开无妨（只能验签）。与 PrintShare 内置的是同一把。
PUBLIC_KEY_HEX = "324B31ED07C4C8772BAD3D5DDAE01F907D9226921C64D928F6D298780A8804C0"
LICENSE_PREFIX = "PDF"


def _b32_decode(s):
    pad = (8 - len(s) % 8) % 8
    return base64.b32decode(s + "=" * pad)


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

        # 默认配置：**不再包含任何签名密钥**（改用非对称签名后，客户端只需要公钥）
        self.default_config = {
            "version": "2.0.0",
            "max_files_per_license": 20,
            "license_prefix": LICENSE_PREFIX,
        }

    # ---------------- 配置 / 文件 ----------------

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

    def get_config(self):
        """获取配置（兼容旧配置文件：忽略其中可能残留的 developer_key）"""
        if os.path.exists(self.config_file):
            with open(self.config_file, 'r', encoding='utf-8') as f:
                cfg = json.load(f)
            if not isinstance(cfg, dict):
                return self.default_config.copy()
            # 旧的 developer_key 字段已废弃，不再使用
            cfg.pop("developer_key", None)
            return cfg
        return self.default_config.copy()

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
            "machine_code": machine_code,
        }

    # ---------------- 许可码验签 ----------------

    @staticmethod
    def parse_license_code(license_code):
        """解析许可码；格式不对返回 None"""
        if not license_code:
            return None
        parts = str(license_code).strip().upper().split("-")
        if len(parts) != 4 or parts[0] != LICENSE_PREFIX:
            return None
        _, mp, serial_str, sig32 = parts
        if len(mp) != 8 or any(c not in "0123456789ABCDEF" for c in mp):
            return None
        if len(serial_str) != 4 or not serial_str.isdigit():
            return None
        return {"machine_prefix": mp, "serial": int(serial_str), "sig32": sig32}

    @staticmethod
    def validate_machine_code(machine_code):
        """机器码格式：XXXX-XXXX-XXXX-XXXX"""
        if not machine_code:
            return False
        code = str(machine_code).strip().upper()
        if len(code) != 19:
            return False
        parts = code.split("-")
        if len(parts) != 4:
            return False
        return all(len(p) == 4 and all(c in "0123456789ABCDEF" for c in p) for p in parts)

    def verify_code(self, license_code, machine_code):
        """用内置公钥验签。返回 (是否有效, 说明)。自包含，不依赖外部许可模块。"""
        if _ed25519_verify is None:
            return False, "验签模块缺失（ed25519.py 未随程序分发），无法注册"
        parsed = self.parse_license_code(license_code)
        if not parsed:
            return False, "许可码格式无效"
        if not self.validate_machine_code(machine_code):
            return False, "机器码格式无效"
        mp = str(machine_code).strip().upper().replace("-", "")[:8]
        if parsed["machine_prefix"] != mp:
            return False, "许可码与机器码不匹配"
        try:
            sig = _b32_decode(parsed["sig32"])
        except Exception:
            return False, "许可码格式无效"
        if len(sig) != 64:
            return False, "许可码格式无效"
        # 用许可码内嵌的序列号重算被签消息，因此天然支持续期（序列号 >= 2）
        msg = ("%s-%s-%04d" % (LICENSE_PREFIX, mp, parsed["serial"])).encode("utf-8")
        try:
            ok = _ed25519_verify(sig, msg, bytes.fromhex(PUBLIC_KEY_HEX))
        except Exception:
            ok = False
        if ok:
            return True, "许可码有效"
        return False, "许可码校验失败（签名不对，可能伪造或输错）"

    # ---------------- 注册 / 续期 ----------------

    def register(self, machine_code, license_code):
        """
        注册 / 续期许可。

        参数:
            machine_code: 机器码
            license_code: 许可码

        返回:
            (成功标志, 消息)

        续期规则：同一台机器必须用**序列号更大**的新许可码，旧码不能重复使用。
        （旧版本会直接拒绝"已注册机器"，导致过期后无法续期，这里已修正。）
        """
        machine_code = str(machine_code).strip().upper()
        license_code = str(license_code).strip().upper()

        is_valid, message = self.verify_code(license_code, machine_code)
        if not is_valid:
            return False, message

        parsed = self.parse_license_code(license_code)
        serial = parsed["serial"]

        existing = self.get_license_info()
        prev_serial = 0
        if existing:
            if existing.get('machine_code') != machine_code:
                return False, "此许可码已注册到另一台机器"
            prev_serial = int(existing.get('max_serial') or 0)
            if not prev_serial:
                old = self.parse_license_code(existing.get('license_code', ''))
                prev_serial = old["serial"] if old else 0
            if serial <= prev_serial:
                return False, (
                    "这是第 %d 次授权，本机已用到第 %d 次。"
                    "请使用序列号大于 %d 的新许可码续期" % (serial, prev_serial, prev_serial)
                )

        limit = self.get_config().get("max_files_per_license", 20)
        license_info = {
            "machine_code": machine_code,
            "license_code": license_code,
            "serial": serial,
            "max_serial": max(serial, prev_serial),
            "registered_at": datetime.now().isoformat(),
            "status": "active",
        }
        self.save_license(license_info)

        # 换了新授权，计数归零（新的一份 20 个名额）
        usage = {"total_files": 0, "files": [], "last_reset": None}
        self.save_usage(usage)

        return True, "注册成功！本次授权可转换 %d 个文件（第 %d 次授权）。" % (limit, serial)

    # ---------------- 配额 ----------------

    def _not_registered_msg(self):
        return (
            "请先注册PDF转换器\n\n"
            "注册方法:\n"
            "  1. 获取机器码: python licensing/scripts/get_machine_code.py\n"
            "  2. 联系开发者获取许可码\n"
            "  3. 注册: python converter.py --register <机器码> <许可码>"
        )

    def check_and_increment(self, filename):
        """检查注册状态并增加使用计数。返回 (允许转换, 消息)"""
        if not self.is_registered():
            return False, self._not_registered_msg()

        usage = self.get_usage()
        config = self.get_config()
        limit = config.get("max_files_per_license", 20)
        used = usage.get("total_files", 0)

        if used >= limit:
            return False, (
                "已用完配额 (%d/%d)\n\n请联系开发者获取序列号更大的新许可码续期。" % (used, limit)
            )

        usage["total_files"] = used + 1
        usage["files"].append({"filename": filename, "timestamp": datetime.now().isoformat()})
        self.save_usage(usage)

        remaining = limit - usage["total_files"]
        return True, "转换成功！剩余配额: %d 个文件" % remaining

    def check_conversion_allowed(self, filename):
        """检查是否允许转换（不扣除配额）。返回 (是否允许, 消息)"""
        if not self.is_registered():
            return False, self._not_registered_msg()

        usage = self.get_usage()
        config = self.get_config()
        limit = config.get("max_files_per_license", 20)
        used = usage.get("total_files", 0)

        if used >= limit:
            return False, (
                "已用完配额 (%d/%d)\n\n请联系开发者获取序列号更大的新许可码续期。" % (used, limit)
            )

        return True, "可以转换，剩余配额: %d 个文件" % (limit - used)

    def show_status(self):
        """显示注册状态"""
        print("=" * 60)
        print("PDF转换器 - 注册状态")
        print("=" * 60)

        if self.is_registered():
            usage = self.get_usage()
            info = self.get_license_info() or {}
            print("\n✓ 已注册")
            print("  机器码:   %s" % usage['machine_code'])
            print("  第几次授权: %s" % info.get('serial', '未知'))
            print("  已使用:   %s / %s 个文件" % (usage['files_used'], usage['limit']))
            print("  剩余配额: %s 个文件" % usage['files_remaining'])
        else:
            print("\n✗ 未注册")
            print("\n请先完成注册:")
            print("  1. python licensing/scripts/get_machine_code.py   (获取机器码)")
            print("  2. 联系开发者获取许可码")
            print("  3. python converter.py --register <机器码> <许可码>")

        print("=" * 60)


def check_conversion_allowed(filename):
    """检查是否允许转换（供转换脚本调用）"""
    return PDFConverterLicense().check_and_increment(filename)


def get_registration_status():
    """获取注册状态（供展示使用）"""
    return PDFConverterLicense().show_status()


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='PDF转换器许可验证')
    parser.add_argument('--register', '-r', nargs=2, metavar=('MACHINE', 'LICENSE'),
                        help='注册: --register <机器码> <许可码>')
    parser.add_argument('--status', '-s', action='store_true', help='查看注册状态')
    parser.add_argument('--check', '-c', metavar='FILENAME', help='检查单个文件转换权限')

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
