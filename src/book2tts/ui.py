import gradio as gr
import edge_tts
import asyncio
import tempfile
import shutil
import os

from book2tts.ebook import get_content_with_href, open_ebook, ebook_toc
from book2tts.pdf import extract_text_by_page
from book2tts.dify import llm_parse_text, llm_parse_text_streaming

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
            dify_api_key = gr.Textbox(label="dify api token")
            btn_llm = gr.Button("AI处理")
            btn1 = gr.Button("生成 TTS")
            btn_clean = gr.Button("清理临时文件")
            pass
        pass
    with gr.Row():
        outfile = gr.Textbox(label="输出文件名称")
        pass

    gr.Markdown("### 编辑文本")
    with gr.Row():
        with gr.Column():
            text_content = gr.TextArea(label="章节内容")
            pass
        with gr.Column():
            tts_content = gr.TextArea(label="语言文本")
            pass
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
            #book = open_pdf_reader(file)
            book_toc = extract_text_by_page(file)
            dropdown = gr.Dropdown(
                choices=[f'page-{i}' for i, _ in enumerate(book_toc)],
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

    def parse_content(value, book_title):
        if book_type == "pdf":
            texts = [
                book_toc[i] for i in [int(s.split("-")[-1]) for s in value]
            ]
            return "\n\n\n\n".join(texts), gen_out_file(book_title, value)

        hrefs = [t.get("href") for t in book_toc if t.get("title") in value]
        texts = [get_content_with_href(book, href) or "" for href in hrefs]
        texts = list(map(lambda v: v or "", texts))
        texts = list(map(lambda v: v.strip(), texts))

        return "\n\n\n".join(texts), gen_out_file(book_title, value)

    def outfile_prefix(dir_tree):
        if dir_tree and len(dir_tree) > 0:
            return f'-{dir_tree[0]}-'

        return ""

    def gen_out_file(book_title, dir_tree):
        os.makedirs("/tmp/book2tts", exist_ok=True)
        tmpfile = tempfile.NamedTemporaryFile(
            suffix=".mp3",
            dir="/tmp/book2tts",
            prefix=f'{book_title}{outfile_prefix(dir_tree)}',
            delete=True)
        outfile = tmpfile.name
        return outfile

    def gen_tts(text_content, tts_content, tts_mode, outfile):
        content = text_content
        if tts_content.strip() != "":
            content = tts_content
            pass

        communicate = edge_tts.Communicate(content, tts_mode)
        asyncio.run(communicate.save(outfile))
        return outfile

    def clean_tmp_file():
        shutil.rmtree("/tmp/book2tts")
        return

    def llm_gen(text, api_key):
        results = []
        for part in llm_parse_text_streaming(text, api_key):
            results.append(part)
            yield "".join(results)  #每次yield累加后的结果
        pass

    file.change(parse_toc, inputs=file, outputs=[dir_tree, book_title])
    dir_tree.change(parse_content,
                    inputs=[dir_tree, book_title],
                    outputs=[text_content, outfile])

    btn1.click(gen_tts,
               inputs=[text_content, tts_content, tts_mode, outfile],
               outputs=[audio])
    btn_clean.click(clean_tmp_file)
    btn_llm.click(llm_gen,
                  inputs=[text_content, dify_api_key],
                  outputs=tts_content)
    pass

if __name__ == "__main__":
    book2tts.launch(
        inline=False,
        share=False,
    )
