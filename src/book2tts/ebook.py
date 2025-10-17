from __future__ import annotations

import posixpath
import re
import zipfile
from dataclasses import dataclass
from functools import lru_cache
from typing import Dict, Iterable, List, Optional
from urllib.parse import urldefrag
from xml.etree import ElementTree as ET

import fitz  # PyMuPDF
from bs4 import BeautifulSoup
from ebooklib import epub


ITEM_DOCUMENT = 9
TEXT_MEDIA_TYPES = {
    "application/xhtml+xml",
    "text/html",
    "application/x-dtbook+xml",
    "text/x-oeb1-document",
}
CONTAINER_NAMESPACE = {"container": "urn:oasis:names:tc:opendocument:xmlns:container"}
OPF_NAMESPACE = {
    "opf": "http://www.idpf.org/2007/opf",
    "dc": "http://purl.org/dc/elements/1.1/",
}


def _normalize_lookup_key(href: str) -> str:
    path = (href or "").strip().replace("\\", "/")
    if path.startswith("./"):
        path = path[2:]
    path, _ = urldefrag(path)
    path = posixpath.normpath(path)
    if path == ".":
        return ""
    return path.lstrip("/")


def _resolve_path(base_path: str, relative: str) -> str:
    relative = (relative or "").strip().replace("\\", "/")
    if relative.startswith("/"):
        return _normalize_lookup_key(relative)
    base_dir = posixpath.dirname(base_path)
    joined = posixpath.normpath(posixpath.join(base_dir, relative))
    return _normalize_lookup_key(joined)


def _resolve_href(base_path: str, href: str) -> str:
    href = (href or "").strip().replace("\\", "/")
    if not href:
        return _normalize_lookup_key(base_path)
    if href.startswith("#"):
        base_clean = _normalize_lookup_key(base_path)
        fragment = href[1:]
        return f"{base_clean}#{fragment}" if fragment else base_clean

    path_part, fragment = urldefrag(href)
    resolved_path = _resolve_path(base_path, path_part)
    return f"{resolved_path}#{fragment}" if fragment else resolved_path


def _decode_bytes(data: bytes) -> str:
    if isinstance(data, str):
        return data
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        for encoding in ("utf-16", "utf-16le", "utf-16be", "gb18030", "latin-1"):
            try:
                return data.decode(encoding)
            except UnicodeDecodeError:
                continue
    return data.decode("utf-8", errors="ignore")


@dataclass
class EpubResource:
    zip_path: str
    media_type: str
    properties: str
    zip_file: zipfile.ZipFile
    original_href: str

    def get_content(self):
        return self.zip_file.read(self.zip_path)

    def get_name(self):
        return self.zip_path

    def get_type(self):
        if self.media_type in TEXT_MEDIA_TYPES:
            return ITEM_DOCUMENT
        return 0


