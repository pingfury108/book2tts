import unicodedata
import tempfile
import os
import pymupdf

from PIL import Image
from pypdf import PdfReader
from io import StringIO, BytesIO

from pdfminer.converter import TextConverter
from pdfminer.layout import LAParams
from pdfminer.pdfdocument import PDFDocument
from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter
from pdfminer.pdfpage import PDFPage
from pdfminer.pdfparser import PDFParser


def extract_text_by_page(pdf_path):
    """
    使用 pdfminer.six 的可组合 API 逐页提取 PDF 文本。

  Args:
    pdf_path: PDF 文件路径。

  Returns:
    一个列表，其中每个元素都是一个字符串，表示一页的文本。返回空列表表示出错。
    """
    try:
        output_strings = []
        with open(pdf_path, 'rb') as in_file:
            parser = PDFParser(in_file)
            doc = PDFDocument(parser)
            rsrcmgr = PDFResourceManager()
            for page in PDFPage.create_pages(doc):
                output_string = StringIO()
                device = TextConverter(rsrcmgr,
                                       output_string,
                                       laparams=LAParams())
                interpreter = PDFPageInterpreter(rsrcmgr, device)
                interpreter.process_page(page)
                output_strings.append(output_string.getvalue())
                device.close()
                output_string.close()
        return list(map(clean_text, output_strings))
    except Exception as e:
        print(f"提取文本出错: {e}")
        return []


def clean_text(text):
    text = unicodedata.normalize('NFKC', text)
    return text


def extract_img_by_page(pdf_path):
    """
    reader = PdfReader(pdf_path)
    print("pdf img page")

    return [page.images[0].data for page in reader.pages if page.images]
    """
    doc = pymupdf.open(pdf_path)
    print("pdf img page")
    return [page.get_pixmap().tobytes() for page in doc]


def save_img(image_data, img_type: str = ".jpeg"):
    os.makedirs("/tmp/book2tts/imgs", exist_ok=True)
    img = Image.open(BytesIO(image_data))
    tmpfile = tempfile.NamedTemporaryFile(suffix=img_type,
                                          dir="/tmp/book2tts/imgs",
                                          delete=False)
    img = img.convert('L')
    img.save(tmpfile.name)

    return tmpfile.name


def extract_img_vector_by_page(pdf_path):
    doc = pymupdf.open(pdf_path)
    print("pdf vector img page")
    return [page.get_pixmap().tobytes() for page in doc]