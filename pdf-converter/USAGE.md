# PDF转换器使用指南

## 项目结构

```
pdf-converter/
├── SKILL.md              # ZCode技能定义
├── README.md             # 项目说明
├── requirements.txt      # Python依赖
├── scripts/
│   ├── converter.py      # 统一转换入口
│   ├── detect_pdf_type.py # PDF类型检测
│   ├── pdf_to_word.py    # PDF转Word
│   ├── pdf_to_excel.py   # PDF转Excel
│   ├── doc_to_pdf.py     # Word转PDF
│   └── excel_to_pdf.py   # Excel转PDF
└── references/           # 参考资料目录
```

## 快速开始

### 1. 安装依赖

```bash
cd pdf-converter
pip install -r requirements.txt
```

**注意**: 已安装以下包：
- pymupdf (1.28.2) ✓
- pdfplumber (0.11.9) ✓
- python-docx ✓ (需要安装)
- openpyxl (3.1.2) ✓
- Pillow (10.1.0) ✓

### 2. 测试转换

#### 测试PDF类型检测（创建一个测试PDF）

```bash
# 先用Python创建一个简单的测试PDF
python -c "
import fitz
doc = fitz.open()
page = doc.new_page()
page.insert_text((72, 72), '这是一篇测试文章\n\n第一段内容。\n\n第二段内容。', fontsize=12)
page.insert_text((72, 200), '这是第二段...\n\n更多内容...')
doc.save('test_document.pdf')
doc.close()
print('测试PDF已创建: test_document.pdf')
"
```

#### 运行类型检测

```bash
cd scripts
python detect_pdf_type.py --input ../test_document.pdf
```

#### 转换为Word

```bash
python pdf_to_word.py --input ../test_document.pdf
```

#### 转换为Excel

```bash
python pdf_to_excel.py --input ../test_document.pdf
```

#### 使用统一入口（推荐）

```bash
# 自动检测并转换
python converter.py --input ../test_document.pdf --auto

# 指定格式
python converter.py --input ../test_document.pdf --format word
python converter.py --input ../test_document.pdf --format excel
```

### 3. Word/Excel转PDF

```bash
# 需要先有Word或Excel文件
python doc_to_pdf.py --input your_doc.docx
python excel_to_pdf.py --input your_sheet.xlsx
```

## 智能检测逻辑

### PDF类型判断标准

| 指标 | 条件 | 推荐格式 |
|------|------|----------|
| 图片密度 > 文字密度 × 0.5 | 扫描PDF | OCR处理 |
| 表格数量 ≥ 0.5 表格/页 | 表格密集 | Excel |
| 文字行数 ≥ 10 行/页 | 文字为主 | Word |
| 其他情况 | 混合类型 | Word（默认） |

### 转换流程

```
用户上传文件
    ↓
检测文件格式 (.pdf/.docx/.xlsx)
    ↓
如果是PDF:
    ├─ 自动模式: 分析内容 → 推荐格式
    ├─ 指定Word: 直接调用 pdf_to_word.py
    └─ 指定Excel: 直接调用 pdf_to_excel.py
如果是Word/Excel:
    └─ 调用LibreOffice转换为PDF
```

## 高级功能

### 批量转换

```bash
# 转换目录下所有文档为PDF
python converter.py --batch-dir ./documents --format pdf

# 转换目录下所有PDF为Word
python converter.py --batch-dir ./pdfs --format word
```

### 强制OCR模式

```bash
# 适用于扫描版PDF
python converter.py --input scanned.pdf --use-ocr
```

**注意**: OCR功能需要额外安装：
```bash
pip install pytesseract
# Windows还需安装Tesseract OCR引擎
```

## 常见问题

### Q: 转换后的Word文档格式不理想？
A: PDF原文档的排版信息可能不完整，建议：
- 检查原PDF是否为扫描件
- 尝试使用 `--detect-tables` 参数
- 对于复杂排版，可手动调整

### Q: Excel中的表格数据丢失？
A: 可能原因：
- PDF中表格使用图片或特殊字体
- 表格结构过于复杂
- 建议使用 `pdf_to_excel.py` 的详细输出查看

### Q: Word/Excel转PDF失败？
A: 确保：
- LibreOffice已正确安装
- 路径包含空格时加引号
- 文件未被其他程序占用

### Q: 如何获取详细的转换日志？
A: 各脚本均支持 `--verbose` 参数（如已实现）

## 技术细节

### PyMuPDF警告处理

代码中使用了 deprecated 的 `fitz` API，如需消除警告：
```python
# 替换
import fitz
# 为
import pymupdf as fitz
```

### LibreOffice路径

脚本自动检测LibreOffice位置，常见路径：
- Windows: `C:\Program Files\LibreOffice\program\soffice.exe`
- Linux: `/usr/bin/soffice`
- macOS: `/Applications/LibreOffice.app/Contents/MacOS/soffice`

## 扩展开发

### 添加新功能

1. 在 `scripts/` 目录创建新脚本
2. 更新 `converter.py` 以支持新格式
3. 修改 `SKILL.md` 添加触发描述

### 贡献代码

欢迎提交Issue和Pull Request改进工具！
