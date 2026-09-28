#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
许可码生成器 - GUI版本（开发者工具）
输入用户机器码，生成注册许可码
"""

import os
import sys
import re
from datetime import datetime

import tkinter as tk
from tkinter import ttk, messagebox

# ============================================================
# 许可码生成核心逻辑：直接复用 generate_license.py
# ------------------------------------------------------------
# 以前这里是一份重复实现（同样带着对称密钥），改一次要改两处、极易走偏。
# 现在统一从 generate_license 导入；本工具是**开发者端**，签名需要私钥，
# 私钥从仓库外读取（见 generate_license.py 的私钥查找顺序），不随仓库分发。
# ============================================================

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from generate_license import (  # noqa: E402
    MAX_FILE_LIMIT,
    validate_machine_code,
    generate_license_code,
    verify_license_code,
    find_private_key_path,
)


# ============================================================
# GUI界面
# ============================================================

class LicenseGeneratorGUI:
    """许可码生成器图形界面"""

    def __init__(self, root):
        self.root = root
        self.root.title("许可码生成器 v2.0（开发者工具 / Ed25519）")
        self.root.geometry("620x520")
        self.root.resizable(False, False)

        # 日志文件路径：打包后写在 exe 同级目录；源码运行时写在本脚本目录
        # （不要用 sys.executable，否则源码运行会把日志丢进 Python 安装目录）
        if getattr(sys, 'frozen', False):
            self.app_dir = os.path.dirname(os.path.abspath(sys.executable))
        else:
            self.app_dir = os.path.dirname(os.path.abspath(__file__))
        self.log_file = os.path.join(self.app_dir, 'license_generator.log')

        # 支持命令行直接发码（GUI 版 exe 也能当脚本用，便于批量/测试）：
        #   LicenseGenerator.exe <机器码> [序列号]
        # 控制台不可见时把结果写到 license_code.txt，双击运行则照常开界面。
        cli_args = [a for a in sys.argv[1:] if not a.startswith('-')]
        if cli_args:
            sys.exit(self._cli_generate(cli_args))

        self.create_widgets()
        self.log("许可码生成器已启动")
        key_path = find_private_key_path()
        if key_path:
            self.log(f"私钥已加载: {key_path}")
        else:
            self.log("警告: 未找到私钥文件，无法生成许可码（放置位置见 licensing/README.md）")

    def _cli_generate(self, args):
        """命令行模式：<机器码> [序列号] → 结果写 license_code.txt 并打印。

        给 GUI 版 exe 留的批处理/自检入口；没有参数时仍是正常的图形界面。
        """
        machine_code = str(args[0]).strip().upper()
        try:
            serial = int(args[1]) if len(args) > 1 else 1
        except ValueError:
            serial = 1
        lines = ["机器码: %s" % machine_code, "序列号: %d" % serial]
        ok = True
        try:
            license_code = generate_license_code(machine_code, serial)
            is_valid, message = verify_license_code(license_code, machine_code)
            lines.append("文件限额: %d" % MAX_FILE_LIMIT)
            lines.append("许可码: %s" % license_code)
            lines.append("自检: %s" % message)
            ok = is_valid
        except Exception as e:
            lines.append("生成失败: %s" % e)
            ok = False
        text = "\n".join(lines)
        try:
            with open(os.path.join(self.app_dir, 'license_code.txt'), 'w', encoding='utf-8') as f:
                f.write(text + "\n")
        except Exception:
            pass
        try:
            print(text)
        except Exception:
            pass
        return 0 if ok else 1

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
