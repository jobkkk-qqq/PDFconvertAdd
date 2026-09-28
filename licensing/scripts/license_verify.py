#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""许可码验签（只读）—— 用户端 / 客户端使用。

本模块**只有公钥**，只能验签、**造不出**许可码：
签名用的 Ed25519 私钥只在开发者发码端（放在仓库外，见仓库上一级的 `license-keys/`），
所以本仓库及其打包产物里都不含任何生成注册码的能力。

许可码格式：
    PDF-{机器码前8位}-{序列号4位}-{签名Base32}
例：PDF-ABCD1234-0001-<103 个字符的 Base32 签名>（整串约 121 字符，必须完整复制）

- 被签名内容：UTF-8 字符串 `PDF-{机器码前8位}-{序列号4位}`
- Ed25519 签名固定 64 字节，**不能截断**，Base32 编码后 103 字符
- 验签时用许可码内嵌的序列号重算被签消息，因此天然支持续期（序列号 >= 2）
"""

import base64
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ed25519  # noqa: E402


LICENSE_PREFIX = "PDF"
# 公钥：公开无妨，它只能验签、不能造码。客户端与发码端内置同一把公钥。
PUBLIC_KEY_HEX = "324B31ED07C4C8772BAD3D5DDAE01F907D9226921C64D928F6D298780A8804C0"
# 本产品配额：每次授权 20 份
MAX_FILE_LIMIT = 20


def _public_key_bytes():
    return bytes.fromhex(PUBLIC_KEY_HEX)


def validate_machine_code(machine_code):
    """机器码格式：XXXX-XXXX-XXXX-XXXX（每段 4 位十六进制）"""
    if not machine_code:
        return False
    code = str(machine_code).strip().upper()
    if len(code) != 19:
        return False
    parts = code.split("-")
    if len(parts) != 4:
        return False
    for p in parts:
        if len(p) != 4 or any(c not in "0123456789ABCDEF" for c in p):
            return False
    return True


def _machine_prefix(machine_code):
    return str(machine_code).strip().upper().replace("-", "")[:8]


def _message(machine_prefix, serial_number):
    return "%s-%s-%04d" % (LICENSE_PREFIX, machine_prefix, int(serial_number))


def _b32_decode(s):
    pad = (8 - len(s) % 8) % 8
    return base64.b32decode(s + "=" * pad)


def verify_license_code(license_code, machine_code):
    """用内置公钥验签。返回 (是否有效, 说明)。"""
    if not license_code or not str(license_code).strip():
        return False, "许可码为空"
    parts = str(license_code).strip().upper().split("-")
    if len(parts) != 4 or parts[0] != LICENSE_PREFIX:
        return False, "许可码格式无效"
    _, mp, serial_str, sig32 = parts
    if len(mp) != 8 or any(c not in "0123456789ABCDEF" for c in mp):
        return False, "许可码格式无效"
    if len(serial_str) != 4 or not serial_str.isdigit():
        return False, "许可码格式无效"
    try:
        sig = _b32_decode(sig32)
    except Exception:
        return False, "许可码格式无效"
    if len(sig) != 64:
        return False, "许可码格式无效"

    if not validate_machine_code(machine_code):
        return False, "机器码格式无效"
    if mp != _machine_prefix(machine_code):
        return False, "许可码与机器码不匹配"

    # 用许可码里内嵌的序列号重算被签名的消息，因此天然支持续期（序列号 >= 2）
    msg = _message(mp, int(serial_str)).encode("utf-8")
    if ed25519.verify(sig, msg, _public_key_bytes()):
        return True, "许可码有效"
    return False, "许可码校验失败（签名不对，可能伪造或输错）"


def get_license_info(license_code):
    """从许可码中提取信息（不校验签名）"""
    if not license_code:
        return None
    parts = str(license_code).strip().upper().split("-")
    if len(parts) != 4 or parts[0] != LICENSE_PREFIX:
        return None
    _, mp, serial_str, sig32 = parts
    if not serial_str.isdigit():
        return None
    return {
        "machine_prefix": mp,
        "serial_number": int(serial_str),
        "signature": sig32,
        "max_files": MAX_FILE_LIMIT,
    }
