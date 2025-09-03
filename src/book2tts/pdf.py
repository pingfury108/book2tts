import unicodedata
import tempfile
import os
import pymupdf
import hashlib

from functools import lru_cache
from PIL import Image
from io import BytesIO


def extract_text_by_page(pdf_path):
    doc = pymupdf.open(pdf_path)
    print("pdf text page")
    toc = doc.get_toc()
    print(toc)
    # 返回目录和页面内容
    return {
        "toc": toc if toc else None,  # 如果没有目录，返回None
        "pages": [page.get_text() for page in doc]
    }


def clean_text(text):
    text = unicodedata.normalize("NFKC", text)
    return text


def extract_img_by_page(pdf_path):
    doc = pymupdf.open(pdf_path)
    print("pdf img page")
    return [page.get_pixmap().tobytes() for page in doc]


def save_img(image_data, img_type: str = ".jpeg"):
    os.makedirs("/tmp/book2tts/imgs", exist_ok=True)
    img = Image.open(BytesIO(image_data))
    tmpfile = tempfile.NamedTemporaryFile(
        suffix=img_type, dir="/tmp/book2tts/imgs", delete=False
    )
    img = img.convert("L")
    img.save(tmpfile.name)

    return tmpfile.name


def extract_img_vector_by_page(pdf_path):
    doc = pymupdf.open(pdf_path)
    print("pdf vector img page")
    return [page.get_pixmap().tobytes() for page in doc]


@lru_cache(maxsize=10)
def open_pdf(pdf_path):
    return pymupdf.open(pdf_path)


@lru_cache(maxsize=10)
def pdf_pages(pdf):
    return list(pdf.pages())


def is_scanned_pdf_page(page, text_threshold: int = 50) -> bool:
    """
    检测PDF页面是否为扫描版本
    
    Args:
        page: pymupdf页面对象
        text_threshold: 文本字符阈值，少于此数量认为是扫描版
    
    Returns:
        True if 页面是扫描版，False otherwise
    """
    text = page.get_text().strip()
    
    # 如果文本很少，可能是扫描版
    if len(text) < text_threshold:
        return True
    
    # 检查是否有图像
    image_list = page.get_images()
    
    # 如果有大图像且文本很少，可能是扫描版
    if image_list:
        for img in image_list:
            # img[2] 和 img[3] 是图像的宽度和高度
            img_width = img[2] if len(img) > 2 else 0
            img_height = img[3] if len(img) > 3 else 0
            
            # 如果图像占据页面大部分区域
            page_rect = page.rect
            if img_width > page_rect.width * 0.8 and img_height > page_rect.height * 0.8:
                return True
    
    return False


def detect_scanned_pdf(pdf_path, sample_pages: int = 5) -> dict:
    """
    检测PDF是否包含扫描页面
    
    Args:
        pdf_path: PDF文件路径
        sample_pages: 检测的样本页数
    
    Returns:
        包含检测结果的字典
    """
    doc = pymupdf.open(pdf_path)
    total_pages = len(doc)
    
    if total_pages == 0:
        return {
            'is_scanned': False,
            'total_pages': 0,
            'scanned_pages': 0,
            'scanned_ratio': 0.0,
            'sample_pages': 0
        }
    
    # 确定要检测的页面数
    pages_to_check = min(sample_pages, total_pages)
    scanned_count = 0
    
    # 均匀分布取样页面
    if total_pages <= sample_pages:
        page_indices = list(range(total_pages))
    else:
        step = total_pages // sample_pages
        page_indices = [i * step for i in range(sample_pages)]
    
    # 检测每个样本页面
    for page_idx in page_indices:
        page = doc[page_idx]
        if is_scanned_pdf_page(page):
            scanned_count += 1
    
    scanned_ratio = scanned_count / len(page_indices)
    
    return {
        'is_scanned': scanned_ratio > 0.5,  # 超过一半页面是扫描版就认为是扫描PDF
        'total_pages': total_pages,
        'scanned_pages': scanned_count,
        'scanned_ratio': scanned_ratio,
        'sample_pages': len(page_indices),
        'checked_pages': page_indices
    }


def get_page_image_data(pdf_path: str, page_num: int, resolution: int = 150) -> bytes:
    """
    获取PDF页面的图像数据
    
    Args:
        pdf_path: PDF文件路径
        page_num: 页码（从0开始）
        resolution: 图像分辨率DPI
    
    Returns:
        图像的字节数据
    """
    doc = pymupdf.open(pdf_path)
    if page_num >= len(doc):
        raise IndexError(f"页码 {page_num} 超出范围，PDF共有 {len(doc)} 页")
    
    page = doc[page_num]
    
    # 计算缩放矩阵以达到指定分辨率
    zoom = resolution / 72.0  # 72 DPI是默认分辨率
    mat = pymupdf.Matrix(zoom, zoom)
    
    # 生成页面图像
    pix = page.get_pixmap(matrix=mat)
    return pix.tobytes("png")


def calculate_image_md5(image_data: bytes) -> str:
    """计算图像数据的MD5哈希值"""
    hash_md5 = hashlib.md5()
    hash_md5.update(image_data)
    return hash_md5.hexdigest()
