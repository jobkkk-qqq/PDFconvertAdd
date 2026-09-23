# PDF转换器注册系统

## 概述

本目录包含PDF转换器的注册和许可管理系统。用户需要注册后才能使用转换功能，每个许可最多可转换20个文件。

## 项目结构

```
licensing/
├── scripts/
│   ├── get_machine_code.py    # 机器码提取工具（用户端）
│   ├── generate_license.py    # 许可码生成工具（开发者端）
│   ├── verify_license.py      # 许可码验证工具
│   └── register.py            # 注册管理工具
└── references/                # 参考资料目录
```

## 快速开始

### 1. 获取机器码（用户）

```bash
cd licensing/scripts
python get_machine_code.py
```

输出示例：
```
============================================================
您的机器码:
  D060-9F8C-3317-EC14
============================================================
```

### 2. 联系开发者获取许可码

将机器码发送给开发者，开发者会使用 `generate_license.py` 生成许可码。

### 3. 注册（用户）

```bash
python register.py --register <机器码> <许可码>
```

示例：
```bash
python register.py --register D060-9F8C-3317-EC14 PDF-D0609F8C-0001-E4F1990B
```

### 4. 查看注册状态

```bash
python register.py --status
python register.py --usage
```

## 开发者工具

### 生成许可码

```bash
python generate_license.py <机器码> [序列号]
```

示例：
```bash
python generate_license.py D060-9F8C-3317-EC14
python generate_license.py D060-9F8C-3317-EC14 2
```

### 验证许可码

```bash
python verify_license.py <机器码> <许可码>
```

## 许可规则

| 项目 | 说明 |
|------|------|
| 文件限制 | 每个许可最多转换 20 个文件 |
| 机器绑定 | 许可码与机器码绑定，不可转移 |
| 有效期 | 永久有效（除非开发者撤销） |
| 重复注册 | 同一机器只能注册一次 |

## 技术实现

### 机器码生成

1. 收集硬件信息：
   - CPU ID
   - 主板序列号
   - MAC地址
   - 硬盘序列号

2. 使用SHA256哈希算法生成唯一机器码
3. 格式化为易读格式：`XXXX-XXXX-XXXX-XXXX`

### 许可码生成

1. 格式：`PDF-{机器码前8位}-{序列号}-{校验位}`
2. 校验位使用HMAC-SHA256签名
3. 开发者密钥用于签名验证

### 数据存储

配置文件存储在用户家目录：
- Windows: `%USERPROFILE%\.pdf_converter\`
- Linux/macOS: `~/.pdf_converter/`

文件说明：
- `license_config.json` - 系统配置
- `license.json` - 注册信息
- `usage.json` - 使用记录

## 安全注意事项

1. **开发者密钥**应安全存储，不要提交到公开仓库
2. **机器码**基于硬件信息，但可能在某些情况下变化
3. **许可码**可验证，但不防逆向工程
4. 生产环境建议使用更严格的授权机制

## 扩展开发

### 添加新的验证方式

修改 `verify_license_code()` 函数以支持其他验证方法。

### 调整文件限制

修改 `MAX_FILE_LIMIT` 常量或配置文件中的 `max_files_per_license` 参数。

### 添加过期时间

在许可码中添加时间戳信息，实现过期机制。

## 许可证

MIT License
