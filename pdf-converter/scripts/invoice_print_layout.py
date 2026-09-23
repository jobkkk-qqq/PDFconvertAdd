#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
发票打印排版工具
功能：将发票PDF（通常为B5尺寸）在A4纸上上下排列两份，一次性排版打印。

用法：
    python invoice_print_layout.py --input 发票.pdf --output 打印版.pdf
可选：
    --copies 2       每页排列份数（默认2，上下排列）
    --margin 8       页面外边距（毫米）
    --spacing 6      上下两份之间的间隔（毫米）
"""

import argparse
import os
import sys


def get_a4_size():
    """返回A4纸张尺寸（点，1pt=1/72英寸）"""
    import fitz
    return fitz.paper_rect("a4")


def build_a4_dual_invoice(source_path, output_path, copies=2,
                          margin_mm=8, spacing_mm=6):
    """把发票PDF排版到A4纸上，上下排列copies份并保存"""
    import fitz

    src = fitz.open(source_path)
    if not src.page_count:
        src.close()
        raise ValueError("PDF 没有页面，无法排版")

    # 以第一页为发票版式（发票通常为单页）
    page = src[0]
    src_w, src_h = page.rect.width, page.rect.height

    a4 = get_a4_size()
    m = margin_mm * 72.0 / 25.4
    sp = spacing_mm * 72.0 / 25.4

    # 缩放：整体（宽度或高度）能放进A4并上下放置copies份
    scale_w = (a4.width - 2 * m) / src_w
    scale_h = (a4.height - 2 * m - (copies - 1) * sp) / (copies * src_h)
    scale = min(scale_w, scale_h)

    cw, ch = src_w * scale, src_h * scale
    x = (a4.width - cw) / 2.0

    out = fitz.open()
    a4_page = out.new_page(width=a4.width, height=a4.height)

    for i in range(copies):
        y = m + i * (ch + sp)
        rect = fitz.Rect(x, y, x + cw, y + ch)
        a4_page.show_pdf_page(rect, src, 0)

    out.save(output_path, garbage=3, deflate=True)
    out.close()
    src.close()

    return {
        "source_size_mm": (round(src_w * 25.4 / 72, 1), round(src_h * 25.4 / 72, 1)),
        "copies": copies,
        "output_path": output_path,
    }


def open_in_default_viewer(pdf_path):
    """用系统默认PDF程序打开文件（其自带打印预览）。Windows仅。"""
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"文件不存在: {pdf_path}")
    if os.name != "nt":
        raise OSError("调用默认PDF程序仅支持Windows系统")
    os.startfile(pdf_path)      # noqa: S606  调用系统默认处理程序


def open_system_print(pdf_path):
    """调用系统默认打印程序（Windows）。返回 (ok, 说明)"""
    if not os.path.exists(pdf_path):
        return False, f"文件不存在: {pdf_path}"
    if os.name != "nt":
        return False, "系统默认打印仅支持Windows系统，请手动打开打印"
    for verb in ("print", "printto"):
        try:
            os.startfile(pdf_path, verb)
            return True, f"已调用系统默认打印程序（动词：{verb}），请在打印窗口中确认"
        except OSError:
            continue
    return False, "系统未找到可用于打印PDF的默认程序，请重新打开PDF后手动打印"


def main():
    parser = argparse.ArgumentParser(description="发票打印排版（B5 → A4 上下两版）")
    parser.add_argument("--input", required=True, help="发票PDF文件路径")
    parser.add_argument("--output", required=True, help="输出A4打印版PDF路径")
    parser.add_argument("--copies", type=int, default=2,
                        help="每页排列份数（默认2）")
    parser.add_argument("--margin", type=float, default=8,
                        help="页面外边距（毫米，默认8）")
    parser.add_argument("--spacing", type=float, default=6,
                        help="上下两份间隔（毫米，默认6）")
    parser.add_argument("--print", action="store_true",
                        help="排版完成后调用系统默认打印")
    args = parser.parse_args()

    if not os.path.exists(args.input):
        print(f"错误: 输入文件不存在: {args.input}")
        sys.exit(1)

    info = build_a4_dual_invoice(args.input, args.output,
                                 copies=args.copies,
                                 margin_mm=args.margin,
                                 spacing_mm=args.spacing)
    src_w, src_h = info["source_size_mm"]
    print(f"原发票尺寸: {src_w} x {src_h} mm")
    print(f"每页排列:   {info['copies']} 份（上下排列）")
    print(f"已保存:     {info['output_path']}")

    if args.print:
        ok, detail = open_system_print(info['output_path'])
        print(f"[打印] {'成功' if ok else '失败'}: {detail}")
        sys.exit(0 if ok else 2)


if __name__ == "__main__":
    main()