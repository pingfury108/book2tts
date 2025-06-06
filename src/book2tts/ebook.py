from functools import lru_cache
from ebooklib import epub
from bs4 import BeautifulSoup


def traverse_toc(items, toc):
    for item in items:
        if isinstance(item, tuple):
            section, children = item
            toc.append(
                {
                    "title": section.title,
                    "href": section.href.split("#")[0],
                    # "href": section.href.split("#")[0].replace("/", "_"),
                }
            )
            traverse_toc(children, toc)
        elif isinstance(item, epub.Link):
            toc.append(
                {
                    "title": item.title,
                    "href": item.href.split("#")[0],
                }
                # {"title": item.title, "href": item.href.split("#")[0].replace("/", "_")}
            )
    return


def get_content_with_href(book, href: str):
    h = href.split("#")[0]
    
    try:
        item = book.get_item_with_href(h)
        
        if item:
            try:
                content = item.get_content()
                
                soup = BeautifulSoup(content, "html.parser")
                
                # p_tags = soup.find_all('p')
                for a in soup.find_all("a"):
                    a.decompose()
                    
                texts = soup.get_text("\n", strip=True)
                
                # texts = "\n".join([p.text for p in p_tags])
                texts = "\n".join(
                    list(
                        map(
                            lambda s: s.replace(" ", "").replace("\xa0", ""),
                            texts.split("\n"),
                        )
                    )
                )
                
                return texts
            except Exception as e:
                return f"Error extracting content: {str(e)}"
        else:
            # Try to log available items to help diagnose the issue
            available_items = [item.get_name() for item in book.items if item.get_type() == 9]
            return f"No content found for href: {href}"
    except Exception as e:
        return f"Error: {str(e)}"


def ebook_toc(book):
    tocs = []
    traverse_toc(book.toc, tocs)

    seen = set()
    result = []

    for t in tocs:
        if t["href"] not in seen:
            seen.add(t["href"])
            result.append(t)
    return result


def ebook_pages(book):
    return [
        # {"title": item.get_name(), "href": item.get_name().replace("/", "_")}
        {"title": item.get_name(), "href": item.get_name()}
        for item in book.items
        if item.get_type() == 9
    ]


@lru_cache(maxsize=10)
def open_ebook(filepath):
    try:
        book = epub.read_epub(filepath)
        return book
    except Exception as e:
        raise
