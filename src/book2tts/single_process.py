import tempfile
import shutil
import os
import time
import gradio as gr

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
from book2tts.ocr import ocr_volc
from book2tts.llm_service import LLMService

# Global variables to be shared with UI
book = None
book_toc = []
book_type = None
book_type_pdf_img = False
book_type_pdf_img_vector = False

def init_single_process_ui(llm_service, DEFAULT_SYSTEM_PROMPT):
    with gr.TabItem("单篇处理"):
        with gr.Row():
            with gr.Column():
                with gr.Row():
                    pdf_img = gr.Checkbox(label="扫描版本PDF")
                    pdf_img_vector = gr.Checkbox(label="矢量图PDF")
                    pass
                file = gr.File(label="选择书")
                pass
            with gr.Column():
                book_title = gr.Textbox(label="书名")
                dir_tree = gr.Dropdown([], label="选择章节", multiselect=True)
                with gr.Row():
                    start_page = gr.Slider(0, 500, label="开始页数")
                    end_page = gr.Slider(0, 500, label="结束页数")
                    pass
                btn_get_text = gr.Button("提取PDF区间页文本")
                pass
            with gr.Column():
                with gr.Row():
                    line_num_head = gr.Slider(
                        label="掐头行数",
                    )
                    line_num_tail = gr.Slider(
                        label="去尾行数",
                    )
                    pass
                btn_clean = gr.Button("清理")
                with gr.Row():
                    volc_ak = gr.Textbox(
                        label="火山云AK",
                        value=os.getenv(
                            "VOLC_AK",
                        ),
                    )
                    volc_sk = gr.Textbox(
                        label="火山云SK",
                        value=os.getenv(
                            "VOLC_SK",
                        ),
                    )
                    btn_ocr_volc = gr.Button("识别PDF图片(OCR)")
                pass

        with gr.Row():
            system_prompt = gr.TextArea(
                label="系统提示词",
                value=DEFAULT_SYSTEM_PROMPT,
                lines=10
            )
        with gr.Row():
            btn_llm = gr.Button("处理语言文本")

        gr.Markdown("### 编辑文本")
        with gr.Row():
            with gr.Column():
                text_content = gr.TextArea(label="章节内容")
                pass
            with gr.Column():
                tts_content = gr.TextArea(label="语音文本")
                pass
            pass

        with gr.Row():
            tts_provide = gr.Dropdown(["edge_tts", "azure"], label="提供商", value="azure")
            azure_key = gr.Textbox(
                label="azure api key",
                value=os.getenv(
                    "AZURE_KEY",
                ),
            )
            azure_region = gr.Textbox(
                label="azure api region",
                value=os.getenv(
                    "AZURE_REGION",
                ),
            )

            tts_mode = gr.Dropdown(
                edge_tts_volices(), label="选择声音模型", value="zh-CN-YunxiNeural"
            )
            btn1 = gr.Button("生成语音")

            pass

        with gr.Row():
            outfile = gr.Textbox(label="输出文件名称")
            pass

        gr.Markdown("### 音频播放")
        with gr.Row():
            audio = gr.Audio(
                label="输出音频", 
                sources=[], 
                autoplay=False,  # 禁用自动播放
                show_download_button=True,  # 显示下载按钮
                format="mp3"  # 指定音频格式
            )
            pass
    
    # Connect event handlers
    def parse_toc(file):
        global book, book_toc, book_type, book_type_pdf_img
        if file is None:
            return None, None
        if file.endswith(".pdf"):
            book_type = "pdf"
            if book_type_pdf_img:
                if book_type_pdf_img_vector:
                    book_toc = extract_img_vector_by_page(file)
                    dropdown = gr.Dropdown(
                        choices=[f"page-{i}" for i, _ in enumerate(book_toc)], multiselect=True
                    )
                else:
                    book_toc = extract_img_by_page(file)
                    dropdown = gr.Dropdown(
                        choices=[f"page-{i}" for i, _ in enumerate(book_toc)], multiselect=True
                    )
            else:
                result = extract_text_by_page(file)
                book_toc = result["pages"]
                
                # 检查是否有目录
                if result["toc"]:
                    # 使用目录结构创建下拉列表选项
                    toc_choices = []
                    # 对目录按页码排序
                    sorted_toc = sorted(result["toc"], key=lambda x: x[2])  # 按页码排序
                    
                    # 处理每个章节的页码范围
                    for i, (level, title, page) in enumerate(sorted_toc):
                        # 计算章节的结束页码
                        end_page = page
                        if i < len(sorted_toc) - 1:
                            # 如果不是最后一个章节，结束页码是下一个章节的开始页码减1
                            end_page = sorted_toc[i + 1][2] - 1
                        
                        # 根据层级添加缩进，页码减1以匹配从0开始的PDF页面索引
                        indent = "  " * (level - 1)
                        # 添加页码范围信息
                        if end_page > page:
                            toc_choices.append(f"{indent}{title} (p.{page-1}-{end_page-1})")
                        else:
                            toc_choices.append(f"{indent}{title} (p.{page-1})")
                            
                    dropdown = gr.Dropdown(choices=toc_choices, multiselect=True)
                else:
                    # 如果没有目录，使用原来的页码方式
                    dropdown = gr.Dropdown(
                        choices=[f"page-{i}" for i, _ in enumerate(book_toc)], multiselect=True
                    )
            return dropdown, file.split("/")[-1].split(".")[0].replace(" ", "_")
        elif file.endswith(".epub"):
            book_type = "epub"
            book = open_ebook(file)
            book_toc = ebook_toc(book)
            dropdown = gr.Dropdown(
                choices=[f"{i}-{t.get('title')}" for i, t in enumerate(book_toc)],
                multiselect=True,
            )
            return dropdown, book.title
        pass

    def ocr_content_volc(value, ak, sk, start_page: int, end_page: int):
        if start_page > 0 and end_page > start_page:
            value = [f"page-{i}" for i in range(start_page, end_page)]
            pass
        if book_type == "pdf":
            if book_type_pdf_img:
                results = []
                for i in [int(s.split("-")[-1]) for s in value]:
                    time.sleep(1)
                    text = ocr_volc(ak, sk, save_img(book_toc[i]))
                    results.append(text)
                    yield "\n\n\n".join(results)
                    pass
            pass
        return ""

    def parse_content_range(
        value,
        start_page: int,
        end_page: int,
        line_num_head: int = 0,
        line_num_tail: int = 0,
    ):
        if start_page > 0 and end_page > start_page:
            value = [f"page-{i}" for i in range(start_page, end_page)]
            pass
        if book_type == "pdf":
            if not book_type_pdf_img:
                results = []
                for i in [int(s.split("-")[-1]) for s in value]:
                    text = book_toc[i]
                    # Apply line number trimming
                    text_lines = text.split("\n")
                    if len(text_lines) > 1:
                        end_idx = (
                            len(text_lines) if line_num_tail == 0 else -line_num_tail
                        )
                        text = "\n".join(text_lines[line_num_head:end_idx])
                    results.append(text)
                    yield "\n\n\n".join(results)
                    pass
            pass
        return ""

    def parse_content(value, book_title, line_num_head: int = 0, line_num_tail: int = 0):
        if value is None or book_title is None:
            return None, None
        if book_type == "pdf":
            if book_type_pdf_img:
                return "", gen_out_file(book_title, value)
            else:
                texts = []
                for selection in value:
                    # 检查是否是目录格式 (包含 "p.") 还是页码格式
                    if "(p." in selection:
                        # 从目录格式中提取页码范围
                        page_range = selection.split("(p.")[-1].rstrip(")")
                        if "-" in page_range:
                            # 处理页码范围
                            start_page, end_page = map(int, page_range.split("-"))
                            # 提取这个区间的所有页面
                            for page_num in range(start_page, end_page + 1):
                                if page_num < len(book_toc):
                                    text = str(book_toc[page_num])
                                    # Apply line number trimming
                                    text_lines = text.split("\n")
                                    if len(text_lines) > 1:
                                        end_idx = len(text_lines) if line_num_tail == 0 else -line_num_tail
                                        text = "\n".join(text_lines[line_num_head:end_idx])
                                    texts.append(text)
                        else:
                            # 处理单个页码
                            page_num = int(page_range)
                            if page_num < len(book_toc):
                                text = str(book_toc[page_num])
                                # Apply line number trimming
                                text_lines = text.split("\n")
                                if len(text_lines) > 1:
                                    end_idx = len(text_lines) if line_num_tail == 0 else -line_num_tail
                                    text = "\n".join(text_lines[line_num_head:end_idx])
                                texts.append(text)
                    else:
                        # 从页码格式中提取页码
                        page_num = int(selection.split("-")[-1])
                        if page_num < len(book_toc):
                            text = str(book_toc[page_num])
                            # Apply line number trimming
                            text_lines = text.split("\n")
                            if len(text_lines) > 1:
                                end_idx = len(text_lines) if line_num_tail == 0 else -line_num_tail
                                text = "\n".join(text_lines[line_num_head:end_idx])
                            texts.append(text)
                return "\n\n\n".join(texts), gen_out_file(book_title, value)

        hrefs = [
            t.get("href")
            for i, t in enumerate(book_toc)
            if f"{i}-{t.get('title')}" in value
        ]
        texts = [get_content_with_href(book, href) or "" for href in hrefs]
        texts = list(map(lambda v: v or "", texts))
        texts = list(map(lambda v: v.strip(), texts))

        return "\n\n\n".join(texts), gen_out_file(book_title, value)

    def outfile_prefix(dir_tree):
        if dir_tree and len(dir_tree) > 0:
            return f"-{dir_tree[0]}-"

        return ""

    def gen_out_file(book_title, dir_tree):
        os.makedirs("/tmp/book2tts", exist_ok=True)
        tmpfile = tempfile.NamedTemporaryFile(
            suffix=".mp3",
            dir="/tmp/book2tts",
            prefix=f"{book_title}{outfile_prefix(dir_tree)}",
            delete=True,
        )
        outfile = tmpfile.name
        return outfile

    def gen_tts(
        text_content,
        tts_content,
        tts_provide,
        tts_mode,
        outfile,
        azure_key,
        azure_region,
    ):
        content = text_content
        if tts_content.strip() != "":
            content = tts_content
            pass

        if tts_provide == "edge_tts":
            r = edge_text_to_speech(content, tts_mode, outfile)
            print(f"edge tts: {r}")
            pass
        elif tts_provide == "azure":
            r = azure_long_text_to_speech(
                key=azure_key,
                region=azure_region,
                text=content,
                output_file=outfile,
                voice_name=tts_mode,
            )
            print(f"azure tts: {r}")
            pass

        return outfile

    def clean_tmp_file():
        shutil.rmtree("/tmp/book2tts")
        return

    def exclude_text(text, line_num_head: int = 1, line_num_tail: int = 1):
        lines = text.split("\n")
        if line_num_tail == 0:
            line_num_tail = len(lines)
        else:
            line_num_tail = -line_num_tail
            pass
        return "\n".join(lines[line_num_head:line_num_tail])

    def llm_gen(text, line_num_head, line_num_tail, system_prompt):
        results = []
        for sub_text in text.split("\n\n\n"):
            result = llm_service.process_text(
                system_prompt=system_prompt,
                user_content=exclude_text(sub_text, line_num_head, line_num_tail),
                temperature=0.7
            )
            if result.get("success"):
                results.append(result["result"])
            else:
                print(f"llm gen error: {result.get('error')}")
            yield "".join(results)
        pass

    def is_pdf_img(img, vector):
        global book_type_pdf_img, book_type_pdf_img_vector
        book_type_pdf_img = img
        book_type_pdf_img_vector = vector
        print(book_type_pdf_img, book_type_pdf_img_vector)
        return img, vector

    # Connect all the events
    file.change(parse_toc, inputs=file, outputs=[dir_tree, book_title])
    dir_tree.change(
        parse_content,
        inputs=[dir_tree, book_title, line_num_head, line_num_tail],
        outputs=[text_content, outfile],
    )

    btn1.click(
        gen_tts,
        inputs=[
            text_content,
            tts_content,
            tts_provide,
            tts_mode,
            outfile,
            azure_key,
            azure_region,
        ],
        outputs=[audio],
    )
    btn_clean.click(clean_tmp_file)
    btn_llm.click(
        llm_gen,
        inputs=[
            text_content,
            line_num_head,
            line_num_tail,
            system_prompt,
        ],
        outputs=tts_content,
    )
    pdf_img.change(is_pdf_img, inputs=[pdf_img, pdf_img_vector])
    pdf_img_vector.change(is_pdf_img, inputs=[pdf_img, pdf_img_vector])
    btn_ocr_volc.click(
        ocr_content_volc,
        inputs=[dir_tree, volc_ak, volc_sk, start_page, end_page],
        outputs=[text_content],
    )

    btn_get_text.click(
        parse_content_range,
        inputs=[dir_tree, start_page, end_page, line_num_head, line_num_tail],
        outputs=[text_content],
    )
    
    # Return components that might need to be accessed from the main file
    return {
        "text_content": text_content,
        "tts_content": tts_content,
        "file": file,
        "dir_tree": dir_tree,
        "audio": audio,
        "book_title": book_title,
        "line_num_head": line_num_head,
        "line_num_tail": line_num_tail,
    } 