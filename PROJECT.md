# PDF转换器项目

## 项目概述

一个智能的PDF文档转换工具，支持PDF与Word/Excel格式互转，包含完整的注册许可管理系统。

## 项目结构

```
pdf2pdf/
├── pdf-converter/           # PDF转换工具
│   ├── scripts/
│   │   ├── converter.py     # 统一转换入口
│   │   ├── detect_pdf_type.py   # PDF类型检测
│   │   ├── pdf_to_word.py   # PDF转Word
│   │   ├── pdf_to_excel.py  # PDF转Excel
│   │   ├── doc_to_pdf.py    # Word转PDF
│   │   ├── excel_to_pdf.py  # Excel转PDF
│   │   ├── invoice_print_layout.py # 发票打印排版（B5→A4上下两份；用系统默认PDF程序预览/打印）
│   │   ├── pdf_page_editor.py # PDF页面编辑（删除/排序/旋转/添加页后合成，支持页面级旋转）
│   │   ├── license_checker.py   # 许可验证
│   │   └── show_registration.py # 注册说明
│   ├── SKILL.md             # ZCode技能定义
│   ├── README.md            # 使用说明
│   ├── USAGE.md             # 详细使用指南
│   └── requirements.txt     # Python依赖
│
├── licensing/               # 注册许可系统
│   ├── scripts/
│   │   ├── get_machine_code.py  # 机器码提取
│   │   ├── generate_license.py  # 许可码生成
│   │   ├── verify_license.py    # 许可码验证
│   │   └── register.py        # 注册管理
│   └── README.md            # 注册系统说明
│
└── PROJECT.md               # 项目总览
```

## 功能特性

### PDF转换
- ✅ PDF → Word（文字类文档）
- ✅ PDF → Excel（表格类文档）
- ✅ Word → PDF
- ✅ Excel → PDF
- ✅ 智能检测PDF类型（检测结果缓存，避免重复解析）
- ✅ 批量转换支持
- ✅ 发票打印排版（B5发票 → A4纸上上下两份、一次成版；生成后用系统默认PDF程序预览打印，也可调用系统默认打印机）

### PDF组合与旋转（统一排版样式）
- ✅ PDF合并：多份PDF按顺序合并为一个，一次打印
- ✅ 合并可旋转：合并前可为每份PDF设置 90°/180°/270° 旋转（如横向扫描件转正）
- ✅ 自动统一方向：合并时可自动把横向页转90°统一为纵向（或反之），满足统一排版
- ✅ PDF页面编辑：拆分预览每页，可删除/排序/旋转/添加（图片/Word/Excel）后重新合成
- ✅ 页面级旋转：每页可单独顺时针旋转90°（可累计至180°/270°），缩略图实时预览，合成时应用
- ✅ 容错与安全：单个损坏PDF自动跳过不中断合并；旋转仅改方向属性不裁剪内容；合成输出不覆盖已有文件（自动加序号）

### 注册许可
- ✅ 机器码提取（基于硬件信息）
- ✅ 许可码生成（开发者工具）
- ✅ 许可码验证
- ✅ 注册状态管理
- ✅ 文件使用计数（转换成功才扣减）
- ✅ 20个文件限额

## 快速开始

### 1. 安装依赖

```bash
cd pdf-converter
pip install -r requirements.txt
```

### 2. 获取机器码

```bash
cd ../licensing/scripts
python get_machine_code.py
```

### 3. 注册（联系开发者获取许可码）

```bash
python register.py --register <机器码> <许可码>
```

### 4. 开始转换

```bash
cd ../../pdf-converter/scripts
python converter.py --input document.pdf --auto
```

## 注册系统工作流程

```
用户侧：
  get_machine_code.py → 提取机器码
      ↓
  发送给开发者
      ↓
开发者侧：
  generate_license.py → 生成许可码
      ↓
  发送给用户
      ↓
用户侧：
  register.py → 注册
      ↓
  converter.py → 转换（自动验证许可）
```

## 技术细节

### 机器码生成

基于以下硬件信息生成唯一标识：
- CPU ID
- 主板序列号
- MAC地址
- 硬盘序列号

算法：SHA256哈希 → 格式化 `XXXX-XXXX-XXXX-XXXX`

### 许可码生成

格式：`PDF-{机器码前8位}-{序列号}-{HMAC校验位}`

示例：
```
PDF-D0609F8C-0001-E4F1990B
```

### 数据存储

配置文件存储在用户家目录：
- Windows: `%USERPROFILE%\.pdf_converter\`
- Linux/macOS: `~/.pdf_converter/`

文件：
- `license_config.json` - 系统配置
- `license.json` - 注册信息
- `usage.json` - 使用记录

## 使用统计

```bash
# 查看注册状态
python register.py --status

# 查看详细使用统计
python register.py --usage
```

输出示例：
```
============================================================
PDF转换器 - 注册状态
============================================================

✓ 已注册
  机器码:   D060-9F8C-3317-EC14
  注册时间: 2026-08-18T11:07:45
  已使用:   1 / 20 个文件
  剩余配额: 19 个文件
============================================================
```

## 测试验证

所有功能已通过测试：

| 功能 | 状态 |
|------|------|
| 机器码提取 | ✓ |
| 许可码生成 | ✓ |
| 许可码验证 | ✓ |
| 注册流程 | ✓ |
| PDF类型检测 | ✓ |
| PDF转Word | ✓ |
| PDF转Excel | ✓ |
| Word转PDF | ✓ |
| 使用计数 | ✓ |
| 配额检查 | ✓ |

## 注意事项

1. **机器码唯一性**: 基于硬件信息生成，更换硬件可能导致机器码变化
2. **许可绑定**: 许可码与机器码绑定，不可转移
3. **文件限额**: 仅在转换成功时扣除1个配额，失败不扣减
4. **数据存储**: 注册信息存储在本地，卸载软件不会清除

## 扩展开发

### 添加新的转换格式

1. 在 `pdf-converter/scripts/` 创建新脚本
2. 在 `converter.py` 添加格式支持
3. 更新 `SKILL.md` 触发描述

### 修改许可规则

修改 `licensing/scripts/generate_license.py` 中的常量：
- `MAX_FILE_LIMIT` - 文件限制
- `PUBLIC_KEY_HEX` - 验签公钥（**可以公开**；签名私钥不在仓库里，只留在开发者本机）

> 许可码用 Ed25519 非对称签名。程序内只放公钥，因此改程序也造不出有效许可码；
> 私钥的存放位置见 `licensing/README.md`。

## 许可证

MIT License

---

**开发者**: ZCode Agent (Agnes)
**创建日期**: 2026-08-18
**版本**: 2.0.0（许可码改用 Ed25519 非对称签名）
