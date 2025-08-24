import edge_tts
import asyncio
import os
import re
import time
import tempfile
import ffmpeg
from typing import Iterator, Optional, Dict, Any


class EdgeTTS:
    def __init__(self, voice_name: str):
        self.voice_name = voice_name
        return
    
    async def synthesize_with_subtitles_v2(
        self, 
        text: str, 
        output_file: str, 
        subtitle_file: str = None, 
        retry_count: int = 3,
        words_in_cue: int = 10
    ) -> Dict[str, Any]:
        """
        改进的字幕生成方法 - 更可靠的实现
        
        Args:
            text: 文本内容
            output_file: 输出音频文件路径
            subtitle_file: 输出字幕文件路径（可选）
            retry_count: 重试次数
            words_in_cue: 每个字幕条目的单词数
            
        Returns:
            包含生成结果信息的字典
        """
        for attempt in range(retry_count):
            try:
                communicate = edge_tts.Communicate(text, self.voice_name)
                
                # 方法1：使用 stream() 获取更精确的字幕数据
                audio_data = b""
                subtitle_data = []
                
                async for chunk in communicate.stream():
                    if chunk["type"] == "audio":
                        audio_data += chunk["data"]
                    elif chunk["type"] == "WordBoundary":
                        # 收集词级时间戳信息
                        subtitle_data.append({
                            "offset": chunk["offset"],
                            "duration": chunk["duration"], 
                            "text": chunk["text"]
                        })
                
                # 保存音频文件
                with open(output_file, "wb") as f:
                    f.write(audio_data)
                
                # 生成VTT字幕
                if subtitle_file and subtitle_data:
                    vtt_content = self._generate_vtt_from_word_boundaries(
                        subtitle_data, text, words_in_cue
                    )
                    with open(subtitle_file, "w", encoding="utf-8") as f:
                        f.write(vtt_content)
                
                # 验证生成结果
                audio_exists = os.path.exists(output_file) and os.path.getsize(output_file) > 0
                subtitle_exists = (not subtitle_file or 
                                (os.path.exists(subtitle_file) and os.path.getsize(subtitle_file) > 0))
                
                return {
                    "success": audio_exists and subtitle_exists,
                    "audio_generated": audio_exists,
                    "subtitle_generated": subtitle_exists,
                    "subtitle_entries": len(subtitle_data) if subtitle_data else 0,
                    "method": "stream_based"
                }
                
            except Exception as e:
                print(f"Stream method attempt {attempt + 1} failed: {str(e)}")
                if attempt < retry_count - 1:
                    await asyncio.sleep(1)  # 异步等待
                    continue
                
                # 如果stream方法失败，回退到传统方法
                return await self._fallback_subtitle_generation(
                    text, output_file, subtitle_file
                )
        
        return await self._fallback_subtitle_generation(text, output_file, subtitle_file)
    
    def _generate_vtt_from_word_boundaries(
        self, 
        word_boundaries: list, 
        original_text: str, 
        words_per_cue: int = 10
    ) -> str:
        """从词边界数据生成VTT字幕"""
        if not word_boundaries:
            return ""
        
        vtt_lines = ["WEBVTT", ""]
        
        # 按组处理单词（每组words_per_cue个单词）
        for i in range(0, len(word_boundaries), words_per_cue):
            group = word_boundaries[i:i + words_per_cue]
            
            # 计算时间戳（毫秒转换为秒）
            start_time = group[0]["offset"] / 10_000_000  # 100ns ticks to seconds
            end_time = (group[-1]["offset"] + group[-1]["duration"]) / 10_000_000
            
            # 格式化时间戳
            start_timestamp = self._format_vtt_timestamp(start_time)
            end_timestamp = self._format_vtt_timestamp(end_time)
            
            # 提取文本内容并清理多余空格
            text_content = " ".join([word["text"] for word in group])
            # 清理多余空格和标点符号前的空格
            text_content = self._clean_subtitle_text(text_content)
            
            vtt_lines.extend([
                f"{start_timestamp} --> {end_timestamp}",
                text_content,
                ""
            ])
        
        return "\n".join(vtt_lines)
    
    def _format_vtt_timestamp(self, seconds: float) -> str:
        """格式化VTT时间戳"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d}.{millis:03d}"
    
    def _clean_subtitle_text(self, text: str) -> str:
        """清理字幕文本中的多余空格"""
        import re
        
        # 去除多余的空格
        text = re.sub(r'\s+', ' ', text)
        
        # 去除标点符号前的空格
        text = re.sub(r'\s+([，。！？；：、）】』」}])', r'\1', text)
        
        # 去除标点符号后多余的空格，保留一个空格
        text = re.sub(r'([，。！？；：、（【『「{])\s+', r'\1', text)
        
        # 去除开头和结尾的空格
        return text.strip()
    
    async def _fallback_subtitle_generation(
        self, 
        text: str, 
        output_file: str, 
        subtitle_file: str = None
    ) -> Dict[str, Any]:
        """回退方案：使用传统的save方法"""
        try:
            communicate = edge_tts.Communicate(text, self.voice_name)
            if subtitle_file:
                await communicate.save(output_file, subtitle_file)
            else:
                await communicate.save(output_file)
            
            audio_exists = os.path.exists(output_file) and os.path.getsize(output_file) > 0
            subtitle_exists = (not subtitle_file or 
                            (os.path.exists(subtitle_file) and os.path.getsize(subtitle_file) > 0))
            
            return {
                "success": audio_exists and subtitle_exists,
                "audio_generated": audio_exists, 
                "subtitle_generated": subtitle_exists,
                "method": "fallback_save"
            }
            
        except Exception as e:
            return {
                "success": False,
                "audio_generated": False,
                "subtitle_generated": False,
                "error": str(e),
                "method": "fallback_failed"
            }

    async def synthesize_with_subtitles(self, text: str, output_file: str, subtitle_file: str = None, retry_count: int = 3) -> bool:
        """
        将文本合成为语音并生成字幕
        :param text: 文本内容
        :param output_file: 输出音频文件路径
        :param subtitle_file: 输出字幕文件路径（可选）
        :param retry_count: 重试次数
        :return: 是否成功
        """
        for attempt in range(retry_count):
            try:
                communicate = edge_tts.Communicate(text, self.voice_name)
                if subtitle_file:
                    await communicate.save(output_file, subtitle_file)
                else:
                    await communicate.save(output_file)
                return True
            except Exception as e:
                if attempt < retry_count - 1:
                    print(f"错误: {str(e)}, 正在重试 ({attempt + 1}/{retry_count})")
                    time.sleep(1)
                    continue
                return False

        return False

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

    def _merge_audio_files(self, input_files: list[str], output_file: str):
        """
        合并多个音频文件
        :param input_files: 输入文件列表
        :param output_file: 输出文件路径
        """

        _, tmp_file = tempfile.mkstemp()
        with open(tmp_file, "w") as f:
            f.write("\n".join([f"file '{audio_file}'" for audio_file in input_files]))

        ffmpeg.input(tmp_file, format="concat", safe=0).output(
            output_file, format="mp3", acodec="copy"
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
                temp_file = os.path.join(temp_dir, f"segment_{i}.mp3")
                temp_files.append(temp_file)

                print(f"正在处理第 {i}/{total_segments} 个段落...")
                if not self._synthesize_to_file(segment, temp_file):
                    raise Exception(f"段落 {i} 合成失败")

            if temp_files:
                # 合并所有临时文件
                print("正在合并音频文件...")
                self._merge_audio_files(temp_files, output_file)
                print(f"合成完成，文件已保存至: {output_file}")
                return True
            else:
                raise Exception("没有生成任何临时文件")

        except Exception as e:
            print(f"合成过程中发生错误: {str(e)}")
            return False

        finally:
            print(temp_dir)
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
