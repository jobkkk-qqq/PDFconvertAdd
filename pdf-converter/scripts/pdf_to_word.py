#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF转Word脚本
适用于文字类文档的PDF转换
"""

import os
import re
import sys
import argparse
import fitz  # PyMuPDF
from docx import Document
from docx.shared import Pt, Inches, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn

# ============================================================
# PDF 字体名 → Word 字体名映射
# ============================================================

_FONT_MAP = {
    # 宋体
    'simsun': '宋体', 'songti': '宋体', 'stsong': '宋体',
    'nsimsun': '新宋体',
    # 黑体
    'simhei': '黑体', 'heiti': '黑体', 'stheiti': '黑体',
    # 楷体
    'kaiti': '楷体', 'simkai': '楷体', 'stkaiti': '楷体',
    # 仿宋
    'fangsong': '仿宋', 'fangsong_gb2312': '仿宋', '仿宋_gb2312': '仿宋',
    '仿宋gb2312': '仿宋', 'stfangsong': '仿宋',
    # 微软雅黑
    'microsoftyahei': '微软雅黑', 'msyh': '微软雅黑',
    # 等线
    'deng': '等线',
    # 华文
    'stzhongs': '华文中宋', 'stxihei': '华文细黑', 'stkaiti': '华文楷体',
    # 西文字体常见名
    'timesnewroman': 'Times New Roman',
    'arial': 'Arial',
    'calibri': 'Calibri',
    'couriernew': 'Courier New',
    'courier': 'Courier New',
    'helvetica': 'Helvetica',
    'helv': 'Helvetica',
    'gothic': 'Century Gothic',
    'garamond': 'Garamond',
    'verdana': 'Verdana',
    'tahoma': 'Tahoma',
    'georgia': 'Georgia',
}

# 判断是否中文字体名的关键词
_CJK_FONT_KEYWORDS = {'sim', 'hei', 'kai', 'song', 'fang', 'yahei', 'deng',
                      'stzhong', 'stxi', 'stkai', 'stheiti', 'stsong',
                      'ming', 'min', 'gothic', 'msmincho', 'yu', 'noto'}


def _normalize_font_name(raw_name):
    """将 PDF 中的字体名规范化为 Word 可用的字体名。"""
    if not raw_name:
        return None
    # PyMuPDF 可能将 UTF-8 字节按 Latin-1 返回（如 "楷体" → "æ¥·ä½"）
    # 尝试修复双重编码
    try:
        decoded = raw_name.encode('latin-1').decode('utf-8')
        raw_name = decoded
    except (UnicodeEncodeError, UnicodeDecodeError):
        pass
    # 去除子集前缀（如 ABCDEF+SimSun → SimSun）
    name = re.sub(r'^[A-Z]{6}\+', '', raw_name)
    # 去空格、小写
    key = re.sub(r'[\s\-_]', '', name).lower()
    if key in _FONT_MAP:
        return _FONT_MAP[key]
    return name


def _is_cjk_font(font_name):
    """粗略判断字体名是否为 CJK 字体。"""
    if not font_name:
        return False
    # 字体名本身就是中文（如"楷体""宋体"），直接判定
    if re.search(r'[\u4e00-\u9fff]', font_name):
        return True
    key = re.sub(r'[\s\-_]', '', font_name).lower()
    return any(kw in key for kw in _CJK_FONT_KEYWORDS)


def _apply_font_to_run(run, font_name, size, color_int, flags, text):
    """将 PyMuPDF span 的字体属性应用到 python-docx 的 run 上。"""
    run.text = text

    # --- 字体名 ---
    if font_name:
        run.font.name = font_name
        # 中文字体需额外设置 eastAsia 属性，否则 Word 中不生效
        rpr = run._element.get_or_add_rPr()
        rfonts = rpr.find(qn('w:rFonts'))
        if rfonts is None:
            rfonts = rpr.makeelement(qn('w:rFonts'), {})
            rpr.insert(0, rfonts)
        rfonts.set(qn('w:ascii'), font_name)
        rfonts.set(qn('w:hAnsi'), font_name)
        if _is_cjk_font(font_name):
            rfonts.set(qn('w:eastAsia'), font_name)

    # --- 字号 ---
    if size and size > 0:
        run.font.size = Pt(size)

    # --- 颜色 ---
    if color_int is not None:
        # PyMuPDF 的 color 是 sRGB int（0xRRGGBB）
        r = (color_int >> 16) & 0xFF
        g = (color_int >> 8) & 0xFF
        b = color_int & 0xFF
        # 0 = 黑色，也是默认值，跳过以避免覆盖默认样式
        if color_int != 0:
            run.font.color.rgb = RGBColor(r, g, b)

    # --- 粗体 / 斜体（flags 位标志）---
    if flags is not None:
        # bit 1 (2) = italic, bit 4 (16) = bold
        if flags & 16:
            run.font.bold = True
        if flags & 2:
            run.font.italic = True
        # bit 0 (1) = superscript, bit 5 (32) might be underline in some fonts
    # 通过字体名推断粗体（如 SimHei 本身是黑体，不在此推断）


def analyze_pdf_content(pdf_path):
    """分析PDF内容，返回文字和图像信息"""
    doc = fitz.open(pdf_path)
    total_text = 0
    total_images = 0
    page_count = len(doc)

    for page_num in range(page_count):
        page = doc[page_num]
        # 统计文字
        text_dict = page.get_text("dict")
        text_blocks = text_dict.get("blocks", [])
        for block in text_blocks:
            if block.get("type") == 0:  # 文本块
                total_text += len(block.get("lines", []))
            elif block.get("type") == 1:  # 图像块
                total_images += 1

    doc.close()
    return {
        "page_count": page_count,
        "text_density": total_text / max(page_count, 1),
        "image_count": total_images,
        "is_image_heavy": total_images > total_text * 0.3
    }


def pdf_to_word(pdf_path, output_path, detect_tables=False):
    """
    将PDF转换为Word文档，保留原文档的字体、字号、颜色、粗斜体样式。
    detect_tables: 是否尝试检测表格结构
    """
    print(f"正在打开PDF: {pdf_path}")
    pdf_doc = fitz.open(pdf_path)
    doc = Document()

    # 默认字体（兜底用，实际每段按 span 原始样式覆盖）
    style = doc.styles['Normal']
    font = style.font
    font.name = '宋体'
    font.size = Pt(11)
    # 设置 Normal 样式的 eastAsia 字体
    rpr = style.element.get_or_add_rPr()
    rfonts = rpr.find(qn('w:rFonts'))
    if rfonts is None:
        rfonts = rpr.makeelement(qn('w:rFonts'), {})
        rpr.insert(0, rfonts)
    rfonts.set(qn('w:eastAsia'), '宋体')

    print(f"共 {len(pdf_doc)} 页，开始转换...")

    for page_num in range(len(pdf_doc)):
        if page_num > 0:
            doc.add_page_break()

        page = pdf_doc[page_num]
        print(f"处理第 {page_num + 1} 页...")

        # 提取文本（dict 模式含坐标 + 字体信息）
        text_dict = page.get_text("dict")
        blocks = text_dict.get("blocks", [])

        for block in blocks:
            if block.get("type") == 0:  # 文本块
                lines = block.get("lines", [])
                for line in lines:
                    spans = line.get("spans", [])
                    if not spans:
                        continue

                    # 检查整行是否有实际文字
                    line_text = "".join(sp.get("text", "") for sp in spans)
                    if not line_text.strip():
                        continue

                    # 创建段落
                    para = doc.add_paragraph()

                    # 对齐方式：按几何位置判断居中
                    align = WD_ALIGN_PARAGRAPH.LEFT
                    bbox = line.get("bbox")
                    if bbox:
                        pw = page.rect.width
                        line_width = bbox[2] - bbox[0]
                        line_center = (bbox[0] + bbox[2]) / 2.0
                        if line_width < pw * 0.6 and \
                                abs(line_center - pw / 2.0) < pw * 0.05:
                            align = WD_ALIGN_PARAGRAPH.CENTER
                    para.alignment = align

                    # 每个 span → 独立 Run，保留原始字体样式
                    for sp in spans:
                        sp_text = sp.get("text", "")
                        if not sp_text:
                            continue
                        raw_font = sp.get("font", "")
                        font_name = _normalize_font_name(raw_font)
                        sp_size = sp.get("size", 11)
                        sp_color = sp.get("color", 0)
                        sp_flags = sp.get("flags", 0)

                        run = para.add_run()
                        _apply_font_to_run(run, font_name, sp_size,
                                           sp_color, sp_flags, sp_text)

            elif block.get("type") == 1 and detect_tables:
                pass

    # 保存Word文档
    print(f"正在保存Word文档: {output_path}")
    doc.save(output_path)
    pdf_doc.close()

    print(f"✓ 转换完成: {output_path}")
    return output_path


def main():
    parser = argparse.ArgumentParser(description='PDF转Word工具')
    parser.add_argument('--input', '-i', required=True, help='输入PDF文件路径')
    parser.add_argument('--output', '-o', help='输出Word文件路径（默认同目录）')
    parser.add_argument('--detect-tables', action='store_true', help='尝试检测表格结构')

    args = parser.parse_args()

    if not os.path.exists(args.input):
        print(f"错误: 文件不存在 {args.input}")
        sys.exit(1)

    # 默认输出路径
    if not args.output:
        base_name = os.path.splitext(args.input)[0]
        args.output = f"{base_name}.docx"

    # 分析PDF
    print("=" * 50)
    print("PDF内容分析")
    print("=" * 50)
    analysis = analyze_pdf_content(args.input)
    print(f"页数: {analysis['page_count']}")
    print(f"文字密度: {analysis['text_density']:.2f} 行/页")
    print(f"图像数量: {analysis['image_count']}")
    print(f"是否图片密集型: {'是' if analysis['is_image_heavy'] else '否'}")
    print()

    if analysis['is_image_heavy']:
        print("⚠ 警告: 此PDF可能包含大量图片，建议使用OCR模式")
        print("   提示: 可使用 --use-ocr 参数启用OCR识别")
        print()

    # 执行转换
    try:
        pdf_to_word(args.input, args.output, args.detect_tables)
        print("\n转换成功！")
    except Exception as e:
        print(f"\n✗ 转换失败: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
