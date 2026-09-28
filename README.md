# PDF转换器（PDFconvertAdd）

智能 PDF 文档转换工具：**PDF ⇄ Word / Excel** 互转，附带 PDF 合并旋转、页面编辑、发票打印排版，以及一套基于 **Ed25519 非对称签名**的注册许可系统。

![Platform](https://img.shields.io/badge/平台-Windows%20%7C%20Linux%20%7C%20macOS-lightgrey)
![Python](https://img.shields.io/badge/Python-%E2%89%A5%203.8-blue)
![License](https://img.shields.io/badge/License-MIT-green)

## 功能特性

### 文档转换

- **PDF → Word**：文字类文档（文章、报告、书籍等）
- **PDF → Excel**：表格类文档（财务报表、数据表格等）
- **Word / Excel → PDF**：经 LibreOffice 高质量转换
- **智能类型检测**：分析文字密度、表格密度、图片占比，自动推荐最佳目标格式
- **扫描件识别**：检测纯图片 PDF 并提示改用 OCR 模式
- **批量转换**：按目录批量处理

### PDF 组合与旋转

- **PDF 合并**：多份 PDF 按顺序合并为一个，方便一次打印
- **合并前旋转**：可为每份 PDF 设置 90°/180°/270°（横向扫描件转正）
- **自动统一方向**：把横向页统一转为纵向（或反向），满足统一排版
- **页面编辑器**：拆分预览每页，支持删除 / 排序 / 旋转 / 插入（图片、Word、Excel）后重新合成
- **容错**：单个损坏 PDF 自动跳过不中断；旋转只改方向属性、不裁剪内容；输出不覆盖已有文件（自动加序号）

### 发票相关

- **电子发票字段识别**（`invoice_recognizer.py`）
- **发票打印排版**：B5 发票 → A4 纸上上下两份、一次成版（`invoice_print_layout.py`）
- **独立小工具 InvPrint**：见 [`inv-print/`](inv-print/README.md)

### 注册许可

- **一机一码**：机器码由硬件信息经 SHA256 生成，形如 `XXXX-XXXX-XXXX-XXXX`
- **Ed25519 非对称签名**：程序内只内置**公钥**（只能验签），签名私钥仅在开发者本机
- **每许可 20 份**：转换成功才扣减配额，失败不计
- **序号续期**：用满后用**序列号更大**的新许可码续期，旧码不可复用

## 项目结构

```
PDFconvertAdd/
├── pdf-converter/            # 转换工具（用户端）
│   ├── scripts/
│   │   ├── converter.py            # 统一转换入口（含许可校验）
│   │   ├── converter_gui.py        # GUI 主程序（转换 / 合并旋转 / 页面编辑 / 许可管理）
│   │   ├── detect_pdf_type.py      # PDF 类型检测
│   │   ├── pdf_to_word.py          # PDF → Word
│   │   ├── pdf_to_excel.py         # PDF → Excel
│   │   ├── doc_to_pdf.py           # Word → PDF
│   │   ├── excel_to_pdf.py         # Excel → PDF
│   │   ├── image_to_pdf.py         # 图片 → PDF
│   │   ├── pdf_page_editor.py      # PDF 页面编辑
│   │   ├── invoice_recognizer.py   # 电子发票字段识别
│   │   ├── invoice_print_layout.py # 发票打印排版
│   │   ├── license_checker.py      # 许可校验（内置公钥验签）
│   │   ├── ed25519.py              # 纯标准库 Ed25519 实现
│   │   └── show_registration.py    # 注册说明
│   ├── README.md / USAGE.md / SKILL.md
│   └── requirements.txt
│
├── licensing/                # 注册许可系统（只含验签，不含发码）
│   ├── scripts/
│   │   ├── get_machine_code.py      # 机器码提取（用户端）
│   │   ├── license_verify.py        # 许可码验签（只读，只有公钥）
│   │   ├── verify_license.py        # 许可码验证工具
│   │   ├── register.py              # 注册管理
│   │   └── ed25519.py               # 纯标准库 Ed25519 实现（验签用）
│   └── README.md             # 注册系统说明（发码工具在仓库外）
│
├── inv-print/                # 发票打印独立小工具 InvPrint
├── PROJECT.md                # 项目总览
├── REGISTRATION_GUIDE.md     # 注册系统使用说明
└── LICENSE                   # MIT
```

## 快速开始

### 1. 安装依赖

```bash
pip install pymupdf pdfplumber python-docx openpyxl Pillow
# 可选：拖拽支持与发票 OCR
pip install tkinterdnd2 rapidocr_onnxruntime
```

Word / Excel 转 PDF 需要本机安装 **LibreOffice**（脚本会自动探测常见路径）。

### 2. 获取机器码

```bash
python licensing/scripts/get_machine_code.py
```

输出示例：

```
============================================================
您的机器码:
  XXXX-XXXX-XXXX-XXXX
============================================================
```

### 3. 注册

把机器码发给开发者换取许可码，然后：

```bash
python licensing/scripts/register.py --register XXXX-XXXX-XXXX-XXXX PDF-XXXXXXXX-0001-<签名>
```

> 许可码较长（约 121 字符），请**完整复制粘贴**，不要手输。

### 4. 开始转换

```bash
cd pdf-converter/scripts

python converter.py --input document.pdf --auto      # 自动检测并转换
python converter.py --input report.pdf --format word # 指定转 Word
python converter.py --input data.pdf   --format excel# 指定转 Excel
python converter.py --input doc.docx   --format pdf  # Word → PDF
python converter.py --batch-dir ./documents --format pdf   # 批量
```

### 图形界面

```bash
cd pdf-converter/scripts
python converter_gui.py
```

打包版直接运行 `dist\PDFConverter_gui\PDFConverter_gui.exe`（onedir 结构，请保持整个文件夹完整）。

## 注册许可说明

许可码使用 **Ed25519 非对称签名**（RFC 8032）：

```
PDF - XXXXXXXX - NNNN - <Base32 签名>
       │          │       └─ Ed25519 签名（64 字节 → Base32 103 字符）
       │          └─ 序列号：第几次授权，续期即 +1
       └─ 机器码前 8 位
```

- **程序内只内置公钥**：它只能验签，**无法生成**许可码——所以即使程序与源码完全公开，也造不出有效码
- **发码工具与私钥都在本仓库之外**（默认 `<仓库根>/../license-keys/`），不随仓库分发、不打进 exe
- **配额**：每个许可最多转换 20 个文件，用满后用序列号更大的新码续期
- ⚠️ **2.0.0 起旧格式许可码全部失效**（旧版用对称 HMAC，密钥随程序分发，等于把发码器交给了每个用户）

开发者的完整工作流见 [`REGISTRATION_GUIDE.md`](REGISTRATION_GUIDE.md)，私钥与发码工具位置见 [`licensing/README.md`](licensing/README.md)。

## 打包

```bash
pip install pyinstaller
pyinstaller --noconfirm PDFConverter_gui.spec      # GUI 版 → dist/PDFConverter_gui/
python build_gui.py                                # 一条命令出客户端 + scripts/ 辅助脚本
```

各 spec 用途：

| 文件 | 产物 |
|------|------|
| `PDFConverter_gui.spec` | GUI 版（推荐分发） |
| `PDFConverter.spec` | 命令行版 |
| `build_gui_spec.spec` | 当前 `build_gui.py` 使用的 GUI 打包配置（onedir → `dist/PDFConverter_gui/`） |

> 本仓库**不打包发码工具**。发码工具的源码与打包脚本都在仓库外（与私钥同目录），
> 用法是在那边执行它自己的 `make-license.bat` 或直接运行打包好的 `LicenseGenerator.exe`。

## 文档

- [`PROJECT.md`](PROJECT.md) —— 项目总览与功能清单
- [`REGISTRATION_GUIDE.md`](REGISTRATION_GUIDE.md) —— 注册系统完整流程
- [`licensing/README.md`](licensing/README.md) —— 许可码格式、私钥存放、安全注意事项
- [`pdf-converter/USAGE.md`](pdf-converter/USAGE.md) —— 详细使用指南与常见问题
- [`inv-print/README.md`](inv-print/README.md) —— 发票打印小工具

## 常见问题

- **扫描版 PDF 转出来是空白 / 乱码**：原文件是纯图片，需先 OCR。可先运行 `detect_pdf_type.py` 确认。
- **Word / Excel 转 PDF 失败**：确认已安装 LibreOffice；路径含空格时加引号；文件未被其它程序占用。
- **换机器或换硬件后提示许可码不匹配**：机器码基于硬件（主板、网卡等），硬件变化会导致机器码改变，需按新机器码重新发码。
- **提示"已用完配额"**：本授权 20 份已用完，请用序列号更大的新许可码续期。
- **`fitz` 弃用警告**：PyMuPDF 的 `fitz` 别名已弃用，可改为 `import pymupdf as fitz`。

## 许可证

[MIT](LICENSE)
