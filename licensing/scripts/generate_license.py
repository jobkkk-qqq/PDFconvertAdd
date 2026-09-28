#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
许可码生成 / 验证工具（开发者使用）—— Ed25519 非对称签名版

许可码格式（与 PrintShare 通用，两边可互发互认）：
    PDF-{机器码前8位}-{序列号4位}-{签名Base32}
例：PDF-ABCD1234-0001-<103 个字符的 Base32 签名>

为什么改用非对称：原来用对称 HMAC，验签密钥必须随程序分发给用户，
等于把"生成器"交到用户手里。现在程序里只内置**公钥**（只能验签），
签名用的**私钥**只在开发者本机的密钥文件里，永不入库、永不进 exe。

关于长度：Ed25519 签名固定 64 字节，必须完整保留才能验签（不能截断），
Base32 编码后 103 字符，所以整串注册码约 121 字符——比原来的 8 字符长得多，
但这是非对称签名的固有代价。用户复制粘贴即可，不需要手输。

私钥查找顺序（第一个存在的即用）：
    1. 环境变量 LICENSE_PRIVATE_KEY 指定的文件
    2. 锚点目录（源码运行=仓库根；打包后=exe 所在目录）及其所有上级目录下的
       `license-private-key.json`，或这些目录下 `license-keys/license-private-key.json`
    3. ~/.license-keys/private-key.json
