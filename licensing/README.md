# PDF转换器注册系统

## 概述

本目录包含 PDF 转换器的注册和许可管理系统。用户需要注册后才能使用转换功能，**每个许可最多可转换 20 个文件**。

许可码使用 **Ed25519 非对称签名**（RFC 8032）：

- 本仓库（含打包出的程序）里只有**公钥** —— 它只能验签，**不能生成**许可码；
- 签名用的**私钥**、以及**发码工具**都放在**本仓库之外**（见下节），不进仓库、不进 exe。

（旧版用对称 HMAC，验签密钥必须随程序分发，等于把发码器交给每个用户；现已弃用，旧格式许可码全部失效。）

## 项目结构

```
licensing/
├── scripts/
│   ├── get_machine_code.py      # 机器码提取工具（用户端）
│   ├── license_verify.py        # 许可码**验签**（只读，只有公钥，不能发码）
│   ├── verify_license.py        # 许可码验证工具（命令行）
│   ├── register.py              # 注册管理工具
│   └── ed25519.py               # 纯标准库 Ed25519 实现（验签用，无第三方依赖）
└── README.md
```

> 发码（签名）程序**不在本仓库**：它需要私钥，与私钥一起放在仓库外，例如
> `<仓库根>/../license-keys/`（本机约定位置）。那边通常有 `make-license.bat` 与打包好的
> `LicenseGenerator.exe` / `LicenseGenerator-cli.exe`，用法：输入机器码 → 得到许可码。
> 本仓库不再包含任何生成注册码的代码或打包配置。

## 私钥与发码工具放哪（开发者必读）

发码端与私钥都在仓库外，默认约定：

```
<仓库根>/../license-keys/
├── license-private-key.json        # 私钥（32 字节 seed，或含 privateSeedHex 的 JSON）
├── license-public-key.json
├── make-license.bat                # 一键发码
├── LicenseGenerator.exe            # 图形界面发码
├── LicenseGenerator-cli.exe        # 命令行发码
└── generators/                     # 发码工具源码（按产品分目录）
```

私钥文件可以是 JSON（含 `privateSeedHex`），也可以是一行 64 位十六进制的私钥种子。

> ⚠️ 私钥**一旦丢失**，就无法再给老用户发新码（只能换密钥对并让所有用户重新注册）。请务必备份。
> 本仓库的 `.gitignore` 已排除 `license-keys/`、`*private-key*.json` 等私钥相关文件。

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
  56BA-91C4-AD56-9ACA
============================================================
```

### 2. 联系开发者获取许可码

把机器码发给开发者，开发者在**仓库外的发码工具**里生成许可码（首次注册用序列号 1，续期用更大的序列号）。

许可码形如（**很长，请完整复制粘贴，不要手输**）：

```
PDF-56BA91C4-0001-67LTR57D6STCN4KO7236ZR6EFNDQCYRMW75LJXTBX2HVCAGBOO6CG5IWXC2GB2FD373O6QNVBZTMNIR4E6BFIUUIGFNC743HGLFYUCQ
```

### 3. 注册（用户）

```bash
python register.py --register <机器码> <许可码>
```

GUI 版客户端可直接点"注册"按钮：机器码已自动填好，粘贴许可码即可。

### 4. 验证许可码（可选）

```bash
python verify_license.py <机器码> <许可码>
```

### 5. 查看注册状态

```bash
python register.py --status
python register.py --usage
```

## 许可规则

| 项目 | 说明 |
|------|------|
| 文件限制 | 每个许可最多转换 **20** 个文件 |
| 机器绑定 | 许可码与机器码绑定，不可转移到别的机器 |
| 序号续期 | 用满后需重新注册，且新码的**序列号必须更大**（旧码不能重复使用） |
| 防伪 | 签名不可伪造；程序内只有公钥，改程序也造不出有效码 |

## 技术实现

### 机器码生成

1. 收集硬件信息（能取到才加入）：CPU ID、主板型号、MAC 地址、硬盘序列号
2. `SHA256("CPU:x|BOARD:x|MAC:x|HDD:x")` 取前 16 位十六进制
3. 格式化为 `XXXX-XXXX-XXXX-XXXX`

> MAC 取自 `uuid.getnode()`（Windows 上即 `UuidCreateSequential`，主网卡地址）。
> 换主板或换网卡会导致机器码变化，需要重新发码。

### 许可码构成

| 段 | 说明 |
|----|------|
| `PDF` | 固定前缀 |
| `XXXXXXXX` | 机器码前 8 位（绑定机器） |
| `NNNN` | 序列号（第几次授权），续期即把它 +1 |
| `<Base32>` | **Ed25519 签名**（64 字节 → Base32 103 字符，无填充） |

- 被签名内容：UTF-8 字符串 `PDF-{机器码前8位}-{序列号4位}`
- 签名必须完整保留（**不能截断**），这是整串码长达 121 字符的原因
- 验签端（`license_verify.py` / 客户端）用内置公钥 + 许可码内嵌的序列号重算消息，因此天然支持续期

### 数据存储

配置文件存储在用户家目录：

- Windows: `%USERPROFILE%\.pdf_converter\`
- Linux/macOS: `~/.pdf_converter/`

文件说明：

- `license_config.json` - 系统配置（**不再含任何密钥**）
- `license.json` - 注册信息（机器码、许可码、序列号）
- `usage.json` - 使用记录

## 安全注意事项

1. **公钥**可以公开（它就写在程序里），**私钥**必须留在开发者本机并做好备份，且不要放进本仓库
2. **机器码**基于硬件信息，换硬件会变
3. 许可码无法伪造，但客户端仍可被逆向后打补丁绕过——本机制防的是"自己造码"，不是防破解
4. 旧版 HMAC 密钥 `PDFConverter2026_SecretKey_v1.0` 已公开，**视为已泄露、已废弃**

## 扩展开发

- 调整文件限制：改 `licensing/scripts/license_verify.py` 的 `MAX_FILE_LIMIT`，以及客户端
  `pdf-converter/scripts/license_checker.py`、`converter_gui.py` 里的配额默认值（配置项 `max_files_per_license`）
- 换密钥对：重新生成 Ed25519 密钥对后，把新**公钥**同步到 `licensing/scripts/license_verify.py`、
  `pdf-converter/scripts/license_checker.py`、`pdf-converter/scripts/converter_gui.py`，
  并把新私钥放到仓库外的发码端
- 添加过期时间：可在被签名消息里加入到期日期，由验签端解析

## 许可证

MIT License
