"""章节生成服务，基于字幕时间轴创建播客式章节列表。"""

from __future__ import annotations

import json
import logging
import math
from typing import Any, Dict, List, Optional

from .llm_service import LLMService
from web.workbench.utils.subtitle_utils import (
    format_srt_time,
    parse_srt_subtitles,
)


logger = logging.getLogger(__name__)


class ChapterGenerator:
    """根据字幕时间轴生成章节信息。"""

    def __init__(self, llm_service: Optional[LLMService] = None, max_chapters: int = 10):
        if llm_service is not None:
            self.llm_service = llm_service
        else:
            try:
                self.llm_service = LLMService()
            except Exception as exc:  # pylint: disable=broad-except
                logger.warning("初始化LLMService失败，将使用回退章节: %s", exc)
                self.llm_service = None
        self.max_chapters = max_chapters

    def generate_chapters(self, srt_content: str, title_hint: str = "") -> List[Dict[str, Any]]:
        """使用字幕内容生成章节列表。"""
        entries = parse_srt_subtitles(srt_content)
        if not entries:
            return []

        if self.llm_service is not None:
            try:
                system_prompt, user_prompt = self._build_prompt(entries, title_hint)
                llm_result = self.llm_service.process_text(
                    system_prompt=system_prompt,
                    user_content=user_prompt,
                    temperature=0.2,
                )

                if llm_result.get("success"):
                    chapters = self._parse_llm_response(llm_result.get("result", ""))
                    if chapters:
                        return chapters[: self.max_chapters]

                logger.warning("章节生成LLM结果不可用，将使用回退方案")
            except Exception as exc:  # pylint: disable=broad-except
                logger.warning("章节生成LLM调用失败: %s", exc)

        return self._generate_fallback(entries)

    def _build_prompt(self, entries: List[Dict[str, Any]], title_hint: str) -> tuple[str, str]:
        limited_entries = self._sample_entries(entries, 200)
        timeline_lines = []
        for item in limited_entries:
            timeline_lines.append(
                f"{format_srt_time(item['start_time'])} | {item['text'].replace('\n', ' ')}"
            )

        system_prompt = (
            "你是一名音频编辑，需要根据字幕时间轴划分清晰的章节。"
            "请严格输出JSON数组，每个元素包含start_seconds,start_srt,title,summary四个字段。"
            "title简洁，summary两句以内。章节数量不超过10个。"
        )

        context_title = title_hint or "音频"
        user_prompt = (
            f"音频标题：{context_title}\n"
            "以下是字幕时间轴，请据此生成章节列表：\n"
            + "\n".join(timeline_lines)
        )

        return system_prompt, user_prompt

    def _sample_entries(self, entries: List[Dict[str, Any]], max_count: int) -> List[Dict[str, Any]]:
        if len(entries) <= max_count:
            return entries

        step = len(entries) / float(max_count)
        sampled = []
        seen_indexes = set()

        for i in range(max_count):
            idx = min(int(math.floor(i * step)), len(entries) - 1)
            # 避免索引重复造成信息集中
            while idx in seen_indexes and idx < len(entries) - 1:
                idx += 1
            if idx in seen_indexes:
                continue
            sampled.append(entries[idx])
            seen_indexes.add(idx)

        if sampled and sampled[-1] is not entries[-1]:
            sampled[-1] = entries[-1]

        return sampled

    def _parse_llm_response(self, raw_response: str) -> List[Dict[str, Any]]:
        if not raw_response:
            return []

        try:
            data = json.loads(raw_response)
        except json.JSONDecodeError:
            try:
                start = raw_response.index("[")
                end = raw_response.rindex("]") + 1
                data = json.loads(raw_response[start:end])
            except (ValueError, json.JSONDecodeError):
                return []

        chapters: List[Dict[str, Any]] = []
        for item in data:
            try:
                start_seconds = float(item.get("start_seconds"))
                title = str(item.get("title", "")).strip()
                summary = str(item.get("summary", "")).strip()
                start_srt = item.get("start_srt") or format_srt_time(start_seconds)

                if not title:
                    continue

                chapters.append(
                    {
                        "start_seconds": max(0.0, start_seconds),
                        "start_srt": start_srt,
                        "title": title,
                        "summary": summary,
                    }
                )
            except (TypeError, ValueError):
                continue

        return chapters

    def _generate_fallback(self, entries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        chunk_size = max(1, len(entries) // self.max_chapters)
        chapters: List[Dict[str, Any]] = []

        for idx in range(0, len(entries), chunk_size):
            if len(chapters) >= self.max_chapters:
                break

            chunk = entries[idx : idx + chunk_size]
            if not chunk:
                continue

            start_entry = chunk[0]
            combined_text = " ".join(part["text"].replace("\n", " ") for part in chunk)
            title = combined_text[:30].strip()
            if len(combined_text) > 30:
                title += "…"

            chapters.append(
                {
                    "start_seconds": start_entry["start_time"],
                    "start_srt": format_srt_time(start_entry["start_time"]),
                    "title": title or "章节",
                    "summary": combined_text[:120],
                }
            )

        return chapters