class PyMuPdfEpubAdapter:
    """Provide a book-like interface backed by PyMuPDF and manual EPUB parsing."""

    def __init__(self, filepath: str):
        self.filepath = filepath
        self.doc = fitz.open(filepath)
        self._zip = zipfile.ZipFile(filepath, "r")
        self._opf_path: Optional[str] = None
        self._opf_dir: str = ""
        self.title: str = ""
        self.language: str = ""

        self._items: List[EpubResource] = []
        self._items_by_key: Dict[str, EpubResource] = {}
        self._manifest_by_id: Dict[str, EpubResource] = {}
        self._spine_order: List[str] = []
        self._guide_refs: Dict[str, str] = {}
        self._nav_href: Optional[str] = None
        self._ncx_href: Optional[str] = None
        self._toc_cache: Optional[List] = None

        self._parse_container()
        self._parse_package()

    # ----- Parsing helpers -------------------------------------------------

    def _parse_container(self):
        try:
            container_xml = self._zip.read("META-INF/container.xml")
        except KeyError as exc:
            raise FileNotFoundError("EPUB container.xml not found") from exc

        root = ET.fromstring(container_xml)
        rootfile = root.find("container:rootfiles/container:rootfile", namespaces=CONTAINER_NAMESPACE)
        if rootfile is None:
            raise ValueError("Invalid EPUB: missing rootfile")
        full_path = rootfile.attrib.get("full-path")
        if not full_path:
            raise ValueError("Invalid EPUB: empty rootfile path")

        self._opf_path = _normalize_lookup_key(full_path)
        self._opf_dir = posixpath.dirname(self._opf_path)

    def _parse_package(self):
        if not self._opf_path:
            raise ValueError("OPF path not resolved")
        opf_bytes = self._zip.read(self._opf_path)
        root = ET.fromstring(opf_bytes)

        metadata = root.find("opf:metadata", namespaces=OPF_NAMESPACE)
        if metadata is not None:
            title_el = metadata.find("dc:title", namespaces=OPF_NAMESPACE)
            if title_el is not None and title_el.text:
                self.title = title_el.text.strip()
            language_el = metadata.find("dc:language", namespaces=OPF_NAMESPACE)
            if language_el is not None and language_el.text:
                self.language = language_el.text.strip()

        manifest = root.find("opf:manifest", namespaces=OPF_NAMESPACE)
        if manifest is None:
            raise ValueError("Invalid EPUB: missing manifest")

        for item in manifest.findall("opf:item", namespaces=OPF_NAMESPACE):
            item_id = item.attrib.get("id")
            href = item.attrib.get("href", "")
            media_type = item.attrib.get("media-type", "")
            properties = item.attrib.get("properties", "")

            normalized_href = _resolve_path(self._opf_path, href)
            resource = EpubResource(
                zip_path=normalized_href,
                media_type=media_type,
                properties=properties,
                zip_file=self._zip,
                original_href=href,
            )
            self._items.append(resource)
            if item_id:
                self._manifest_by_id[item_id] = resource
            self._register_resource(resource)

            if "nav" in properties.split():
                self._nav_href = normalized_href
            if media_type == "application/x-dtbncx+xml":
                self._ncx_href = normalized_href

        spine = root.find("opf:spine", namespaces=OPF_NAMESPACE)
        if spine is not None:
            toc_ref = spine.attrib.get("toc")
            if toc_ref and toc_ref in self._manifest_by_id:
                self._ncx_href = self._manifest_by_id[toc_ref].zip_path

            for itemref in spine.findall("opf:itemref", namespaces=OPF_NAMESPACE):
                idref = itemref.attrib.get("idref")
                linear = itemref.attrib.get("linear", "yes").lower()
                if not idref or linear == "no":
                    continue
                resource = self._manifest_by_id.get(idref)
                if resource:
                    self._spine_order.append(resource.zip_path)

        guide = root.find("opf:guide", namespaces=OPF_NAMESPACE)
        if guide is not None:
            for ref in guide.findall("opf:reference", namespaces=OPF_NAMESPACE):
                ref_type = ref.attrib.get("type", "").lower()
                href = ref.attrib.get("href", "")
                resolved = _resolve_path(self._opf_path, href)
                if ref_type:
                    self._guide_refs[ref_type] = resolved

        if not self.title:
            self.title = posixpath.basename(self.filepath)
        if not self.language:
            self.language = "und"

    def _register_resource(self, resource: EpubResource):
        keys = {resource.zip_path, _normalize_lookup_key(resource.zip_path)}
        keys.add(resource.zip_path.replace("/", "_"))
        if resource.original_href:
            original_norm = _normalize_lookup_key(resource.original_href)
            if original_norm:
                keys.add(original_norm)
                keys.add(original_norm.replace("/", "_"))
        basename = posixpath.basename(resource.zip_path)
        if basename:
            keys.add(basename)
        for key in keys:
            if key:
                self._items_by_key.setdefault(key, resource)

    # ----- Public API mirrors ----------------------------------------------

    @property
    def items(self) -> Iterable[EpubResource]:
        return list(self._items)

    def get_item_with_href(self, href: str) -> EpubResource:
        if not href:
            raise KeyError("Empty href")
        candidates = set()
        raw = href.strip()
        candidates.add(raw)
        candidates.add(raw.replace("_", "/"))
        for candidate in list(candidates):
            lookup_key = _normalize_lookup_key(candidate)
            candidates.add(lookup_key)
            fragment_stripped, _ = urldefrag(candidate)
            candidates.add(fragment_stripped)
            candidates.add(_normalize_lookup_key(fragment_stripped))

        for candidate in candidates:
            lookup = _normalize_lookup_key(candidate)
            resource = self._items_by_key.get(lookup)
            if resource:
                return resource
        raise KeyError(href)

    @property
    def toc(self):
        if self._toc_cache is None:
            self._toc_cache = self._build_toc()
        return self._toc_cache

    # ----- Content helpers -------------------------------------------------

    def iter_document_items(self) -> Iterable[EpubResource]:
        if self._spine_order:
            for href in self._spine_order:
                resource = self._items_by_key.get(href)
                if resource and resource.get_type() == ITEM_DOCUMENT:
                    yield resource
            return

        for item in self._items:
            if item.get_type() == ITEM_DOCUMENT:
                yield item

    def extract_text_by_href(self, href: str) -> str:
        normalized = _normalize_lookup_key(href)
        if not normalized:
            return ""

        if self._spine_order:
            try:
                approx_index = self._spine_order.index(normalized)
            except ValueError:
                approx_index = None
        else:
            approx_index = None

        if approx_index is None:
            return self._extract_text_globally()

        if approx_index >= self.doc.page_count:
            approx_index = self.doc.page_count - 1
        if approx_index < 0:
            approx_index = 0

        try:
            page = self.doc.load_page(approx_index)
        except (ValueError, IndexError):
            return self._extract_text_globally()
        return page.get_text("text")

    def _extract_text_globally(self) -> str:
        texts = []
        for page_index in range(min(self.doc.page_count, 5)):
            try:
                page = self.doc.load_page(page_index)
            except (ValueError, IndexError):
                break
            texts.append(page.get_text("text"))
        return "\n".join(filter(None, texts))

    # ----- TOC extraction --------------------------------------------------

    def _build_toc(self):
        for builder in (
            self._extract_nav_toc,
            self._extract_ncx_toc,
            self._extract_guide_toc,
            self._extract_text_toc,
        ):
            toc = builder()
            if toc:
                return toc
        return []

    def _extract_nav_toc(self):
        if not self._nav_href:
            return []
        try:
            resource = self.get_item_with_href(self._nav_href)
        except KeyError:
            return []
        html = _decode_bytes(resource.get_content())
        soup = BeautifulSoup(html, "html.parser")

        nav_candidates = []
        for nav in soup.find_all("nav"):
            nav_type = nav.get("epub:type", "").lower()
            nav_role = nav.get("type", "").lower()
            if "toc" in nav_type or nav.get("id") == "toc" or nav_role == "toc":
                nav_candidates.append(nav)
        if not nav_candidates:
            nav_candidates = soup.find_all("nav")
        if not nav_candidates:
            return []

        base = resource.zip_path

        def walk_list(ol_tag):
            entries = []
            if not ol_tag:
                return entries
            for li in ol_tag.find_all("li", recursive=False):
                link = li.find("a", recursive=False)
                if not link:
                    continue
                title = link.get_text(strip=True)
                href = link.get("href", "").strip()
                if not title or not href:
                    continue
                resolved = _resolve_href(base, href)
                children_container = li.find(["ol", "ul"], recursive=False)
                child_entries = walk_list(children_container)
                if child_entries:
                    section = epub.Section(title, resolved)
                    entries.append((section, child_entries))
                else:
                    entries.append(epub.Link(resolved, title))
            return entries

        for nav in nav_candidates:
            first_list = nav.find(["ol", "ul"])
            toc_entries = walk_list(first_list)
            if toc_entries:
                return toc_entries
        return []

    def _extract_ncx_toc(self):
        if not self._ncx_href:
            return []
        try:
            ncx_bytes = self._zip.read(self._ncx_href)
        except KeyError:
            return []
        root = ET.fromstring(ncx_bytes)
        namespace = ""
        if root.tag.startswith("{"):
            namespace = root.tag.split("}", 1)[0][1:]

        def ns(tag: str) -> str:
            return f"{{{namespace}}}{tag}" if namespace else tag

        nav_map = root.find(ns("navMap"))
        if nav_map is None:
            return []

        def walk_navpoints(nodes):
            entries = []
            for nav_point in nodes:
                label = nav_point.find(f"{ns('navLabel')}/{ns('text')}")
                content = nav_point.find(ns("content"))
                if content is None:
                    continue
                src = content.attrib.get("src", "")
                title = label.text.strip() if label is not None and label.text else ""
                if not title or not src:
                    continue
                resolved = _resolve_href(self._ncx_href, src)
                child_navpoints = nav_point.findall(ns("navPoint"))
                child_entries = walk_navpoints(child_navpoints)
                if child_entries:
                    section = epub.Section(title, resolved)
                    entries.append((section, child_entries))
                else:
                    entries.append(epub.Link(resolved, title))
            return entries

        return walk_navpoints(nav_map.findall(ns("navPoint")))

    def _extract_guide_toc(self):
        toc_href = self._guide_refs.get("toc")
        if not toc_href:
            return []
        try:
            resource = self.get_item_with_href(toc_href)
        except KeyError:
            return []
        html = _decode_bytes(resource.get_content())
        soup = BeautifulSoup(html, "html.parser")

        links = soup.find_all("a")
        entries = []
        for link in links:
            title = link.get_text(strip=True)
            href = link.get("href", "").strip()
            if not title or not href:
                continue
            resolved = _resolve_href(resource.zip_path, href)
            entries.append(epub.Link(resolved, title))
        return entries

    def _extract_text_toc(self):
        pattern = re.compile(r"^(?P<title>.+?)\s+(?P<page>\d+)$")
        for page_index in range(min(self.doc.page_count, 10)):
            page = self.doc.load_page(page_index)
            text = page.get_text("text")
            if not text:
                continue
            if "table of contents" not in text.lower() and "contents" not in text.lower():
                continue
            entries = []
            for line in text.splitlines():
                match = pattern.match(line.strip())
                if not match:
                    continue
                title = match.group("title").strip().strip("·.")
                page_number = match.group("page")
                # Fabricate href using page index to maintain interface
                fabricated_href = f"page-{page_number}"
                entries.append(epub.Link(fabricated_href, title))
            if entries:
                return entries
        return []


