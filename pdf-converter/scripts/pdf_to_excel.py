#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF转Excel脚本
适用于表格类文档的PDF转换
"""

import os
import sys
import argparse
import fitz  # PyMuPDF
import pdfplumber
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, Border, Side, PatternFill
from openpyxl.utils import get_column_letter


def extract_tables_from_pdf(pdf_path):
    """使用pdfplumber提取PDF中的表格"""
    tables_data = []

    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages, 1):
            tables = page.extract_tables()

            if tables:
                for table_num, table in enumerate(tables, 1):
                    # 清理表格数据
                    clean_table = []
                    for row in table:
                        clean_row = [cell.strip() if cell else "" for cell in row]
                        clean_table.append(clean_row)
                    tables_data.append({
                        "page": page_num,
                        "table_num": table_num,
                        "data": clean_table
                    })

    return tables_data


def extract_text_content(pdf_path):
    """提取PDF中的文字内容（用于非表格区域）"""
    text_content = []
    doc = fitz.open(pdf_path)

    for page_num in range(len(doc)):
        page = doc[page_num]
        text = page.get_text()
        if text.strip():
            text_content.append({
                "page": page_num + 1,
                "text": text
            })

    doc.close()
    return text_content


def create_excel(tables_data, text_content, output_path):
    """创建Excel工作簿"""
    wb = Workbook()

    # 样式定义
    header_font = Font(bold=True, size=11)
    header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
    header_font_white = Font(bold=True, size=11, color="FFFFFF")
    thin_border = Border(
        left=Side(style='thin'),
        right=Side(style='thin'),
        top=Side(style='thin'),
        bottom=Side(style='thin')
    )

    # 为每个表格创建工作表
    for idx, table_info in enumerate(tables_data):
        sheet_name = f"表格{idx + 1}"
        ws = wb.create_sheet(title=sheet_name)

        table = table_info["data"]
        if not table:
            continue

        # 写入表格数据
        for row_idx, row in enumerate(table, 1):
            for col_idx, cell in enumerate(row, 1):
                cell_obj = ws.cell(row=row_idx, column=col_idx, value=cell)
                cell_obj.border = thin_border

                # 第一行设为表头样式
                if row_idx == 1:
                    cell_obj.font = header_font_white
                    cell_obj.fill = header_fill
                else:
                    cell_obj.font = Font(size=10)

                # 自动调整列宽
                if cell:
                    max_length = len(str(cell))
                    adjusted_width = min(max(max_length * 1.2, 8), 50)
                    ws.column_dimensions[get_column_letter(col_idx)].width = adjusted_width

        # 添加页码信息
        ws.cell(row=len(table) + 2, column=1, value=f"来源: 第 {table_info['page']} 页")

    # 如果没有表格，但有文字内容，创建文字工作表
    if not tables_data and text_content:
        ws = wb.active
        ws.title = "文字内容"

        for idx, text_info in enumerate(text_content):
            if idx > 0:
                ws.append([])  # 空行分隔
            ws.append([f"--- 第 {text_info['page']} 页 ---"])
            for line in text_info["text"].split('\n'):
                if line.strip():
                    ws.append([line])

    # 保存文件
    wb.save(output_path)
    print(f"✓ Excel文件已保存: {output_path}")


def analyze_pdf_for_tables(pdf_path):
    """分析PDF中的表格密度"""
    table_count = 0
    text_density = 0

    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            tables = page.extract_tables()
            table_count += len(tables)

            # 计算文字密度
            text = page.extract_text()
            if text:
                text_density += len(text.split())

    return table_count, text_density


def main():
    parser = argparse.ArgumentParser(description='PDF转Excel工具')
    parser.add_argument('--input', '-i', required=True, help='输入PDF文件路径')
    parser.add_argument('--output', '-o', help='输出Excel文件路径（默认同目录）')

    args = parser.parse_args()

    if not os.path.exists(args.input):
        print(f"错误: 文件不存在 {args.input}")
        sys.exit(1)

    # 默认输出路径
    if not args.output:
        base_name = os.path.splitext(args.input)[0]
        args.output = f"{base_name}.xlsx"

    # 分析PDF
    print("=" * 50)
    print("PDF表格分析")
    print("=" * 50)
    table_count, text_density = analyze_pdf_for_tables(args.input)
    print(f"检测到的表格数量: {table_count}")
    print(f"文字密度: {text_density:.0f} 词/页")
    print()

    if table_count == 0:
        print("⚠ 未检测到表格结构")
        print("   将尝试使用OCR或手动检测")
        print()

    # 提取数据
    print("正在提取表格数据...")
    tables_data = extract_tables_from_pdf(args.input)
    text_content = extract_text_content(args.input)

    print(f"发现 {len(tables_data)} 个表格")
    print()

    # 创建Excel
    print("正在生成Excel文件...")
    try:
        create_excel(tables_data, text_content, args.output)
        print("\n转换成功！")
    except Exception as e:
        print(f"\n✗ 转换失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
