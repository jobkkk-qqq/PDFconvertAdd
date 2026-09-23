---
name: pdf-converter
description: PDF与Word/Excel格式互转工具。支持PDF转Word（文字文档）、PDF转Excel（表格文档）、Word/Excel转PDF。智能检测PDF来源类型，图片PDF使用OCR识别，原文档PDF使用精准解析工具。当用户提到PDF转换、文档格式转换、文字转表格、表格转文字时使用此工具。
---

# PDF转换器

一个功能完整的PDF文档转换工具，支持多种格式互转和智能识别。

## 核心功能

### 1. PDF → Word (文字类文档)
- 适用场景：文章、报告、书籍等以文字为主的PDF
- 智能检测：自动分析PDF内容类型，判断是否适合转为Word
- 输出格式：.docx（兼容现代Word版本）

### 2. PDF → Excel (表格类文档)
- 适用场景：财务报表、数据表格、统计数据的PDF
- 智能检测：分析PDF中的表格结构和密度
- 输出格式：.xlsx（原生Excel格式）

### 3. Word/Excel → PDF
- 通过LibreOffice命令行转换
- 支持批量转换
- 保持原始格式和样式

## 使用流程

### 基本信息收集
1. 确认输入文件路径
2. 确认输出格式（如未指定则自动检测）
3. 确认输出目录（默认为输入文件同目录）

### 转换策略选择

**文字类PDF转Word：**
```bash
python scripts/pdf_to_word.py --input file.pdf --output file.docx
```

**表格类PDF转Excel：**
```bash
python scripts/pdf_to_excel.py --input file.pdf --output file.xlsx
```

**文档转PDF：**
```bash
python scripts/doc_to_pdf.py --input file.docx --output file.pdf
# 或
python scripts/excel_to_pdf.py --input file.xlsx --output file.pdf
```

### 智能检测流程
1. 分析PDF内容（文字密度 vs 表格密度）
2. 检测是否为扫描/图片PDF（检查页面是否有图片元素）
3. 选择合适的转换策略
4. 执行转换并输出结果

## 脚本说明

详细使用方法请参考 `scripts/` 目录下的各脚本文件：
- `pdf_to_word.py` - PDF转Word脚本
- `pdf_to_excel.py` - PDF转Excel脚本
- `detect_pdf_type.py` - PDF类型检测工具
- `doc_to_pdf.py` - Word转PDF脚本
- `excel_to_pdf.py` - Excel转PDF脚本
- `converter.py` - 统一转换入口

## 依赖要求

确保已安装以下Python包：
- pymupdf (fitz) - PDF解析
- pdfplumber - 表格提取
- python-docx - Word文档创建
- openpyxl - Excel文档创建
- Pillow - 图像处理
- pytesseract - OCR识别（可选）

## 示例

```bash
# 转换PDF为Word
python scripts/converter.py --input report.pdf --format word

# 转换PDF为Excel
python scripts/converter.py --input data.pdf --format excel

# 自动检测并转换
python scripts/converter.py --input document.pdf --auto

# Word转PDF
python scripts/converter.py --input doc.docx --format pdf

# Excel转PDF
python scripts/converter.py --input sheet.xlsx --format pdf
```
