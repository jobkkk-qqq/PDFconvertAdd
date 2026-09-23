# PDF转换器 - 注册系统使用说明

## 项目结构

```
D:\python\pdf2pdf\
├── pdf-converter\          # PDF转换工具（用户端）
│   ├── scripts\
│   │   ├── converter.py        # 统一入口（集成注册验证）
│   │   ├── license_checker.py  # 许可验证模块
│   │   ├── pdf_to_word.py      # PDF转Word
│   │   ├── pdf_to_excel.py     # PDF转Excel
│   │   ├── doc_to_pdf.py       # Word转PDF
│   │   ├── excel_to_pdf.py     # Excel转PDF
│   │   └── detect_pdf_type.py  # PDF类型检测
│   └── ...
│
└── licensing\              # 注册许可系统
    ├── scripts\
    │   ├── get_machine_code.py    # 机器码提取
    │   ├── generate_license.py    # 许可码生成（开发者）
    │   ├── verify_license.py      # 许可码验证
    │   └── register.py            # 注册管理
    └── README.md
```

## 完整工作流程

### 用户侧流程

```
┌─────────────────────────────────────────────────────────────────┐
│                     用户操作步骤                                 │
└─────────────────────────────────────────────────────────────────┘

第1步：首次运行，查看注册引导
┌─────────────────────────────────────────────────────────────────┐
│  命令: python converter.py                                      │
│                                                                 │
│  输出:                                                          │
│  ✗ 请先注册PDF转换器                                            │
│  注册方法:                                                      │
│    1. 运行: python get_machine_code.py 获取机器码                │
│    2. 联系开发者获取许可码                                       │
│    3. 运行: python register.py --register <机器码> <许可码>      │
└─────────────────────────────────────────────────────────────────┘
                          ↓
第2步：获取机器码
┌─────────────────────────────────────────────────────────────────┐
│  命令: python converter.py --get-machine-code                   │
│                                                                 │
│  输出:                                                          │
│  ============================================================ │
│  您的机器码: D060-9F8C-3317-EC14                               │
│  ============================================================ │
│                                                                 │
│  注册说明:                                                      │
│    步骤 1: 获取机器码 ✓（已完成）                               │
│    步骤 2: 发送机器码给开发者                                   │
│    步骤 3: 使用许可码注册                                       │
└─────────────────────────────────────────────────────────────────┘
                          ↓
第3步：发送机器码给开发者，获取许可码
┌─────────────────────────────────────────────────────────────────┐
│  用户将机器码发送给开发者                                        │
│  开发者使用 generate_license.py 生成许可码                       │
│                                                                 │
│  示例许可码: PDF-D0609F8C-0001-E4F1990B                        │
└─────────────────────────────────────────────────────────────────┘
                          ↓
第4步：注册
┌─────────────────────────────────────────────────────────────────┐
│  命令: python converter.py --register D060-9F8C-3317-EC14 \     │
│                  PDF-D0609F8C-0001-E4F1990B                     │
│                                                                 │
│  输出:                                                          │
│  正在注册...                                                    │
│  注册成功！您现在可以转换20个文件。                              │
└─────────────────────────────────────────────────────────────────┘
                          ↓
第5步：查看注册状态
┌─────────────────────────────────────────────────────────────────┐
│  命令: python converter.py --status                             │
│                                                                 │
│  输出:                                                          │
│  ============================================================ │
│  【注册状态】✓ 已注册                                           │
│    机器码: D060-9F8C-3317-EC14                                 │
│    已使用: 0 / 20 个文件                                        │
│    剩余配额: 20 个文件                                          │
│  ============================================================ │
└─────────────────────────────────────────────────────────────────┘
                          ↓
第6步：开始转换
┌─────────────────────────────────────────────────────────────────┐
│  命令: python converter.py --input document.pdf --format word   │
│                                                                 │
│  输出:                                                          │
│  ✓ 转换成功！剩余配额: 19 个文件                                │
│  [转换过程...]                                                  │
│  转换完成！                                                     │
└─────────────────────────────────────────────────────────────────┘
```

### 开发者侧流程

```
┌─────────────────────────────────────────────────────────────────┐
│                     开发者操作步骤                               │
└─────────────────────────────────────────────────────────────────┘

第1步：接收用户机器码
┌─────────────────────────────────────────────────────────────────┐
│  用户发送: D060-9F8C-3317-EC14                                  │
└─────────────────────────────────────────────────────────────────┘
                          ↓
第2步：生成许可码
┌─────────────────────────────────────────────────────────────────┐
│  命令: python generate_license.py D060-9F8C-3317-EC14           │
│                                                                 │
│  输出:                                                          │
│  ============================================================ │
│  机器码:   D060-9F8C-3317-EC14                                 │
│  序列号:   1                                                    │
│  文件限制: 20 个文件                                            │
│  ============================================================ │
│  许可码:                                                         │
│    PDF-D0609F8C-0001-E4F1990B                                  │
│  ============================================================ │
└─────────────────────────────────────────────────────────────────┘
                          ↓
第3步：发送许可码给用户
┌─────────────────────────────────────────────────────────────────┐
│  用户收到许可码: PDF-D0609F8C-0001-E4F1990B                     │
└─────────────────────────────────────────────────────────────────┘
```

## 技术实现细节

### 1. 机器码提取 (`get_machine_code.py`)

