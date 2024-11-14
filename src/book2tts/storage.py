from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import json
import shutil
import hashlib

from book2tts.books import Metadata, Content, Book, TocEntry
from book2tts.audiobook import AudioBook


@dataclass
class StorageConfig:
    """存储配置"""

    root_path: Path  # 根目录
    books_dir: str = "books"  # 书籍目录
    audio_dir: str = "audio_books"  # 音频目录
    temp_dir: str = "temp"  # 临时文件目录


class BookStorage:
    """书籍存储管理"""

    def __init__(self, config: StorageConfig):
        self.config = config
        self._init_directories()

    def _init_directories(self):
        """初始化目录结构"""
        # 创建主目录
        self.root_path = self.config.root_path
        self.books_path = self.root_path / self.config.books_dir
        self.audio_path = self.root_path / self.config.audio_dir
        self.temp_path = self.root_path / self.config.temp_dir

        # 确保目录存在
        for path in [self.root_path, self.books_path, self.audio_path, self.temp_path]:
            path.mkdir(parents=True, exist_ok=True)

    def _get_book_hash(self, book: "Book") -> str:
        """生成书籍唯一标识"""
        # 使用书籍元数据生成唯一标识
        metadata_str = (
            f"{book.metadata.title}_{book.metadata.isbn}_{book.metadata.original_file}"
        )
        return hashlib.sha256(metadata_str.encode()).hexdigest()[:16]

    def _get_book_path(self, book_id: str) -> Path:
        """获取书籍存储路径"""
        return self.books_path / book_id

    def _get_audio_book_path(self, book_id: str, audio_book_id: str) -> Path:
        """获取有声书存储路径"""
        return self.audio_path / book_id / audio_book_id

    def store_book(self, book: "Book") -> str:
        """存储书籍"""
        book_id = self._get_book_hash(book)
        book_path = self._get_book_path(book_id)
        book_path.mkdir(parents=True, exist_ok=True)

        # 存储目录结构
        """
        books/
        └── {book_id}/
            ├── metadata.json     # 书籍元数据
            ├── toc.json         # 目录结构
            ├── content/         # 内容目录
            │   ├── chapter_1.txt
            │   ├── chapter_2.txt
            │   └── ...
            └── original/        # 原始文件
                └── book.pdf
        """

        # 存储元数据
        with open(book_path / "metadata.json", "w", encoding="utf-8") as f:
            json.dump(
                asdict(book.metadata), f, ensure_ascii=False, indent=2, default=str
            )

        # 存储目录结构
        with open(book_path / "toc.json", "w", encoding="utf-8") as f:
            json.dump(
                [asdict(toc) for toc in book.table_of_contents],
                f,
                ensure_ascii=False,
                indent=2,
            )

        # 存储内容
        content_dir = book_path / "content"
        content_dir.mkdir(exist_ok=True)

        # 按章节存储内容
        for toc in book.table_of_contents:
            chapter_content = [
                content
                for content in book.content
                if content.chapter_index == toc.content_position
            ]

            if chapter_content:
                chapter_file = content_dir / f"chapter_{toc.content_position}.txt"
                with open(chapter_file, "w", encoding="utf-8") as f:
                    for content in chapter_content:
                        f.write(content.text + "\n")

        # 复制原始文件
        original_dir = book_path / "original"
        original_dir.mkdir(exist_ok=True)
        if book.metadata.original_file:
            shutil.copy2(
                book.metadata.original_file,
                original_dir / Path(book.metadata.original_file).name,
            )

        return book_id

    def store_audio_book(self, book_id: str, audio_book: "AudioBook"):
        """存储有声书"""
        audio_book_path = self._get_audio_book_path(book_id, audio_book.book_id)
        audio_book_path.mkdir(parents=True, exist_ok=True)

        # 存储目录结构
        """
        audio_books/
        └── {book_id}/
            └── {audio_book_id}/
                ├── config.json      # TTS配置
                ├── metadata.json    # 音频元数据
                └── chapters/        # 章节音频
                    ├── chapter_1/
                    │   ├── metadata.json     # 章节音频元数据
                    │   ├── combined.mp3      # 合并后的章节音频
                    │   └── segments/         # 音频片段
                    │       ├── segment_1.mp3
                    │       ├── segment_2.mp3
                    │       └── ...
                    └── chapter_2/
                        └── ...
        """

        # 存储配置
        with open(audio_book_path / "config.json", "w", encoding="utf-8") as f:
            json.dump(asdict(audio_book.config), f, ensure_ascii=False, indent=2)

        # 存储音频元数据
        metadata = {
            "book_id": audio_book.book_id,
            "total_duration": audio_book.total_duration,
            "status": audio_book.status.value,
            "created_at": str(audio_book.created_at),
            "updated_at": str(audio_book.updated_at),
        }
        with open(audio_book_path / "metadata.json", "w", encoding="utf-8") as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)

        # 存储章节音频
        chapters_dir = audio_book_path / "chapters"
        chapters_dir.mkdir(exist_ok=True)

        for chapter in audio_book.chapters:
            chapter_dir = chapters_dir / f"chapter_{chapter.chapter_index}"
            chapter_dir.mkdir(exist_ok=True)

            # 存储章节元数据
            chapter_metadata = asdict(chapter)
            del chapter_metadata["segments"]  # 单独存储段落信息
            with open(chapter_dir / "metadata.json", "w", encoding="utf-8") as f:
                json.dump(chapter_metadata, f, ensure_ascii=False, indent=2)

            # 存储音频片段
            segments_dir = chapter_dir / "segments"
            segments_dir.mkdir(exist_ok=True)

            for segment in chapter.segments:
                if segment.audio_path:
                    # 复制音频文件
                    shutil.copy2(
                        segment.audio_path,
                        segments_dir
                        / f"segment_{segment.id}.{audio_book.config.format.value}",
                    )

                # 存储片段元数据
                segment_metadata = asdict(segment)
                del segment_metadata["audio_path"]  # 路径信息单独处理
                with open(
                    segments_dir / f"segment_{segment.id}.json", "w", encoding="utf-8"
                ) as f:
                    json.dump(segment_metadata, f, ensure_ascii=False, indent=2)

            # 复制合并后的章节音频
            if chapter.combined_audio_path:
                shutil.copy2(
                    chapter.combined_audio_path,
                    chapter_dir / f"combined.{audio_book.config.format.value}",
                )

    def load_book(self, book_id: str) -> Optional["Book"]:
        """加载书籍"""
        book_path = self._get_book_path(book_id)
        if not book_path.exists():
            return None

        # 加载元数据
        with open(book_path / "metadata.json", "r", encoding="utf-8") as f:
            metadata = Metadata(**json.load(f))

        # 加载目录
        with open(book_path / "toc.json", "r", encoding="utf-8") as f:
            toc = [TocEntry(**entry) for entry in json.load(f)]

        # 加载内容
        content = []
        content_dir = book_path / "content"
        for chapter_file in sorted(content_dir.glob("chapter_*.txt")):
            chapter_index = int(chapter_file.stem.split("_")[1])
            with open(chapter_file, "r", encoding="utf-8") as f:
                paragraphs = f.readlines()
                for idx, text in enumerate(paragraphs):
                    content.append(
                        Content(
                            text=text.strip(),
                            page_number=None,  # 可能需要从其他地方恢复
                            paragraph_index=idx,
                            chapter_index=chapter_index,
                        )
                    )

        return Book(metadata=metadata, table_of_contents=toc, content=content)
