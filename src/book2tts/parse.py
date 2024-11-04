from ebooklib import epub
from datetime import datetime
from bs4 import BeautifulSoup

from book2tts.books import (Book, Metadata, TocEntry, Content)


def traverse_toc(items, toc, level):
    level = level + 1
    for i, item in enumerate(items):
        if isinstance(item, tuple):
            section, children = item
            entry = TocEntry(
                title=section.title,
                level=level,
                page=section.href,
                position=0,
                children=[],
                index=i,
            )
            traverse_toc(children, entry.children, level)
            toc.append(entry)
        elif isinstance(item, epub.Link):
            entry = TocEntry(
                title=item.title,
                page=item.href,
                level=level,
                position=0,
                children=[],
                index=i,
            )
            toc.append(entry)

    return


def html2texts(content):
    soup = BeautifulSoup(content, 'xml')
    texts = soup.get_text('\n', strip=True)
    """
    texts = '\n'.join(
        list(
            map(lambda s: s.replace(' ', '').replace('\xa0', ''),
                texts.split('\n'))))
    """
    return texts


def parse_epub(filename) -> Book:
    ebook = epub.read_epub(filename)
    md = Metadata(
        title=ebook.title,
        authors=[],
        language=ebook.language,
        file_type="epub",
        isbn="",
        original_file=filename,
        created_at=datetime.now(),
    )
    toc = []
    traverse_toc(ebook.toc, toc, level=0)
    contents = []
    for i, it in enumerate(ebook.items):
        print(it.get_name())
        if it.get_type() == 9:
            content = Content(page=it.get_name(),
                              position=i,
                              text=html2texts(it.get_content()),
                              toc_index=None)
            contents.append(content)
    return Book(metadata=md, table_of_contents=toc, content=contents)
