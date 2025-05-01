import tempfile
import shutil
import os
import time
import gradio as gr
import uuid
import json
import datetime
from concurrent.futures import ThreadPoolExecutor

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

# from book2tts.llm import ocr_gemini
from book2tts.ocr import ocr_volc

load_dotenv()

# Initialize LLM service
llm_service = LLMService()

# Global batch tasks storage
batch_tasks = []
batch_executor = ThreadPoolExecutor(max_workers=1)
# Storage for text content of tasks
task_text_contents = {}

# Global variable to store current task index for retry button
current_task_index = None

with gr.Blocks(title="Book 2 TTS") as book2tts:
    gr.Markdown("# Book 2 TTS")
    
    with gr.Tabs() as tabs:
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
                    value="""
# Role: 我是一个专门用于排版文本内容的 AI 角色

## Constrains: 
- 保持原有语言
- 输出纯文本
- 去除页码(数字）之后行的文字
- 去页首，页尾这些文字，e.g: THE BIBLE STORY, BACK TO THE BEGINNING, PART ONE , STORY 2，BIRTHDAY OF A WORLD, THE BIBLE STORY
- 使用小写字母
- 缺失的标点符号补全
                    """,
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
        
        # Batch processing tab
        with gr.TabItem("批量处理"):
            with gr.Row():
                with gr.Column():
                    batch_file = gr.File(label="选择书")
                    batch_book_title = gr.Textbox(label="名称", info="将作为输出文件名")
                    with gr.Row():
                        batch_pdf_img = gr.Checkbox(label="扫描版本PDF")
                        batch_pdf_img_vector = gr.Checkbox(label="矢量图PDF")
                        pass
                    with gr.Row():
                        batch_start_page = gr.Slider(0, 500, label="开始页数")
                        batch_end_page = gr.Slider(0, 500, label="结束页数")
                        pass
                    with gr.Row():
                        batch_line_num_head = gr.Slider(label="掐头行数")
                        batch_line_num_tail = gr.Slider(label="去尾行数")
                        pass
                with gr.Column():
                    batch_system_prompt = gr.TextArea(
                        label="系统提示词",
                        value="""
# Role: 我是一个专门用于排版文本内容的 AI 角色

## Constrains: 
- 保持原有语言
- 输出纯文本
- 去除页码(数字）之后行的文字
- 去页首，页尾这些文字，e.g: THE BIBLE STORY, BACK TO THE BEGINNING, PART ONE , STORY 2，BIRTHDAY OF A WORLD, THE BIBLE STORY
- 使用小写字母
- 缺失的标点符号补全
                        """,
                        lines=10
                    )
                    
                    # TTS Provider selection
                    batch_tts_provide = gr.Dropdown(
                        ["edge_tts", "azure"], 
                        label="语音合成提供商", 
                        value="azure",
                        info="选择不同的TTS提供商"
                    )
                    
                    # Azure TTS settings
                    with gr.Group(visible=True) as azure_settings:
                        batch_azure_key = gr.Textbox(
                            label="Azure API Key",
                            value=os.getenv("AZURE_KEY", ""),
                            info="Azure TTS服务的API密钥"
                        )
                        batch_azure_region = gr.Textbox(
                            label="Azure Region",
                            value=os.getenv("AZURE_REGION", ""),
                            info="Azure TTS服务的区域"
                        )
                        batch_tts_mode = gr.Dropdown(
                            edge_tts_volices(), 
                            label="选择声音模型", 
                            value="zh-CN-YunxiNeural"
                        )
                    
                    # Edge TTS settings - kept for backward compatibility but hidden
                    with gr.Group(visible=False) as edge_settings:
                        pass
                
                    add_batch_btn = gr.Button("添加到队列")

            gr.Markdown("### 批量任务队列")
            batch_tasks_table = gr.Dataframe(
                headers=["ID", "名称", "页面范围", "状态", "操作"],
                datatype=["str", "str", "str", "str", "str"],
                row_count=10,
                col_count=(5, "fixed"),
                label="任务队列"
            )
            
            with gr.Row():
                start_batch_btn = gr.Button("开始处理队列")
                clear_batch_btn = gr.Button("清空队列")
                retry_task_btn = gr.Button("重试选中任务")
            
            batch_progress = gr.Markdown("准备就绪")
            batch_results = gr.Audio(
                label="已完成音频", 
                sources=[], 
                autoplay=False,  
                show_download_button=True,  
                format="mp3"
            )
            
            # Task details modal
            with gr.Accordion("任务详情", open=False, visible=False) as task_details:
                with gr.Row():
                    task_id_display = gr.Textbox(label="任务ID", interactive=False)
                    retry_button = gr.Button("重试此任务")
                
                task_title_display = gr.Textbox(label="名称", interactive=False)
                task_pages_display = gr.Textbox(label="页面范围", interactive=False)
                task_status_display = gr.Textbox(label="状态", interactive=False)
                task_output_display = gr.Textbox(label="输出文件", interactive=False)
                
                with gr.Tabs() as task_detail_tabs:
                    with gr.TabItem("原始文本"):
                        task_original_text = gr.TextArea(label="提取的原始文本", interactive=False, lines=15)
                    with gr.TabItem("处理后文本"):
                        task_processed_text = gr.TextArea(label="LLM处理后的文本", interactive=False, lines=15)
                    with gr.TabItem("执行日志"):
                        task_logs = gr.TextArea(label="任务执行日志", interactive=False, lines=15)
                    with gr.TabItem("错误详情"):
                        task_error_details = gr.TextArea(label="详细错误信息", interactive=False, lines=15)

    book = None
    book_toc = []
    book_type = None
    book_type_pdf_img = False
    book_type_pdf_img_vector = False

    default_replace_texts = []

    replace_texts = default_replace_texts

    def parse_toc(file):
        global book, book_toc, book_type, book_type_pdf_img
        if file is None:
            return None, None
        if file.endswith(".pdf"):
            book_type = "pdf"
            # book = open_pdf_reader(file)
            if book_type_pdf_img:
                if book_type_pdf_img_vector:
                    book_toc = extract_img_vector_by_page(file)
                else:
                    book_toc = extract_img_by_page(file)
            else:
                book_toc = extract_text_by_page(file)
                pass
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

    def parse_content(
        value, book_title, line_num_head: int = 0, line_num_tail: int = 0
    ):
        if value is None or book_title is None:
            return None, None
        if book_type == "pdf":
            if book_type_pdf_img:
                return "", gen_out_file(book_title, value)
            else:
                texts = []
                for i in [int(s.split("-")[-1]) for s in value]:
                    text = str(book_toc[i])
                    # Apply line number trimming
                    text_lines = text.split("\n")
                    if len(text_lines) > 1:
                        end_idx = (
                            len(text_lines) if line_num_tail == 0 else -line_num_tail
                        )
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
            """
            r = azure_text_to_speech(
                key=azure_key,
                region=azure_region,
                text=content,
                output_file=outfile,
                voice_name=tts_mode,
            )
            """
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
            line_num_tail = -line_tail
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

    # Batch processing functions
    def add_batch_task(
        batch_file, 
        batch_book_title, 
        batch_start_page, 
        batch_end_page, 
        batch_line_num_head, 
        batch_line_num_tail,
        batch_system_prompt,
        batch_tts_provide,
        batch_azure_key,
        batch_azure_region,
        batch_tts_mode,
        batch_pdf_img,
        batch_pdf_img_vector
    ):
        global batch_tasks
        
        if batch_file is None or batch_book_title == "":
            return update_batch_tasks_table()
        
        task_id = str(uuid.uuid4())[:8]
        
        # Handle file paths correctly
        file_path = ""
        if isinstance(batch_file, dict) and "name" in batch_file:
            file_path = batch_file.get("path", "")
        else:
            file_path = batch_file
            
        # Use book title or generate one if empty
        if not batch_book_title:
            if isinstance(batch_file, dict) and "name" in batch_file:
                batch_book_title = batch_file["name"].split(".")[0].replace(" ", "_")
            elif isinstance(batch_file, str):
                batch_book_title = batch_file.split("/")[-1].split(".")[0].replace(" ", "_")
        
        task = {
            "id": task_id,
            "file": file_path,
            "book_title": batch_book_title,
            "start_page": int(batch_start_page),
            "end_page": int(batch_end_page),
            "line_num_head": int(batch_line_num_head),
            "line_num_tail": int(batch_line_num_tail),
            "system_prompt": batch_system_prompt,
            "tts_provide": batch_tts_provide,
            "azure_key": batch_azure_key,
            "azure_region": batch_azure_region,
            "tts_mode": batch_tts_mode,
            "pdf_img": batch_pdf_img,
            "pdf_img_vector": batch_pdf_img_vector,
            "status": "等待中",
            "output_file": "",
            "original_text": "",
            "processed_text": "",
            "logs": [f"{get_timestamp()} 任务已创建"],
            "attempt_count": 0
        }
        
        batch_tasks.append(task)
        
        return update_batch_tasks_table()
    
    def get_timestamp():
        """Get a formatted timestamp for logs"""
        return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    def toggle_tts_settings(provider):
        """Toggle visibility of TTS provider settings based on selection"""
        # We're using the same approach as single processing
        # Just keep azure_settings visible regardless, but we'll still use the provider selection
        return gr.update(visible=True), gr.update(visible=False)
    
    def update_batch_tasks_table():
        table_data = []
        for task in batch_tasks:
            # Add a view button for each task
            view_button = "查看详情" if task["status"] != "等待中" else "暂无内容"
            table_data.append([
                task["id"],
                task["book_title"],
                f"{task['start_page']}-{task['end_page']}",
                task["status"],
                view_button
            ])
        return table_data
    
    def clear_batch_tasks():
        global batch_tasks, task_text_contents
        batch_tasks = []
        task_text_contents = {}
        return update_batch_tasks_table()
    
    def view_task_details(evt: gr.SelectData):
        row_index = evt.index[0]
        if row_index < len(batch_tasks):
            task = batch_tasks[row_index]
            
            # Don't show details for tasks that haven't been processed
            if task["status"] == "等待中" and task["attempt_count"] == 0:
                return {
                    task_details: gr.update(visible=False)
                }
            
            # Format logs as a string
            logs_text = "\n".join(task.get("logs", []))
            
            # Extract error details if available
            error_details = ""
            if "error_details" in task:
                error_details = task["error_details"]
            elif task["status"].startswith("错误"):
                error_details = task["status"]
            
            # Store the task index for retry button
            global current_task_index
            current_task_index = row_index
            
            # Return updates without changing the visible state of the accordion
            # This prevents flickering when selecting different tasks
            return {
                task_id_display: task["id"],
                task_title_display: task["book_title"],
                task_pages_display: f"{task['start_page']}-{task['end_page']}",
                task_status_display: task["status"],
                task_output_display: task["output_file"],
                task_original_text: task.get("original_text", ""),
                task_processed_text: task.get("processed_text", ""),
                task_logs: logs_text,
                task_error_details: error_details,
                task_details: gr.update(visible=True)  # Only update visibility, don't change open state
            }
        
        return {
            task_details: gr.update(visible=False)
        }
    
    def retry_current_task():
        """Retry the currently displayed task"""
        global current_task_index
        if current_task_index is not None and current_task_index < len(batch_tasks):
            task = batch_tasks[current_task_index]
            
            # Check if the task can be retried
            if task["status"].startswith("错误") or task["status"] == "不支持的操作":
                # Mark task for retry
                task["status"] = "等待重试"
                task["logs"].append(f"{get_timestamp()} 任务标记为重试")
                task["attempt_count"] += 1
                
                # Return updated task details and table
                logs_text = "\n".join(task.get("logs", []))
                return {
                    task_status_display: task["status"],
                    task_logs: logs_text,
                    batch_tasks_table: update_batch_tasks_table()
                }
        
        return {
            batch_tasks_table: update_batch_tasks_table()
        }
        
    def add_task_log(task, message):
        """Add a log entry to the task"""
        if "logs" not in task:
            task["logs"] = []
        
        log_entry = f"{get_timestamp()} {message}"
        task["logs"].append(log_entry)
        return log_entry

    def set_error_detail(task, error_message, error_details=None):
        """Set error status and detailed error information"""
        task["status"] = f"错误: {error_message}"
        
        # Store detailed error information if provided
        if error_details:
            task["error_details"] = error_details
        else:
            task["error_details"] = error_message
            
        add_task_log(task, f"错误: {error_message}")
        
    def process_batch_task(task, progress_callback=None):
        task["attempt_count"] += 1
        log_message = f"开始处理任务 (尝试 #{task['attempt_count']})"
        add_task_log(task, log_message)
        
        try:
            if not task["file"]:
                set_error_detail(task, "文件路径为空")
                if progress_callback:
                    progress_callback(f"任务 {task['id']} 错误: 文件路径为空")
                return False
                
            # Step 1: Extract text
            task["status"] = "提取文本中"
            status_msg = f"提取文本中 (从 {task['file']})"
            add_task_log(task, status_msg)
            if progress_callback:
                progress_callback(f"正在处理任务 {task['id']}: {status_msg}")
            
            # Handle different file types for text extraction
            extracted_text = ""
            
            file_path = task["file"]
            # Check if the file exists
            if not os.path.exists(file_path):
                set_error_detail(task, f"文件不存在 {file_path}", f"系统无法找到指定的文件路径: {file_path}\n请检查文件是否存在，或者路径是否有误。")
                if progress_callback:
                    progress_callback(f"任务 {task['id']} 错误: 文件不存在 {file_path}")
                return False
                
            if file_path.endswith(".pdf"):
                # Use a local variable for book_toc to avoid conflicts with global
                local_book_toc = []
                try:
                    if task["pdf_img"]:
                        if task["pdf_img_vector"]:
                            add_task_log(task, "提取矢量图PDF页面")
                            local_book_toc = extract_img_vector_by_page(file_path)
                        else:
                            add_task_log(task, "提取图像PDF页面")
                            local_book_toc = extract_img_by_page(file_path)
                    else:
                        add_task_log(task, "提取文本PDF页面")
                        local_book_toc = extract_text_by_page(file_path)
                except Exception as e:
                    set_error_detail(task, f"PDF解析失败", f"解析PDF文件时出错: {str(e)}\n\n这可能是由于PDF文件格式问题或权限问题导致的。")
                    if progress_callback:
                        progress_callback(f"任务 {task['id']} 错误: PDF解析失败 - {str(e)}")
                    return False
                
                # Extract text from selected pages
                if task["pdf_img"]:
                    # For image PDFs, we would need to implement OCR here
                    # This is just a placeholder
                    set_error_detail(task, "图像PDF处理暂不支持批量处理", "当前版本不支持对图像型PDF进行批量OCR处理。\n请使用单篇处理功能，或使用文本型PDF。")
                    task["status"] = "不支持的操作"
                    if progress_callback:
                        progress_callback(f"任务 {task['id']}: 图像PDF处理暂不支持批量处理")
                    return False
                else:
                    results = []
                    pages_processed = 0
                    pages_failed = 0
                    failed_pages = []
                    
                    # Validate page range
                    if task["start_page"] >= len(local_book_toc) or task["end_page"] > len(local_book_toc):
                        set_error_detail(task, "页面范围超出PDF总页数", 
                                        f"指定的页面范围 ({task['start_page']}-{task['end_page']}) 超出了PDF文件的总页数 ({len(local_book_toc)})。\n请调整页面范围重试。")
                        if progress_callback:
                            progress_callback(f"任务 {task['id']} 错误: 页面范围超出PDF总页数 ({len(local_book_toc)})")
                        return False
                    
                    for i in range(task["start_page"], task["end_page"]):
                        try:
                            if i < len(local_book_toc):
                                text = local_book_toc[i]
                                if not text or text.strip() == "":
                                    add_task_log(task, f"警告: 页面 {i} 没有提取到文本内容")
                                    pages_failed += 1
                                    failed_pages.append(i)
                                    continue
                                    
                                text_lines = text.split("\n")
                                if len(text_lines) > 1:
                                    end_idx = len(text_lines) if task["line_num_tail"] == 0 else -task["line_num_tail"]
                                    text = "\n".join(text_lines[task["line_num_head"]:end_idx])
                                results.append(text)
                                pages_processed += 1
                                add_task_log(task, f"已提取页面 {i} (共 {task['end_page'] - task['start_page']} 页)")
                        except Exception as e:
                            add_task_log(task, f"警告: 处理页面 {i} 时出错: {str(e)}")
                            pages_failed += 1
                            failed_pages.append(i)
                            
                    if pages_processed == 0:
                        set_error_detail(task, "所有页面处理失败", 
                                        f"所有指定页面 ({task['start_page']}-{task['end_page']}) 处理失败，无法提取文本。\n请检查PDF文件格式和内容。")
                        if progress_callback:
                            progress_callback(f"任务 {task['id']} 错误: 所有页面处理失败")
                        return False
                    elif pages_failed > 0:
                        add_task_log(task, f"警告: {pages_failed} 页处理失败，失败页面: {', '.join(map(str, failed_pages))}")
                    
                    extracted_text = "\n\n\n".join(results)
            
            # If no text was extracted, report an error
            if not extracted_text:
                set_error_detail(task, "无法提取文本", "未能从指定文件中提取到任何文本内容。\n可能原因：\n- PDF文件不包含可提取文本\n- 指定的页面范围不正确\n- 文件格式问题")
                if progress_callback:
                    progress_callback(f"任务 {task['id']} 错误: 无法提取文本")
                return False
            
            # Store the extracted text
            task["original_text"] = extracted_text
            add_task_log(task, f"成功提取文本 ({len(extracted_text)} 字符)")
                
            # Step 2: LLM processing
            task["status"] = "处理文本中"
            add_task_log(task, "开始LLM处理文本")
            if progress_callback:
                progress_callback(f"正在处理任务 {task['id']}: 处理文本中")
                
            processed_text = ""
            chunk_count = 0
            success_chunks = 0
            failed_chunks = 0
            
            try:
                for sub_text in extracted_text.split("\n\n\n"):
                    if not sub_text.strip():
                        continue
                        
                    chunk_count += 1
                    add_task_log(task, f"处理文本块 {chunk_count} (长度: {len(sub_text)} 字符)")
                    
                    try:
                        result = llm_service.process_text(
                            system_prompt=task["system_prompt"],
                            user_content=sub_text,
                            temperature=0.7
                        )
                        
                        if result.get("success"):
                            processed_text += result["result"] + "\n\n"
                            add_task_log(task, f"文本块 {chunk_count} 处理成功")
                            success_chunks += 1
                        else:
                            error_msg = f"处理文本块 {chunk_count} 失败: {result.get('error', '未知错误')}"
                            add_task_log(task, error_msg)
                            failed_chunks += 1
                            if progress_callback:
                                progress_callback(f"任务 {task['id']}: {error_msg}")
                    except Exception as e:
                        error_msg = f"处理文本块 {chunk_count} 出现异常: {str(e)}"
                        add_task_log(task, error_msg)
                        failed_chunks += 1
                        if progress_callback:
                            progress_callback(f"任务 {task['id']}: {error_msg}")
                
                if success_chunks == 0:
                    set_error_detail(task, "所有文本块处理失败", 
                                    f"尝试处理的 {chunk_count} 个文本块全部失败。\n可能是LLM服务出现问题或文本内容格式不适合处理。")
                    return False
                elif failed_chunks > 0:
                    add_task_log(task, f"警告: {failed_chunks}/{chunk_count} 个文本块处理失败")
                
            except Exception as e:
                set_error_detail(task, "LLM处理过程失败", f"LLM处理文本时出现异常: {str(e)}\n\n这可能是由于网络问题、API限制或格式问题导致的。")
                if progress_callback:
                    progress_callback(f"任务 {task['id']} 错误: LLM处理过程失败 - {str(e)}")
                return False
            
            # Store the processed text
            task["processed_text"] = processed_text
            add_task_log(task, f"文本处理完成 ({len(processed_text)} 字符)")
            
            # Step 3: TTS generation
            task["status"] = "生成语音中"
            add_task_log(task, f"开始生成语音 (使用 {task['tts_provide']})")
            if progress_callback:
                progress_callback(f"正在处理任务 {task['id']}: 生成语音中")
            
            # Generate output filename - use book name as directory
            try:
                os.makedirs("/tmp/book2tts", exist_ok=True)
                
                # 从文件路径中提取PDF文件名（不含扩展名）
                pdf_filename = ""
                if task["file"].endswith(".pdf"):
                    pdf_filename = os.path.basename(task["file"]).split(".")[0].replace(" ", "_")
                else:
                    pdf_filename = "未知书籍"
                    
                # 确保书籍目录存在（使用PDF文件名）
                book_dir = f"/tmp/book2tts/{pdf_filename}"
                os.makedirs(book_dir, exist_ok=True)
                
                # 使用任务名称作为输出文件名
                output_file = f"{book_dir}/{task['book_title']}.mp3"
                
                # Generate TTS
                add_task_log(task, f"使用语音模型: {task['tts_mode']}")
                if task["tts_provide"] == "edge_tts":
                    edge_text_to_speech(processed_text, task["tts_mode"], output_file)
                elif task["tts_provide"] == "azure":
                    azure_long_text_to_speech(
                        key=task["azure_key"],
                        region=task["azure_region"],
                        text=processed_text,
                        output_file=output_file,
                        voice_name=task["tts_mode"],
                    )
                
                task["status"] = "已完成"
                task["output_file"] = output_file
                add_task_log(task, f"语音生成完成: {output_file}")
                if progress_callback:
                    progress_callback(f"任务 {task['id']} 已完成: {output_file}")
                
                return True
            except Exception as e:
                set_error_detail(task, "语音生成失败", f"生成语音文件时出错: {str(e)}\n\n可能原因:\n- TTS服务配置错误\n- API密钥或区域设置不正确\n- 网络连接问题\n- 文本格式不适合TTS处理")
                if progress_callback:
                    progress_callback(f"任务 {task['id']} 错误: 语音生成失败 - {str(e)}")
                return False
                
        except Exception as e:
            set_error_detail(task, str(e), f"处理任务时出现未捕获的异常: {str(e)}\n\n异常类型: {type(e).__name__}\n这可能是由于程序内部错误或不受支持的操作导致的。")
            if progress_callback:
                progress_callback(f"任务 {task['id']} 错误: {str(e)}")
            return False

    def start_batch_processing(progress):
        progress_text = "开始处理队列..."
        
        def update_progress(message):
            nonlocal progress_text
            progress_text = message
            return progress_text
        
        # Find tasks that are waiting or marked for retry
        waiting_tasks = [task for task in batch_tasks if task["status"] == "等待中" or task["status"] == "等待重试"]
        if not waiting_tasks:
            return update_batch_tasks_table(), None, "没有等待的任务"
        
        update_progress("开始处理队列...")
        
        # Process each task
        for task in waiting_tasks:
            process_batch_task(task, update_progress)
            yield update_batch_tasks_table(), None, progress_text
        
        # Collect completed tasks for the audio player
        completed_tasks = [task for task in batch_tasks if task["status"] == "已完成"]
        
        # 找到最近完成的任务，用于音频预览
        latest_completed_task = None
        if completed_tasks:
            latest_completed_task = completed_tasks[-1]  # 获取最新完成的任务
            if latest_completed_task["output_file"] and os.path.exists(latest_completed_task["output_file"]):
                audio_file = latest_completed_task["output_file"]
                update_progress(f"队列处理完成，最新生成的音频: {audio_file}")
                yield update_batch_tasks_table(), audio_file, f"队列处理完成，最新生成的音频: {audio_file}"
            else:
                update_progress("队列处理完成，但无法找到生成的音频文件")
                yield update_batch_tasks_table(), None, "队列处理完成，但无法找到生成的音频文件"
        else:
            update_progress("队列处理完成，但没有成功完成的任务")
            yield update_batch_tasks_table(), None, "队列处理完成，但没有成功完成的任务"
    
    def batch_parse_file(batch_file):
        if batch_file is None:
            return ""
        if isinstance(batch_file, str):
            if batch_file.endswith(".pdf"):
                return batch_file.split("/")[-1].split(".")[0].replace(" ", "_")
        elif isinstance(batch_file, dict) and "name" in batch_file:
            if batch_file["name"].endswith(".pdf"):
                return batch_file["name"].split(".")[0].replace(" ", "_")
        return ""

    # Connect batch UI functions
    batch_file.change(batch_parse_file, inputs=batch_file, outputs=batch_book_title)
    
    # Toggle TTS provider settings
    batch_tts_provide.change(
        toggle_tts_settings,
        inputs=[batch_tts_provide],
        outputs=[azure_settings, edge_settings]
    )
    
    add_batch_btn.click(
        add_batch_task,
        inputs=[
            batch_file,
            batch_book_title,
            batch_start_page,
            batch_end_page,
            batch_line_num_head,
            batch_line_num_tail,
            batch_system_prompt,
            batch_tts_provide,
            batch_azure_key,
            batch_azure_region,
            batch_tts_mode,
            batch_pdf_img,
            batch_pdf_img_vector
        ],
        outputs=[batch_tasks_table]
    )
    
    clear_batch_btn.click(clear_batch_tasks, outputs=[batch_tasks_table])
    
    start_batch_btn.click(
        start_batch_processing,
        inputs=[batch_progress],
        outputs=[batch_tasks_table, batch_results, batch_progress]
    )
    
    # Connect the task details view
    batch_tasks_table.select(
        view_task_details,
        outputs=[
            task_id_display, 
            task_title_display, 
            task_pages_display,
            task_status_display,
            task_output_display,
            task_original_text,
            task_processed_text,
            task_logs,
            task_error_details,
            task_details
        ]
    )
    
    # Connect retry button in task details
    retry_button.click(
        retry_current_task,
        inputs=None,
        outputs=[task_status_display, task_logs, batch_tasks_table]
    )
    
    # 将重试任务按钮连接到retry_current_task函数
    retry_task_btn.click(
        retry_current_task,
        inputs=None,
        outputs=[task_status_display, task_logs, batch_tasks_table]
    )

if __name__ == "__main__":
    book2tts.launch(
        inline=False,
        share=False,
    )
