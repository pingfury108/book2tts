import gradio as gr
import edge_tts
import asyncio
import tempfile

from book2tts.ebook import get_content_with_href, open_ebook, ebook_toc

with gr.Blocks(title="Book 2 TTS") as book2tts:
    gr.Markdown("# Book 2 TTS")
    with gr.Row():
        file = gr.File(label="选择书")
        dir_tree = gr.Dropdown([], label="选择章节", multiselect=True)
        pass

    with gr.Row():
        text_content = gr.Textbox(label="内容")
        pass

    with gr.Row():
        voices = asyncio.run(edge_tts.list_voices())
        voices = sorted(voices, key=lambda voice: voice["ShortName"])
        tts_mode = gr.Dropdown([v.get("ShortName") for v in voices],
                               label="选择声音模型",
                               value="zh-CN-YunxiNeural")
        btn1 = gr.Button("生成 TTS")
        pass
    with gr.Row():
        audio = gr.Audio(label="音频", sources=[])
        pass

    book = None
    book_toc = []

    def parse_toc(file):
        global book, book_toc
        book = open_ebook(file)
        book_toc = ebook_toc(book)
        dropdown = gr.Dropdown(choices=[t.get("title") for t in book_toc],
                               multiselect=True)
        return dropdown

    def parse_content(value):
        hrefs = [t.get("href") for t in book_toc if t.get("title") in value]
        texts = [get_content_with_href(book, href) or "" for href in hrefs]
        texts = list(map(lambda v: v or "", texts))
        texts = list(map(lambda v: v.strip(), texts))
        return "\n\n".join(texts)

    def gen_tts(text_content, tts_mode):
        tmpfile = tempfile.NamedTemporaryFile(suffix=".mp3",
                                              dir="/tmp/book2tts",
                                              delete=False)
        outfile = tmpfile.name
        communicate = edge_tts.Communicate(text_content, tts_mode)
        asyncio.run(communicate.save(outfile))
        return outfile

    file.change(parse_toc, inputs=file, outputs=dir_tree)
    dir_tree.change(parse_content, inputs=dir_tree, outputs=[text_content])

    btn1.click(gen_tts, inputs=[text_content, tts_mode], outputs=audio)
    pass

if __name__ == "__main__":
    book2tts.launch(inline=False, share=False)