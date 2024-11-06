import gradio as gr
import tempfile
import shutil
import os
import time

from dotenv import load_dotenv

from book2tts.ebook import get_content_with_href, open_ebook, ebook_toc
from book2tts.pdf import (extract_text_by_page, extract_img_by_page, save_img,
                          extract_img_vector_by_page)
from book2tts.dify import (llm_parse_text, llm_parse_text_streaming,
                           file_upload, file_2_md, BASE_API,
                           llm_parse_text_workflow)
from book2tts.tts import (azure_text_to_speech, edge_tts_volices,
                          edge_text_to_speech, azure_long_text_to_speech)
#from book2tts.llm import ocr_gemini
from book2tts.ocr import ocr_volc

load_dotenv()

with gr.Blocks(title="Book 2 TTS") as book2tts:
    gr.Markdown("# Book 2 TTS")
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
            dify_base_api = gr.Textbox(label="Dify BASE API", value=BASE_API)
            dify_api_key = gr.Textbox(label="Dify API Token",
                                      value=os.getenv("DIFY_APP_TOKEN", ))
            with gr.Row():
                line_num_head = gr.Slider(label="掐头行数", )
                line_num_tail = gr.Slider(label="去尾行数", )
                pass
            btn_clean = gr.Button("清理")
            pass

    with gr.Row():
        volc_ak = gr.Textbox(label="火山云AK", value=os.getenv("VOLC_AK", ))
        volc_sk = gr.Textbox(label="火山云SK", value=os.getenv("VOLC_SK", ))
        btn_ocr = gr.Button("识别PDF图片(LLM)")
        btn_ocr_volc = gr.Button("识别PDF图片(OCR)")

        pass
    with gr.Row():
        btn_llm = gr.Button("处理语言文本")
        pass

    with gr.Row():
        tts_provide = gr.Dropdown(["edge_tts", "azure"],
                                  label="提供商",
                                  value="azure")
        azure_key = gr.Textbox(label="azure api key",
                               value=os.getenv("AZURE_KEY", ))
        azure_region = gr.Textbox(label="azure api region",
                                  value=os.getenv("AZURE_REGION", ))

        tts_mode = gr.Dropdown(edge_tts_volices(),
                               label="选择声音模型",
                               value="zh-CN-YunxiNeural")
        btn1 = gr.Button("生成语音")

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
            tts_content = gr.TextArea(label="语音文本")
            pass
        pass

    gr.Markdown("### 音频播放")
    with gr.Row():
        audio = gr.Audio(label="输出音频", sources=[])
        pass

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
            #book = open_pdf_reader(file)
            if book_type_pdf_img:
                if book_type_pdf_img_vector:
                    book_toc = extract_img_vector_by_page(file)
                else:
                    book_toc = extract_img_by_page(file)
            else:
                book_toc = extract_text_by_page(file)
                pass
            dropdown = gr.Dropdown(
                choices=[f'page-{i}' for i, _ in enumerate(book_toc)],
                multiselect=True)
            return dropdown, file.split('/')[-1].split(".")[0].replace(
                " ", "_")
        elif file.endswith(".epub"):
            book_type = "epub"
            book = open_ebook(file)
            book_toc = ebook_toc(book)
            dropdown = gr.Dropdown(choices=[t.get("title") for t in book_toc],
                                   multiselect=True)
            return dropdown, book.title
        pass

    def ocr_content_llm(value, api_key, base_api, start_page: int,
                        end_page: int):
        if start_page > 0 and end_page > start_page:
            value = [f'page-{i}' for i in range(start_page, end_page)]
            pass
        if book_type == "pdf":
            if book_type_pdf_img:
                results = []
                for i in [int(s.split("-")[-1]) for s in value]:
                    text = llm_parse_text(
                        text="",
                        api_key=api_key,
                        files=[{
                            "type":
                            "image",
                            "transfer_method":
                            "local_file",
                            "upload_file_id":
                            file_upload(api_key,
                                        files=file_2_md(save_img(book_toc[i])))
                        }],
                        base_api=base_api)
                    """
                    text = ocr_gemini(save_img(book_toc[i]))
                    """
                    results.append(text)
                    yield "\n\n\n".join(results)
                    pass
            pass
        return ""

    def ocr_content_volc(value, ak, sk, start_page: int, end_page: int):
        if start_page > 0 and end_page > start_page:
            value = [f'page-{i}' for i in range(start_page, end_page)]
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

    def parse_content_range(value, start_page: int, end_page: int):
        if start_page > 0 and end_page > start_page:
            value = [f'page-{i}' for i in range(start_page, end_page)]
            pass
        if book_type == "pdf":
            if not book_type_pdf_img:
                results = []
                for i in [int(s.split("-")[-1]) for s in value]:
                    text = book_toc[i]
                    results.append(text)
                    yield "\n\n\n".join(results)
                    pass
            pass
        return ""

    def parse_content(value, book_title):
        if value is None or book_title is None:
            return None, None
        if book_type == "pdf":
            if book_type_pdf_img:
                return "", gen_out_file(book_title, value)
            else:
                texts = [
                    str(book_toc[i])
                    for i in [int(s.split("-")[-1]) for s in value]
                ]
                return "\n\n\n".join(texts), gen_out_file(book_title, value)

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

    def gen_tts(text_content, tts_content, tts_provide, tts_mode, outfile,
                azure_key, azure_region):
        content = text_content
        if tts_content.strip() != "":
            content = tts_content
            pass

        if tts_provide == "edge_text":
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
            line_num_tail = -line_num_tail
            pass
        return "\n".join(lines[line_num_head:line_num_tail])

    def llm_gen(text, api_key, base_api, line_num_head, line_num_tail):
        results = []
        for sub_text in text.split("\n\n\n"):
            """
            for part in llm_parse_text_streaming(exclude_text(
                    sub_text, line_num_head, line_num_tail),
                                                 api_key,
                                                 base_api=base_api):
                results.append(part)
                yield "".join(results)  #每次yield累加后的结果
            """
            result = llm_parse_text_workflow(exclude_text(
                sub_text, line_num_head, line_num_tail),
                                             api_key,
                                             base_api=base_api)
            if result is not None:
                results.append(result)
            else:
                print(f"llm gen result: {result}")
                pass
            yield "".join(results)
        pass

    def is_pdf_img(img, vector):
        global book_type_pdf_img, book_type_pdf_img_vector
        book_type_pdf_img = img
        book_type_pdf_img_vector = vector
        print(book_type_pdf_img, book_type_pdf_img_vector)
        return img, vector

    file.change(parse_toc, inputs=file, outputs=[dir_tree, book_title])
    dir_tree.change(parse_content,
                    inputs=[dir_tree, book_title],
                    outputs=[text_content, outfile])

    btn1.click(gen_tts,
               inputs=[
                   text_content, tts_content, tts_provide, tts_mode, outfile,
                   azure_key, azure_region
               ],
               outputs=[audio])
    btn_clean.click(clean_tmp_file)
    btn_llm.click(llm_gen,
                  inputs=[
                      text_content, dify_api_key, dify_base_api, line_num_head,
                      line_num_tail
                  ],
                  outputs=tts_content)
    pdf_img.change(is_pdf_img, inputs=[pdf_img, pdf_img_vector])
    pdf_img_vector.change(is_pdf_img, inputs=[pdf_img, pdf_img_vector])
    btn_ocr.click(
        ocr_content_llm,
        inputs=[dir_tree, dify_api_key, dify_base_api, start_page, end_page],
        outputs=[text_content])
    btn_ocr_volc.click(
        ocr_content_volc,
        inputs=[dir_tree, volc_ak, volc_sk, start_page, end_page],
        outputs=[text_content])

    btn_get_text.click(parse_content_range,
                       inputs=[dir_tree, start_page, end_page],
                       outputs=[text_content])
    pass

if __name__ == "__main__":
    book2tts.launch(
        inline=False,
        share=False,
    )
