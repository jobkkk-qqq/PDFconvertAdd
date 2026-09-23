#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生成PDF转换器图标
创建文档转换主题的ICO文件
"""

from PIL import Image, ImageDraw, ImageFont
import os


def create_pdf_converter_icon(output_path="pdf_converter.ico"):
    """创建PDF转换器图标"""

    # 创建不同尺寸的图像
    sizes = [16, 32, 48, 64, 128, 256]
    images = []

    for size in sizes:
        # 创建透明背景的图像
        img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        # 绘制文档背景（圆角矩形）
        padding = size // 10
        doc_width = size - padding * 2
        doc_height = size - padding * 2
        corner_radius = size // 8

        # 文档主体 - 蓝色渐变效果
        for y in range(padding, padding + doc_height):
            ratio = (y - padding) / doc_height
            r = int(30 + 20 * ratio)
            g = int(100 + 50 * ratio)
            b = int(200 + 55 * ratio)
            draw.line([(padding, y), (padding + doc_width, y)],
                     fill=(r, g, b, 255))

        # 绘制文档折角
        fold_size = size // 6
        draw.polygon([
            (size - padding - fold_size, padding),
            (size - padding, padding),
            (size - padding, padding + fold_size)
        ], fill=(40, 120, 220, 255))

        # 绘制文档线条（表示文字）
        line_count = max(3, size // 16)
        line_spacing = doc_height // (line_count + 1)
        for i in range(1, line_count + 1):
            y = padding + line_spacing * i
            line_width = int(doc_width * (0.6 + 0.3 * (i % 2)))
            draw.rectangle(
                [padding + (doc_width - line_width) // 2, y,
                 padding + (doc_width + line_width) // 2, y + max(2, size // 20)],
                fill=(255, 255, 255, 200)
            )

        # 绘制PDF标识
        if size >= 48:
            pdf_text = "PDF"
            try:
                font_size = max(8, size // 5)
                font = ImageFont.truetype("arial.ttf", font_size)
            except:
                font = ImageFont.load_default()

            bbox = draw.textbbox((0, 0), pdf_text, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            text_x = padding + (doc_width - text_width) // 2
            text_y = size - padding - font_size - 5
            draw.text((text_x, text_y), pdf_text, fill=(255, 80, 80), font=font)

        images.append(img)

    # 保存为ICO文件
    images[0].save(output_path, format='ICO',
                   sizes=[(i.width, i.height) for i in images])

    print(f"✓ 图标已保存: {output_path}")
    return output_path


def create_word_icon(output_path="word_converter.ico"):
    """创建Word转换图标（绿色主题）"""
    sizes = [16, 32, 48, 64, 128, 256]
    images = []

    for size in sizes:
        img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        padding = size // 10
        doc_width = size - padding * 2
        doc_height = size - padding * 2

        # 绿色渐变
        for y in range(padding, padding + doc_height):
            ratio = (y - padding) / doc_height
            r = int(30 + 10 * ratio)
            g = int(150 + 50 * ratio)
            b = int(50 + 30 * ratio)
            draw.line([(padding, y), (padding + doc_width, y)],
                     fill=(r, g, b, 255))

        # 折角
        fold_size = size // 6
        draw.polygon([
            (size - padding - fold_size, padding),
            (size - padding, padding),
            (size - padding, padding + fold_size)
        ], fill=(50, 160, 70, 255))

        # 文字线条
        line_count = max(3, size // 16)
        line_spacing = doc_height // (line_count + 1)
        for i in range(1, line_count + 1):
            y = padding + line_spacing * i
            line_width = int(doc_width * (0.6 + 0.3 * (i % 2)))
            draw.rectangle(
                [padding + (doc_width - line_width) // 2, y,
                 padding + (doc_width + line_width) // 2, y + max(2, size // 20)],
                fill=(255, 255, 255, 200)
            )

        # Word标识
        if size >= 48:
            word_text = "DOC"
            try:
                font_size = max(8, size // 5)
                font = ImageFont.truetype("arial.ttf", font_size)
            except:
                font = ImageFont.load_default()

            bbox = draw.textbbox((0, 0), word_text, font=font)
            text_width = bbox[2] - bbox[0]
            text_x = padding + (doc_width - text_width) // 2
            text_y = size - padding - font_size - 5
            draw.text((text_x, text_y), word_text, fill=(255, 255, 255), font=font)

        images.append(img)

    images[0].save(output_path, format='ICO',
                   sizes=[(i.width, i.height) for i in images])
    print(f"✓ Word图标已保存: {output_path}")


def create_excel_icon(output_path="excel_converter.ico"):
    """创建Excel转换图标（绿色主题）"""
    sizes = [16, 32, 48, 64, 128, 256]
    images = []

    for size in sizes:
        img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        padding = size // 10
        doc_width = size - padding * 2
        doc_height = size - padding * 2

        # 绿色渐变（Excel绿色）
        for y in range(padding, padding + doc_height):
            ratio = (y - padding) / doc_height
            r = int(20 + 10 * ratio)
            g = int(160 + 40 * ratio)
            b = int(50 + 20 * ratio)
            draw.line([(padding, y), (padding + doc_width, y)],
                     fill=(r, g, b, 255))

        # 折角
        fold_size = size // 6
        draw.polygon([
            (size - padding - fold_size, padding),
            (size - padding, padding),
            (size - padding, padding + fold_size)
        ], fill=(34, 168, 50, 255))

        # 表格线条（表示Excel）
        if size >= 32:
            grid_size = size // 4
            for i in range(1, 3):
                x = padding + doc_width * i // 3
                draw.line([(x, padding), (x, padding + doc_height)],
                         fill=(255, 255, 255, 150), width=max(1, size // 40))
            for i in range(1, 3):
                y = padding + doc_height * i // 3
                draw.line([(padding, y), (padding + doc_width, y)],
                         fill=(255, 255, 255, 150), width=max(1, size // 40))

        images.append(img)

    images[0].save(output_path, format='ICO',
                   sizes=[(i.width, i.height) for i in images])
    print(f"✓ Excel图标已保存: {output_path}")


if __name__ == '__main__':
    output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'icons')
    os.makedirs(output_dir, exist_ok=True)

    print("生成PDF转换器图标...")
    create_pdf_converter_icon(os.path.join(output_dir, 'pdf_converter.ico'))
    create_word_icon(os.path.join(output_dir, 'word_converter.ico'))
    create_excel_icon(os.path.join(output_dir, 'excel_converter.ico'))

    print(f"\n图标已保存到: {output_dir}")
