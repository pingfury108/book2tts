import edge_tts
import asyncio
import os
import re
import time
import tempfile
import ffmpeg
from typing import Iterator


class EdgeTTS:
    def __init__(self, voice_name: str):
        self.voice_name = voice_name
        return

    def _text_to_segments(self, text: str, max_length: int = 1000) -> Iterator[str]:
        """
        将文本转换为段落迭代器
        :param text: 输入文本
        :param max_length: 每段最大长度
        :return: 文本段落迭代器
        """
        current_segment = []
        current_length = 0

        # 按句号、感叹号、问号分割
        sentences = re.split("\n", text)

        for i in range(0, len(sentences), 2):
            if i + 1 < len(sentences):
                sentence = sentences[i] + sentences[i + 1]
            else:
                sentence = sentences[i]

            sentence_length = len(sentence)

            if current_length + sentence_length > max_length and current_segment:
                yield "".join(current_segment)
                current_segment = [sentence]
                current_length = sentence_length
            else:
                current_segment.append(sentence)
                current_length += sentence_length

        if current_segment:
            yield "".join(current_segment)

    def _synthesize_to_file(
        self, text: str, output_file: str, retry_count: int = 3
    ) -> bool:
        """
        将文本合成为语音并直接写入文件
        :param text: 文本内容
        :param output_file: 输出文件路径
        :param retry_count: 重试次数
        :return: 是否成功
        """

        for attempt in range(retry_count):
            try:
                communicate = edge_tts.Communicate(text, self.voice_name)
                asyncio.run(communicate.save(output_file))
                return True
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
        with open(tmp_file, "w") as f:
            f.write("\n".join([f"file '{audio_file}'" for audio_file in input_files]))

        ffmpeg.input(tmp_file, format="concat", safe=0).output(
            output_file, format="wav", acodec="copy"
        ).run(overwrite_output=True)  # Add overwrite_output=True to force overwrite
        os.remove(tmp_file)
        return

    def synthesize_long_text(
        self, text: str, output_file: str, segment_length: int = 2000
    ) -> bool:
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
            print(f"tmp_dir: {temp_dir}")
            total_segments = sum(
                1 for _ in self._text_to_segments(text, segment_length)
            )

            # 处理每个文本段落
            for i, segment in enumerate(
                self._text_to_segments(text, segment_length), 1
            ):
                # 创建临时文件
                temp_file = os.path.join(temp_dir, f"segment_{i}.wav")
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
