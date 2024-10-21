import json
import os
from dify_client import CompletionClient


def llm_parse_text(text: str, api_key: str, files=None) -> str:
    completion_client = CompletionClient(api_key)
    # Create Completion Message using CompletionClient
    completion_response = completion_client.create_completion_message(
        inputs={"query": text},
        response_mode="blocking",
        user="book2tts",
        files=files)

    completion_response.raise_for_status()

    result = completion_response.json()
    return result.get('answer')


def llm_parse_text_streaming(text: str, api_key: str, files=None):
    completion_client = CompletionClient(api_key)
    # Create Completion Message using CompletionClient
    completion_response = completion_client.create_completion_message(
        inputs={"query": text},
        response_mode="streaming",
        user="book2tts",
        files=files)

    completion_response.raise_for_status()

    for line in completion_response.iter_lines(decode_unicode=True):
        line = line.split('data:', 1)[-1]
        if line.strip():
            try:
                data = json.loads(line.strip())
                answer = data.get('answer')
                if answer:
                    yield answer
            except json.JSONDecodeError as e:
                print(line)
                print(f"JSON decoding error: {e}")


def file_upload(api_key: str, files):
    completion_client = CompletionClient(api_key)
    completion_response = completion_client.file_upload(user="book2tts",
                                                        files=files)
    completion_response.raise_for_status()

    result = completion_response.json()
    return result.get('id')


def file_2_md(file):
    md = {'file': (os.path.basename(file), open(file, 'rb'), 'image/jpeg')}
    return md