def traverse_toc(items, toc):
    for item in items:
        if isinstance(item, tuple):
            section, children = item
            toc.append(
                {
                    "title": section.title,
                    "href": section.href.split("#")[0],
                }
            )
            traverse_toc(children, toc)
        elif isinstance(item, epub.Link):
            toc.append(
                {
                    "title": item.title,
                    "href": item.href.split("#")[0],
                }
            )
    return


def _html_to_plain_text(content: str) -> str:
    soup = BeautifulSoup(content, "html.parser")

    for a in soup.find_all("a"):
        a.decompose()

    for br in soup.find_all("br"):
        br.replace_with("\n")

    block_level_tags = {
        "address",
        "article",
        "aside",
        "blockquote",
        "canvas",
        "dd",
        "div",
        "dl",
        "dt",
        "fieldset",
        "figcaption",
        "figure",
        "footer",
        "form",
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "header",
        "hgroup",
        "hr",
        "li",
        "main",
        "nav",
        "noscript",
        "ol",
        "output",
        "p",
        "pre",
        "section",
        "table",
        "tfoot",
        "ul",
        "video",
    }

    parts: List[str] = []

    def walk(node):
        from bs4 import NavigableString, Tag

        if isinstance(node, NavigableString):
            parts.append(str(node))
            return

        if isinstance(node, Tag):
            name = node.name.lower()
            if name == "br":
                parts.append("\n")
                return

            if name in block_level_tags:
                parts.append("\n")

            for child in node.children:
                walk(child)

            if name in block_level_tags:
                parts.append("\n")

    walk(soup.body or soup)

    merged = "".join(parts)
    lines = [line.rstrip() for line in merged.split("\n")]

    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()

    normalized_lines = []
    blank_pending = False
    for line in lines:
        if line.strip():
            if blank_pending and normalized_lines:
                normalized_lines.append("")
            blank_pending = False
            normalized_lines.append(line)
        else:
            blank_pending = True

    if blank_pending and normalized_lines:
        normalized_lines.append("")

    return "\n".join(normalized_lines)


