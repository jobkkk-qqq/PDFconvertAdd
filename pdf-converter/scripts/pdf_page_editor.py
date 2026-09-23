#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF页面编辑模块
拆分预览PDF每页 → 删除/排序/旋转/添加（图片/Word/Excel）→ 重新合成PDF
每页可单独顺时针旋转90°（可累计），合成时应用旋转，满足统一排版样式
"""

import os
import sys
import tempfile
import shutil
import subprocess
import fitz  # PyMuPDF

import tkinter as tk
from tkinter import ttk, filedialog, messagebox

# 拖拽支持（与主程序一致）
try:
    from tkinterdnd2 import DND_FILES
    HAS_DND = True
except ImportError:
    HAS_DND = False


def find_libreoffice():
    """查找LibreOffice可执行文件"""
    import platform
    system = platform.system()
    if system == "Windows":
        paths = [
            r"C:\Program Files\LibreOffice\program\soffice.exe",
            r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
        ]
        for p in paths:
            if os.path.exists(p):
                return p
        try:
            result = subprocess.run(['where', 'soffice'], capture_output=True, text=True)
            if result.returncode == 0:
                return result.stdout.strip().split('\n')[0]
        except Exception:
            pass
    elif system == "Linux":
        for p in ["/usr/bin/libreoffice", "/usr/bin/soffice"]:
            if os.path.exists(p):
                return p
    elif system == "Darwin":
        p = "/Applications/LibreOffice.app/Contents/MacOS/soffice"
        if os.path.exists(p):
            return p
    return None


def doc_to_tmp_pdf(file_path, log_func=None):
    """Word/Excel → 临时PDF（LibreOffice），返回临时PDF路径"""
    soffice = find_libreoffice()
    if not soffice:
        raise RuntimeError("未找到LibreOffice，无法转换Word/Excel，请先安装LibreOffice")

    tmp_dir = tempfile.mkdtemp(prefix="pdf_editor_")
    if log_func:
        log_func(f"正在通过LibreOffice转换: {os.path.basename(file_path)}")

    # 独立用户配置目录，避免与本机已打开的LibreOffice实例冲突导致转换挂起
    profile = os.path.join(tempfile.gettempdir(), 'pdf_converter_lo_profile')
    try:
        os.makedirs(profile, exist_ok=True)
    except Exception:
        pass
    result = subprocess.run(
        [soffice, '--headless', '--norestore',
         f'-env:UserInstallation=file:///{profile.replace(os.sep, "/")}',
         '--convert-to', 'pdf', '--outdir', tmp_dir, file_path],
        capture_output=True, text=True, timeout=180)

    if result.returncode != 0:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        raise RuntimeError(f"LibreOffice转换失败: {(result.stderr or result.stdout or '')[:200]}")

    # 找到生成的PDF（文件名与源文件相同）
    base = os.path.splitext(os.path.basename(file_path))[0]
    pdf_path = os.path.join(tmp_dir, base + '.pdf')
    if not os.path.exists(pdf_path):
        shutil.rmtree(tmp_dir, ignore_errors=True)
        raise RuntimeError("LibreOffice转换未生成PDF文件")

    if log_func:
        log_func(f"✓ 已转换为临时PDF: {os.path.basename(pdf_path)}")
    return pdf_path


class PagePreviewWindow:
    """页面大图预览窗口：缩放/翻页/拖拽平移，旋转与编辑列表实时同步"""

    MIN_SCALE, MAX_SCALE = 0.05, 6.0

    def __init__(self, editor, pos):
        self.ed = editor
        self.item = editor.pages[pos]
        self.sub = 0        # 插入文档(tmp_pdf)内的页索引
        self.zoom = None    # None=适配窗口；否则为渲染比例（1.0=原始大小）
        self._photo = None
        self._resize_job = None

        self.win = tk.Toplevel(editor.win)
        self.win.title("页面预览")
        self.win.geometry("960x740")
        self.win.transient(editor.win)

        # 标题栏
        top = ttk.Frame(self.win, padding=(8, 6, 8, 0))
        top.pack(fill=tk.X)
        self.title_var = tk.StringVar(value="加载中...")
        ttk.Label(top, textvariable=self.title_var,
                  font=('Microsoft YaHei', 10, 'bold')).pack(side=tk.LEFT)

        # 工具栏
        bar = ttk.Frame(self.win, padding=(8, 2, 8, 4))
        bar.pack(fill=tk.X)
        ttk.Button(bar, text="◀ 上一页", width=9, command=lambda: self.nav(-1))\
            .pack(side=tk.LEFT, padx=2)
        ttk.Button(bar, text="下一页 ▶", width=9, command=lambda: self.nav(1))\
            .pack(side=tk.LEFT, padx=2)
        ttk.Separator(bar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=6)
        ttk.Button(bar, text="放大 +", width=7, command=self.zoom_in).pack(side=tk.LEFT, padx=2)
        ttk.Button(bar, text="缩小 −", width=7, command=self.zoom_out).pack(side=tk.LEFT, padx=2)
        ttk.Button(bar, text="适配窗口", width=9, command=self.fit).pack(side=tk.LEFT, padx=2)
        ttk.Button(bar, text="1:1", width=5, command=self.actual).pack(side=tk.LEFT, padx=2)
        self.zoom_var = tk.StringVar(value="适配")
        ttk.Label(bar, textvariable=self.zoom_var, width=8, anchor=tk.CENTER)\
            .pack(side=tk.LEFT, padx=2)
        ttk.Separator(bar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=6)
        ttk.Button(bar, text="旋转90°", width=8, command=self.rotate).pack(side=tk.LEFT, padx=2)
        ttk.Label(bar, text="滚轮缩放 · 拖拽平移 · Esc关闭", foreground='gray')\
            .pack(side=tk.RIGHT)

        # 画布
        mid = ttk.Frame(self.win)
        mid.pack(fill=tk.BOTH, expand=True, padx=8, pady=6)
        self.canvas = tk.Canvas(mid, bg='#404040', highlightthickness=0)
        vsb = ttk.Scrollbar(mid, orient=tk.VERTICAL, command=self.canvas.yview)
        hsb = ttk.Scrollbar(mid, orient=tk.HORIZONTAL, command=self.canvas.xview)
        self.canvas.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        hsb.pack(side=tk.BOTTOM, fill=tk.X)
        self.canvas.pack(fill=tk.BOTH, expand=True)

        # 交互
        self.canvas.bind('<MouseWheel>',
                         lambda e: self.zoom_in() if e.delta > 0 else self.zoom_out())
        self.canvas.bind('<Button-1>', self._pan_start)
        self.canvas.bind('<B1-Motion>', self._pan_move)
        self.win.bind('<Escape>', lambda e: self.close())
        self.win.protocol("WM_DELETE_WINDOW", self.close)
        self.win.bind('<Configure>', self._on_resize)

        self.show()

    # ---------- 状态 ----------

    def _pos(self):
        """当前项在编辑列表中的位置（按对象身份查找）；已被删除返回None"""
        for i, p in enumerate(self.ed.pages):
            if p is self.item:
                return i
        return None

    def _sub_total(self, item):
        """该项包含的页数（插入的Word/Excel文档可能多页，其余为1）"""
        try:
            if item['type'] == 'tmp_pdf' and os.path.exists(item['source']):
                d = fitz.open(item['source'])
                n = d.page_count
                d.close()
                return max(n, 1)
        except Exception:
            pass
        return 1

    def _page_size(self, item):
        """页面尺寸（pt/px）与子页数；失败返回None"""
        try:
            if item['type'] == 'pdf' and self.ed.pdf_doc:
                r = self.ed.pdf_doc[item['index']].rect
                return r.width, r.height
            if item['type'] == 'image':
                from PIL import Image
                with Image.open(item['source']) as im:
                    return float(im.width), float(im.height)
            if item['type'] == 'tmp_pdf' and os.path.exists(item['source']):
                d = fitz.open(item['source'])
                if d.page_count:
                    r = d[min(self.sub, d.page_count - 1)].rect
                    d.close()
                    return r.width, r.height
                d.close()
        except Exception:
            pass
        return None

    # ---------- 渲染 ----------

    def _render_pil(self, item, scale):
        """按渲染比例生成页面PIL图（应用额外旋转角），失败返回None"""
        from PIL import Image
        rot = item.get('rot', 0)
        transpose = {0: None, 90: Image.ROTATE_270, 180: Image.ROTATE_180,
                     270: Image.ROTATE_90}[rot]  # PIL角度=逆时针，PDF顺时针
        img = None
        try:
            if item['type'] == 'pdf' and self.ed.pdf_doc:
                page = self.ed.pdf_doc[item['index']]
                pix = page.get_pixmap(matrix=fitz.Matrix(scale, scale))
                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            elif item['type'] == 'image':
                img = Image.open(item['source'])
                if scale < 0.99 or scale > 1.01:
                    img = img.resize((max(1, int(img.width * scale)),
                                      max(1, int(img.height * scale))), Image.LANCZOS)
            elif item['type'] == 'tmp_pdf' and os.path.exists(item['source']):
                d = fitz.open(item['source'])
                page = d[min(self.sub, d.page_count - 1)]
                pix = page.get_pixmap(matrix=fitz.Matrix(scale, scale))
                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                d.close()
        except Exception:
            return None
        if img is None:
            return None
        if transpose is not None:
            img = img.transpose(transpose)
        return img

    def _canvas_size(self):
        """可用显示区尺寸：优先实际映射尺寸；窗口未映射时用请求尺寸兜底"""
        cw, ch = self.canvas.winfo_width(), self.canvas.winfo_height()
        if cw <= 1 or ch <= 1:
            # 布局未完成（低配机器/窗口管理器慢）：用内容请求尺寸估算
            try:
                cw, ch = self.canvas.winfo_reqwidth(), self.canvas.winfo_reqheight()
            except Exception:
                cw = ch = 0
            if cw <= 1:
                cw, ch = 900, 640
        return max(cw - 8, 50), max(ch - 8, 50)

    def show(self):
        """按当前缩放渲染页面；窗口未映射时按估算尺寸先渲染，稍后自动精化"""
        if not self.win.winfo_exists():
            return
        if self.canvas.winfo_width() > 1:
            self._retries = 0  # 窗口已映射，重置精化计数
        elif getattr(self, '_retries', 0) < 40:  # 未映射重试上限≈3秒，防止无限排队
            self._retries = getattr(self, '_retries', 0) + 1
            self.win.after(80, self.show)

        pos = self._pos()
        if pos is None:  # 该页已在主列表中删除
            self.close()
            return

        item = self.item
        size = self._page_size(item)
        cw, ch = self._canvas_size()
        if size:
            w_pt, h_pt = size
            if self.zoom is None:
                scale = min(cw / max(w_pt, 1), ch / max(h_pt, 1))
                zoom_text = "适配"
            else:
                scale = self.zoom
                zoom_text = f"{scale * 100:.0f}%"
            scale = max(self.MIN_SCALE, min(scale, self.MAX_SCALE))
            img = self._render_pil(item, scale)
        else:
            img = None
            zoom_text = "--"

        self.canvas.delete('all')
        n_sub = self._sub_total(item)
        sub_note = f"  · 文档内第 {self.sub + 1}/{n_sub} 页" if n_sub > 1 else ""
        title = f"列表第 {pos + 1}/{len(self.ed.pages)} 页 · {self.ed._item_label(item)}{sub_note}"

        if img is None:
            self._photo = None
            self.title_var.set(title + "  （无法渲染）")
            self.zoom_var.set(zoom_text)
            return

        from PIL import ImageTk
        self._photo = ImageTk.PhotoImage(img)
        iw, ih = img.size
        x = max(0, (cw - iw) // 2)
        y = max(0, (ch - ih) // 2)
        self.canvas.create_image(x, y, image=self._photo, anchor='nw')
        self.canvas.configure(scrollregion=(0, 0, max(cw, x + iw), max(ch, y + ih)))
        self.title_var.set(title)
        self.zoom_var.set(zoom_text)

    # ---------- 操作 ----------

    def nav(self, delta):
        """翻页：文档内页优先，越界后切到列表相邻页"""
        pos = self._pos()
        if pos is None:
            self.close()
            return
        n_sub = self._sub_total(self.item)
        if delta > 0:
            if self.sub + 1 < n_sub:
                self.sub += 1
            elif pos + 1 < len(self.ed.pages):
                self.item = self.ed.pages[pos + 1]
                self.sub = 0
        else:
            if self.sub > 0:
                self.sub -= 1
            elif pos - 1 >= 0:
                self.item = self.ed.pages[pos - 1]
                self.sub = self._sub_total(self.item) - 1
        self.show()

    def _fit_scale(self):
        size = self._page_size(self.item)
        if not size:
            return 1.0
        w_pt, h_pt = size
        cw, ch = self._canvas_size()
        return max(self.MIN_SCALE, min(cw / max(w_pt, 1), ch / max(h_pt, 1)))

    def zoom_in(self):
        base = self._fit_scale() if self.zoom is None else self.zoom
        self.zoom = min(base * 1.25, self.MAX_SCALE)
        self.show()

    def zoom_out(self):
        base = self._fit_scale() if self.zoom is None else self.zoom
        self.zoom = max(base * 0.8, self.MIN_SCALE)
        self.show()

    def fit(self):
        self.zoom = None
        self.show()

    def actual(self):
        self.zoom = 1.0
        self.show()

    def rotate(self):
        """旋转当前页（与主列表同步；插入文档为整份旋转）"""
        item = self.item
        item['rot'] = (item.get('rot', 0) + 90) % 360
        note = "（整份插入文档）" if self._sub_total(item) > 1 else ""
        self.ed.log(f"预览中旋转页面: {self.ed._item_label(item)}{note}")
        self.ed.refresh_preview()
        self.show()

    # ---------- 交互辅助 ----------

    def _pan_start(self, e):
        self.canvas.scan_mark(e.x, e.y)

    def _pan_move(self, e):
        self.canvas.scan_dragto(e.x, e.y, gain=1)

    def _on_resize(self, e):
        # 适配模式下窗口尺寸变化后重新居中（去抖）
        if self.zoom is None and self.win.winfo_exists():
            if self._resize_job:
                self.win.after_cancel(self._resize_job)
            self._resize_job = self.win.after(120, self.show)

    def close(self):
        try:
            self.win.destroy()
        except Exception:
            pass


class PDFPageEditor:
    """PDF页面编辑窗口"""

    def __init__(self, parent_root, checker, log_func, initial_file=None):
        self.parent = parent_root
        self.checker = checker
        self.log = log_func

        self.win = tk.Toplevel(parent_root)
        self.win.title("PDF页面编辑")
        self.win.geometry("900x620")
        self.win.transient(parent_root)

        # 页面列表: [{type: 'pdf'|'image'|'tmp_pdf', source: 路径, index: 页索引,
        #             label: 显示名, rot: 额外顺时针旋转角(0/90/180/270)}]
        self.pages = []
        self.pdf_doc = None          # 原PDF（只读）
        self.pdf_path = None
        self.thumbs = []             # PhotoImage引用（防GC）
        self.tmp_pdfs = []           # 临时PDF路径（退出时清理）
        self.thumb_w = 150           # 缩略图宽度
        self.output_dir = os.path.dirname(initial_file) if initial_file else os.path.expanduser("~")

        self.create_widgets()

        if initial_file and os.path.exists(initial_file) and initial_file.lower().endswith('.pdf'):
            self.load_pdf(initial_file)

    # ==================== 界面构建 ====================

    def create_widgets(self):
        win = self.win

        # 顶部：文件选择
        top = ttk.Frame(win, padding="8")
        top.pack(fill=tk.X)
        ttk.Label(top, text="PDF文件:").pack(side=tk.LEFT)
        self.file_var = tk.StringVar()
        entry = ttk.Entry(top, textvariable=self.file_var, width=45)
        entry.pack(side=tk.LEFT, padx=5)
        ttk.Button(top, text="打开PDF...", command=self.choose_pdf).pack(side=tk.LEFT, padx=3)
        if HAS_DND:
            entry.drop_target_register(DND_FILES)
            entry.dnd_bind('<<Drop>>', lambda e: self._drop_pdf(e))
            ttk.Label(top, text="⇩ 可拖入PDF", foreground='blue').pack(side=tk.LEFT, padx=5)

        # 信息栏
        self.info_var = tk.StringVar(value="请打开一个PDF文件")
        ttk.Label(win, textvariable=self.info_var, foreground='gray').pack(anchor=tk.W, padx=12)

        # 中间：页面缩略图（可滚动）
        mid = ttk.Frame(win)
        mid.pack(fill=tk.BOTH, expand=True, padx=8, pady=5)
        self.canvas = tk.Canvas(mid, bg='#f0f0f0', highlightthickness=0)
        vsb = ttk.Scrollbar(mid, orient=tk.VERTICAL, command=self.canvas.yview)
        hsb = ttk.Scrollbar(mid, orient=tk.HORIZONTAL, command=self.canvas.xview)
        self.canvas.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        hsb.pack(side=tk.BOTTOM, fill=tk.X)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.inner = ttk.Frame(self.canvas)
        self.canvas.create_window((0, 0), window=self.inner, anchor='nw')
        self.inner.bind('<Configure>', lambda e: self.canvas.configure(scrollregion=self.canvas.bbox('all')))

        # 底部：操作区
        bottom = ttk.LabelFrame(win, text="操作", padding="8")
        bottom.pack(fill=tk.X, padx=8, pady=5)

        add_frame = ttk.Frame(bottom)
        add_frame.pack(fill=tk.X)
        ttk.Label(add_frame, text="添加页面:").pack(side=tk.LEFT)
        ttk.Button(add_frame, text="添加图片...", command=self.add_image).pack(side=tk.LEFT, padx=3)
        ttk.Button(add_frame, text="添加PDF...", command=self.add_pdf).pack(side=tk.LEFT, padx=3)
        ttk.Button(add_frame, text="添加Word...", command=self.add_word).pack(side=tk.LEFT, padx=3)
        ttk.Button(add_frame, text="添加Excel...", command=self.add_excel).pack(side=tk.LEFT, padx=3)

        out_frame = ttk.Frame(bottom)
        out_frame.pack(fill=tk.X, pady=(8, 0))
        ttk.Label(out_frame, text="输出目录:").pack(side=tk.LEFT)
        self.out_var = tk.StringVar(value=self.output_dir)
        out_entry = ttk.Entry(out_frame, textvariable=self.out_var, width=45)
        out_entry.pack(side=tk.LEFT, padx=5)
        ttk.Button(out_frame, text="浏览...", command=self.choose_output).pack(side=tk.LEFT, padx=3)
        if HAS_DND:
            out_entry.drop_target_register(DND_FILES)
            out_entry.dnd_bind('<<Drop>>', self._drop_output)

        btn_frame = ttk.Frame(bottom)
        btn_frame.pack(fill=tk.X, pady=(10, 0))
        ttk.Label(btn_frame, text="提示: 原文件不会被修改，合成后生成新文件", foreground='gray')\
            .pack(side=tk.LEFT)
        self.merge_btn = ttk.Button(btn_frame, text="合 成 PDF", command=self.merge_pdf, width=16)
        self.merge_btn.pack(side=tk.RIGHT)

        win.protocol("WM_DELETE_WINDOW", self.close)

    # ==================== 文件操作 ====================

    def choose_pdf(self):
        path = filedialog.askopenfilename(
            title="选择PDF文件",
            filetypes=[("PDF文件", "*.pdf"), ("所有文件", "*.*")])
        if path:
            self.load_pdf(path)

    def _drop_pdf(self, event):
        try:
            files = self.win.tk.splitlist(event.data)
            if files and files[0].lower().endswith('.pdf'):
                self.load_pdf(files[0])
            elif files:
                messagebox.showwarning("提示", "请拖入PDF文件")
        except Exception as e:
            self.log(f"拖入PDF失败: {e}")

    def _drop_output(self, event):
        try:
            files = self.win.tk.splitlist(event.data)
            if files and os.path.isdir(files[0]):
                self.out_var.set(files[0])
                self.output_dir = files[0]
        except Exception:
            pass

    def choose_output(self):
        folder = filedialog.askdirectory(title="选择输出目录")
        if folder:
            self.out_var.set(folder)
            self.output_dir = folder

    def load_pdf(self, path):
        """打开并拆分预览PDF"""
        try:
            if self.pdf_doc:
                self.pdf_doc.close()
            self.pdf_doc = fitz.open(path)
            self.pdf_path = path
            self.file_var.set(path)
            self.output_dir = os.path.dirname(path)
            self.out_var.set(self.output_dir)

            # 初始化页面列表（全部原PDF页）
            self.pages = []
            for i in range(len(self.pdf_doc)):
                self.pages.append({'type': 'pdf', 'source': path, 'index': i, 'rot': 0})
            self.info_var.set(f"已打开: {os.path.basename(path)} (共{len(self.pages)}页)")
            self.log(f"PDF页面编辑: 打开 {os.path.basename(path)}，共{len(self.pages)}页")
            self.refresh_preview()
        except Exception as e:
            messagebox.showerror("错误", f"打开PDF失败: {e}")
            self.log(f"打开PDF失败: {e}")

    # ==================== 预览 ====================

    def open_preview(self, pos):
        """打开页面大图预览窗口"""
        if 0 <= pos < len(self.pages):
            try:
                PagePreviewWindow(self, pos)
            except Exception as e:
                self.log(f"打开预览失败: {e}")
                messagebox.showerror("错误", f"打开预览失败:\n{e}")

    def refresh_preview(self):
        """重建缩略图列表"""
        # 清空
        for child in self.inner.winfo_children():
            child.destroy()
        self.thumbs = []

        if not self.pdf_doc and not self.pages:
            return

        self.info_var.set(f"共 {len(self.pages)} 页  (点击缩略图放大预览；可删除/排序/旋转/添加页面，原文件不变)")

        cols = 4  # 每行4个卡片
        for pos, item in enumerate(self.pages):
            row, col = divmod(pos, cols)
            card = ttk.Frame(self.inner, relief='groove', borderwidth=2, padding=5)
            card.grid(row=row, column=col, padx=6, pady=6, sticky='n')

            # 点击缩略图打开大图预览（排版时看不清内容）
            open_preview = lambda p=pos: self.open_preview(p)
            for w in (card,):
                w.bind('<Button-1>', lambda e, p=pos: self.open_preview(p))
                w.bind('<Double-Button-1>', lambda e, p=pos: self.open_preview(p))

            # 缩略图
            thumb = self._render_thumb(item)
            if thumb:
                self.thumbs.append(thumb)
                lbl = ttk.Label(card, image=thumb, cursor='hand2')
                lbl.pack()
                lbl.bind('<Button-1>', open_preview)
                lbl.bind('<Double-Button-1>', open_preview)
            else:
                lbl = ttk.Label(card, text="(无法预览)\n点击查看大图", cursor='hand2')
                lbl.pack(pady=20)
                lbl.bind('<Button-1>', open_preview)
                lbl.bind('<Double-Button-1>', open_preview)

            # 标签（含旋转角提示；可点击预览）
            label = self._item_label(item)
            lbl2 = ttk.Label(card, text=label, foreground='blue', cursor='hand2')
            lbl2.pack(pady=(3, 0))
            lbl2.bind('<Button-1>', open_preview)
            lbl2.bind('<Double-Button-1>', open_preview)

            # 按钮
            btns = ttk.Frame(card)
            btns.pack(pady=3)
            ttk.Button(btns, text="↑", width=3,
                       command=lambda p=pos: self.move_up(p)).pack(side=tk.LEFT, padx=1)
            ttk.Button(btns, text="↓", width=3,
                       command=lambda p=pos: self.move_down(p)).pack(side=tk.LEFT, padx=1)
            ttk.Button(btns, text="旋转", width=5,
                       command=lambda p=pos: self.rotate_page(p)).pack(side=tk.LEFT, padx=1)
            ttk.Button(btns, text="删除", width=5,
                       command=lambda p=pos: self.delete_page(p)).pack(side=tk.LEFT, padx=1)
            ttk.Button(btns, text="🔍预览", width=6,
                       command=lambda p=pos: self.open_preview(p)).pack(side=tk.LEFT, padx=1)

    def _render_thumb(self, item):
        """渲染缩略图（应用额外旋转角），返回PhotoImage（无则None）"""
        try:
            from PIL import Image, ImageTk
            rot = item.get('rot', 0)
            pil_rotate = {0: None, 90: Image.ROTATE_270, 180: Image.ROTATE_180,
                          270: Image.ROTATE_90}[rot]  # PIL角度=逆时针，PDF顺时针
            if item['type'] == 'pdf' and self.pdf_doc:
                page = self.pdf_doc[item['index']]
                zoom = self.thumb_w / max(page.rect.width, 1)
                pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom))
                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                if pil_rotate is not None:
                    img = img.transpose(pil_rotate)
                return ImageTk.PhotoImage(img)
            elif item['type'] == 'image':
                img = Image.open(item['source'])
                ratio = self.thumb_w / max(img.width, 1)
                img = img.resize((self.thumb_w, max(1, int(img.height * ratio))))
                if pil_rotate is not None:
                    img = img.transpose(pil_rotate)
                return ImageTk.PhotoImage(img)
            elif item['type'] == 'tmp_pdf':
                if os.path.exists(item['source']):
                    d = fitz.open(item['source'])
                    if len(d) > 0:
                        page = d[0]
                        zoom = self.thumb_w / max(page.rect.width, 1)
                        pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom))
                        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                        d.close()
                        if pil_rotate is not None:
                            img = img.transpose(pil_rotate)
                        return ImageTk.PhotoImage(img)
                    d.close()
        except Exception:
            pass
        return None

    def _item_label(self, item):
        rot = item.get('rot', 0)
        rot_note = f" ↻{rot}°" if rot else ""
        if item['type'] == 'pdf':
            return f"原页 {item['index'] + 1}{rot_note}"
        elif item['type'] == 'image':
            return f"图片: {os.path.basename(item['source'])[:14]}{rot_note}"
        else:
            kind = {'word': 'Word:', 'excel': 'Excel:', 'pdf': 'PDF:'}.get(
                item.get('kind'), '')
            return f"{kind}{os.path.splitext(os.path.basename(item['source']))[0][:14]}{rot_note}"

    # ==================== 增删排序 ====================

    def delete_page(self, pos):
        if 0 <= pos < len(self.pages):
            removed = self.pages.pop(pos)
            self.log(f"删除页面: {self._item_label(removed)}")
            self.refresh_preview()

    def rotate_page(self, pos):
        """页面顺时针旋转90°（累计，可连续旋转到180°/270°）"""
        if 0 <= pos < len(self.pages):
            item = self.pages[pos]
            item['rot'] = (item.get('rot', 0) + 90) % 360
            self.log(f"旋转页面: {self._item_label(item)}")
            self.refresh_preview()

    def move_up(self, pos):
        if pos > 0:
            self.pages[pos], self.pages[pos - 1] = self.pages[pos - 1], self.pages[pos]
            self.refresh_preview()

    def move_down(self, pos):
        if pos < len(self.pages) - 1:
            self.pages[pos], self.pages[pos + 1] = self.pages[pos + 1], self.pages[pos]
            self.refresh_preview()

    def add_image(self):
        """添加图片页"""
        files = filedialog.askopenfilenames(
            title="选择图片（可多选）",
            filetypes=[("图片文件", "*.png;*.jpg;*.jpeg;*.bmp;*.gif"), ("所有文件", "*.*")])
        for f in files:
            self.pages.append({'type': 'image', 'source': f, 'index': None, 'rot': 0})
            self.log(f"添加图片页: {os.path.basename(f)}")
        if files:
            self.refresh_preview()

    def add_pdf(self):
        """添加PDF页（直接引用源文件的所有页面，多页支持）"""
        files = filedialog.askopenfilenames(
            title="选择PDF文件（可多选）",
            filetypes=[("PDF文件", "*.pdf"), ("所有文件", "*.*")])
        if not files:
            return
        for f in files:
            try:
                d = fitz.open(f)
                pages_count = len(d)
                d.close()
                # 直接引用源PDF（不复制到临时目录，也不加入清理列表，避免误删用户文件）
                self.pages.append({'type': 'tmp_pdf', 'source': f, 'kind': 'pdf',
                                   'index': None, 'rot': 0})
                self.log(f"添加PDF页: {os.path.basename(f)} ({pages_count}页)")
            except Exception as e:
                messagebox.showerror("错误", f"打开PDF失败: {os.path.basename(f)}\n{e}")
                self.log(f"添加PDF失败: {os.path.basename(f)}: {e}")
        if files:
            self.refresh_preview()

    def add_word(self):
        """添加Word页（LibreOffice转临时PDF）"""
        files = filedialog.askopenfilenames(
            title="选择Word文件（可多选）",
            filetypes=[("Word文件", "*.docx;*.doc"), ("所有文件", "*.*")])
        if not files:
            return
        try:
            for f in files:
                pdf_path = doc_to_tmp_pdf(f, self.log)
                self.tmp_pdfs.append(pdf_path)
                d = fitz.open(pdf_path)
                pages_count = len(d)
                d.close()
                self.pages.append({'type': 'tmp_pdf', 'source': pdf_path, 'kind': 'word',
                                   'index': None, 'rot': 0})
                self.log(f"添加Word页: {os.path.basename(f)} ({pages_count}页)")
            self.refresh_preview()
        except Exception as e:
            messagebox.showerror("错误", str(e))
            self.log(f"添加Word失败: {e}")

    def add_excel(self):
        """添加Excel页（LibreOffice转临时PDF）"""
        files = filedialog.askopenfilenames(
            title="选择Excel文件（可多选）",
            filetypes=[("Excel文件", "*.xlsx;*.xls"), ("所有文件", "*.*")])
        if not files:
            return
        try:
            for f in files:
                pdf_path = doc_to_tmp_pdf(f, self.log)
                self.tmp_pdfs.append(pdf_path)
                d = fitz.open(pdf_path)
                pages_count = len(d)
                d.close()
                self.pages.append({'type': 'tmp_pdf', 'source': pdf_path, 'kind': 'excel',
                                   'index': None, 'rot': 0})
                self.log(f"添加Excel页: {os.path.basename(f)} ({pages_count}页)")
            self.refresh_preview()
        except Exception as e:
            messagebox.showerror("错误", str(e))
            self.log(f"添加Excel失败: {e}")

    # ==================== 合成 ====================

    def merge_pdf(self):
        """按页面列表顺序合成新PDF"""
        if not self.pages:
            messagebox.showwarning("提示", "没有可合成的页面")
            return

        if not self.checker.is_registered():
            messagebox.showwarning("警告", "请先注册")
            return
        usage = self.checker.get_usage()
        if usage.get('files_remaining', 0) <= 0:
            messagebox.showerror("错误", "配额已用完，请联系开发者")
            return

        # 输出路径
        output_dir = self.out_var.get().strip()
        if not output_dir or not os.path.exists(output_dir):
            try:
                os.makedirs(output_dir, exist_ok=True)
            except Exception:
                output_dir = os.path.dirname(self.pdf_path) if self.pdf_path else os.path.expanduser("~")
                self.out_var.set(output_dir)

        if self.pdf_path:
            base = os.path.splitext(os.path.basename(self.pdf_path))[0]
        else:
            base = "merged"
        output_path = os.path.join(output_dir, f"{base}_编辑后.pdf")

        self.log(f"开始合成PDF: 共{len(self.pages)}页 → {output_path}")
        self.merge_btn.config(state='disabled')
        self.win.update()

        try:
            out = fitz.open()
            src_doc = None
            if self.pdf_path and os.path.exists(self.pdf_path):
                src_doc = fitz.open(self.pdf_path)

            for item in self.pages:
                n0 = out.page_count
                if item['type'] == 'pdf':
                    if src_doc:
                        out.insert_pdf(src_doc, from_page=item['index'], to_page=item['index'])
                elif item['type'] == 'image':
                    self._insert_image_page(out, item['source'])
                elif item['type'] == 'tmp_pdf':
                    if os.path.exists(item['source']):
                        tmp = fitz.open(item['source'])
                        out.insert_pdf(tmp)
                        tmp.close()
                # 对本次新插入的页面应用额外旋转角（与页面已有旋转叠加）
                rot = item.get('rot', 0)
                if rot:
                    for p in range(n0, out.page_count):
                        page = out[p]
                        page.set_rotation((page.rotation + rot) % 360)

            if src_doc:
                src_doc.close()
            # 输出文件已存在时避免覆盖，自动加序号
            final_path = output_path
            if os.path.exists(output_path):
                base, ext = os.path.splitext(output_path)
                seq = 1
                while os.path.exists(f"{base}_{seq}{ext}"):
                    seq += 1
                final_path = f"{base}_{seq}{ext}"
            out.save(final_path, garbage=3, deflate=True)
            out.close()

            # 扣配额
            allowed, msg = self.checker.check_and_increment(os.path.basename(self.pdf_path or "pdf_edit"))
            rotated_n = sum(1 for it in self.pages if it.get('rot'))
            self.log(f"✓ 合成成功: {final_path} ({len(self.pages)}页，含旋转{rotated_n}页)")
            self.log(msg)
            messagebox.showinfo("成功", f"PDF合成成功！\n\n输出文件:\n{final_path}\n\n{msg}")

        except Exception as e:
            self.log(f"✗ 合成失败: {e}")
            messagebox.showerror("错误", f"合成失败:\n{str(e)}")
        finally:
            self.merge_btn.config(state='normal')

    def _insert_image_page(self, out, img_path):
        """插入图片页（A4比例居中缩放）"""
        from PIL import Image
        im = Image.open(img_path)
        w, h = im.size
        im.close()
        page_w, page_h = 595.0, 842.0  # A4 pt
        margin = 28.0
        scale = min((page_w - margin * 2) / max(w, 1), (page_h - margin * 2) / max(h, 1))
        scale = min(scale, 1.0)  # 不放大
        iw, ih = w * scale, h * scale
        x0 = (page_w - iw) / 2
        y0 = (page_h - ih) / 2
        page = out.new_page(width=page_w, height=page_h)
        page.insert_image(fitz.Rect(x0, y0, x0 + iw, y0 + ih), filename=img_path)

    # ==================== 关闭清理 ====================

    def close(self):
        """关闭窗口并清理临时文件"""
        try:
            if self.pdf_doc:
                self.pdf_doc.close()
            for tmp in self.tmp_pdfs:
                tmp_dir = os.path.dirname(tmp)
                shutil.rmtree(tmp_dir, ignore_errors=True)
        except Exception:
            pass
        self.win.destroy()
