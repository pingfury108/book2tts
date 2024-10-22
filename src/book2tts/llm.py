import google.generativeai as genai
import os

genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))

prompt = """
#Role: 我是一个专门用于从PDF 图片中识别文本内容的专业 AI 角色

## Goals: 逐字识别图片中文字, 不输出其他信息

## Constrains:
- 只输出识别的文本
- 不输出其他内容
- 不识别页首，页尾内容
- 不识别页脚注释，以及页脚注释引用数字

## outputs:
- text
- no markdown

## Workflows:
- 识别文本
- 调整空格，换行，重新排版
- 去除页脚引用注释
"""


def ocr_gemini(file):
    img_file = genai.upload_file(path=file)
    file = genai.get_file(name=img_file.name)
    model = genai.GenerativeModel(model_name="gemini-1.5-flash-latest")

    # Prompt the model with text and the previously uploaded image.
    resp = model.generate_content([img_file, prompt])

    return resp.text
