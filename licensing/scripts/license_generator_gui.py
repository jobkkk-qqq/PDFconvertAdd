#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
许可码生成器 - GUI版本（开发者工具）
输入用户机器码，生成注册许可码
"""

import os
import sys
import re
import hashlib
import hmac
from datetime import datetime

import tkinter as tk
from tkinter import ttk, messagebox

# ============================================================
# 许可码生成核心逻辑（与 generate_license.py 保持一致）
# ============================================================

DEVELOPER_SECRET = "PDFConverter2026_SecretKey_v1.0"
MAX_FILE_LIMIT = 20


def validate_machine_code(machine_code):
    """验证机器码格式 XXXX-XXXX-XXXX-XXXX"""
    pattern = r'^[A-F0-9]{4}-[A-F0-9]{4}-[A-F0-9]{4}-[A-F0-9]{4}$'
    return re.match(pattern, machine_code.upper()) is not None


def generate_license_code(machine_code, serial_number=1):
    """
    生成许可码
    格式: PDF-{机器码前8位}-{序列号4位}-{HMAC签名8位}
    """
    if not validate_machine_code(machine_code):
        raise ValueError(f"无效的机器码格式: {machine_code}")

    machine_code = machine_code.upper()
    code_hash = machine_code.replace("-", "")
    machine_prefix = code_hash[:8]
    serial_str = f"{serial_number:04d}"

    # 计算校验位（HMAC-SHA256）
    message = f"PDF-{machine_prefix}-{serial_str}"
    signature = hmac.new(
        DEVELOPER_SECRET.encode('utf-8'),
        message.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()[:8].upper()

    return f"PDF-{machine_prefix}-{serial_str}-{signature}"


def verify_license_code(license_code, machine_code):
    """验证许可码"""
    pattern = r'^PDF-[A-F0-9]{8}-\d{4}-[A-F0-9]{8}$'
    if not re.match(pattern, license_code.upper()):
        return False, "许可码格式无效"
    if not validate_machine_code(machine_code):
        return False, "机器码格式无效"

    license_code = license_code.upper()
    machine_code = machine_code.upper()

    m = re.match(r'^PDF-([A-F0-9]{8})-(\d{4})-([A-F0-9]{8})$', license_code)
    machine_prefix = machine_code.replace('-', '')[:8]

    if m.group(1) != machine_prefix:
        return False, "许可码与机器码不匹配"

    message = f"PDF-{machine_prefix}-{m.group(2)}"
    expected = hmac.new(DEVELOPER_SECRET.encode('utf-8'),
                        message.encode('utf-8'),
                        hashlib.sha256).hexdigest()[:8].upper()

    if m.group(3) == expected:
        return True, "许可码有效"
    return False, "许可码校验失败"


# ============================================================
# GUI界面
# ============================================================

class LicenseGeneratorGUI:
    """许可码生成器图形界面"""

    def __init__(self, root):
        self.root = root
        self.root.title("许可码生成器 v1.0（开发者工具）")
        self.root.geometry("620x520")
        self.root.resizable(False, False)

        # 日志文件路径
        try:
            exe_dir = os.path.dirname(os.path.abspath(sys.executable))
        except Exception:
            exe_dir = os.path.dirname(os.path.abspath(__file__))
        self.log_file = os.path.join(exe_dir, 'license_generator.log')

        self.create_widgets()
        self.log("许可码生成器已启动")

    def create_widgets(self):
        """创建界面"""
        main_frame = ttk.Frame(self.root, padding="15")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 标题
        ttk.Label(main_frame, text="许可码生成器", font=('Microsoft YaHei', 16, 'bold'))\
            .pack(pady=(0, 5))
        ttk.Label(main_frame, text="根据用户机器码生成注册许可码（每个许可可转换20个文件）",
                  foreground='gray').pack(pady=(0, 10))

        # 输入区域
        input_frame = ttk.LabelFrame(main_frame, text="用户信息", padding="10")
        input_frame.pack(fill=tk.X, pady=5)

        # 机器码
        ttk.Label(input_frame, text="用户机器码:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.machine_entry = ttk.Entry(input_frame, width=40)
        self.machine_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=5, pady=5)
        ttk.Button(input_frame, text="粘贴", width=8, command=self.paste_machine)\
            .grid(row=0, column=2, padx=5)
        ttk.Label(input_frame, text="格式: XXXX-XXXX-XXXX-XXXX", foreground='gray')\
            .grid(row=1, column=1, sticky=tk.W, padx=5)

        # 序列号
        ttk.Label(input_frame, text="序列号:").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.serial_var = tk.StringVar(value="1")
        ttk.Entry(input_frame, textvariable=self.serial_var, width=10)\
            .grid(row=2, column=1, sticky=tk.W, padx=5, pady=5)
        ttk.Label(input_frame, text="同一机器多次授权时递增（1, 2, 3...）", foreground='gray')\
            .grid(row=3, column=1, sticky=tk.W, padx=5)

        # 生成按钮
        ttk.Button(main_frame, text="生 成 许 可 码", command=self.do_generate,
                   width=20).pack(pady=10)

        # 结果区域
        result_frame = ttk.LabelFrame(main_frame, text="生成结果", padding="10")
        result_frame.pack(fill=tk.X, pady=5)

        ttk.Label(result_frame, text="许可码:").grid(row=0, column=0, sticky=tk.W)
        self.result_var = tk.StringVar(value="（点击生成后显示）")
        result_entry = ttk.Entry(result_frame, textvariable=self.result_var, width=45,
                                 font=('Consolas', 11))
        result_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=5)

        btn_frame = ttk.Frame(result_frame)
        btn_frame.grid(row=1, column=1, sticky=tk.W, padx=5, pady=8)
        ttk.Button(btn_frame, text="复制", width=8, command=self.copy_result)\
            .pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="验证许可码", width=10, command=self.show_verify_dialog)\
            .pack(side=tk.LEFT, padx=2)

        ttk.Label(result_frame, text="文件限额: 20 个文件", foreground='gray')\
            .grid(row=2, column=1, sticky=tk.W, padx=5)

        # 生成历史
        history_frame = ttk.LabelFrame(main_frame, text="生成历史（保存到 license_generator.log）", padding="10")
        history_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        self.history_text = tk.Text(history_frame, height=8, width=70, wrap=tk.WORD)
        self.history_text.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)

        scrollbar = ttk.Scrollbar(history_frame, orient=tk.VERTICAL, command=self.history_text.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.history_text['yscrollcommand'] = scrollbar.set

    def log(self, message):
        """记录日志（界面 + .log文件）"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        line = f"[{timestamp}] {message}"
        self.history_text.insert(tk.END, line + "\n")
        self.history_text.see(tk.END)
        try:
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(line + "\n")
        except Exception:
            pass

    def paste_machine(self):
        """从剪贴板粘贴机器码"""
        try:
            text = self.root.clipboard_get().strip()
            if text:
                self.machine_entry.delete(0, tk.END)
                self.machine_entry.insert(0, text.upper())
                self.log(f"已粘贴机器码: {text.upper()}")
        except Exception:
            messagebox.showwarning("提示", "剪贴板中没有可粘贴的内容")

    def do_generate(self):
        """生成许可码"""
        machine_code = self.machine_entry.get().strip().upper()
        serial_str = self.serial_var.get().strip()

        if not machine_code:
            messagebox.showwarning("警告", "请输入用户机器码")
            return

        # 清理常见粘贴格式
        machine_code = machine_code.replace(' ', '')

        if not validate_machine_code(machine_code):
            messagebox.showerror("错误", "机器码格式无效！\n\n正确格式: XXXX-XXXX-XXXX-XXXX\n（16位十六进制字符，用连字符分隔为4组）")
            return

        try:
            serial_number = int(serial_str)
            if serial_number < 1:
                raise ValueError
        except ValueError:
            messagebox.showerror("错误", "序列号必须是正整数（1, 2, 3...）")
            return

        try:
            license_code = generate_license_code(machine_code, serial_number)
            self.result_var.set(license_code)

            # 自动复制到剪贴板
            try:
                self.root.clipboard_clear()
                self.root.clipboard_append(license_code)
            except Exception:
                pass

            self.log(f"机器码: {machine_code} | 序列号: {serial_number} | 许可码: {license_code}（已复制）")
            messagebox.showinfo(
                "生成成功",
                f"许可码已生成并复制到剪贴板:\n\n{license_code}\n\n"
                f"请将许可码发送给用户完成注册。"
            )
        except Exception as e:
            messagebox.showerror("错误", f"生成失败: {str(e)}")
            self.log(f"生成失败: {str(e)}")

    def copy_result(self):
        """复制许可码"""
        license_code = self.result_var.get()
        if license_code and license_code != "（点击生成后显示）":
            try:
                self.root.clipboard_clear()
                self.root.clipboard_append(license_code)
                self.log(f"已复制许可码: {license_code}")
                messagebox.showinfo("成功", "许可码已复制到剪贴板")
            except Exception as e:
                messagebox.showerror("错误", f"复制失败: {str(e)}")
        else:
            messagebox.showwarning("提示", "请先生成许可码")

    def show_verify_dialog(self):
        """验证许可码对话框"""
        dialog = tk.Toplevel(self.root)
        dialog.title("验证许可码")
        dialog.geometry("440x180")
        dialog.transient(self.root)
        dialog.grab_set()

        ttk.Label(dialog, text="机器码:").grid(row=0, column=0, sticky=tk.W, padx=10, pady=10)
        machine_entry = ttk.Entry(dialog, width=35)
        machine_entry.grid(row=0, column=1, padx=10, pady=10)
        if self.machine_entry.get():
            machine_entry.insert(0, self.machine_entry.get().strip().upper())

        ttk.Label(dialog, text="许可码:").grid(row=1, column=0, sticky=tk.W, padx=10, pady=5)
        license_entry = ttk.Entry(dialog, width=35)
        license_entry.grid(row=1, column=1, padx=10, pady=5)
        if self.result_var.get() and self.result_var.get() != "（点击生成后显示）":
            license_entry.insert(0, self.result_var.get())

        def do_verify():
            machine_code = machine_entry.get().strip().upper()
            license_code = license_entry.get().strip().upper()
            is_valid, message = verify_license_code(license_code, machine_code)
            self.log(f"验证: 机器码={machine_code} 许可码={license_code} → {message}")
            if is_valid:
                messagebox.showinfo("验证结果", "✓ 许可码有效！")
            else:
                messagebox.showerror("验证结果", f"✗ {message}")

        ttk.Button(dialog, text="验证", command=do_verify).grid(row=2, column=1, padx=10, pady=15)

        dialog.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() - dialog.winfo_width()) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - dialog.winfo_height()) // 2
        dialog.geometry(f"+{x}+{y}")


def main():
    """主函数"""
    # 高DPI支持
    if sys.platform == 'win32':
        try:
            from ctypes import windll
            windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            pass

    root = tk.Tk()
    app = LicenseGeneratorGUI(root)
    root.mainloop()


if __name__ == '__main__':
    main()