```python
硬件信息收集:
  ├─ CPU ID      (Windows: WMI, Linux: /proc/cpuinfo)
  ├─ 主板序列    (Windows: WMI, Linux: DMI)
  ├─ MAC地址     (跨平台: uuid.getnode())
  └─ 硬盘序列    (Windows: WMI, Linux: /sys/class)

算法流程:
  raw_string = "CPU:xxx|BOARD:xxx|MAC:xxx|HDD:xxx"
  hash_value = SHA256(raw_string.encode())
  machine_code = format_first_32_chars(hash_value)
  # 输出格式: XXXX-XXXX-XXXX-XXXX
```

### 2. 许可码生成 (`generate_license.py`)

```python
许可码格式:
  PDF - D0609F8C - 0001 - E4F1990B
   │       │        │        │
   │       │        │        └─ HMAC-SHA256签名(8位)
   │       │        └─ 序列号(4位数字)
   │       └─ 机器码前缀(8位)
   └─ 固定前缀

生成算法:
  1. 提取机器码前8位
  2. 格式化序列号为4位数字
  3. 构造签名字符串: "PDF-{prefix}-{serial}"
  4. 计算HMAC-SHA256签名
  5. 取前8位作为校验位
  6. 组装完整许可码
```

### 3. 注册验证流程 (`converter.py` → `license_checker.py`)

```python
注册流程:
  1. 验证机器码格式 (XXXX-XXXX-XXXX-XXXX)
  2. 验证许可码格式 (PDF-XXXXXXXX-NNNN-XXXXXXXX)
  3. 验证许可码签名 (HMAC-SHA256)
  4. 检查是否已注册 (比较机器码)
  5. 保存注册信息 (~/.pdf_converter/license.json)
  6. 初始化使用记录 (~/.pdf_converter/usage.json)

转换流程:
  1. 检查是否已注册 (读取 license.json)
  2. 检查配额是否充足 (读取 usage.json)
  3. 执行转换操作
  4. 增加使用计数 (total_files += 1)
  5. 记录转换详情 (文件名 + 时间戳)
  6. 显示剩余配额
```

### 4. 数据存储结构

```
~/.pdf_converter/
├── license_config.json      # 系统配置
│   {
│     "version": "1.0.0",
│     "max_files_per_license": 20,
│     "license_prefix": "PDF",
│     "developer_key": "PDFConverter2026_SecretKey_v1.0"
│   }
│
├── license.json             # 注册信息
│   {
│     "machine_code": "D060-9F8C-3317-EC14",
│     "license_code": "PDF-D0609F8C-0001-E4F1990B",
│     "registered_at": "2026-08-18T11:17:45",
│     "status": "active"
│   }
│
└── usage.json               # 使用记录
    {
      "total_files": 1,
      "last_reset": null,
      "files": [
        {
          "filename": "test.pdf",
          "timestamp": "2026-08-18T11:18:30"
        }
      ]
    }
```

## 使用命令汇总

### 用户常用命令

```bash
# 查看帮助
python converter.py --help

# 获取机器码（首次使用）
python converter.py --get-machine-code

# 注册
python converter.py --register <机器码> <许可码>

# 查看注册状态
python converter.py --status

# PDF转Word
python converter.py --input document.pdf --format word

# PDF转Excel
python converter.py --input document.pdf --format excel

# 自动检测并转换
python converter.py --input document.pdf --auto

# Word转PDF
python converter.py --input document.docx --format pdf

# Excel转PDF
python converter.py --input document.xlsx --format pdf

# 批量转换
python converter.py --batch-dir ./documents --format pdf

# 测试模式（跳过注册检查）
python converter.py --input document.pdf --no-check
```

### 开发者常用命令

```bash
# 生成许可码
python generate_license.py <机器码> [序列号]

# 验证许可码
python verify_license.py <机器码> <许可码>

# 管理注册（备用）
python register.py --register <机器码> <许可码>
python register.py --status
python register.py --usage
python register.py --reset
```

## 安全特性

| 特性 | 实现方式 |
|------|---------|
| 机器唯一性 | 多硬件来源组合 + SHA256哈希 |
| 许可码防伪造 | HMAC-SHA256签名 + 服务端密钥 |
| 一机一许可 | 注册时验证机器码绑定 |
| 配额防篡改 | 本地JSON存储 + 实时验证 |
| 密钥保护 | 开发者密钥不存储在客户端 |

## 注意事项

1. **机器码稳定性**: 更换主要硬件（CPU/主板/网卡）可能导致机器码变化
2. **许可绑定**: 许可码与机器码绑定，不可转移
3. **配额扣除**: 每次转换调用都会扣减配额，无论成功失败
4. **数据存储**: 注册信息存储在用户家目录，卸载软件不会自动清除
5. **网络需求**: 注册和转换无需网络连接

## 故障排除

### 问题1：注册后仍提示未注册

**原因**: `register()` 方法可能未正确保存文件

**解决**:
```bash
# 清除旧数据
rm -rf ~/.pdf_converter

# 使用licensing目录的register.py重新注册
cd licensing/scripts
python register.py --register <机器码> <许可码>
```

### 问题2：无法获取机器码

**原因**: 路径计算错误

**解决**:
```bash
# 直接运行机器码提取脚本
cd licensing/scripts
python get_machine_code.py
```

### 问题3：配额显示异常

**原因**: usage.json文件损坏

**解决**:
```bash
# 重置使用计数
python register.py --reset
```

---

**开发团队**: ZCode Agent (Agnes)
**版本**: 1.0.0
**更新日期**: 2026-08-18
