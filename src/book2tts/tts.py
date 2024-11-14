import edge_tts
import asyncio
import azure.cognitiveservices.speech as speechsdk

from book2tts.long_tts import LongTTS
from book2tts.edge_tts import EdgeTTS


def azure_text_to_speech(
    key, region, text, output_file, voice_name="zh-CN-YunxiNeural"
):
    # 创建语音配置对象
    speech_config = speechsdk.SpeechConfig(subscription=key, region=region)

    # 设置语音合成的语音名称（语言模型）
    speech_config.speech_synthesis_voice_name = voice_name

    # 创建音频输出配置，设置为文件输出
    audio_config = speechsdk.audio.AudioOutputConfig(filename=output_file)

    # 创建语音合成器对象
    synthesizer = speechsdk.SpeechSynthesizer(
        speech_config=speech_config, audio_config=audio_config
    )

    # 合成文本并保存到文件
    result = synthesizer.speak_text_async(text).get()

    if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
        return result
    else:
        return result


def azure_long_text_to_speech(
    key, region, text, output_file, voice_name="zh-CN-YunxiNeural"
):
    tts = LongTTS(key, region, voice_name)
    ok = tts.synthesize_long_text(text=text, output_file=output_file)

    return ok


def edge_text_to_speech(content, tts_mode, output_file):
    tts = EdgeTTS(voice_name=tts_mode)
    tts.synthesize_long_text(text=content, output_file=output_file)
    return


def edge_tts_volices():
    voices = asyncio.run(edge_tts.list_voices())
    voices = sorted(voices, key=lambda voice: voice["ShortName"])

    return [v.get("ShortName") for v in voices]
