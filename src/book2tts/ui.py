import tempfile
import shutil
import os
import time
import gradio as gr
import uuid
import json
import datetime
from concurrent.futures import ThreadPoolExecutor
import zipfile

from dotenv import load_dotenv

from book2tts.ebook import get_content_with_href, open_ebook, ebook_toc
from book2tts.pdf import (
    extract_text_by_page,
    extract_img_by_page,
    save_img,
    extract_img_vector_by_page,
)
from book2tts.tts import (
    edge_tts_volices,
    edge_text_to_speech,
    azure_long_text_to_speech,
)
from book2tts.llm_service import LLMService
from book2tts.single_process import init_single_process_ui
from book2tts.batch_process import init_batch_process_ui

# from book2tts.llm import ocr_gemini
from book2tts.ocr import ocr_volc

load_dotenv()

# Initialize LLM service
llm_service = LLMService()

# Global system prompt for text processing
DEFAULT_SYSTEM_PROMPT = """
# Role: 我是一个专门用于排版文本内容的 AI 角色

## Goal: 将输入的文本内容，重新排版后输出，只输出排版后的文本内容

## Constrains:
- 严格保持原有语言，不进行任何语言转换（如中文保持中文，英文保持英文）
- 输出纯文本
- 去除页码(数字）之后行的文字
- 去页首，页尾不相关的文字
- 去除引文标注（如[1]、[2]、(1)、(2)等数字标注）
- 去除文本末尾的注释说明（如[1] 弗朗西斯·鲍蒙特...这类详细的注释说明）
- 缺失的标点符号补全
- 不去理解输，阐述输入内容，让输入内容，除过排版问题，都保持原样

## outputs
- 只输出排版后的文本，不要输出任何解释说明
- 纯文本格式，不适用 markdown 格式
"""

with gr.Blocks(title="Book 2 TTS") as book2tts:
    gr.Markdown("# Book 2 TTS")

    with gr.Tabs() as tabs:
        # Initialize single process UI
        single_process_components = init_single_process_ui(
            llm_service, DEFAULT_SYSTEM_PROMPT
        )

        # Initialize batch process UI
        batch_process_components = init_batch_process_ui(
            llm_service, DEFAULT_SYSTEM_PROMPT
        )

if __name__ == "__main__":
    book2tts.launch(
        inline=False,
        share=False,
    )
