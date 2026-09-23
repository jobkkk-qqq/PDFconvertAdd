# PDF转换器

一个智能的PDF文档转换工具，支持PDF与Word/Excel格式互转。

## 功能特性

### PDF转换
- **PDF → Word**: 文字类文档转换（文章、报告、书籍等）
- **PDF → Excel**: 表格类文档转换（财务报表、数据表格等）
- **智能检测**: 自动分析PDF内容，推荐最佳转换格式
- **OCR支持**: 可检测扫描PDF并建议使用OCR模式

### 反向转换
- **Word → PDF**: 通过LibreOffice高质量转换
- **Excel → PDF**: 通过LibreOffice高质量转换
- **批量转换**: 支持目录批量处理

### PDF组合与旋转（GUI功能）
- **PDF合并**: 多份PDF按顺序合并为一个，方便一次打印
- **合并旋转**: 合并前可为每份PDF设置90°/180°/270°旋转（横向扫描件转正）
- **自动统一方向**: 自动把横向页转90°统一为纵向（或反向），满足统一排版样式
- **PDF页面编辑**: 拆分预览每页，支持删除/排序/旋转/添加（图片/Word/Excel）后合成新PDF
- **页面级旋转**: 每页可单独顺时针旋转90°（可累计），缩略图实时预览
- **容错**: 单个损坏PDF跳过不中断合并；输出不覆盖已有文件；旋转不裁剪内容

## 快速开始

### 1. 安装依赖

```bash
cd pdf-converter
pip install -r requirements.txt
```

### 2. 基础使用

```bash
# 自动检测PDF类型
python scripts/converter.py --input document.pdf --auto

# 转换为Word
python scripts/converter.py --input report.pdf --format word

# 转换为Excel
python scripts/converter.py --input data.pdf --format excel

# Word/Excel转PDF
python scripts/converter.py --input doc.docx --format pdf
python scripts/converter.py --input sheet.xlsx --format pdf
```

### 3. 批量转换

```bash
# 转换目录下所有文档
python scripts/converter.py --batch-dir ./documents --format pdf
```

## 脚本说明

| 脚本 | 功能 |
|------|------|
| `converter.py` | 统一入口，智能选择转换策略 |
| `converter_gui.py` | GUI主程序（含转换、合并旋转、许可管理） |
| `detect_pdf_type.py` | 分析PDF内容，推荐最佳格式 |
| `pdf_to_word.py` | PDF转Word（文字类） |
| `pdf_to_excel.py` | PDF转Excel（表格类） |
| `doc_to_pdf.py` | Word转PDF |
| `excel_to_pdf.py` | Excel转PDF |
| `pdf_page_editor.py` | PDF页面编辑（删除/排序/旋转/添加页后合成） |
| `invoice_recognizer.py` | 电子发票字段识别 |
| `invoice_print_layout.py` | 发票打印排版（B5→A4上下两份） |

## 技术细节

### PDF类型检测算法

1. **文字密度分析**: 统计每页文字行数
2. **表格密度分析**: 检测表格结构和数量
3. **图片占比分析**: 判断是否为扫描PDF
4. **智能推荐**: 基于以上指标选择最佳格式

### 转换引擎

- **PDF解析**: PyMuPDF (fitz) + pdfplumber
- **Word创建**: python-docx
- **Excel创建**: openpyxl
- **格式转换**: LibreOffice命令行

## 注意事项

1. 扫描版PDF（纯图片）建议使用OCR工具预处理
2. 复杂排版的PDF转换效果可能受限
3. LibreOffice转换需要一定时间，请耐心等待
4. 大批量转换建议分批进行

## 许可证

MIT License
