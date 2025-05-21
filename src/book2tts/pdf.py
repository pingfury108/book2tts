import unicodedata
import tempfile
import os
import pymupdf

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
