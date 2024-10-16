import unicodedata
from pypdf import PdfReader, PageObject


def open_pdf_reader(file):
    reader = PdfReader(file)
    return reader


def pdf_pages(reader: PdfReader):
    return [p for p in reader.pages]


def page_text(page: PageObject):
    text = page.extract_text().strip()
    text = text.replace('\n', "")
    text = unicodedata.normalize('NFKC', text)
    return text
