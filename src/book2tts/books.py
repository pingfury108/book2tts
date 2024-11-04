import json
import os

from dataclasses import dataclass, asdict, field
from typing import List, Dict, Optional, Any
from datetime import datetime
from pathlib import Path


@dataclass
class Author:
    name: str
    other_info: Dict = field(default_factory=dict)
    pass


@dataclass
class TocEntry:
    title: str
    level: int
    page: Optional[str]
    index: int
    position: int  # 在文本中的位置
    children: List['TocEntry'] = field(default_factory=list)
    pass


@dataclass
class Content:
    text: str
    page: Optional[str]
    position: int
    toc_index: Optional[int]
    pass


@dataclass
class Metadata:
    title: str
    authors: List[Author]
    language: str
    isbn: Optional[str]
    file_type: str  # pdf/epub/mobi etc
    original_file: Path
    created_at: Any
    additional_info: Dict = field(default_factory=dict)
    pass


@dataclass
class Book:
    metadata: Metadata
    table_of_contents: List[TocEntry]
    content: List[Content]

    def save_json(self, file_path: str):
        """将书籍数据保存为JSON格式"""
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(asdict(self),
                      f,
                      ensure_ascii=False,
                      indent=2,
                      default=str)
        pass

    def save(self, dir_path):
        os.makedirs(dir_path, exist_ok=True)

        # save metadata
        self.metadata.created_at = self.metadata.created_at.isoformat()
        with open(os.path.join(dir_path, "metadata.json"),
                  'w',
                  encoding='utf-8') as f:
            json.dump(asdict(self.metadata), f, ensure_ascii=False)
            pass

        # save toc
        with open(os.path.join(dir_path, "toc.json"), 'w',
                  encoding='utf-8') as f:
            json.dump([asdict(toc) for toc in self.table_of_contents],
                      f,
                      ensure_ascii=False)
            pass

        # save content
        content_dir = os.path.join(dir_path, "contents")
        os.makedirs(content_dir, exist_ok=True)

        for c in self.content:
            with open(os.path.join(content_dir, f"page_{c.position}.txt"),
                      'w',
                      encoding='utf-8') as f:

                f.write(c.text)
                pass
            pass

        # save original

        return
