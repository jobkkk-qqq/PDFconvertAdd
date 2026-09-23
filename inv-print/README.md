# 发票打印（独立版 / InvPrint）

将 **B5 发票在 A4 纸上上下排列两份、一次成版** 的独立小程序。
排版完成后使用 **Windows 默认 PDF 程序** 打开（自带打印预览），也可直接调系统默认打印机打印。

## 运行

### 图形界面（推荐）
运行目录版启动器：`dist\InvPrint\InvPrint.exe`
（onedir 结构，运行库在 exe 同目录，请保持整个 `InvPrint` 文件夹完整；启动比单文件更快，无需每次解压。）
1. 点击「浏览…」选择发票 PDF（建议为 B5 尺寸）。
2. 点击「排版并预览」→ 用系统默认 PDF 程序打开，其中可打印预览并打印；
   或点击「排版并打印」→ 直接调系统默认打印机。

### 命令行
```bash
InvPrint.exe 发票.pdf            # 排版后打开默认PDF程序预览
InvPrint.exe --print 发票.pdf    # 排版后直接调用系统默认打印
```

## 排版规则
- 发票按原尺寸等比缩放；
- 在 A4 纸上上下排列 **2 份**，水平居中，带边距与间隔。

## 源码
- `inv_print.py` —— 主程序（自带排版核心，不依赖主项目）

## 打包
```bash
pip install pyinstaller pymupdf
pyinstaller --noconfirm --clean --distpath dist --workpath build build.spec
```
产物：`dist\InvPrint.exe`