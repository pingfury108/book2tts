import json
from dify_client import CompletionClient


def llm_parse_text(text: str, api_key: str) -> str:
    completion_client = CompletionClient(api_key)
    # Create Completion Message using CompletionClient
    completion_response = completion_client.create_completion_message(
        inputs={"query": text}, response_mode="blocking", user="book2tts")

    completion_response.raise_for_status()

    result = completion_response.json()
    return result.get('answer')


def llm_parse_text_streaming(text: str, api_key: str):
    completion_client = CompletionClient(api_key)
    # Create Completion Message using CompletionClient
    completion_response = completion_client.create_completion_message(
        inputs={"query": text}, response_mode="streaming", user="book2tts")

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
