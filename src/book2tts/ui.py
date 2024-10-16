import gradio as gr
import edge_tts
import asyncio
import tempfile
import shutil
import os
import re

from book2tts.ebook import get_content_with_href, open_ebook, ebook_toc
from book2tts.pdf import open_pdf_reader, pdf_pages, page_text

with gr.Blocks(title="Book 2 TTS") as book2tts:
    gr.Markdown("# Book 2 TTS")
    with gr.Row():
        file = gr.File(label="选择书")
        with gr.Column():
            book_title = gr.Textbox(label="书名")
            dir_tree = gr.Dropdown([], label="选择章节", multiselect=True)
            voices = asyncio.run(edge_tts.list_voices())
            voices = sorted(voices, key=lambda voice: voice["ShortName"])
            tts_mode = gr.Dropdown([v.get("ShortName") for v in voices],
                                   label="选择声音模型",
                                   value="zh-CN-YunxiNeural")
            pass
        with gr.Column():
            outfile = gr.Textbox(label="输出文件名称")
            btn1 = gr.Button("生成 TTS")
            btn_clean = gr.Button("清理临时文件")
            pass
        pass

    gr.Markdown("### 替换文本")
    with gr.Row():
        with gr.Column():
            text_old = gr.Textbox(label="旧文本")
            pass
        with gr.Column():
            text_new = gr.Textbox(label="新文本", )
            pass
        with gr.Column():
            replace_list = gr.List()
            pass
        pass

    with gr.Row():
        text_replace_add = gr.Button("添加")
        text_replace_clean = gr.Button("清空")
        pass

    gr.Markdown("### 编辑文本")
    with gr.Row():
        text_content = gr.TextArea(label="章节内容")
        pass

    gr.Markdown("### 音频播放")
    with gr.Row():
        audio = gr.Audio(label="输出音频", sources=[])
        pass

    book = None
    book_toc = []
    book_type = None
    default_replace_texts = []

    replace_texts = default_replace_texts

    def parse_toc(file):
        global book, book_toc, book_type
        if file.endswith(".pdf"):
            book_type = "pdf"
            book = open_pdf_reader(file)
            book_toc = pdf_pages(book)
            dropdown = gr.Dropdown(
                choices=[f'page-{p.page_number}' for p in book_toc],
                multiselect=True)
            return dropdown, file.split('/')[-1].split(".")[0]
        elif file.endswith(".epub"):
            book_type = "epub"
            book = open_ebook(file)
            book_toc = ebook_toc(book)
            dropdown = gr.Dropdown(choices=[t.get("title") for t in book_toc],
                                   multiselect=True)
            return dropdown, book.title
        pass

    def replace_text(text):
        new_text = text
        for old, new in replace_texts:
            new_text = re.sub(old, new, new_text)
            pass
        return new_text

    def parse_content(value, book_title):
        if book_type == "pdf":
            texts = [
                page_text(book_toc[i])
                for i in [int(s.split("-")[-1]) for s in value]
            ]
            texts = list(map(replace_text, texts))
            return "\n\n\n\n".join(texts), gen_out_file(book_title, value)

        hrefs = [t.get("href") for t in book_toc if t.get("title") in value]
        texts = [get_content_with_href(book, href) or "" for href in hrefs]
        texts = list(map(lambda v: v or "", texts))
        texts = list(map(lambda v: v.strip(), texts))
        texts = list(map(replace_text, texts))

        return "\n\n\n\n".join(texts), gen_out_file(book_title, value)

    def gen_out_file(book_title, dir_tree):
        os.makedirs("/tmp/book2tts", exist_ok=True)

        def outfile_prefix():
            if dir_tree and len(dir_tree) > 0:
                return f'-{dir_tree[0]}-'

            return ""

        tmpfile = tempfile.NamedTemporaryFile(
            suffix=".mp3",
            dir="/tmp/book2tts",
            prefix=f'{book_title}{outfile_prefix()}',
            delete=True)
        outfile = tmpfile.name
        return outfile

    def gen_tts(text_content, tts_mode, outfile):

        communicate = edge_tts.Communicate(text_content, tts_mode)
        asyncio.run(communicate.save(outfile))
        return outfile

    def clean_tmp_file():
        shutil.rmtree("/tmp/book2tts")
        return

    def add_replace_text(old, new):
        global replace_texts
        replace_texts = [*replace_texts, (old, new)]
        return replace_texts

    def clean_replace_text():
        global replace_texts, default_replace_texts
        replace_texts = default_replace_texts

        return replace_texts

    file.change(parse_toc, inputs=file, outputs=[dir_tree, book_title])
    dir_tree.change(parse_content,
                    inputs=[dir_tree, book_title],
                    outputs=[text_content, outfile])

    btn1.click(gen_tts,
               inputs=[text_content, tts_mode, outfile],
               outputs=[audio])
    btn_clean.click(clean_tmp_file)
    text_replace_add.click(add_replace_text,
                           inputs=[text_old, text_new],
                           outputs=[replace_list])
    text_replace_clean.click(clean_replace_text, outputs=replace_list)
    pass

if __name__ == "__main__":
    book2tts.launch(inline=False, share=False)