def _split_href_and_fragment(href: str) -> tuple[str, Optional[str]]:
    if not href:
        return "", None
    parts = href.split("#", 1)
    base = parts[0]
    fragment = parts[1] if len(parts) > 1 else None
    return base, fragment


def _matches_fragment(node, fragment: Optional[str]) -> bool:
    if not fragment or not fragment.strip():
        return False
    fragment = fragment.strip()
    from bs4 import Tag

    if isinstance(node, Tag):
        if node.get("id") == fragment or node.get("name") == fragment:
            return True
        anchor = node.find(attrs={"id": fragment})
        if anchor:
            return True
        anchor = node.find(attrs={"name": fragment})
        if anchor:
            return True
    return False


def _locate_fragment_start(soup: BeautifulSoup, fragment: Optional[str]):
    if not fragment or not fragment.strip():
        return None

    fragment = fragment.strip()
    from bs4 import Tag

    target = soup.find(id=fragment)
    if not target:
        target = soup.find(attrs={"name": fragment})
    if not target:
        target = soup.find("a", attrs={"href": f"#{fragment}"})

    if not target:
        return None

    if isinstance(target, Tag) and target.name in {"a", "span"}:
        heading_parent = target.find_parent(["h1", "h2", "h3", "h4", "h5", "h6"])
        if heading_parent:
            return heading_parent
        if target.parent and isinstance(target.parent, Tag):
            # 避免回退到 <body>/<html> 级别，否则会导致整章被提取
            parent_name = target.parent.name.lower()
            if parent_name not in {"body", "html"}:
                return target.parent

    return target