密钥文件可以是本仓库工具生成的 JSON（含 privateSeedHex），
也可以是一行 64 位十六进制的私钥种子。
"""

import base64
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ed25519  # noqa: E402


LICENSE_PREFIX = "PDF"
# 公钥：公开无妨，它只能验签、不能造码。两个程序内置同一个公钥。
PUBLIC_KEY_HEX = "324B31ED07C4C8772BAD3D5DDAE01F907D9226921C64D928F6D298780A8804C0"
# 本产品配额：每次授权 20 份（PDFconvertAdd 的既有政策，未改动）
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


def _b32_nopad(raw):
    return base64.b32encode(raw).decode("ascii").rstrip("=")


def _b32_decode(s):
    pad = (8 - len(s) % 8) % 8
    return base64.b32decode(s + "=" * pad)


# ---------------- 私钥（仅生成端使用） ----------------

def _search_roots():
    """私钥搜索的锚点目录。

    源码运行时锚点是仓库根；**打包成 exe 后** `__file__` 指向 PyInstaller
    的临时解包目录（_MEIxxxx），一切相对路径都会失效，必须改用 exe 自身
    所在目录，才能找到 exe 旁边的私钥，或上层目录里的 license-keys。
    """
    roots = []
    if getattr(sys, "frozen", False):
        try:
            roots.append(os.path.dirname(os.path.abspath(sys.executable)))
        except Exception:
            pass
    else:
        here = os.path.dirname(os.path.abspath(__file__))
        roots.append(os.path.dirname(os.path.dirname(here)))

    out = []
    for r in roots:
        cur = os.path.abspath(r)
        for _ in range(16):  # 锚点自身 + 一路向上直到盘符根目录
            if cur and cur not in out:
                out.append(cur)
            parent = os.path.dirname(cur)
            if parent == cur:
                break
            cur = parent
    return out


def _candidate_key_paths():
    cands = []
    env = os.environ.get("LICENSE_PRIVATE_KEY")
    if env:
        cands.append(env)
    for root in _search_roots():
        # 私钥直接放在该目录下，或放在该目录的 license-keys/ 子目录里
        cands.append(os.path.join(root, "license-private-key.json"))
        cands.append(os.path.join(root, "license-keys", "license-private-key.json"))
    cands.append(os.path.join(os.path.expanduser("~"), ".license-keys", "private-key.json"))
    # 去重且保序
    seen = set()
    uniq = []
    for c in cands:
        if c and c not in seen:
            seen.add(c)
            uniq.append(c)
    return uniq


def _read_seed_file(path):
    """从单个文件里解析出 32 字节私钥种子；解析不了就返回 None。"""
    if not path or not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            raw = f.read().strip()
    except OSError:
        return None
    seed = None
    if raw.startswith("{"):
        try:
            seed = bytes.fromhex(json.loads(raw)["privateSeedHex"].strip())
        except Exception:
            seed = None
    elif len(raw) == 64:
        try:
            seed = bytes.fromhex(raw)
        except ValueError:
            seed = None
    return seed if seed and len(seed) == 32 else None


def find_private_key_path():
    """返回第一个可用的私钥文件路径；找不到返回 None（用于日志/排查）。"""
    for p in _candidate_key_paths():
        if _read_seed_file(p):
            return p
    return None


def load_private_seed(path=None):
    """读取 32 字节私钥种子；找不到就抛出带指引的错误。"""
    if path:
        seed = _read_seed_file(path)
        if seed:
            return seed
    else:
        for p in _candidate_key_paths():
            seed = _read_seed_file(p)
            if seed:
                return seed
    raise RuntimeError(
        "找不到私钥。请把私钥文件放到下列任一位置，或用环境变量指定：\n"
        "  - 环境变量 LICENSE_PRIVATE_KEY=<私钥文件路径>\n"
        "  - 发码工具 exe 同级目录 / 其上级目录下的 license-private-key.json\n"
        "  - 发码工具 exe 同级目录 / 其上级目录下的 license-keys/license-private-key.json\n"
        "  - <仓库根>/license-private-key.json\n"
        "  - <仓库根>/../license-keys/license-private-key.json\n"
        "  - ~/.license-keys/private-key.json"
    )


# ---------------- 生成 / 验证 ----------------

def generate_license_code(machine_code, serial_number=1, private_seed=None):
    """生成许可码。序列号用于续期：同一台机器每次续期都要用更大的序列号。"""
    if not validate_machine_code(machine_code):
        raise ValueError("无效的机器码格式: %s" % machine_code)
    serial_number = int(serial_number)
    if serial_number < 1 or serial_number > 9999:
        raise ValueError("序列号必须是 1..9999 之间的整数")
    if private_seed is None:
        private_seed = load_private_seed()
    prefix = _machine_prefix(machine_code)
    sig = ed25519.sign(_message(prefix, serial_number).encode("utf-8"), private_seed)
    return "%s-%s-%04d-%s" % (LICENSE_PREFIX, prefix, serial_number, _b32_nopad(sig))


def verify_license_code(license_code, machine_code):
    """验证许可码是否为本机有效码（用内置公钥验签）。返回 (是否有效, 说明)。"""
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


def _print_license(machine_code, serial, license_code):
    print("=" * 60)
    print("PDF转换器 - 许可码生成工具（Ed25519）")
    print("=" * 60)
    print()
    print("机器码:   %s" % machine_code)
    print("序列号:   %s" % serial)
    print("文件限制: %s 个文件" % MAX_FILE_LIMIT)
    print()
    print("=" * 60)
    print("许可码:")
    print("  %s" % license_code)
    print("=" * 60)
    print()
    print("请将此许可码完整复制给用户进行注册（复制粘贴，不要手输）。")


def _safe_input(prompt=""):
    """读取一行输入；stdin 关闭或被中断时返回空串，避免闪退。"""
    try:
        return input(prompt)
    except (EOFError, KeyboardInterrupt):
        return ""


def _interactive_main():
    """无参数时进入交互模式（双击运行），结束前驻留以便查看结果。"""
    print("=" * 60)
    print("PDF转换器 - 许可码生成工具（交互模式 / Ed25519）")
    print("=" * 60)
    print()
    while True:
        machine_code = _safe_input("请输入机器码 (格式 XXXX-XXXX-XXXX-XXXX，直接回车退出): ").strip().upper()
        if not machine_code:
            print("已退出。")
            break
        if not validate_machine_code(machine_code):
            print("  机器码格式无效，请重新输入。")
            print()
            continue
        serial_str = _safe_input("请输入序列号 (默认1，续期请填比上次更大的数字): ").strip() or "1"
        try:
            serial = int(serial_str)
        except ValueError:
            print("  序列号无效，已使用默认值1。")
            serial = 1
        try:
            license_code = generate_license_code(machine_code, serial)
        except Exception as e:
            print("  生成失败：%s" % e)
            print()
            continue
        print()
        _print_license(machine_code, serial, license_code)
        print()
    _safe_input("\n按回车键退出...")


def main():
    # 控制台输出统一 UTF-8，避免中文乱码
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
        print("错误: %s" % e, file=sys.stderr)
        sys.exit(1)
    except RuntimeError as e:
        print("错误: %s" % e, file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
