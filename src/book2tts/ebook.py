import ebooklib
from ebooklib import epub
from bs4 import BeautifulSoup


def traverse_toc(items, toc):
    for item in items:
        if isinstance(item, tuple):
            section, children = item
            toc.append({"title": section.title, "href": section.href})
            traverse_toc(children, toc)
        elif isinstance(item, epub.Link):
            toc.append({"title": item.title, "href": item.href})
    return


def get_content_with_href(book, href: str):
    h = href.split('#')[0]
    item = book.get_item_with_href(h)

    if item:
        soup = BeautifulSoup(item.get_content(), 'html.parser')
        return soup.get_text('\n\n', strip=True)
    else:
        return None


def ebook_toc(book):
    tocs = []
    traverse_toc(book.toc, tocs)
    return tocs


def open_ebook(filepath):
    book = epub.read_epub(filepath)
    return book