def _extract_fragment_html(content_text: str, fragment: Optional[str], end_fragment: Optional[str]) -> str:
    if not fragment:
        return content_text

    soup = BeautifulSoup(content_text, "html.parser")
    start_node = _locate_fragment_start(soup, fragment)
    if start_node is None:
        return content_text

    nodes_html: List[str] = []
    current = start_node

    while current is not None:
        if current is not start_node and _matches_fragment(current, end_fragment):
            break
        nodes_html.append(str(current))
        current = current.next_sibling

    if not nodes_html:
        return content_text

    return "".join(nodes_html)


def get_content_with_href(book: PyMuPdfEpubAdapter, href: str, end_fragment: Optional[str] = None):
    base_href, fragment = _split_href_and_fragment(href)
    h = base_href

    try:
        item = book.get_item_with_href(h)
    except KeyError:
        fallback_text = book.extract_text_by_href(h)
        return fallback_text or f"No content found for href: {href}"

    try:
        content_bytes = item.get_content()
        content_text = _decode_bytes(content_bytes)
        fragment_html = _extract_fragment_html(content_text, fragment, end_fragment and end_fragment.strip())
        return _html_to_plain_text(fragment_html)
    except Exception as exc:  # noqa: BLE001
        fallback_text = book.extract_text_by_href(h)
        return fallback_text or f"Error extracting content: {exc}"


def ebook_toc(book: PyMuPdfEpubAdapter):
    tocs: List[Dict[str, str]] = []
    traverse_toc(book.toc, tocs)

    seen = set()
    result = []

    for t in tocs:
        if t["href"] not in seen:
            seen.add(t["href"])
            result.append(t)
    return result


def ebook_pages(book: PyMuPdfEpubAdapter):
    pages = []
    for item in book.iter_document_items():
        name = item.get_name()
        pages.append({"title": name, "href": name})
    return pages


@lru_cache(maxsize=10)
def open_ebook(filepath):
    return PyMuPdfEpubAdapter(filepath)
