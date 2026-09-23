#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
发票打印（独立版 / inv-print）
将 B5 发票在 A4 纸上上下排列两份，一键排版，并使用 Windows 默认 PDF 程序进行打印预览 / 打印。

用法（命令行）:
    inv_print.py 发票.pdf                 # 排版后用系统默认 PDF 程序打开（打印预览）
    inv_print.py --print 发票.pdf         # 排版后直接调用系统默认打印

无参数运行时启动图形界面。
"""

import argparse
import datetime
import os
import sys
import tempfile


# ------------------------------------------------------------------ 核心排版
def build_a4_dual_invoice(source_path, output_path, copies=2,
                          margin_mm=8, spacing_mm=6):
    """把发票PDF排版到A4纸上，上下排列 copies 份并保存。返回信息字典。"""
    import fitz

    src = fitz.open(source_path)
    if len(src) == 0:
        src.close()
        raise ValueError("发票PDF为空")
    if len(src) > 1:
        src.close()
        raise ValueError("发票PDF包含多页，请先拆分为单页后再打印")

    page = src[0]
    src_rect = page.rect
    src_w_mm = src_rect.width / 72.0 * 25.4
    src_h_mm = src_rect.height / 72.0 * 25.4

    # 打印边距
    margin_pt = margin_mm / 25.4 * 72
    spacing_pt = spacing_mm / 25.4 * 72

    a4 = fitz.paper_rect("a4")
    usable_w = a4.width - 2 * margin_pt
    usable_h = a4.height - 2 * margin_pt - (copies - 1) * spacing_pt

    scale = min(usable_w / src_rect.width, usable_h / (src_rect.height * copies))
    scaled_w = src_rect.width * scale
    scaled_h = src_rect.height * scale

    total_h = copies * scaled_h + (copies - 1) * spacing_pt
    start_y = (a4.height - total_h) / 2.0
    x0 = (a4.width - scaled_w) / 2.0

    out = fitz.open()
    new_page = out.new_page(width=a4.width, height=a4.height)
    for i in range(copies):
        y0 = start_y + i * (scaled_h + spacing_pt)
        rect = fitz.Rect(x0, y0, x0 + scaled_w, y0 + scaled_h)
        new_page.show_pdf_page(rect, src, 0)
    out.save(output_path)
    out.close()
    src.close()

    return {
        "source_size_mm": (round(src_w_mm, 1), round(src_h_mm, 1)),
        "copies": copies,
        "output_path": output_path,
        "page_size_mm": (round(a4.width / 72.0 * 25.4, 1), round(a4.height / 72.0 * 25.4, 1)),
    }


# ------------------------------------------------------------- 系统默认打印/预览
def is_windows():
    return os.name == "nt"


def open_in_default_viewer(path):
    """用系统默认 PDF 程序打开文件（其自带打印预览）。"""
    if not is_windows():
        raise OSError("仅支持 Windows 系统调用默认PDF程序")
    os.startfile(path)      # noqa: S606  调用系统默认处理程序


def open_system_print(path):
    """调用系统默认打印（Windows）。返回 (ok, 说明)"""
    if not os.path.exists(path):
        return False, f"文件不存在: {path}"
    if not is_windows():
        return False, "系统默认打印仅支持 Windows，请手动打开打印"
    for verb in ("print", "printto"):
        try:
            os.startfile(path, verb)      # noqa: S606
            return True, f"已调用系统默认打印（{verb}）"
        except OSError:
            continue
    return False, "系统未找到可打印PDF的默认程序，请在打开后的PDF中手动打印"


# ------------------------------------------------------------- 临时工作目录
def make_output_path(src_path):
    """生成 A4 打印版文件的临时保存路径。"""
    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    base = os.path.splitext(os.path.basename(src_path))[0]
    return os.path.join(tempfile.gettempdir(), f"inva4_{base}_{stamp}.pdf")


# ------------------------------------------------------------------ 图形界面
def run_gui():
    import tkinter as tk
    from tkinter import filedialog, messagebox, ttk

    app = tk.Tk()
    app.title("发票打印（B5 → A4 上下两份）")
    app.geometry("520x300")
    app.minsize(500, 280)
    app.configure(bg="#f5f6fa")

    state = {"src": None, "a4": None}

    tk.Label(app, text="发票打印排版工具", bg="#f5f6fa",
             font=("Microsoft YaHei", 14, "bold")).pack(pady=(14, 2))

    row = tk.Frame(app, bg="#f5f6fa")
    row.pack(fill="x", padx=16, pady=8)
    tk.Label(row, text="发票PDF:", bg="#f5f6fa").pack(side="left")
    entry = tk.Entry(row)
    entry.pack(side="left", fill="x", expand=True, padx=6)
    tk.Button(row, text="浏览…", command=lambda: _browse()).pack(side="left")

    info = tk.StringVar(value="尚未选择文件")
    tk.Label(app, textvariable=info, bg="#f5f6fa", fg="#666",
             font=("Microsoft YaHei", 10)).pack(pady=(0, 6))

    tip_txt = ("排版规则：将发票（建议B5）按原尺寸等比缩放，"
               "在A4纸上上下排列 2 份，居中留边距。")
    tk.Label(app, text=tip_txt, bg="#f5f6fa", fg="#888", wraplength=470,
             justify="left", font=("Microsoft YaHei", 9)).pack(padx=16)

    btns = tk.Frame(app, bg="#f5f6fa")
    btns.pack(fill="x", padx=16, pady=(12, 4))
    ttk.Button(btns, text="排版并预览（默认PDF程序）",
               command=lambda: _go(preview=True)).pack(side="left", padx=4)
    ttk.Button(btns, text="排版并打印（默认打印机）",
               command=lambda: _go(preview=False)).pack(side="left", padx=4)
    ttk.Button(btns, text="退出", command=app.destroy).pack(side="right", padx=4)

    outkv = tk.StringVar(value="")
    tk.Label(app, textvariable=outkv, bg="#f5f6fa", fg="#2a7a3a", wraplength=480,
             font=("Microsoft YaHei", 9)).pack(pady=(6, 0))

    def _browse():
        path = filedialog.askopenfilename(
            title="选择发票PDF（建议为B5尺寸）",
            filetypes=[("PDF文件", "*.pdf")])
        if path:
            _load(path)

    def _load(path):
        try:
            stat = _probe(path)
        except Exception as e:
            messagebox.showerror("错误", f"无法读取PDF:\n{e}")
            return
        state["src"] = path
        entry.delete(0, tk.END)
        entry.insert(0, path)
        info.set(f"发票尺寸: {stat['w']} x {stat['h']} mm   |   每页排列 2 份（A4）")
        outkv.set("")

    def _go(preview):
        if not state["src"]:
            messagebox.showwarning("提示", "请先选择一个发票PDF文件")
            return
        a4 = make_output_path(state["src"])
        try:
            r = build_a4_dual_invoice(state["src"], a4)
            state["a4"] = a4
            outkv.set(f"已生成: {a4}")
            if preview:
                open_in_default_viewer(a4)
                messagebox.showinfo("预览", f"已用系统默认PDF程序打开（其中自带打印预览）：\n{a4}")
            else:
                ok, d = open_system_print(a4)
                messagebox.showinfo("打印" if ok else "打印失败", d + "\n" + a4 if ok else d)
        except Exception as e:
            messagebox.showerror("出错", f"排版失败:\n{e}")

    if len(sys.argv) > 1 and os.path.exists(sys.argv[1]):
        app.after(200, lambda: _load(sys.argv[1]))

    app.mainloop()


def _probe(path):
    import fitz
    doc = fitz.open(path)
    try:
        r = doc[0].rect
        w = round(r.width / 72 * 25.4, 1)
        h = round(r.height / 72 * 25.4, 1)
        return {"w": w, "h": h}
    finally:
        doc.close()


# ------------------------------------------------------------------ 主入口
def main():
    parser = argparse.ArgumentParser(description="发票打印（B5 → A4 上下两份）")
    parser.add_argument("pdf", nargs="?", help="发票PDF文件路径")
    parser.add_argument("--print", action="store_true", help="排版后直接调用系统默认打印")
    args = parser.parse_args()

    if args.pdf:
        if not os.path.exists(args.pdf):
            print(f"错误: 文件不存在: {args.pdf}", file=sys.stderr)
            sys.exit(1)
        a4 = make_output_path(args.pdf)
        try:
            info = build_a4_dual_invoice(args.pdf, a4)
        except Exception as e:
            print(f"排版失败: {e}", file=sys.stderr)
            sys.exit(1)
        w, h = info["source_size_mm"]
        print(f"原发票尺寸: {w} x {h} mm   ->  已生成 A4 两联版: {a4}")
        if args.print:
            ok, d = open_system_print(a4)
            print(f"[打印] {'成功' if ok else '失败'}: {d}")
            sys.exit(0 if ok else 2)
        open_in_default_viewer(a4)   # 用默认PDF程序打开（打印预览）
        print("已用系统默认PDF程序打开，可在其中进行打印预览。")
    else:
        run_gui()


if __name__ == "__main__":
    main()