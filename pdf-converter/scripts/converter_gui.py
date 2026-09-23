#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF转换器 - GUI版本（自包含单文件）
所有核心逻辑内嵌，打包后无需依赖外部脚本
"""

import os
import sys
import json
import re
import hashlib
import hmac
import subprocess
import platform
from datetime import datetime

# ============================================================
# 第一部分: 机器码生成逻辑（原 get_machine_code.py）
# ============================================================

def get_cpu_id():
    """获取CPU ID"""
    system = platform.system()
    if system == "Windows":
        try:
            import winreg
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                                 r"HARDWARE\DESCRIPTION\System\CentralProcessor\0")
            cpu_id, _ = winreg.QueryValueEx(key, "ProcessorId")
            winreg.CloseKey(key)
            if cpu_id:
                return str(cpu_id).strip()
        except Exception:
            pass
        try:
            result = subprocess.run(['wmic', 'cpu', 'get', 'ProcessorId'],
                                    capture_output=True, text=True, timeout=10)
            for line in result.stdout.strip().split('\n'):
                if line.strip() and line.strip() != 'ProcessorId':
                    return line.strip()
        except Exception:
            pass
    elif system == "Linux":
        try:
            with open('/proc/cpuinfo', 'r') as f:
                for line in f:
                    if line.startswith('processor id'):
                        return line.split(':')[1].strip().upper()
        except Exception:
            pass
    elif system == "Darwin":
        try:
            result = subprocess.run(['sysctl', 'machdep.cpu.brand_string'],
                                    capture_output=True, text=True)
            return hashlib.sha256(result.stdout.encode()).hexdigest()[:16].upper()
        except Exception:
            pass
    return None


def get_board_id():
    """获取主板序列号"""
    system = platform.system()
    if system == "Windows":
        try:
            result = subprocess.run(['wmic', 'baseboard', 'get', 'Product'],
                                    capture_output=True, text=True, timeout=10)
            for line in result.stdout.strip().split('\n'):
                if line.strip() and line.strip() != 'Product':
                    return line.strip()
        except Exception:
            pass
        try:
            result = subprocess.run(['wmic', 'computersystem', 'get', 'UUID'],
                                    capture_output=True, text=True, timeout=10)
            for line in result.stdout.strip().split('\n'):
                if line.strip() and line.strip() != 'UUID':
                    return line.strip()
        except Exception:
            pass
    elif system == "Linux":
        try:
            with open('/sys/class/dmi/id/board_serial', 'r') as f:
                return f.read().strip().upper()
        except Exception:
            pass
    elif system == "Darwin":
        try:
            result = subprocess.run(['system_profiler', 'SPHardwareDataType'],
                                    capture_output=True, text=True)
            for line in result.stdout.split('\n'):
                if 'Serial Number (system)' in line:
                    return line.split(':')[1].strip().upper()
        except Exception:
            pass
    return None


def get_mac_address():
    """获取网卡MAC地址"""
    try:
        import uuid
        mac = uuid.getnode()
        if mac:
            return ':'.join(('%012x' % mac)[i:i+2] for i in range(0, 12, 2)).upper()
    except Exception:
        pass
    return None


def get_hdd_serial():
    """获取硬盘序列号"""
    system = platform.system()
    if system == "Windows":
        try:
            result = subprocess.run(['wmic', 'diskdrive', 'get', 'SerialNumber'],
                                    capture_output=True, text=True, timeout=10)
            for line in result.stdout.strip().split('\n'):
                if line.strip() and line.strip() != 'SerialNumber':
                    return line.strip()
        except Exception:
            pass
    return None


def generate_machine_code():
    """生成机器码"""
    components = []
    cpu_id = get_cpu_id()
    board_id = get_board_id()
    mac_addr = get_mac_address()
    hdd_serial = get_hdd_serial()

    if cpu_id:
        components.append(f"CPU:{cpu_id}")
    if board_id:
        components.append(f"BOARD:{board_id}")
    if mac_addr:
        components.append(f"MAC:{mac_addr}")
    if hdd_serial:
        components.append(f"HDD:{hdd_serial}")

    if not components:
        # 兜底：使用主机名+用户目录
        raw = f"HOST:{platform.node()}|USER:{os.path.expanduser('~')}"
        components.append(f"FALLBACK:{platform.node()}")

    raw_string = "|".join(components)
    hash_obj = hashlib.sha256(raw_string.encode('utf-8'))
    machine_code = hash_obj.hexdigest().upper()

    # 格式化为 XXXX-XXXX-XXXX-XXXX
    code_part = machine_code[:16]
    groups = [code_part[i:i+4] for i in range(0, 16, 4)]
    return "-".join(groups), components


# ============================================================
# 第二部分: 许可码验证逻辑（原 generate_license.py）
# ============================================================

DEVELOPER_SECRET = "PDFConverter2026_SecretKey_v1.0"


def verify_license_code(license_code, machine_code):
    """验证许可码是否有效"""
    pattern = r'^PDF-[A-F0-9]{8}-\d{4}-[A-F0-9]{8}$'
    if not re.match(pattern, license_code.upper()):
        return False, "许可码格式无效"

    machine_pattern = r'^[A-F0-9]{4}-[A-F0-9]{4}-[A-F0-9]{4}-[A-F0-9]{4}$'
    if not re.match(machine_pattern, machine_code.upper()):
        return False, "机器码格式无效"

    license_code = license_code.upper()
    machine_code = machine_code.upper()

    # 提取许可码组成部分
    m = re.match(r'^PDF-([A-F0-9]{8})-(\d{4})-([A-F0-9]{8})$', license_code)
    machine_prefix = machine_code.replace('-', '')[:8]

    if m.group(1) != machine_prefix:
        return False, "许可码与机器码不匹配"

    # 重新计算校验位
    message = f"PDF-{machine_prefix}-{m.group(2)}"
    expected = hmac.new(DEVELOPER_SECRET.encode('utf-8'),
                        message.encode('utf-8'),
                        hashlib.sha256).hexdigest()[:8].upper()

    if m.group(3) == expected:
        return True, "许可码有效"
    else:
        return False, "许可码校验失败"


# ============================================================
# 第三部分: 文档转换逻辑
# ============================================================

def find_libreoffice():
    """查找LibreOffice可执行文件"""
    system = platform.system()
    if system == "Windows":
        possible_paths = [
            r"C:\Program Files\LibreOffice\program\soffice.exe",
            r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
        ]
        for path in possible_paths:
            if os.path.exists(path):
                return path
        try:
            result = subprocess.run(['where', 'soffice'], capture_output=True, text=True)
            if result.returncode == 0:
                return result.stdout.strip().split('\n')[0]
        except Exception:
            pass
    elif system == "Linux":
        for path in ["/usr/bin/libreoffice", "/usr/bin/soffice"]:
            if os.path.exists(path):
                return path
    elif system == "Darwin":
        path = "/Applications/LibreOffice.app/Contents/MacOS/soffice"
        if os.path.exists(path):
            return path
    return None


_image_pdf_cache = {}  # 图片型PDF检测结果缓存（同一文件多次检测时避免重复解析）


def detect_image_pdf(pdf_path, log_func=None):
    """检测是否为图片型PDF（扫描件）：页面被大面积图片覆盖"""
    import fitz
    cache_key = f"{pdf_path}|{os.path.getmtime(pdf_path):.0f}" if os.path.exists(pdf_path) else pdf_path
    if cache_key in _image_pdf_cache:
        return _image_pdf_cache[cache_key]
    result = False
    try:
        doc = fitz.open(pdf_path)
        total_pages = max(len(doc), 1)
        image_pages = 0  # 页面有大面积图片的页数

        for page in doc:
            page_area = page.rect.width * page.rect.height
            has_large_image = False
            for img in page.get_images(full=True):
                rects = page.get_image_rects(img[0])
                for rect in rects:
                    img_area = rect.width * rect.height
                    if img_area > page_area * 0.5:  # 图片覆盖页面一半以上
                        has_large_image = True
                        break
                if has_large_image:
                    break
            if has_large_image:
                image_pages += 1

        doc.close()

        # 一半以上页面被大面积图片覆盖 → 图片型PDF（扫描件）
        if image_pages >= total_pages * 0.5:
            result = True
    except Exception:
        pass
    _image_pdf_cache[cache_key] = result
    return result


def extract_images(pdf_path, output_dir, log_func=None):
    """提取PDF中的图片到输出目录（图片型PDF的内容保全方案）"""
    import fitz
    doc = fitz.open(pdf_path)
    saved = []
    for i, page in enumerate(doc):
        imgs = page.get_images(full=True)
        for j, img in enumerate(imgs):
            xref = img[0]
            try:
                pix = fitz.Pixmap(doc, xref)
                if pix.n > 3:
                    pix = fitz.Pixmap(fitz.csRGB, pix)
                out_name = f"第{i+1}页_图片{j+1}.png"
                out_path = os.path.join(output_dir, out_name)
                pix.save(out_path)
                saved.append(out_path)
                if log_func:
                    log_func(f"  已提取: {out_name} ({pix.width}x{pix.height})")
            except Exception as e:
                if log_func:
                    log_func(f"  提取图片失败: {e}")
    doc.close()
    return saved


def collect_watermark_lines(pdf_doc):
    """跨页统计文本行：出现在大多数页面(>=60%)的短行(<=15字符)视为水印"""
    from collections import Counter
    pages_text = []
    for page in pdf_doc:
        lines = [l.strip() for l in page.get_text().split('\n') if l.strip()]
        pages_text.append(lines)

    total_pages = max(len(pages_text), 1)
    page_freq = Counter()
    for lines in pages_text:
        page_freq.update(set(lines))  # 每页相同行只计一次

    watermark_lines = set()
    for line, pages in page_freq.items():
        if pages >= total_pages * 0.6 and len(line) <= 15:
            watermark_lines.add(line)
    return watermark_lines, pages_text


def filter_watermark_text(text):
    """过滤PDF文本中的水印（单页内重复出现多次的短文本，兜底方案）"""
    if not text:
        return ""
    lines = [l.strip() for l in text.split('\n') if l.strip()]
    if not lines:
        return ""
    from collections import Counter
    counter = Counter(lines)
    total = max(len(lines), 1)
    # 水印特征：出现次数 >= max(3, 行数*25%) 且 行较短（<=15字符）
    filtered = []
    for l in lines:
        freq = counter[l]
        is_watermark = (freq >= max(3, int(total * 0.25))) and len(l) <= 15
        if not is_watermark:
            filtered.append(l)
    return '\n'.join(filtered)


_ocr_engine = None  # OCR引擎单例（懒加载）


def get_ocr_engine(log_func=None):
    """获取OCR引擎（懒加载，首次调用时初始化）"""
    global _ocr_engine
    if _ocr_engine is None:
        if log_func:
            log_func("正在初始化OCR识别引擎（首次使用需加载模型，约3秒）...")
        from rapidocr_onnxruntime import RapidOCR
        _ocr_engine = RapidOCR()
        if log_func:
            log_func("✓ OCR识别引擎就绪")
    return _ocr_engine


def ocr_image(img_path, log_func=None):
    """OCR识别图片中的文字，返回按阅读顺序排列的文字行列表"""
    try:
        engine = get_ocr_engine(log_func)
        # 降低分辨率加速（最长边1600px，识别精度影响很小）
        from PIL import Image
        img = Image.open(img_path)
        max_side = max(img.size)
        if max_side > 1600:
            ratio = 1600 / max_side
            img = img.resize((int(img.width * ratio), int(img.height * ratio)), Image.LANCZOS)
            tmp_small = os.path.join(tempfile.gettempdir(), 'ocr_small.png')
            img.save(tmp_small)
            result, elapse = engine(tmp_small)
            try:
                os.remove(tmp_small)
            except Exception:
                pass
        else:
            result, elapse = engine(img_path)

        if not result:
            return []
        # 按坐标排序保持阅读顺序：先按y分块（同区域同行），行内按x
        items = []
        for item in result:
            box, text, score = item[0], item[1], item[2]
            if text and float(score) >= 0.5:
                ys = [p[1] for p in box]
                xs = [p[0] for p in box]
                items.append((sum(ys)/4, sum(xs)/4, str(text).strip()))
        # 按 y 主排序（容差50px分行），x 次排序
        items.sort(key=lambda t: (int(t[0] / 50), t[1]))
        return [t[2] for t in items if t[2]]
    except Exception as e:
        if log_func:
            log_func(f"OCR识别失败: {e}")
        return []


def ocr_image_with_layout(img_path, log_func=None):
    """OCR识别图片文字，返回带排版信息: [{text, x_center, y_center, height_px, width_px}]"""
    try:
        engine = get_ocr_engine(log_func)
        from PIL import Image
        img = Image.open(img_path)
        orig_w, orig_h = img.size
        max_side = max(img.size)
        scale = 1.0
        if max_side > 1600:
            # 降采样加速，坐标还原到原图
            scale = 1600 / max_side
            img = img.resize((int(orig_w * scale), int(orig_h * scale)), Image.LANCZOS)
            tmp_small = os.path.join(tempfile.gettempdir(), 'ocr_small.png')
            img.save(tmp_small)
            result, elapse = engine(tmp_small)
            try:
                os.remove(tmp_small)
            except Exception:
                pass
        else:
            result, elapse = engine(img_path)

        if not result:
            return []

        items = []
        for item in result:
            box, text, score = item[0], item[1], item[2]
            if text and float(score) >= 0.5:
                xs = [p[0] / scale for p in box]  # 还原原图坐标
                ys = [p[1] / scale for p in box]
                height_px = max(abs(ys[1] - ys[0]), abs(ys[3] - ys[2]))
                width_px = max(abs(xs[1] - xs[0]), abs(xs[3] - xs[2]))
                if height_px <= 0:
                    continue
                items.append({
                    'text': str(text).strip(),
                    'x_center': sum(xs) / 4,
                    'y_center': sum(ys) / 4,
                    'x_left': min(xs),
                    'x_right': max(xs),
                    'height_px': height_px,
                    'width_px': width_px,
                })
        # 按 y 排序（阅读顺序）
        items.sort(key=lambda it: it['y_center'])
        return items
    except Exception as e:
        if log_func:
            log_func(f"OCR识别失败: {e}")
        return []


def build_ocr_layout_paragraphs(doc, ocr_items, page_pt_w, page_pt_h, pix_w, pix_h, log_func=None):
    """根据OCR文本框坐标重建Word排版（字号/缩进/对齐/段落间距）"""
    from docx.shared import Pt as DxPt
    from docx.enum.text import WD_ALIGN_PARAGRAPH

    if not ocr_items:
        return 0

    pt_per_px = page_pt_h / max(pix_h, 1)  # 像素→磅 比例

    # 按y聚类成行
    lines = []
    current = []
    prev_y = None
    prev_h = 0
    for it in ocr_items:
        # 同一行：y差小于行高1.3倍
        if prev_y is None or (it['y_center'] - prev_y) < max(it['height_px'], prev_h) * 1.3:
            current.append(it)
        else:
            if current:
                lines.append(current)
            current = [it]
        prev_y = it['y_center']
        prev_h = it['height_px']
    if current:
        lines.append(current)

    # 计算正文基准字号（行高70%分位数，最小9pt）
    font_sizes = [max(l, key=lambda it: it['height_px'])['height_px'] * pt_per_px * 0.78 for l in lines]
    font_sizes.sort()
    body_size = max(9.0, font_sizes[int(len(font_sizes) * 0.7)]) if font_sizes else 10.5

    para_count = 0
    prev_line_y = None
    prev_line_h = None

    for line_items in lines:
        # 行内按x排序
        line_items.sort(key=lambda it: it['x_center'])
        first = line_items[0]
        last = line_items[-1]

        # 字号：取本行最大框高
        max_h_item = max(line_items, key=lambda it: it['height_px'])
        font_pt = max(6.0, max_h_item['height_px'] * pt_per_px * 0.78)

        # 写入文字（同一行多个框用空格连接）
        text = ' '.join(it['text'] for it in line_items)

        # 长句（>=10字符）且字号明显小于正文 → OCR框高异常，按正文处理
        if len(text) >= 10 and font_pt < body_size * 0.85:
            font_pt = body_size

        # 版面定位
        left_pt = first['x_left'] * pt_per_px
        right_pt = last['x_right'] * pt_per_px
        center_pt = (left_pt + right_pt) / 2
        line_width_pt = right_pt - left_pt
        margin = 72  # 默认页边距 1英寸

        para = doc.add_paragraph()
        para_count += 1

        # 对齐方式判断：仅短行（宽度<页面55%）才考虑居中/右对齐
        if line_width_pt < page_pt_w * 0.55:
            left_gap = abs(left_pt - margin)
            right_gap = abs(page_pt_w - margin - right_pt)
            center_dev = abs(center_pt - page_pt_w / 2)
            if center_dev < 35 and abs(left_gap - right_gap) < 50:
                para.alignment = WD_ALIGN_PARAGRAPH.CENTER
            elif right_gap < 35:
                para.alignment = WD_ALIGN_PARAGRAPH.RIGHT
            else:
                para.alignment = WD_ALIGN_PARAGRAPH.LEFT
                if left_pt > margin + 5:
                    para.paragraph_format.left_indent = DxPt(left_pt - margin)
        else:
            # 宽行默认左对齐
            para.alignment = WD_ALIGN_PARAGRAPH.LEFT
            if left_pt > margin + 10:
                para.paragraph_format.left_indent = DxPt(left_pt - margin)

        # 首行缩进（正文段首缩进2字符约等于36pt）
        if para.alignment == WD_ALIGN_PARAGRAPH.LEFT and font_pt <= body_size * 1.1 and left_pt < margin + 10:
            para.paragraph_format.first_line_indent = DxPt(36)

        # 段落间距：与上一行的垂直间隙
        if prev_line_y is not None and prev_line_h:
            gap_pt = (first['y_center'] - prev_line_y - prev_line_h / 2) * pt_per_px
            if gap_pt > font_pt * 0.6:
                para.paragraph_format.space_before = DxPt(min(gap_pt * 0.8, 24))
        prev_line_y = first['y_center']
        prev_line_h = max_h_item['height_px']

        run = para.add_run(text)
        run.font.size = DxPt(font_pt)
        run.font.name = 'SimSun'
        # 标题启发式：字号 >= 12pt 且显著大于正文 → 加粗黑体
        if font_pt >= max(12.0, body_size * 1.15):
            run.bold = True
            run.font.name = 'SimHei'

    return para_count


_FONT_ALIAS = {
    'simsun': '宋体', 'songti': '宋体', 'stsong': '宋体', 'nsimsun': '新宋体',
    'simhei': '黑体', 'heiti': '黑体', 'stheiti': '黑体',
    'kaiti': '楷体', 'simkai': '楷体', 'stkaiti': '楷体',
    'fangsong': '仿宋', 'fangsong_gb2312': '仿宋', '仿宋_gb2312': '仿宋',
    'stfangsong': '仿宋',
    'microsoftyahei': '微软雅黑', 'msyh': '微软雅黑', 'deng': '等线',
    'timesnewroman': 'Times New Roman', 'arial': 'Arial', 'calibri': 'Calibri',
    'couriernew': 'Courier New', 'courier': 'Courier New',
    'helvetica': 'Helvetica', 'helv': 'Helvetica', 'tahoma': 'Tahoma',
    'verdana': 'Verdana', 'georgia': 'Georgia',
}


def _pdf_to_word_span_preserve(pdf_path, output_path, log_func=None):
    """PDF→Word span 级字体保留实现（pdf2docx 不可用时的回退）。
    复用与 pdf_to_word.py 相同的字体映射/双重编码修复逻辑，保持自包含。"""
    import fitz as _fitz
    from docx import Document as _Document
    from docx.shared import Pt as _Pt, RGBColor as _RGBColor
    from docx.enum.text import WD_ALIGN_PARAGRAPH as _WD_ALIGN
    from docx.oxml.ns import qn as _qn

    def _norm_font(raw_name):
        if not raw_name:
            return None
        try:
            decoded = raw_name.encode('latin-1').decode('utf-8')
        except (UnicodeEncodeError, UnicodeDecodeError):
            decoded = raw_name
        name = re.sub(r'^[A-Z]{6}\+', '', decoded)
        key = re.sub(r'[\s\-_]', '', name).lower()
        return _FONT_ALIAS.get(key, name)

    def _is_cjk(font_name):
        if not font_name:
            return False
        if re.search(r'[\u4e00-\u9fff]', font_name):
            return True
        key = re.sub(r'[\s\-_]', '', font_name).lower()
        return any(kw in key for kw in ('sim', 'hei', 'kai', 'song', 'fang',
                                        'yahei', 'deng', 'stzhong', 'stxi',
                                        'stkai', 'stheiti', 'stsong', 'ming',
                                        'msmincho', 'gothic'))

    def _apply_run(run, font_name, size, color_int, flags, text):
        run.text = text
        if font_name:
            run.font.name = font_name
            rpr = run._element.get_or_add_rPr()
            rfonts = rpr.find(_qn('w:rFonts'))
            if rfonts is None:
                rfonts = rpr.makeelement(_qn('w:rFonts'), {})
                rpr.insert(0, rfonts)
            rfonts.set(_qn('w:ascii'), font_name)
            rfonts.set(_qn('w:hAnsi'), font_name)
            if _is_cjk(font_name):
                rfonts.set(_qn('w:eastAsia'), font_name)
        if size and size > 0:
            run.font.size = _Pt(size)
        if color_int is not None and color_int != 0:
            run.font.color.rgb = _RGBColor(
                (color_int >> 16) & 0xFF, (color_int >> 8) & 0xFF, color_int & 0xFF)
        if flags is not None:
            if flags & 16:
                run.font.bold = True
            if flags & 2:
                run.font.italic = True

    pdf_doc = _fitz.open(pdf_path)
    doc = _Document()
    style = doc.styles['Normal']
    style.font.name = '宋体'
    style.font.size = _Pt(11)
    for i, page in enumerate(pdf_doc):
        if i > 0:
            doc.add_page_break()
        td = page.get_text("dict")
        for blk in td.get("blocks", []):
            if blk.get("type") != 0:
                continue
            for line in blk.get("lines", []):
                spans = line.get("spans", [])
                line_text = "".join(s.get("text", "") for s in spans)
                if not line_text.strip():
                    continue
                para = doc.add_paragraph()
                bbox = line.get("bbox")
                if bbox:
                    pw = page.rect.width
                    lw = bbox[2] - bbox[0]
                    lc = (bbox[0] + bbox[2]) / 2.0
                    if lw < pw * 0.6 and abs(lc - pw / 2.0) < pw * 0.05:
                        para.alignment = _WD_ALIGN.CENTER
                for sp in spans:
                    sp_text = sp.get("text", "")
                    if not sp_text:
                        continue
                    run = para.add_run()
                    _apply_run(run, _norm_font(sp.get("font", "")),
                               sp.get("size", 11), sp.get("color", 0),
                               sp.get("flags", 0), sp_text)
    pdf_doc.close()
    doc.save(output_path)
    if log_func:
        log_func(f"✓ Word文档已保存（保留字体样式）: {output_path}")
    return output_path


def pdf_to_word_internal(pdf_path, output_path=None, log_func=None):
    """PDF转Word（精准版）：
    有文字层 → pdf2docx引擎保留格式/表格/图片
    图片型PDF → 忽略水印文本层，直接嵌入原始页面图片
    """
    import fitz
    from docx import Document
    from docx.shared import Inches, Pt

    if not output_path:
        output_path = os.path.splitext(pdf_path)[0] + '.docx'

    # 图片型PDF：忽略水印，嵌入原始页面图片
    if detect_image_pdf(pdf_path):
        if log_func:
            log_func("检测到图片型PDF（扫描件），忽略水印文本层，直接嵌入页面图片")
        doc = Document()
        style = doc.styles['Normal']
        style.font.name = 'SimSun'
        style.font.size = Pt(11)

        pdf_doc = fitz.open(pdf_path)
        tmp_dir = tempfile.gettempdir()
        total_pages = len(pdf_doc)
        embedded = 0

        # 跨页识别水印行
        watermark_lines, pages_text = collect_watermark_lines(pdf_doc)
        if watermark_lines and log_func:
            log_func(f"  已识别水印 {len(watermark_lines)} 种，将被忽略: {sorted(watermark_lines)[:5]}...")

        for i, page in enumerate(pdf_doc):
            if i > 0:
                doc.add_page_break()
            # 添加页标题（不含水印）
            doc.add_heading(f'第 {i+1} 页', level=2)

            # 提取页面原始图片并嵌入（忽略文本层水印）
            page_images = page.get_images(full=True)
            ocr_items = []  # 收集OCR识别（含坐标）
            if page_images:
                for j, img in enumerate(page_images):
                    xref = img[0]
                    try:
                        pix = fitz.Pixmap(pdf_doc, xref)
                        if pix.n > 3:
                            pix = fitz.Pixmap(fitz.csRGB, pix)
                        tmp_img = os.path.join(tmp_dir, f"pdf2word_tmp_{i}_{j}.png")
                        pix.save(tmp_img)
                        # 按图片在页面上的实际显示尺寸换算嵌入宽度（A4正文宽约6.5英寸），
                        # 避免大图被压成6.5英寸导致DPI虚高、小图被放大
                        img_rects = page.get_image_rects(xref)
                        display_w_in = 0.0
                        if img_rects:
                            r = img_rects[0]
                            # 页面pt宽 → 正文英寸宽（按正文/页面比例换算）
                            display_w_in = max(1.0, 6.5 * r.width / max(page.rect.width, 1)) \
                                if r.width > 0 else 0.0
                        doc.add_picture(tmp_img, width=Inches(min(6.5, display_w_in or 6.5)))
                        doc.add_paragraph()  # 图片后留空行
                        embedded += 1

                        # OCR识别图片中的文字（带坐标）
                        if log_func:
                            log_func(f"  正在OCR识别第{i+1}页图片...")
                        page_items = ocr_image_with_layout(tmp_img, log_func)
                        ocr_items.extend(page_items)
                        try:
                            os.remove(tmp_img)
                        except Exception:
                            pass
                    except Exception as e:
                        if log_func:
                            log_func(f"  第{i+1}页图片嵌入失败: {e}")
            else:
                # 无原始图片：渲染整页为图片（兜底）
                try:
                    pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
                    tmp_img = os.path.join(tmp_dir, f"pdf2word_tmp_page_{i}.png")
                    pix.save(tmp_img)
                    doc.add_picture(tmp_img, width=Inches(6.5))
                    doc.add_paragraph()
                    embedded += 1
                    # OCR识别整页
                    if log_func:
                        log_func(f"  正在OCR识别第{i+1}页...")
                    page_items = ocr_image_with_layout(tmp_img, log_func)
                    ocr_items.extend(page_items)
                    try:
                        os.remove(tmp_img)
                    except Exception:
                        pass
                except Exception:
                    pass

            # 输出OCR识别文字（保留原PDF排版样式）
            if ocr_items:
                doc.add_heading(f'第 {i+1} 页 OCR识别文字（保留排版）', level=3)
                # 页面尺寸换算
                pix_w = 0
                pix_h = 0
                if page_images:
                    try:
                        xref = page_images[0][0]
                        p = fitz.Pixmap(pdf_doc, xref)
                        pix_w, pix_h = p.width, p.height
                    except Exception:
                        pass
                if pix_h <= 0:
                    pix_w, pix_h = page.rect.width * 2, page.rect.height * 2
                build_ocr_layout_paragraphs(doc, ocr_items,
                                            page.rect.width, page.rect.height,
                                            pix_w, pix_h, log_func)
                doc.add_paragraph()

            # 文本层水印过滤后的真实文本补充（若有）
            page_lines = pages_text[i] if i < len(pages_text) else []
            clean_lines = [l for l in page_lines if l not in watermark_lines]
            clean_text = filter_watermark_text('\n'.join(clean_lines))
            if clean_text:
                for line in clean_text.split('\n')[:10]:
                    if line.strip():
                        doc.add_paragraph(line.strip())

        pdf_doc.close()
        doc.save(output_path)
        if log_func:
            log_func(f"✓ Word文档已保存（嵌入 {embedded} 张页面图片）: {output_path}")
        return output_path

    # 有文字层的PDF：优先 pdf2docx 精准转换；不可用时回退内置 span 级字体保留实现
    try:
        from pdf2docx import Converter
        if log_func:
            log_func(f"正在精准转换PDF→Word: {pdf_path}")
        cv = Converter(pdf_path)
        cv.convert(output_path, start=0, end=None)
        cv.close()
        if log_func:
            log_func(f"✓ Word文档已保存: {output_path}")
        return output_path
    except ImportError:
        if log_func:
            log_func("pdf2docx 引擎不可用，回退内置字体保留转换...")
        return _pdf_to_word_span_preserve(pdf_path, output_path, log_func)


def pdf_to_excel_internal(pdf_path, output_path=None, log_func=None):
    """PDF转Excel（精准版）：
    表格型 → 表格结构提取 + 单元格样式
    图片型PDF → 忽略水印，将页面图片嵌入Excel工作表
    """
    import fitz
    import pdfplumber
    from openpyxl import Workbook
    from openpyxl.styles import Font, Alignment, Border, Side, PatternFill
    from openpyxl.utils import get_column_letter

    if not output_path:
        output_path = os.path.splitext(pdf_path)[0] + '.xlsx'

    # 图片型PDF：忽略水印，嵌入页面图片
    if detect_image_pdf(pdf_path):
        if log_func:
            log_func("检测到图片型PDF（扫描件），忽略水印文本层，将页面图片嵌入Excel")
        wb = Workbook()
        wb.remove(wb.active)

        pdf_doc = fitz.open(pdf_path)
        total_pages = len(pdf_doc)
        tmp_dir = tempfile.gettempdir()
        tmp_files = []  # 延迟清理：openpyxl在save时才读取图片

        for i, page in enumerate(pdf_doc):
            sheet = wb.create_sheet(title=f"第{i+1}页")
            sheet.cell(row=1, column=1, value=f"第 {i+1} 页（扫描件图片）").font = Font(bold=True)

            # 嵌入页面原始图片
            page_images = page.get_images(full=True)
            if page_images:
                for j, img in enumerate(page_images):
                    xref = img[0]
                    try:
                        pix = fitz.Pixmap(pdf_doc, xref)
                        if pix.n > 3:
                            pix = fitz.Pixmap(fitz.csRGB, pix)
                        tmp_img = os.path.join(tmp_dir, f"pdf2excel_tmp_{i}_{j}.png")
                        pix.save(tmp_img)
                        tmp_files.append(tmp_img)

                        from openpyxl.drawing.image import Image as XLImage
                        img_obj = XLImage(tmp_img)
                        # 缩放图片到合适宽度（约800像素）
                        ratio = 800 / max(img_obj.width, 1)
                        img_obj.width = int(img_obj.width * ratio)
                        img_obj.height = int(img_obj.height * ratio)
                        # 放在第3行开始（留标题行）
                        img_obj.anchor = "A3"
                        sheet.add_image(img_obj)
                        if log_func:
                            log_func(f"  第{i+1}页图片已嵌入 ({pix.width}x{pix.height})")
                    except Exception as e:
                        if log_func:
                            log_func(f"  第{i+1}页图片嵌入失败: {e}")
            else:
                # 兜底：渲染整页
                try:
                    pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
                    tmp_img = os.path.join(tmp_dir, f"pdf2excel_tmp_page_{i}.png")
                    pix.save(tmp_img)
                    tmp_files.append(tmp_img)
                    from openpyxl.drawing.image import Image as XLImage
                    img_obj = XLImage(tmp_img)
                    ratio = 800 / max(img_obj.width, 1)
                    img_obj.width = int(img_obj.width * ratio)
                    img_obj.height = int(img_obj.height * ratio)
                    img_obj.anchor = "A3"
                    sheet.add_image(img_obj)
                except Exception:
                    pass

            # 水印过滤后的文本补充
            clean_text = filter_watermark_text(page.get_text().strip())
            if clean_text:
                row = 2
                for line in clean_text.split('\n')[:20]:
                    if line.strip():
                        sheet.cell(row=row, column=1, value=line.strip())
                        row += 1

        pdf_doc.close()
        wb.save(output_path)

        # 保存完成后统一清理临时文件
        for tmp in tmp_files:
            try:
                os.remove(tmp)
            except Exception:
                pass

        if log_func:
            log_func(f"✓ Excel文件已保存（嵌入 {total_pages} 页图片）: {output_path}")
        return output_path

    # ===== 表格型PDF：精准提取 =====
    if log_func:
        log_func(f"正在提取PDF表格: {pdf_path}")

    wb = Workbook()
    wb.remove(wb.active)  # 删除默认空表

    # 样式
    header_font = Font(bold=True, size=11, color="FFFFFF")
    header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
    thin_border = Border(
        left=Side(style='thin'), right=Side(style='thin'),
        top=Side(style='thin'), bottom=Side(style='thin'))
    center_align = Alignment(horizontal='center', vertical='center')
    wrap_align = Alignment(vertical='center', wrap_text=True)

    sheet_index = 0
    total_tables = 0

    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages, 1):
            tables = page.extract_tables()
            text = page.extract_text() or ""

            if tables:
                for table in tables:
                    if not table:
                        continue
                    # 清理空行
                    clean_rows = []
                    for row in table:
                        clean = [str(c).strip() if c else "" for c in row]
                        if any(clean):
                            clean_rows.append(clean)
                    if not clean_rows:
                        continue

                    total_tables += 1
                    sheet_index += 1
                    sheet_name = f"表格{sheet_index}"
                    if len(sheet_name) > 31:
                        sheet_name = sheet_name[:31]
                    ws = wb.create_sheet(title=sheet_name)

                    for r_idx, row in enumerate(clean_rows):
                        for c_idx, value in enumerate(row):
                            cell = ws.cell(row=r_idx + 1, column=c_idx + 1, value=value)
                            cell.border = thin_border
                            if r_idx == 0:
                                # 表头样式
                                cell.font = header_font
                                cell.fill = header_fill
                                cell.alignment = center_align
                            else:
                                cell.alignment = wrap_align
                                if value and value.replace('.', '').replace('-', '').isdigit():
                                    cell.alignment = Alignment(horizontal='right', vertical='center')

                    # 自动列宽（基于内容）
                    for col_idx in range(len(clean_rows[0])):
                        max_len = 4
                        for r_idx in range(len(clean_rows)):
                            val = clean_rows[r_idx][col_idx]
                            if val:
                                max_len = max(max_len, len(val) * 2 if any('\u4e00' <= ch <= '\u9fff' for ch in val) else len(val))
                        ws.column_dimensions[get_column_letter(col_idx + 1)].width = min(max_len + 2, 40)

            # 记录表格外的文字（供日志提示）
            if text.strip():
                pass  # 表格已足够，文本仅作参考

    if total_tables == 0:
        # 没有表格：把所有文本逐行写入一个工作表
        if log_func:
            log_func("未检测到表格结构，将文本写入Excel（建议改用Word格式）")
        ws = wb.create_sheet(title="文本内容")
        row_idx = 1
        with pdfplumber.open(pdf_path) as pdf:
            for page_num, page in enumerate(pdf.pages, 1):
                text = page.extract_text()
                if text and text.strip():
                    ws.cell(row=row_idx, column=1, value=f"--- 第 {page_num} 页 ---").font = Font(bold=True)
                    row_idx += 1
                    for line in text.split('\n'):
                        if line.strip():
                            ws.cell(row=row_idx, column=1, value=line.strip())
                            row_idx += 1

    if log_func:
        log_func(f"共提取 {total_tables} 个表格")

    wb.save(output_path)

    if log_func:
        log_func(f"✓ Excel文件已保存: {output_path}")
    return output_path


def _libreoffice_profile_uri():
    """LibreOffice独立用户配置目录（URI形式），避免与本机已打开的LibreOffice实例冲突"""
    profile = os.path.join(tempfile.gettempdir(), 'pdf_converter_lo_profile')
    try:
        os.makedirs(profile, exist_ok=True)
    except Exception:
        pass
    return 'file:///' + profile.replace(os.sep, '/')


def run_libreoffice_convert(doc_path, output_dir, log_func=None, timeout=180):
    """调用LibreOffice把文档转换为PDF（headless模式，独立配置目录）
    返回生成的PDF路径（LibreOffice输出文件名固定为"输入文件同名.pdf"）"""
    libreoffice = find_libreoffice()
    if not libreoffice:
        raise RuntimeError("未找到LibreOffice，请先安装")

    os.makedirs(output_dir, exist_ok=True)
    cmd = [libreoffice, '--headless', '--norestore',
           f'-env:UserInstallation={_libreoffice_profile_uri()}',
           '--convert-to', 'pdf', '--outdir', output_dir, doc_path]
    if log_func:
        log_func(f"正在通过LibreOffice转换: {doc_path}")

    # LibreOffice偶发卡死，超时则报错（不无限等待）
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        raise RuntimeError(f"LibreOffice转换超时（>{timeout}秒），请稍后重试或检查文档是否过大")

    if result.returncode != 0:
        raise RuntimeError(f"LibreOffice转换失败: {(result.stderr or result.stdout or '')[:200]}")

    real_output = os.path.join(
        output_dir, os.path.splitext(os.path.basename(doc_path))[0] + '.pdf')
    if not os.path.exists(real_output):
        raise RuntimeError("LibreOffice转换未生成PDF文件（文档可能为空或格式不受支持）")
    if log_func:
        log_func(f"✓ PDF已生成: {real_output}")
    return real_output


def _rename_output(real_output, output_path):
    """把LibreOffice固定命名的输出重命名为目标路径"""
    if os.path.abspath(real_output) != os.path.abspath(output_path):
        if os.path.exists(output_path):
            os.remove(output_path)
        os.replace(real_output, output_path)
    return output_path


def doc_to_pdf_internal(doc_path, output_path=None, log_func=None):
    """Word转PDF（通过LibreOffice）"""
    if not output_path:
        output_path = os.path.splitext(doc_path)[0] + '.pdf'

    real_output = run_libreoffice_convert(doc_path, os.path.dirname(output_path) or '.', log_func)
    output_path = _rename_output(real_output, output_path)
    if log_func:
        log_func(f"✓ PDF文件已保存: {output_path}")
    return output_path


IMAGE_EXTS = {'.png', '.jpg', '.jpeg', '.bmp', '.gif', '.webp', '.tif', '.tiff'}


def image_to_pdf_internal(image_paths, output_path=None, log_func=None):
    """图片转PDF：将一张或多张图片合成为一个PDF（逐图成页）"""
    import fitz

    if isinstance(image_paths, str):
        image_paths = [image_paths]
    image_paths = [p for p in image_paths if os.path.exists(p)]
    if not image_paths:
        raise FileNotFoundError("没有可转换的图片文件")

    if not output_path:
        if len(image_paths) == 1:
            base = os.path.splitext(image_paths[0])[0]
        else:
            base = os.path.splitext(image_paths[0])[0] + "_merged"
        output_path = base + ".pdf"

    out_dir = os.path.dirname(output_path)
    if out_dir and not os.path.exists(out_dir):
        os.makedirs(out_dir, exist_ok=True)

    doc = fitz.open()
    added = 0
    try:
        for img_path in image_paths:
            img = fitz.open(img_path)
            if len(img) == 0:
                img.close()
                continue
            rect = img[0].rect
            page = doc.new_page(width=rect.width, height=rect.height)
            page.insert_image(rect, filename=img_path)
            img.close()
            added += 1
            if log_func:
                log_func(f"  ✓ 已加入图片: {os.path.basename(img_path)}")
        doc.save(output_path, deflate=True)
    finally:
        doc.close()

    if log_func:
        log_func(f"✓ PDF已生成: {output_path}（{added} 张图片，{added} 页）")
    return output_path


def excel_to_pdf_internal(excel_path, output_path=None, log_func=None):
    """Excel转PDF（通过LibreOffice）"""
    if not output_path:
        output_path = os.path.splitext(excel_path)[0] + '.pdf'

    real_output = run_libreoffice_convert(excel_path, os.path.dirname(output_path) or '.', log_func)
    output_path = _rename_output(real_output, output_path)
    if log_func:
        log_func(f"✓ PDF文件已保存: {output_path}")
    return output_path


def get_pdf_page_info(pdf_path):
    """快速获取PDF信息: (页数, 主要方向 'portrait'|'landscape'|'mixed', 是否可读)
    方向取多数页的视觉方向（page.rect已含旋转信息）"""
    import fitz
    try:
        doc = fitz.open(pdf_path)
        n = doc.page_count
        portrait = landscape = 0
        for page in doc:
            if page.rect.width > page.rect.height:
                landscape += 1
            else:
                portrait += 1
        doc.close()
        if n == 0:
            return 0, 'mixed', True
        orient = 'portrait' if portrait >= landscape else 'landscape'
        if portrait > 0 and landscape > 0:
            orient = 'mixed'
        return n, orient, True
    except Exception:
        return 0, 'mixed', False


def normalize_rotation(rot):
    """旋转角度规范化到 0/90/180/270（顺时针，PDF标准）"""
    try:
        rot = int(rot) % 360
    except (TypeError, ValueError):
        return 0
    return {0: 0, 90: 90, 180: 180, 270: 270}.get(rot, 0)


def merge_pdf_files(files, output_path, rotations=None, auto_orient=None,
                    log_func=None):
    """合并多个PDF为一个，支持对每份PDF整体旋转与自动统一页面方向。

    files:        PDF路径列表（按合并顺序）
    rotations:    {文件路径: 顺时针旋转角度(0/90/180/270)}，作用于该文件所有页
    auto_orient:  None=不处理；'portrait'=横向页转90°统一为纵向；
                  'landscape'=纵向页转90°统一为横向
    返回: (总页数, [{'file':..., 'pages':加入页数, 'rotated':旋转页数}])
    单个文件损坏时跳过并记录，不中断整体合并；全部失败则抛错。
    """
    import fitz
    rotations = rotations or {}
    out = fitz.open()
    total_pages = 0
    per_file = []
    failed = []

    for idx, f in enumerate(files, 1):
        try:
            src = fitz.open(f)
            n0 = out.page_count
            out.insert_pdf(src)
            added = out.page_count - n0
            src.close()
        except Exception as e:
            failed.append((f, str(e)))
            if log_func:
                log_func(f"  ✗ [{idx}/{len(files)}] {os.path.basename(f)} 无法读取，已跳过: {e}")
            continue

        # 对该文件新加入的页面应用旋转（在已有旋转基础上顺时针叠加）
        rot = normalize_rotation(rotations.get(f, 0))
        rotated_count = 0
        for p in range(n0, out.page_count):
            page = out[p]
            final_rot = (page.rotation + rot) % 360
            page.set_rotation(final_rot)
            if rot:
                rotated_count += 1

        # 自动统一方向：视觉方向与目标不符时旋转90°
        if auto_orient in ('portrait', 'landscape'):
            for p in range(n0, out.page_count):
                page = out[p]
                is_landscape = page.rect.width > page.rect.height
                if (auto_orient == 'portrait' and is_landscape) or \
                   (auto_orient == 'landscape' and not is_landscape and page.rect.width != page.rect.height):
                    page.set_rotation((page.rotation + 90) % 360)
                    rotated_count += 1

        total_pages = out.page_count
        per_file.append({'file': f, 'pages': added, 'rotated': rotated_count})
        if log_func:
            rot_note = f"，旋转{rot}°" if rot else ""
            orient_note = ""
            if auto_orient and rotated_count > (1 if rot else 0):
                orient_note = f"（含自动统一{'纵向' if auto_orient == 'portrait' else '横向'}）"
            log_func(f"  [{idx}/{len(files)}] {os.path.basename(f)}  加入 {added} 页{rot_note}{orient_note}")

    if total_pages == 0:
        out.close()
        detail = "; ".join(f"{os.path.basename(f)}: {e}" for f, e in failed[:3])
        raise ValueError("没有可合并的页面，请检查所选PDF" + (f"（{detail}）" if detail else ""))

    os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)
    out.save(output_path, garbage=3, deflate=True)
    out.close()

    if failed and log_func:
        log_func(f"  ⚠ {len(failed)} 个文件读取失败被跳过")
    return total_pages, per_file


# ============================================================
# 第四部分: 许可状态管理（原 license_checker.py）
# ============================================================

class PDFConverterLicense:
    """许可管理"""

    def __init__(self, config_dir=None):
        if config_dir is None:
            config_dir = os.path.join(os.path.expanduser("~"), ".pdf_converter")
        self.config_dir = config_dir
        self.config_file = os.path.join(config_dir, "license_config.json")
        self.license_file = os.path.join(config_dir, "license.json")
        self.usage_file = os.path.join(config_dir, "usage.json")
        self.default_config = {
            "version": "1.0.0",
            "max_files_per_license": 20,
        }

    def init(self):
        os.makedirs(self.config_dir, exist_ok=True)
        if not os.path.exists(self.config_file):
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.default_config, f, indent=2)

    def save_license(self, license_info):
        with open(self.license_file, 'w', encoding='utf-8') as f:
            json.dump(license_info, f, indent=2)

    def save_usage(self, usage_data):
        with open(self.usage_file, 'w', encoding='utf-8') as f:
            json.dump(usage_data, f, indent=2)

    def is_registered(self):
        return os.path.exists(self.license_file)

    def get_license_info(self):
        if os.path.exists(self.license_file):
            with open(self.license_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return None

    def get_usage(self):
        if os.path.exists(self.usage_file):
            with open(self.usage_file, 'r', encoding='utf-8') as f:
                usage = json.load(f)
        else:
            usage = {"total_files": 0, "files": [], "last_reset": None}

        limit = self.get_config().get("max_files_per_license", 20)
        used = usage.get("total_files", 0)
        license_info = self.get_license_info()

        return {
            "total_files": used,
            "files_used": used,
            "files_remaining": max(0, limit - used),
            "limit": limit,
            "machine_code": license_info.get("machine_code", "未知") if license_info else "未知",
        }

    def get_config(self):
        if os.path.exists(self.config_file):
            with open(self.config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return self.default_config.copy()

    def register(self, machine_code, license_code):
        """注册"""
        if not re.match(r'^[A-F0-9]{4}-[A-F0-9]{4}-[A-F0-9]{4}-[A-F0-9]{4}$', machine_code.upper()):
            return False, "机器码格式无效"
        if not re.match(r'^PDF-[A-F0-9]{8}-\d{4}-[A-F0-9]{8}$', license_code.upper()):
            return False, "许可码格式无效"

        is_valid, message = verify_license_code(license_code, machine_code)
        if not is_valid:
            return False, message

        existing = self.get_license_info()
        if existing:
            if existing.get('machine_code') == machine_code:
                return False, "此机器已注册，无需重复注册"
            return False, "此许可码已注册到另一台机器"

        license_info = {
            "machine_code": machine_code.upper(),
            "license_code": license_code.upper(),
            "registered_at": datetime.now().isoformat(),
            "status": "active"
        }
        self.save_license(license_info)
        self.save_usage({"total_files": 0, "files": [], "last_reset": None})
        return True, "注册成功！您现在可以转换20个文件。"

    def check_and_increment(self, filename):
        """检查配额并计数"""
        if not self.is_registered():
            return False, "请先注册"
        usage = self.get_usage()
        limit = usage.get('limit', 20)
        used = usage.get('total_files', 0)
        if used >= limit:
            return False, f"已用完配额 ({used}/{limit})，请联系开发者"
        used += 1
        data = {"total_files": used, "files": [], "last_reset": None}
        if os.path.exists(self.usage_file):
            with open(self.usage_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
        data["total_files"] = used
        data["files"].append({"filename": filename, "timestamp": datetime.now().isoformat()})
        self.save_usage(data)
        return True, f"剩余配额: {limit - used} 个文件"


# ============================================================
# 第五部分: GUI界面
# ============================================================

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import tempfile

# 拖拽支持（tkinterdnd2）
try:
    from tkinterdnd2 import TkinterDnD, DND_FILES
    HAS_DND = True
except ImportError:
    HAS_DND = False

# 功能模块（同目录，PyInstaller自动打包）
try:
    from pdf_page_editor import PDFPageEditor
    from invoice_recognizer import InvoiceRecognizerWindow
    from invoice_print_layout import build_a4_dual_invoice
    HAS_EXTRA_TOOLS = True
except ImportError:
    HAS_EXTRA_TOOLS = False


def is_process_running(pid):
    """检查进程是否存活（Windows）"""
    try:
        result = subprocess.run(['tasklist', '/FI', f'PID eq {pid}'],
                                capture_output=True, text=True, timeout=5)
        return str(pid) in result.stdout
    except Exception:
        return False


def check_single_instance():
    """单实例检查：防止重复打开多个GUI窗口"""
    lock_file = os.path.join(tempfile.gettempdir(), 'pdf_converter_gui.lock')
    if os.path.exists(lock_file):
        try:
            with open(lock_file, 'r') as f:
                old_pid = int(f.read().strip())
            if is_process_running(old_pid):
                return False  # 已有实例在运行
        except Exception:
            pass
        # 旧实例已退出，删除残留锁文件
        try:
            os.remove(lock_file)
        except Exception:
            pass
    # 创建锁文件
    try:
        with open(lock_file, 'w') as f:
            f.write(str(os.getpid()))
    except Exception:
        pass
    return True


class PDFMergeDialog:
    """PDF合并设置对话框：为每份PDF设置旋转角度，可自动统一页面方向"""

    ROT_LABELS = {0: "0°（不旋转）", 90: "90° 顺时针", 180: "180°", 270: "270°（逆时针90°）"}
    ORIENT_LABELS = {"none": "保持原样", "portrait": "统一纵向（横向页转90°）",
                     "landscape": "统一横向（纵向页转90°）"}

    def __init__(self, parent, files, log_func):
        self.result = None  # (rotations, auto_orient) 或 None（取消）

        self.win = tk.Toplevel(parent)
        self.win.title("PDF合并设置（可旋转每份PDF）")
        self.win.transient(parent)
        self.win.grab_set()

        ttk.Label(self.win, text=f"已选择 {len(files)} 个PDF，可为每一份设置旋转角度：",
                  font=('Microsoft YaHei', 10, 'bold')).pack(anchor=tk.W, padx=10, pady=(10, 5))

        # 文件列表区（可滚动）
        list_frame = ttk.Frame(self.win)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        canvas = tk.Canvas(list_frame, height=min(280, 40 * len(files) + 20),
                           highlightthickness=0)
        vsb = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=canvas.yview)
        canvas.configure(yscrollcommand=vsb.set)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        inner = ttk.Frame(canvas)
        canvas.create_window((0, 0), window=inner, anchor='nw')
        inner.bind('<Configure>', lambda e: canvas.configure(scrollregion=canvas.bbox('all')))

        # 每份PDF的缩略图 + 方向信息 + 旋转选择
        self.rot_vars = {}
        from PIL import Image, ImageTk
        self._thumbs = []
        for f in files:
            row = ttk.Frame(inner)
            row.pack(fill=tk.X, pady=3)
            try:
                import fitz
                d = fitz.open(f)
                page = d[0]
                zoom = 60.0 / max(page.rect.width, 1)
                pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom))
                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                self._thumbs.append(ImageTk.PhotoImage(img))
                ttk.Label(row, image=self._thumbs[-1]).pack(side=tk.LEFT, padx=(2, 8))
                d.close()
            except Exception:
                pass
            n, orient, ok = get_pdf_page_info(f)
            orient_cn = {'portrait': '纵向', 'landscape': '横向', 'mixed': '混合'}.get(orient, '?')
            name = os.path.basename(f)
            if len(name) > 30:
                name = name[:27] + '...'
            ttk.Label(row, text=f"{name}\n{n}页 · {orient_cn}" + ("" if ok else " · ⚠不可读"),
                      justify=tk.LEFT).pack(side=tk.LEFT, padx=4)
            var = tk.StringVar(value=self.ROT_LABELS[0])
            self.rot_vars[f] = var
            ttk.Combobox(row, textvariable=var, state='readonly', width=14,
                         values=list(self.ROT_LABELS.values())).pack(side=tk.RIGHT, padx=6)
        canvas.update_idletasks()
        canvas.configure(height=min(280, max(120, canvas.bbox('all')[3])))

        # 方向统一选项
        opt_frame = ttk.LabelFrame(self.win, text="页面方向统一（满足统一排版样式）", padding="8")
        opt_frame.pack(fill=tk.X, padx=10, pady=5)
        ttk.Label(opt_frame, text="自动方向:").grid(row=0, column=0, sticky=tk.W)
        self.orient_var = tk.StringVar(value=self.ORIENT_LABELS['none'])
        ttk.Combobox(opt_frame, textvariable=self.orient_var, state='readonly', width=22,
                     values=list(self.ORIENT_LABELS.values())).grid(row=0, column=1, padx=6, sticky=tk.W)
        ttk.Label(opt_frame, foreground='gray',
                  text="说明: 旋转仅改变页面方向属性，不裁剪内容；\n"
                       "若个别PDF需旋转请在上方逐份设置（如横向扫描件转正）。",
                  justify=tk.LEFT).grid(row=1, column=0, columnspan=2, sticky=tk.W, pady=(6, 0))

        # 按钮
        btn_frame = ttk.Frame(self.win)
        btn_frame.pack(fill=tk.X, padx=10, pady=10)
        ttk.Button(btn_frame, text="取 消", command=self.cancel).pack(side=tk.RIGHT, padx=4)
        ttk.Button(btn_frame, text="开 始 合 并", command=self.confirm).pack(side=tk.RIGHT, padx=4)

        # Esc关闭
        self.win.bind('<Escape>', lambda e: self.cancel())
        self.win.protocol("WM_DELETE_WINDOW", self.cancel)
        self.win.wait_window()

    def confirm(self):
        # 标签 → 角度
        rot_lookup = {v: k for k, v in self.ROT_LABELS.items()}
        rotations = {}
        for f, var in self.rot_vars.items():
            angle = rot_lookup.get(var.get(), 0)
            if angle:
                rotations[f] = angle
        orient_lookup = {v: k for k, v in self.ORIENT_LABELS.items()}
        auto_orient = orient_lookup.get(self.orient_var.get(), 'none')
        self.result = (rotations, None if auto_orient == 'none' else auto_orient)
        self.win.destroy()

    def cancel(self):
        self.result = None
        self.win.destroy()


class PDFConverterGUI:
    """PDF转换器图形界面"""

    def __init__(self, root):
        self.root = root
        self.root.title("PDF转换器 v1.0")
        self.root.geometry("720x540")
        self.root.resizable(True, True)

        # 日志文件路径（exe所在目录）
        try:
            exe_dir = os.path.dirname(os.path.abspath(sys.executable))
        except Exception:
            exe_dir = os.path.dirname(os.path.abspath(__file__))
        self.log_file = os.path.join(exe_dir, 'pdf_converter.log')

        # 初始化许可管理器
        self.checker = PDFConverterLicense()
        self.checker.init()

        # 创建界面
        self.create_widgets()
        self.update_status()
        self.log("PDF转换器已启动")
        self.log(f"日志文件: {self.log_file}")

    def create_widgets(self):
        """创建界面"""
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)

        # 标题
        title_label = ttk.Label(main_frame, text="PDF转换器",
                                font=('Microsoft YaHei', 16, 'bold'))
        title_label.grid(row=0, column=0, columnspan=3, pady=(0, 8))

        # 顶部：授权/注册按钮（与功能按钮分开排列）
        top_action_frame = ttk.Frame(main_frame)
        top_action_frame.grid(row=1, column=0, columnspan=3, sticky=tk.W, pady=(0, 5))
        ttk.Label(top_action_frame, text="授权/注册:").pack(side=tk.LEFT, padx=(2, 10))
        ttk.Button(top_action_frame, text="获取机器码", command=self.get_machine_code, width=12)\
            .pack(side=tk.LEFT, padx=5)
        ttk.Button(top_action_frame, text="注册", command=self.show_register_dialog, width=12)\
            .pack(side=tk.LEFT, padx=5)

        # 注册状态
        status_frame = ttk.LabelFrame(main_frame, text="注册状态", padding="10")
        status_frame.grid(row=2, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=5)
        status_frame.columnconfigure(1, weight=1)

        self.status_var = tk.StringVar(value="未注册")
        self.status_label = ttk.Label(status_frame, textvariable=self.status_var, foreground='red')
        self.status_label.grid(row=0, column=0, sticky=tk.W)

        # 机器码显示（可选中复制）
        self.machine_var = tk.StringVar(value="点击'获取机器码'后显示")
        self.machine_entry_display = ttk.Entry(status_frame, textvariable=self.machine_var,
                                               state='readonly', width=30)
        self.machine_entry_display.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=10)
        # 只读Entry支持鼠标拖动选中 + Ctrl+C
        self.machine_entry_display.bind("<Control-c>", lambda e: self.copy_text(self.machine_var.get()))

        self.copy_machine_btn = ttk.Button(status_frame, text="复制机器码", width=10,
                                           command=self.copy_machine_code)
        self.copy_machine_btn.grid(row=0, column=2, padx=5)

        self.quota_var = tk.StringVar(value="配额: --")
        ttk.Label(status_frame, textvariable=self.quota_var).grid(row=1, column=0, sticky=tk.W, pady=(5, 0))

        # 许可码显示（注册后可见，方便续期时提供序列号给开发者）
        ttk.Label(status_frame, text="许可码:").grid(row=2, column=0, sticky=tk.W, pady=(5, 0))
        self.license_var = tk.StringVar(value="（注册后显示）")
        self.license_entry_display = ttk.Entry(status_frame, textvariable=self.license_var,
                                               state='readonly', width=30)
        self.license_entry_display.grid(row=2, column=1, sticky=(tk.W, tk.E), padx=10, pady=(5, 0))
        self.license_entry_display.bind("<Control-c>", lambda e: self.copy_text(self.license_var.get()))

        self.copy_license_btn = ttk.Button(status_frame, text="复制许可码", width=10,
                                           command=self.copy_license_code)
        self.copy_license_btn.grid(row=2, column=2, padx=5, pady=(5, 0))

        self.serial_var = tk.StringVar(value="")
        ttk.Label(status_frame, textvariable=self.serial_var, foreground='gray')\
            .grid(row=3, column=1, sticky=tk.W, padx=10, pady=(2, 0))

        # 文件选择
        file_frame = ttk.LabelFrame(main_frame, text="文件选择", padding="10")
        file_frame.grid(row=3, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=5)
        file_frame.columnconfigure(1, weight=1)

        ttk.Label(file_frame, text="输入文件:").grid(row=0, column=0, sticky=tk.W)
        self.file_var = tk.StringVar()
        self.file_entry = ttk.Entry(file_frame, textvariable=self.file_var, width=50)
        self.file_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=5)
        ttk.Button(file_frame, text="浏览...", command=self.browse_file).grid(row=0, column=2)

        # 拖拽提示（支持拖文件到界面）
        if HAS_DND:
            ttk.Label(file_frame, text="⇩ 支持拖拽文件到下方区域", foreground='blue')\
                .grid(row=1, column=1, sticky=tk.W, padx=5)
            # 输入文件框注册拖拽
            self.file_entry.drop_target_register(DND_FILES)
            self.file_entry.dnd_bind('<<Drop>>', self.on_file_drop)

        ttk.Label(file_frame, text="输出目录:").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.output_var = tk.StringVar(value=os.path.expanduser("~"))
        self.output_entry = ttk.Entry(file_frame, textvariable=self.output_var, width=50)
        self.output_entry.grid(row=2, column=1, sticky=(tk.W, tk.E), padx=5, pady=5)
        ttk.Button(file_frame, text="浏览...", command=self.browse_output).grid(row=2, column=2)
        if HAS_DND:
            # 输出目录框也支持拖拽
            self.output_entry.drop_target_register(DND_FILES)
            self.output_entry.dnd_bind('<<Drop>>', self.on_output_drop)

        # 转换选项
        option_frame = ttk.LabelFrame(main_frame, text="转换选项", padding="10")
        option_frame.grid(row=4, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=5)

        ttk.Label(option_frame, text="输出格式:").grid(row=0, column=0, sticky=tk.W)
        self.format_var = tk.StringVar(value="word")
        format_combo = ttk.Combobox(option_frame, textvariable=self.format_var,
                                    values=["word", "excel", "pdf", "auto"], state="readonly", width=15)
        format_combo.grid(row=0, column=1, sticky=tk.W, padx=5)
        # “开始转换”与“输出格式”同一行，表示它负责完成本次转换
        self.convert_btn = ttk.Button(option_frame, text="开始转换", command=self.start_conversion, width=12)
        self.convert_btn.grid(row=0, column=2, sticky=tk.W, padx=(20, 0))

        # 功能按钮（授权/注册已移到界面顶端，“开始转换”已并入“转换选项”行）
        if HAS_EXTRA_TOOLS:
            button_frame = ttk.Frame(main_frame)
            button_frame.grid(row=5, column=0, columnspan=3, pady=(5, 15))
            ttk.Button(button_frame, text="PDF页面编辑", command=self.open_page_editor, width=12)\
                .grid(row=0, column=0, padx=5)
            ttk.Button(button_frame, text="发票识别", command=self.open_invoice_recognizer, width=12)\
                .grid(row=0, column=1, padx=5)
            ttk.Button(button_frame, text="发票打印", command=self.open_invoice_print, width=12)\
                .grid(row=0, column=2, padx=5)
            ttk.Button(button_frame, text="PDF合并", command=self.merge_pdfs, width=12)\
                .grid(row=0, column=3, padx=5)

        # 日志区域
        log_frame = ttk.LabelFrame(main_frame, text="操作日志 (同时保存到 pdf_converter.log)", padding="10")
        log_frame.grid(row=6, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5)
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(1, weight=1)
        main_frame.rowconfigure(6, weight=1)

        # 日志工具栏
        log_toolbar = ttk.Frame(log_frame)
        log_toolbar.grid(row=0, column=0, columnspan=2, sticky=tk.W, pady=(0, 5))
        ttk.Button(log_toolbar, text="复制全部日志", width=12, command=self.copy_log)\
            .pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(log_toolbar, text="清空界面日志", width=12, command=self.clear_log)\
            .pack(side=tk.LEFT)
        ttk.Label(log_toolbar, text="（也可鼠标选中文字后按 Ctrl+C）", foreground='gray')\
            .pack(side=tk.LEFT, padx=10)

        self.log_text = tk.Text(log_frame, height=9, width=80, wrap=tk.WORD)
        self.log_text.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        scrollbar = ttk.Scrollbar(log_frame, orient=tk.VERTICAL, command=self.log_text.yview)
        scrollbar.grid(row=1, column=1, sticky=(tk.N, tk.S))
        self.log_text['yscrollcommand'] = scrollbar.set

        # 日志右键菜单 + 快捷键
        self.log_menu = tk.Menu(self.log_text, tearoff=0)
        self.log_menu.add_command(label="复制选中", command=self.copy_selection)
        self.log_menu.add_command(label="复制全部日志", command=self.copy_log)
        self.log_menu.add_separator()
        self.log_menu.add_command(label="清空界面日志", command=self.clear_log)
        self.log_text.bind("<Button-3>", self.show_log_menu)
        self.log_text.bind("<Control-c>", lambda e: self.copy_selection())

    def log(self, message):
        """记录日志（界面 + .log文件）"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        line = f"[{timestamp}] {message}"

        # 写入界面
        self.log_text.insert(tk.END, line + "\n")
        self.log_text.see(tk.END)

        # 写入日志文件
        try:
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(line + "\n")
        except Exception:
            pass

    def browse_file(self):
        """选择文件"""
        # 提示文本说明可选的格式兼容性
        files = filedialog.askopenfilenames(
            title="选择PDF/Word/Excel/图片文件",
            filetypes=[("支持的文件", "*.pdf;*.docx;*.doc;*.xlsx;*.xls;*.png;*.jpg;*.jpeg;*.bmp;*.gif;*.webp"),
                       ("PDF文件", "*.pdf"),
                       ("Word文件", "*.docx;*.doc"),
                       ("Excel文件", "*.xlsx;*.xls"),
                       ("图片文件", "*.png;*.jpg;*.jpeg;*.bmp;*.gif;*.webp;*.tif;*.tiff"),
                       ("所有文件", "*.*")]
        )
        if files:
            self.file_var.set(files[0])
            self.log(f"选择文件: {files[0]}")

    def on_file_drop(self, event):
        """拖拽文件到界面 → 完成文件选择"""
        try:
            files = self.root.tk.splitlist(event.data)
            if files:
                self.file_var.set(files[0])
                self.log(f"拖入文件: {files[0]}")
                if len(files) > 1:
                    self.log(f"共拖入 {len(files)} 个文件，已选择第一个（其余可逐个转换）")
                # 若未指定输出目录，默认使用文件所在目录
                if not self.output_var.get().strip():
                    self.output_var.set(os.path.dirname(files[0]))
        except Exception as e:
            self.log(f"处理拖拽文件失败: {e}")

    def on_output_drop(self, event):
        """拖拽文件夹到输出目录框"""
        try:
            files = self.root.tk.splitlist(event.data)
            if files and os.path.isdir(files[0]):
                self.output_var.set(files[0])
                self.log(f"拖入输出目录: {files[0]}")
            elif files:
                self.log(f"提示: 输出目录需要拖入文件夹，不是文件: {files[0]}")
        except Exception as e:
            self.log(f"处理拖拽目录失败: {e}")

    def browse_output(self):
        """选择输出目录"""
        folder = filedialog.askdirectory(title="选择输出目录")
        if folder:
            self.output_var.set(folder)
            self.log(f"输出目录: {folder}")

    def copy_text(self, text):
        """复制文本到剪贴板"""
        try:
            self.root.clipboard_clear()
            self.root.clipboard_append(text)
            return True
        except Exception:
            return False

    def copy_machine_code(self):
        """复制机器码按钮"""
        machine_code = self.machine_var.get()
        if machine_code and machine_code not in ("点击'获取机器码'后显示", "--"):
            if self.copy_text(machine_code):
                self.log(f"机器码已复制: {machine_code}")
                messagebox.showinfo("成功", "机器码已复制到剪贴板，可直接 Ctrl+V 粘贴发送")
            else:
                messagebox.showerror("错误", "复制失败")
        else:
            messagebox.showwarning("提示", "请先点击'获取机器码'")

    def copy_license_code(self):
        """复制许可码按钮"""
        license_code = self.license_var.get()
        if license_code and license_code not in ("（注册后显示）", "--"):
            if self.copy_text(license_code):
                self.log(f"许可码已复制: {license_code}")
                messagebox.showinfo("成功", "许可码已复制到剪贴板")
            else:
                messagebox.showerror("错误", "复制失败")
        else:
            messagebox.showwarning("提示", "请先完成注册")

    def parse_serial_from_license(self, license_code):
        """从许可码解析序列号: PDF-XXXXXXXX-NNNN-XXXXXXXX"""
        m = re.match(r'^PDF-[A-F0-9]{8}-(\d{4})-[A-F0-9]{8}$', license_code.strip().upper())
        if m:
            return int(m.group(1))
        return None

    def copy_selection(self):
        """复制日志中选中的内容"""
        try:
            selected = self.log_text.get(tk.SEL_FIRST, tk.SEL_LAST)
            if selected:
                if self.copy_text(selected):
                    self.log(f"已复制选中的日志内容 ({len(selected)} 字符)")
        except tk.TclError:
            # 没有选中内容，复制全部
            self.copy_log()

    def copy_log(self):
        """复制全部日志"""
        content = self.log_text.get("1.0", tk.END).strip()
        if content:
            if self.copy_text(content):
                self.log(f"已复制全部日志 ({len(content)} 字符)")
                messagebox.showinfo("成功", "全部日志已复制到剪贴板")
            else:
                messagebox.showerror("错误", "复制失败")
        else:
            messagebox.showwarning("提示", "日志为空")

    def clear_log(self):
        """清空界面日志（不影响.log文件）"""
        self.log_text.delete("1.0", tk.END)
        self.log("界面日志已清空（.log文件保留完整记录）")

    def show_log_menu(self, event):
        """显示日志右键菜单"""
        try:
            self.log_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.log_menu.grab_release()

    def get_machine_code(self):
        """获取机器码（直接计算，不调用外部脚本）"""
        try:
            self.log("正在获取本机硬件信息...")
            machine_code, components = generate_machine_code()

            for comp in components:
                self.log(f"  硬件: {comp}")

            self.log(f"机器码: {machine_code}")
            self.machine_var.set(machine_code)

            # 自动复制到剪贴板，方便发送给开发者
            if self.copy_text(machine_code):
                self.log("机器码已自动复制到剪贴板")
                copied_hint = "已自动复制到剪贴板（Ctrl+V可直接粘贴发送）"
            else:
                copied_hint = "可直接点击'复制机器码'按钮复制"

            messagebox.showinfo(
                "机器码",
                f"您的机器码是:\n\n{machine_code}\n\n"
                f"{copied_hint}\n\n"
                f"请将此机器码发送给开发者以获取注册许可码。\n\n"
                f"（机器码也已写入日志文件 pdf_converter.log）"
            )
        except Exception as e:
            self.log(f"获取机器码失败: {str(e)}")
            messagebox.showerror("错误", f"获取机器码失败:\n{str(e)}")

    def show_register_dialog(self):
        """注册对话框"""
        dialog = tk.Toplevel(self.root)
        dialog.title("注册")
        dialog.geometry("420x220")
        dialog.transient(self.root)
        dialog.grab_set()

        ttk.Label(dialog, text="机器码:").grid(row=0, column=0, sticky=tk.W, padx=10, pady=10)
        machine_entry = ttk.Entry(dialog, width=40)
        machine_entry.grid(row=0, column=1, padx=10, pady=10)

        ttk.Label(dialog, text="许可码:").grid(row=1, column=0, sticky=tk.W, padx=10, pady=5)
        license_entry = ttk.Entry(dialog, width=40)
        license_entry.grid(row=1, column=1, padx=10, pady=5)

        # 提示：可以从日志获取机器码
        ttk.Label(dialog, text="提示: 机器码可在日志文件中查看", foreground='gray')\
            .grid(row=2, column=0, columnspan=2, pady=5)

        def do_register():
            machine_code = machine_entry.get().strip()
            license_code = license_entry.get().strip()
            if not machine_code or not license_code:
                messagebox.showwarning("警告", "请填写机器码和许可码")
                return
            self.log(f"正在注册: 机器码={machine_code}")
            success, message = self.checker.register(machine_code, license_code)
            self.log(message)
            if success:
                serial = self.parse_serial_from_license(license_code)
                msg = "注册成功！"
                if serial is not None:
                    msg += f"\n\n许可码序列号: {serial}\n配额用完后，请将机器码和许可码告知开发者，\n开发者将生成序列号 {serial + 1} 的新许可码。"
                messagebox.showinfo("成功", msg)
                self.update_status()
                dialog.destroy()
            else:
                messagebox.showerror("失败", message)

        ttk.Button(dialog, text="注册", command=do_register).grid(row=3, column=1, padx=10, pady=20)

        dialog.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() - dialog.winfo_width()) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - dialog.winfo_height()) // 2
        dialog.geometry(f"+{x}+{y}")

    def update_status(self):
        """更新状态显示"""
        try:
            if self.checker.is_registered():
                usage = self.checker.get_usage()
                license_info = self.checker.get_license_info()
                self.status_var.set("已注册")
                self.status_label.config(foreground='green')
                self.machine_var.set(usage.get('machine_code', ''))
                self.quota_var.set(f"配额: {usage.get('files_used', 0)}/{usage.get('limit', 20)}")
                if usage.get('files_remaining', 0) <= 0:
                    self.quota_var.set("配额已用完")
                    self.status_label.config(foreground='red')

                # 显示许可码和序列号（续期时告知开发者）
                license_code = license_info.get('license_code', '') if license_info else ''
                self.license_var.set(license_code)
                serial = self.parse_serial_from_license(license_code) if license_code else None
                if serial is not None:
                    self.serial_var.set(
                        f"当前序列号: {serial}（续期时请告知开发者，将生成序列号 {serial + 1} 的新许可码）")
                else:
                    self.serial_var.set("")
            else:
                self.status_var.set("未注册")
                self.status_label.config(foreground='red')
                self.machine_var.set("点击'获取机器码'后显示")
                self.quota_var.set("配额: --")
                self.license_var.set("（注册后显示）")
                self.serial_var.set("")
        except Exception as e:
            self.log(f"更新状态出错: {str(e)}")

    def open_page_editor(self):
        """打开PDF页面编辑窗口"""
        if not self.checker.is_registered():
            messagebox.showwarning("警告", "请先注册后才能使用该功能")
            self.show_register_dialog()
            return
        try:
            initial = self.file_var.get().strip()
            if initial and not initial.lower().endswith('.pdf'):
                initial = None
            PDFPageEditor(self.root, self.checker, self.log, initial_file=initial if os.path.exists(initial or '') else None)
        except Exception as e:
            self.log(f"打开页面编辑失败: {e}")
            messagebox.showerror("错误", f"打开页面编辑失败:\n{str(e)}")

    def open_invoice_recognizer(self):
        """打开发票识别窗口"""
        if not self.checker.is_registered():
            messagebox.showwarning("警告", "请先注册后才能使用该功能")
            self.show_register_dialog()
            return
        try:
            initial = self.file_var.get().strip()
            if initial and not initial.lower().endswith('.pdf'):
                initial = None
            InvoiceRecognizerWindow(self.root, self.checker, self.log,
                                    initial_file=initial if os.path.exists(initial or '') else None)
        except Exception as e:
            self.log(f"打开发票识别失败: {e}")
            messagebox.showerror("错误", f"打开发票识别失败:\n{str(e)}")

    def open_invoice_print(self):
        """发票打印排版：B5发票→A4上下两份，自动保存到临时目录，并调用系统默认的打印预览"""
        if not self.checker.is_registered():
            messagebox.showwarning("警告", "请先注册后才能使用该功能")
            self.show_register_dialog()
            return

        initial = self.file_var.get().strip()
        if not (initial and initial.lower().endswith('.pdf') and os.path.exists(initial)):
            initial = None
        src = filedialog.askopenfilename(
            title="选择发票PDF（建议为B5尺寸）",
            filetypes=[("PDF文件", "*.pdf")],
            initialdir=os.path.dirname(initial) if initial else None)
        if not src:
            return

        # 输出自动保存到临时目录（不弹保存对话框）
        import tempfile
        dst = os.path.join(
            tempfile.gettempdir(),
            f"invoice_a4_{datetime.now().strftime('%Y%m%d_%H%M%S')}_"
            f"{os.path.splitext(os.path.basename(src))[0]}.pdf")

        # 先检查配额（不扣减，成功生成后才扣）
        usage = self.checker.get_usage()
        limit = usage.get('limit', 20)
        if usage.get('total_files', 0) >= limit:
            messagebox.showwarning("配额不足", f"配额已用完 ({usage.get('total_files', 0)}/{limit})，请联系开发者。")
            self.update_status()
            return

        try:
            self.log("正在生成发票A4打印版（上下两份）...")
            info = build_a4_dual_invoice(src, dst)
            self.checker.check_and_increment(os.path.basename(src))
            w, h = info["source_size_mm"]
            self.log(f"  发票尺寸: {w} x {h} mm")
            self.log(f"  已生成: {dst}")
            self.update_status()
        except Exception as e:
            self.log(f"发票打印排版失败: {e}")
            messagebox.showerror("错误", f"发票打印排版失败:\n{str(e)}")
            return

        # 生成成功：调用系统默认的打印预览（系统默认PDF程序打开，自带打印预览）
        from invoice_print_layout import open_in_default_viewer
        try:
            open_in_default_viewer(dst)
            self.log(f"已生成并调用系统默认打印预览: {dst}")
            messagebox.showinfo(
                "发票打印",
                f"已生成A4两联版并打开系统默认打印预览。\n"
                f"可在预览中打印，或用系统打印对话框确认。\n\n输出(临时目录)：{dst}")
        except Exception as e:
            self.log(f"[发票打印] 调用系统默认打印预览失败: {e}")
            messagebox.showerror(
                "打印预览失败",
                f"无法调用系统默认打印预览：\n{e}\n\n"
                f"输出文件已保存（临时目录）：\n{dst}\n可用任意PDF软件打开打印。")

    def merge_pdfs(self):
        """PDF合并：多份PDF合并为一个，可对每份PDF旋转并统一页面方向，方便一次打印"""
        if not self.checker.is_registered():
            messagebox.showwarning("警告", "请先注册后才能使用该功能")
            self.show_register_dialog()
            return

        files = list(filedialog.askopenfilenames(
            title="选择要合并的PDF（按选择顺序合并；可多选）",
            filetypes=[("PDF文件", "*.pdf")]))
        if not files:
            return
        if len(files) < 2:
            messagebox.showinfo("提示", "请至少选择两个PDF文件进行合并。")
            return

        # 旋转/方向设置对话框
        dlg = PDFMergeDialog(self.root, files, self.log)
        if dlg.result is None:
            self.log("已取消合并")
            return
        rotations, auto_orient = dlg.result
        if rotations:
            for f, a in rotations.items():
                self.log(f"旋转设置: {os.path.basename(f)} → {a}°顺时针")
        if auto_orient:
            self.log(f"自动统一页面方向: {'纵向' if auto_orient == 'portrait' else '横向'}")

        dst = filedialog.asksaveasfilename(
            title="保存合并后的PDF",
            defaultextension=".pdf",
            filetypes=[("PDF文件", "*.pdf")],
            initialfile="合并结果.pdf")
        if not dst:
            return

        # 先检查配额（不扣减，成功合并后才扣）
        usage = self.checker.get_usage()
        limit = usage.get('limit', 20)
        if usage.get('total_files', 0) >= limit:
            messagebox.showwarning("配额不足",
                                   f"配额已用完 ({usage.get('total_files', 0)}/{limit})，请联系开发者。")
            self.update_status()
            return

        try:
            self.log(f"开始合并 {len(files)} 个PDF...")
            total_pages, per_file = merge_pdf_files(files, dst, rotations=rotations,
                                                     auto_orient=auto_orient, log_func=self.log)
            self.checker.check_and_increment(os.path.basename(dst))
            rotated_total = sum(p['rotated'] for p in per_file)
            self.log(f"合并完成，共 {total_pages} 页（旋转调整 {rotated_total} 页）-> {dst}")
            self.update_status()
        except Exception as e:
            self.log(f"PDF合并失败: {e}")
            messagebox.showerror("错误", f"PDF合并失败:\n{str(e)}")
            return

        from invoice_print_layout import open_in_default_viewer
        if messagebox.askyesno(
                "PDF合并",
                f"合并成功，共 {total_pages} 页。\n输出文件：{dst}\n\n是否打开系统默认打印预览？"):
            try:
                open_in_default_viewer(dst)
                self.log(f"已调用系统默认打印预览: {dst}")
            except Exception as e2:
                messagebox.showwarning("提示", f"无法调用预览：{e2}\n文件已保存于：{dst}")

    def start_conversion(self):
        """开始转换（直接调用内嵌逻辑，不启动新进程）"""
        if not self.checker.is_registered():
            messagebox.showwarning("警告", "请先注册后才能使用转换功能")
            self.show_register_dialog()
            return

        usage = self.checker.get_usage()
        if usage.get('files_remaining', 0) <= 0:
            messagebox.showerror("错误", "配额已用完，请联系开发者获取新的许可码")
            return

        input_file = self.file_var.get().strip()
        if not input_file:
            messagebox.showwarning("警告", "请选择要转换的文件")
            return
        if not os.path.exists(input_file):
            messagebox.showerror("错误", f"文件不存在: {input_file}")
            return

        output_dir = self.output_var.get().strip()
        if not output_dir:
            output_dir = os.path.dirname(input_file)
            self.output_var.set(output_dir)
        elif not os.path.exists(output_dir):
            # 目录不存在则自动创建
            try:
                os.makedirs(output_dir, exist_ok=True)
                self.log(f"已自动创建输出目录: {output_dir}")
            except Exception:
                output_dir = os.path.dirname(input_file)
                self.output_var.set(output_dir)

        output_format = self.format_var.get()
        file_ext = os.path.splitext(input_file)[1].lower()
        base_name = os.path.splitext(input_file)[0]
        # 输出文件基础路径（使用用户指定的输出目录）
        out_base = os.path.join(output_dir, os.path.basename(base_name))

        self.log(f"开始转换: {os.path.basename(input_file)}")
        self.log(f"输出格式: {output_format}")
        self.log(f"输出目录: {output_dir}")
        self.convert_btn.config(state='disabled')
        self.root.update()

        try:
            output_file = None

            if file_ext == '.pdf':
                # 图片型PDF：转换函数内部自动处理（忽略水印嵌入图片）
                if detect_image_pdf(input_file):
                    self.log("⚠ 检测到图片型PDF（扫描件）")
                    self.log("   将忽略水印文本层，直接转换页面图片")
                    self.log("   图片将嵌入到输出的Word/Excel文档中")

                # 非图片型或图片型，都走统一的转换逻辑
                if output_format == 'excel':
                    output_file = pdf_to_excel_internal(input_file, out_base + '.xlsx', self.log)
                elif output_format == 'word':
                    output_file = pdf_to_word_internal(input_file, out_base + '.docx', self.log)
                else:
                    # 自动检测: 有表格倾向excel，否则word
                    self.log("自动检测PDF类型...")
                    import pdfplumber
                    table_count = 0
                    text_chars = 0
                    with pdfplumber.open(input_file) as pdf:
                        for page in pdf.pages:
                            table_count += len(page.extract_tables())
                            text = page.extract_text()
                            if text:
                                text_chars += len(text)
                    self.log(f"检测结果: 表格={table_count}, 文字={text_chars}字符")
                    if table_count > 0 and table_count * 500 > text_chars:
                        output_file = pdf_to_excel_internal(input_file, out_base + '.xlsx', self.log)
                    else:
                        output_file = pdf_to_word_internal(input_file, out_base + '.docx', self.log)

            elif file_ext in ['.docx', '.doc']:
                # Word → PDF
                output_file = doc_to_pdf_internal(input_file,
                                                  os.path.join(output_dir, os.path.basename(base_name) + '.pdf'),
                                                  self.log)
            elif file_ext in ['.xlsx', '.xls']:
                # Excel → PDF
                output_file = excel_to_pdf_internal(input_file,
                                                    os.path.join(output_dir, os.path.basename(base_name) + '.pdf'),
                                                    self.log)
            elif file_ext in IMAGE_EXTS:
                # 图片 → PDF
                self.log("图片输入，输出固定为PDF格式")
                output_file = image_to_pdf_internal(input_file,
                                                    os.path.join(output_dir, os.path.basename(base_name) + '.pdf'),
                                                    self.log)
            else:
                raise ValueError(f"不支持的文件格式: {file_ext}")

            # 转换成功，扣减配额
            self.log(f"✓ 转换成功: {output_file}")
            allowed, msg = self.checker.check_and_increment(os.path.basename(input_file))
            self.log(msg)
            self.update_status()
            messagebox.showinfo("成功", f"转换成功！\n\n输出文件:\n{output_file}")

        except Exception as e:
            self.log(f"✗ 转换失败: {str(e)}")
            messagebox.showerror("错误", f"转换失败:\n{str(e)}")
        finally:
            self.convert_btn.config(state='normal')


def main():
    """主函数"""
    # 单实例检查：防止重复打开多个GUI窗口
    if not check_single_instance():
        messagebox.showwarning(
            "提示",
            "PDF转换器已经在运行中！\n请查看已打开的窗口，无需重复启动。"
        )
        return

    # 高DPI支持
    if sys.platform == 'win32':
        try:
            from ctypes import windll
            windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            pass

    # 使用TkinterDnD支持拖拽（不可用时回退到普通Tk）
    if HAS_DND:
        root = TkinterDnD.Tk()
    else:
        root = tk.Tk()
    app = PDFConverterGUI(root)
    root.mainloop()


if __name__ == '__main__':
    main()
