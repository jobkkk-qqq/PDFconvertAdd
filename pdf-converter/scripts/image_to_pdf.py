#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
图片转PDF脚本
使用 PyMuPDF(fitz) + Pillow 将一张或多张图片合成为一个PDF
支持单张图片生成、多张图片追加合成为一个PDF
"""

import os
import sys
import argparse

SUPPORTED_EXTS = {'.png', '.jpg', '.jpeg', '.bmp', '.gif', '.webp', '.tif', '.tiff'}


def image_to_pdf(image_paths, output_path=None):
    """将一张或多张图片转换为PDF"""
    import fitz

    if not image_paths:
        raise ValueError("未指定输入图片")

    # 过滤并校验存在的图片
    valid = []
    for p in image_paths:
        if not os.path.exists(p):
            print(f"警告: 文件不存在，跳过 {p}")
            continue
        valid.append(p)
    if not valid:
        raise FileNotFoundError("没有可转换的图片文件")

    # 默认输出路径：单图用图片同名，多图用第一张图片名+_merged
    if not output_path:
        if len(valid) == 1:
            base = os.path.splitext(valid[0])[0]
        else:
            base = os.path.splitext(valid[0])[0] + "_merged"
        output_path = base + ".pdf"

    output_dir = os.path.dirname(output_path)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)

    print(f"输入图片数: {len(valid)}")
    print(f"输出PDF: {output_path}")
    print()

    doc = fitz.open()
    try:
        for img_path in valid:
            # 用 PyMuPDF 直接插入图片（自动读取尺寸，保证页面与图片等比）
            img = fitz.open(img_path)
            if len(img) == 0:
                img.close()
                continue
            rect = img[0].rect
            page = doc.new_page(width=rect.width, height=rect.height)
            page.insert_image(rect, filename=img_path)
            img.close()
            print(f"  ✓ 已加入: {os.path.basename(img_path)} ({rect.width:.0f}x{rect.height:.0f}pt)")
        doc.save(output_path, deflate=True)
    finally:
        doc.close()

    print()
    print("✓ 转换成功！")
    print(f"输出文件: {output_path}")
    print(f"文件大小: {os.path.getsize(output_path) / 1024:.1f} KB")
    return output_path


def main():
    parser = argparse.ArgumentParser(description='图片转PDF工具')
    parser.add_argument('--input', '-i', nargs='+', required=True,
                        help='输入图片路径（可多个，将合成为一个PDF）')
    parser.add_argument('--output', '-o', help='输出PDF文件路径（默认同目录）')

    args = parser.parse_args()
    try:
        image_to_pdf(args.input, args.output)
    except Exception as e:
        print(f"✗ 转换失败: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()