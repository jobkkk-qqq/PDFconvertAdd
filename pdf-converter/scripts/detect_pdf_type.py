#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF类型检测工具
智能分析PDF内容，判断适合转换为Word还是Excel
"""

import os
import sys
import argparse
import fitz  # PyMuPDF
import pdfplumber


def analyze_pdf_structure(pdf_path):
    """详细分析PDF结构"""
    analysis = {
        "page_count": 0,
        "text_density": 0,
        "table_count": 0,
        "image_count": 0,
        "has_form_fields": False,
        "is_scanned": False,
        "recommendation": "word"  # 默认推荐Word
    }

    # 使用PyMuPDF分析
    doc = fitz.open(pdf_path)
    analysis["page_count"] = len(doc)

    total_text_lines = 0
    total_images = 0
    total_tables = 0

    for page_num in range(len(doc)):
        page = doc[page_num]

        # 统计文字
        text_dict = page.get_text("dict")
        blocks = text_dict.get("blocks", [])
        for block in blocks:
            if block.get("type") == 0:  # 文本
                total_text_lines += len(block.get("lines", []))
            elif block.get("type") == 1:  # 图像
                total_images += 1

    doc.close()

    # 使用pdfplumber检测表格
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                tables = page.extract_tables()
                total_tables += len(tables)
    except Exception as e:
        print(f"表格检测警告: {e}")

    # 计算指标
    page_count = max(analysis["page_count"], 1)
    analysis["text_density"] = total_text_lines / page_count
    analysis["image_count"] = total_images
    analysis["table_count"] = total_tables

    # 判断是否为扫描PDF（图片占比高）
    if total_images > total_text_lines * 0.5:
        analysis["is_scanned"] = True

    # 智能推荐
    table_ratio = total_tables / max(page_count, 1)
    text_ratio = total_text_lines / max(page_count, 1)

    if analysis["is_scanned"]:
        analysis["recommendation"] = "ocr"
        analysis["reason"] = "检测到大量图片，建议先进行OCR识别"
    elif table_ratio >= 0.5:
        analysis["recommendation"] = "excel"
        analysis["reason"] = f"检测到 {total_tables} 个表格，表格密度较高"
    elif text_ratio >= 10:
        analysis["recommendation"] = "word"
        analysis["reason"] = "文字密度较高，适合转换为Word文档"
    else:
        analysis["recommendation"] = "word"
        analysis["reason"] = "混合型文档，默认推荐Word格式"

    return analysis


def print_analysis_report(analysis):
    """打印分析报告"""
    print("=" * 60)
    print("PDF 分析报告")
    print("=" * 60)
    print(f"页数: {analysis['page_count']}")
    print(f"文字密度: {analysis['text_density']:.1f} 行/页")
    print(f"表格数量: {analysis['table_count']}")
    print(f"图片数量: {analysis['image_count']}")
    print(f"是否扫描PDF: {'是' if analysis['is_scanned'] else '否'}")
    print("-" * 60)
    print(f"推荐格式: {analysis['recommendation'].upper()}")
    print(f"原因: {analysis['reason']}")
    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(description='PDF类型智能检测')
    parser.add_argument('--input', '-i', required=True, help='输入PDF文件路径')
    parser.add_argument('--format', '-f', choices=['word', 'excel', 'auto'],
                       default='auto', help='指定输出格式（默认自动检测）')

    args = parser.parse_args()

    if not os.path.exists(args.input):
        print(f"错误: 文件不存在 {args.input}")
        sys.exit(1)

    print(f"正在分析: {args.input}")
    print()

    analysis = analyze_pdf_structure(args.input)
    print_analysis_report(analysis)

    # 输出最终推荐
    if args.format == 'auto':
        recommended = analysis['recommendation']
        if recommended == 'ocr':
            print("\n建议使用OCR工具处理此PDF")
            print("推荐工具: pdf2pdf-ocr.py")
        elif recommended == 'excel':
            print("\n建议命令:")
            print(f"  python scripts/pdf_to_excel.py --input {args.input}")
        else:
            print("\n建议命令:")
            print(f"  python scripts/pdf_to_word.py --input {args.input}")
    else:
        print(f"\n按用户要求使用格式: {args.format}")

    return analysis


if __name__ == '__main__':
    main()
