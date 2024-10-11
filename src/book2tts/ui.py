import gradio as gr
import edge_tts
import asyncio
import tempfile
import shutil
import os

from book2tts.ebook import get_content_with_href, open_ebook, ebook_toc

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

    with gr.Row():
        text_content = gr.TextArea(label="章节内容")
        pass

    with gr.Row():
        audio = gr.Audio(label="输出音频", sources=[])
        pass

    book = None
    book_toc = []

    def parse_toc(file):
        global book, book_toc
        book = open_ebook(file)
        book_toc = ebook_toc(book)
        dropdown = gr.Dropdown(choices=[t.get("title") for t in book_toc],
                               multiselect=True)
        return dropdown, book.title

    def parse_content(value):
        hrefs = [t.get("href") for t in book_toc if t.get("title") in value]
        texts = [get_content_with_href(book, href) or "" for href in hrefs]
        texts = list(map(lambda v: v or "", texts))
        texts = list(map(lambda v: v.strip(), texts))
        return "\n\n\n\n".join(texts)

    def gen_tts(text_content, tts_mode, book_title, dir_tree):
        os.makedirs("/tmp/book2tts", exist_ok=True)

        def outfile_prefix():
            if dir_tree and len(dir_tree) > 0:
                return f'-{dir_tree[0]}-'

            return ""

        tmpfile = tempfile.NamedTemporaryFile(
            suffix=".mp3",
            dir="/tmp/book2tts",
            prefix=f'{book_title}{outfile_prefix()}',
            delete=False)
        outfile = tmpfile.name
        print(outfile)
        communicate = edge_tts.Communicate(text_content, tts_mode)
        asyncio.run(communicate.save(outfile))
        return outfile, outfile

    def clean_tmp_file():
        shutil.rmtree("/tmp/book2tts")
        return

    file.change(parse_toc, inputs=file, outputs=[dir_tree, book_title])
    dir_tree.change(parse_content, inputs=dir_tree, outputs=[text_content])

    btn1.click(gen_tts,
               inputs=[text_content, tts_mode, book_title, dir_tree],
               outputs=[audio, outfile])
    btn_clean.click(clean_tmp_file)
    pass

if __name__ == "__main__":
    book2tts.launch(inline=False, share=False)
