import azure.cognitiveservices.speech as speechsdk
import os
import re
import time
import tempfile
import ffmpeg
from typing import Iterator


class LongTTS:

    def __init__(self, subscription_key: str, region: str, voice_name: str):
        """
        初始化语音合成器
        :param subscription_key: Azure 语音服务密钥
        :param region: 服务区域
        """
        self.speech_config = speechsdk.SpeechConfig(
            subscription=subscription_key, region=region)
        # 设置中文音色
        self.speech_config.speech_synthesis_voice_name = voice_name
        #self.speech_config.set_speech_synthesis_output_format(
        #    speechsdk.SpeechSynthesisOutputFormat.Raw16Khz16BitMonoPcm)

    def _text_to_segments(self,
                          text: str,
                          max_length: int = 1000) -> Iterator[str]:
        """
        将文本转换为段落迭代器
        :param text: 输入文本
        :param max_length: 每段最大长度
        :return: 文本段落迭代器
        """
        current_segment = []
        current_length = 0

        # 按句号、感叹号、问号分割
        sentences = re.split('\n\n', text)

        for i in range(0, len(sentences), 2):
            if i + 1 < len(sentences):
                sentence = sentences[i] + sentences[i + 1]
            else:
                sentence = sentences[i]

            sentence_length = len(sentence)

            if current_length + sentence_length > max_length and current_segment:
                yield ''.join(current_segment)
                current_segment = [sentence]
                current_length = sentence_length
            else:
                current_segment.append(sentence)
                current_length += sentence_length

        if current_segment:
            yield ''.join(current_segment)

    def _synthesize_to_file(self,
                            text: str,
                            output_file: str,
                            retry_count: int = 3) -> bool:
        """
        将文本合成为语音并直接写入文件
        :param text: 文本内容
        :param output_file: 输出文件路径
        :param retry_count: 重试次数
        :return: 是否成功
        """
        audio_config = speechsdk.audio.AudioOutputConfig(filename=output_file)
        synthesizer = speechsdk.SpeechSynthesizer(
            speech_config=self.speech_config, audio_config=audio_config)

        for attempt in range(retry_count):
            try:
                # 使用 speak_text_async 替代 speak_ssml_async
                result = synthesizer.speak_text_async(text).get()

                if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
                    return True

                elif result.reason == speechsdk.ResultReason.Canceled:
                    if attempt < retry_count - 1:
                        print(f"合成失败，正在重试 ({attempt + 1}/{retry_count})")
                        print(f"错误详情: {result}")
                        time.sleep(1)
                        continue
                    return False

            except Exception as e:
                if attempt < retry_count - 1:
                    print(f"错误: {str(e)}, 正在重试 ({attempt + 1}/{retry_count})")
                    time.sleep(1)
                    continue
                return False

        return False

    def _merge_wav_files(self, input_files: list[str], output_file: str):
        """
        合并多个WAV文件
        :param input_files: 输入文件列表
        :param output_file: 输出文件路径
        """

        _, tmp_file = tempfile.mkstemp()
        with open(tmp_file, 'w') as f:
            f.write("\n".join(
                [f"file '{audio_file}'" for audio_file in input_files]))
        ffmpeg.input(tmp_file,
                     format='concat', safe=0).output(output_file,
                                                     format='wav',
                                                     acodec='copy').run()
        os.remove(tmp_file)
        return

    def synthesize_long_text(self,
                             text: str,
                             output_file: str,
                             segment_length: int = 2000) -> bool:
        """
        合成长文本
        :param text: 输入文本
        :param output_file: 输出文件路径
        :param segment_length: 段落长度
        :return: 是否成功
        """
        temp_files = []
        try:
            # 创建临时文件夹
            temp_dir = tempfile.mkdtemp()
            print(f'tmp_dir: {temp_dir}')
            total_segments = sum(
                1 for _ in self._text_to_segments(text, segment_length))

            # 处理每个文本段落
            for i, segment in enumerate(
                    self._text_to_segments(text, segment_length), 1):
                # 创建临时文件
                temp_file = os.path.join(temp_dir, f'segment_{i}.wav')
                temp_files.append(temp_file)

                print(f"正在处理第 {i}/{total_segments} 个段落...")
                if not self._synthesize_to_file(segment, temp_file):
                    raise Exception(f"段落 {i} 合成失败")

            if temp_files:
                # 合并所有临时文件
                print("正在合并音频文件...")
                self._merge_wav_files(temp_files, output_file)
                print(f"合成完成，文件已保存至: {output_file}")
                return True
            else:
                raise Exception("没有生成任何临时文件")

        except Exception as e:
            print(f"合成过程中发生错误: {str(e)}")
            return False

        finally:
            print(temp_dir)
            """
            # 清理临时文件
            for temp_file in temp_files:
                try:
                    if os.path.exists(temp_file):
                        os.remove(temp_file)
                except Exception as e:
                    print(f"清理临时文件时发生错误: {str(e)}")

            # 清理临时目录
            try:
                if 'temp_dir' in locals() and os.path.exists(temp_dir):
                    os.rmdir(temp_dir)
            except Exception as e:
                print(f"清理临时目录时发生错误: {str(e)}")

                """
