import os
import tempfile
import ffmpeg
from typing import Dict, List, Any, Optional
from pathlib import Path
import asyncio
import edge_tts
from .tts import edge_text_to_speech
from .long_tts import LongTTS
from .edgetts import EdgeTTS
from .audio_utils import get_audio_duration

class MultiVoiceTTS:
    """多角色语音合成服务，支持为不同角色分配不同的音色"""
    
    def __init__(self):
        """初始化多角色TTS服务"""
        self.temp_dir = None
    
    def synthesize_dialogue(
        self, 
        dialogue_data: Dict[str, Any], 
        voice_mapping: Dict[str, Dict[str, str]],
        output_file: str
    ) -> Dict[str, Any]:
        """
        合成对话音频
        
        Args:
            dialogue_data: 对话数据（包含segments）
            voice_mapping: 角色到音色的映射 {speaker: {provider: "edge_tts", voice_name: "zh-CN-XiaoxiaoNeural"}}
            output_file: 输出文件路径
            
        Returns:
            合成结果字典
        """
        try:
            # 创建临时目录
            self.temp_dir = tempfile.mkdtemp(prefix="dialogue_tts_")
            temp_files = []
            
            segments = dialogue_data.get("segments", [])
            if not segments:
                return {"success": False, "error": "没有找到对话片段"}
            
            # 为每个片段生成音频
            for i, segment in enumerate(segments):
                speaker = segment.get("speaker", "未知")
                utterance = segment.get("utterance", "")
                
                if not utterance.strip():
                    continue
                
                # 获取该说话者的音色配置
                voice_config = voice_mapping.get(speaker)
                if not voice_config:
                    return {
                        "success": False, 
                        "error": f"未找到说话者 '{speaker}' 的音色配置"
                    }
                
                # 生成片段音频文件
                segment_file = os.path.join(self.temp_dir, f"segment_{i+1:03d}.wav")
                
                synthesis_result = self._synthesize_segment(
                    utterance, 
                    voice_config, 
                    segment_file
                )
                
                if not synthesis_result["success"]:
                    return {
                        "success": False,
                        "error": f"片段 {i+1} ({speaker}) 合成失败: {synthesis_result['error']}"
                    }
                
                temp_files.append(segment_file)
            
            if not temp_files:
                return {"success": False, "error": "没有生成任何音频片段"}
            
            # 合并所有音频片段
            merge_result = self._merge_audio_files(temp_files, output_file)
            if not merge_result["success"]:
                return merge_result
            
            return {
                "success": True,
                "output_file": output_file,
                "segments_count": len(temp_files),
                "speakers": list(voice_mapping.keys())
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"对话音频合成过程中发生错误: {str(e)}"
            }
        finally:
            # 清理临时文件
            self._cleanup_temp_files()
    
    async def generate_segment_with_subtitles_v2(self, text: str, voice_name: str):
        """改进的单个文本片段音频和字幕生成方法"""
        # 创建临时文件
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as audio_file:
            audio_path = audio_file.name
        
        with tempfile.NamedTemporaryFile(suffix=".vtt", delete=False) as subtitle_file:
            subtitle_path = subtitle_file.name
        
        try:
            # 使用改进的EdgeTTS方法
            edge_tts_instance = EdgeTTS(voice_name)
            result = await edge_tts_instance.synthesize_with_subtitles_v2(
                text=text,
                output_file=audio_path,
                subtitle_file=subtitle_path,
                words_in_cue=8
            )
            
            if not result['success']:
                return {
                    'success': False,
                    'error': result.get('error', '字幕生成失败')
                }
            
            # 读取VTT字幕内容
            vtt_content = ""
            subtitle_data = []
            
            if os.path.exists(subtitle_path) and os.path.getsize(subtitle_path) > 0:
                with open(subtitle_path, 'r', encoding='utf-8') as f:
                    vtt_content = f.read()
                    
                # 解析VTT为结构化数据
                subtitle_data = self.parse_vtt_subtitles(vtt_content)
            
            # 获取音频时长
            duration = get_audio_duration(audio_path, text)
            
            # 如果没有字幕数据，生成基础字幕
            if not subtitle_data:
                print(f"No subtitle data found, generating fallback for: {text[:50]}...")
                # 生成简单的单条字幕
                subtitle_data = [{
                    'start_time': 0.0,
                    'end_time': duration,
                    'text': text
                }]
            
            return {
                'audio_path': audio_path,
                'subtitle_vtt': vtt_content,
                'subtitle_data': subtitle_data,  # 返回结构化字幕数据
                'duration': duration,
                'success': True,
                'method': result.get('method', 'unknown')
            }
            
        except Exception as e:
            # 清理临时文件
            for path in [audio_path, subtitle_path]:
                if os.path.exists(path):
                    os.remove(path)
            return {
                'success': False,
                'error': str(e)
            }

    async def generate_segment_with_subtitles(self, text: str, voice_name: str):
        """为单个文本片段生成音频和字幕"""
        # 创建临时文件
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as audio_file:
            audio_path = audio_file.name
        
        with tempfile.NamedTemporaryFile(suffix=".vtt", delete=False) as subtitle_file:
            subtitle_path = subtitle_file.name
        
        try:
            # 生成音频和字幕
            communicate = edge_tts.Communicate(text, voice_name)
            await communicate.save(audio_path, subtitle_path)
            
            # 读取VTT字幕内容
            vtt_content = ""
            if os.path.exists(subtitle_path):
                with open(subtitle_path, 'r', encoding='utf-8') as f:
                    vtt_content = f.read()
            
            # 获取音频时长
            duration = get_audio_duration(audio_path, "")
            
            return {
                'audio_path': audio_path,
                'subtitle_vtt': vtt_content,
                'duration': duration,
                'success': True
            }
            
        except Exception as e:
            # 清理临时文件
            for path in [audio_path, subtitle_path]:
                if os.path.exists(path):
                    os.remove(path)
            return {
                'success': False,
                'error': str(e)
            }
    
    def parse_vtt_time(self, time_str: str) -> float:
        """解析VTT时间格式为秒数 (HH:MM:SS.mmm)"""
        time_str = time_str.strip()
        if '.' in time_str:
            time_parts, milli_part = time_str.rsplit('.', 1)
            milli = int(milli_part.ljust(3, '0')[:3])  # 确保是3位毫秒
        else:
            time_parts = time_str
            milli = 0
        
        time_components = time_parts.split(':')
        if len(time_components) == 3:
            hours, minutes, seconds = map(int, time_components)
        elif len(time_components) == 2:
            hours = 0
            minutes, seconds = map(int, time_components)
        else:
            return milli / 1000.0
        
        return hours * 3600 + minutes * 60 + seconds + milli / 1000.0
    
    def parse_vtt_subtitles(self, vtt_content: str) -> List[Dict[str, Any]]:
        """解析VTT字幕内容，返回字幕条目列表"""
        if not vtt_content:
            return []
        
        lines = vtt_content.strip().split('\n')
        subtitles = []
        
        i = 0
        # 跳过WEBVTT头部
        if lines and lines[0].startswith('WEBVTT'):
            i = 1
            # 跳过空行
            while i < len(lines) and lines[i].strip() == '':
                i += 1
        
        while i < len(lines):
            line = lines[i].strip()
            
            # 查找时间戳行
            if '-->' in line and ':' in line:
                timestamp_line = line
                start_time_str, end_time_str = timestamp_line.split('-->')
                start_time = self.parse_vtt_time(start_time_str.strip())
                end_time = self.parse_vtt_time(end_time_str.strip())
                
                # 获取字幕文本
                i += 1
                subtitle_text = []
                while i < len(lines) and lines[i].strip() != '':
                    subtitle_text.append(lines[i].strip())
                    i += 1
                
                if subtitle_text:
                    # 清理字幕文本中的多余空格
                    cleaned_text = self._clean_subtitle_text('\n'.join(subtitle_text))
                    subtitles.append({
                        'start_time': start_time,
                        'end_time': end_time,
                        'text': cleaned_text
                    })
            else:
                i += 1
        
        return subtitles
    
    def _clean_subtitle_text(self, text: str) -> str:
        """清理字幕文本中的多余空格"""
        import re
        
        # 去除所有空格
        text = re.sub(r'\s+', '', text)
        
        return text
    
    def adjust_subtitle_timestamps(self, subtitles: List[Dict[str, Any]], time_offset: float) -> List[Dict[str, Any]]:
        """调整字幕时间戳，添加时间偏移"""
        adjusted_subtitles = []
        for subtitle in subtitles:
            adjusted_subtitles.append({
                'start_time': subtitle['start_time'] + time_offset,
                'end_time': subtitle['end_time'] + time_offset,
                'text': subtitle['text']
            })
        return adjusted_subtitles
    
    def generate_srt_from_subtitles(self, subtitles: List[Dict[str, Any]]) -> str:
        """从字幕条目列表生成SRT格式内容"""
        print(f"Generating SRT from {len(subtitles)} subtitles")
        if not subtitles:
            return ""
        
        def format_srt_time(seconds: float) -> str:
            """将秒数格式化为SRT时间戳格式 (HH:MM:SS,mmm)"""
            hours = int(seconds // 3600)
            minutes = int((seconds % 3600) // 60)
            secs = int(seconds % 60)
            millisecs = int((seconds % 1) * 1000)
            return f"{hours:02d}:{minutes:02d}:{secs:02d},{millisecs:03d}"
        
        srt_lines = []
        for i, subtitle in enumerate(subtitles):
            print(f"Subtitle {i+1}: start={subtitle.get('start_time')}, end={subtitle.get('end_time')}, text={subtitle.get('text', '')[:50] if subtitle.get('text') else 'None'}")
            srt_lines.append(str(i + 1))
            srt_lines.append(f"{format_srt_time(subtitle['start_time'])} --> {format_srt_time(subtitle['end_time'])}")
            srt_lines.append(subtitle['text'])
            srt_lines.append("")  # 空行分隔
        result = '\n'.join(srt_lines)
        print(f"Generated SRT content length: {len(result)}")
        return result
    
    async def synthesize_dialogue_segments_with_subtitles_v2(self, dialogue_data: Dict[str, Any], voice_mapping: Dict[str, Dict[str, str]]):
        """改进的对话片段生成音频和字幕（带时间戳校对和说话者标识）"""
        segments = dialogue_data.get("segments", [])
        segment_files = []
        all_subtitles = []
        current_time_offset = 0.0
        
        for i, segment_data in enumerate(segments):
            speaker = segment_data.get("speaker", "未知")
            text = segment_data.get("utterance", "")
            
            # 获取说话者对应的音色
            voice_config = voice_mapping.get(speaker)
            if not voice_config:
                continue
                
            voice_name = voice_config.get("voice_name")
            
            # 使用改进的方法为当前片段生成音频和字幕
            result = await self.generate_segment_with_subtitles_v2(text, voice_name)
            
            if not result['success']:
                # 清理已创建的文件
                for file_info in segment_files:
                    if os.path.exists(file_info['audio_path']):
                        os.remove(file_info['audio_path'])
                raise Exception(f"生成片段{i+1}失败: {result['error']}")
            
            # 处理字幕数据 - 使用结构化数据而不是重新解析VTT
            if result.get('subtitle_data'):
                # 调整时间戳，不添加说话者标识
                for subtitle in result['subtitle_data']:
                    adjusted_subtitle = {
                        'start_time': subtitle['start_time'] + current_time_offset,
                        'end_time': subtitle['end_time'] + current_time_offset,
                        'text': subtitle['text']  # 直接使用原文本，不添加说话者标识
                    }
                    all_subtitles.append(adjusted_subtitle)
            else:
                # 如果没有详细字幕数据，创建一个基础条目
                all_subtitles.append({
                    'start_time': current_time_offset,
                    'end_time': current_time_offset + result['duration'],
                    'text': text  # 直接使用原文本
                })
            
            # 记录音频文件和更新时间偏移
            segment_files.append({
                'audio_path': result['audio_path'],
                'duration': result['duration']
            })
            
            current_time_offset += result['duration']
        
        return {
            'segment_files': segment_files,
            'subtitles': all_subtitles,
            'total_duration': current_time_offset
        }

    async def synthesize_dialogue_segments_with_subtitles(self, dialogue_data: Dict[str, Any], voice_mapping: Dict[str, Dict[str, str]]):
        """为对话片段生成音频和字幕（带时间戳校对）"""
        segments = dialogue_data.get("segments", [])
        segment_files = []
        all_subtitles = []
        current_time_offset = 0.0
        
        for i, segment_data in enumerate(segments):
            speaker = segment_data.get("speaker", "未知")
            text = segment_data.get("utterance", "")
            
            # 获取说话者对应的音色
            voice_config = voice_mapping.get(speaker)
            if not voice_config:
                continue
                
            voice_name = voice_config.get("voice_name")
            
            # 为当前片段生成音频和字幕
            result = await self.generate_segment_with_subtitles(text, voice_name)
            
            if not result['success']:
                # 清理已创建的文件
                for file_info in segment_files:
                    if os.path.exists(file_info['audio_path']):
                        os.remove(file_info['audio_path'])
                raise Exception(f"生成片段{i+1}失败: {result['error']}")
            
            # 解析并调整字幕时间戳
            subtitles = self.parse_vtt_subtitles(result['subtitle_vtt'])
            adjusted_subtitles = self.adjust_subtitle_timestamps(subtitles, current_time_offset)
            all_subtitles.extend(adjusted_subtitles)
            
            # 记音频文件和更新时间偏移
            segment_files.append({
                'audio_path': result['audio_path'],
                'duration': result['duration']
            })
            
            current_time_offset += result['duration']
        
        return {
            'segment_files': segment_files,
            'subtitles': all_subtitles,
            'total_duration': current_time_offset
        }
    
    def synthesize_dialogue_with_subtitles_v2(self, dialogue_data: Dict[str, Any], voice_mapping: Dict[str, Dict[str, str]], output_file: str, subtitle_file: str):
        """改进的生成对话音频和字幕文件（带时间戳校对和更好的错误处理）"""
        try:
            # 创建临时目录
            self.temp_dir = tempfile.mkdtemp(prefix="dialogue_tts_")
            
            # 获取当前事件循环或创建新的
            try:
                loop = asyncio.get_event_loop()
                if loop.is_closed():
                    raise RuntimeError("Event loop is closed")
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            # 使用改进的方法生成音频片段和字幕
            result = loop.run_until_complete(
                self.synthesize_dialogue_segments_with_subtitles_v2(dialogue_data, voice_mapping)
            )
            
            print(f"Improved synthesis result: segments={len(result.get('segment_files', []))}, subtitles={len(result.get('subtitles', []))}")
            
            # 合并音频文件
            merge_result = self._merge_audio_files([f['audio_path'] for f in result['segment_files']], output_file)
            if not merge_result['success']:
                raise Exception(f"音频合并失败: {merge_result['error']}")
            
            # 生成最终的SRT字幕
            final_srt = self.generate_srt_from_subtitles(result['subtitles'])
            print(f"Generated SRT content length: {len(final_srt)}")
            
            if final_srt:
                print(f"SRT content preview: {final_srt[:200] if final_srt else 'None'}")
                
                # 保存字幕文件
                with open(subtitle_file, 'w', encoding='utf-8') as f:
                    f.write(final_srt)
                
                # 检查字幕文件是否正确创建
                if os.path.exists(subtitle_file):
                    file_size = os.path.getsize(subtitle_file)
                    print(f"Subtitle file created: {subtitle_file}, size: {file_size}")
                    if file_size == 0:
                        print("Warning: Subtitle file is empty")
                else:
                    print(f"Warning: Subtitle file not created: {subtitle_file}")
            else:
                print("Warning: No SRT content generated")
                # 生成基础字幕作为回退
                fallback_srt = self._generate_fallback_dialogue_subtitle(dialogue_data, result['total_duration'])
                if fallback_srt:
                    with open(subtitle_file, 'w', encoding='utf-8') as f:
                        f.write(fallback_srt)
                    print(f"Generated fallback subtitle, length: {len(fallback_srt)}")
            
            # 清理临时音频文件
            for file_info in result['segment_files']:
                if os.path.exists(file_info['audio_path']):
                    os.remove(file_info['audio_path'])
            
            return {
                'success': True,
                'segments_count': len(result['segment_files']),
                'total_duration': result['total_duration'],
                'subtitle_entries': len(result['subtitles'])
            }
            
        except Exception as e:
            print(f"Error in synthesize_dialogue_with_subtitles_v2: {str(e)}")
            # 清理可能残留的临时文件
            if 'result' in locals() and 'segment_files' in result:
                for file_info in result['segment_files']:
                    if os.path.exists(file_info['audio_path']):
                        os.remove(file_info['audio_path'])
            return {
                'success': False,
                'error': str(e)
            }
        finally:
            # 清理临时目录
            self._cleanup_temp_files()
    
    def _generate_fallback_dialogue_subtitle(self, dialogue_data: Dict[str, Any], total_duration: float) -> str:
        """为对话生成基础回退字幕"""
        segments = dialogue_data.get("segments", [])
        if not segments or total_duration <= 0:
            return ""
        
        # 计算每个片段的平均时长
        time_per_segment = total_duration / len(segments)
        
        srt_lines = []
        for i, segment in enumerate(segments):
            speaker = segment.get("speaker", "未知")
            text = segment.get("utterance", "")
            
            start_time = i * time_per_segment
            end_time = (i + 1) * time_per_segment
            
            srt_lines.extend([
                str(i + 1),
                f"{self._format_srt_timestamp(start_time)} --> {self._format_srt_timestamp(end_time)}",
                text,  # 直接使用文本，不添加说话者前缀
                ""
            ])
        
        return "\n".join(srt_lines)
    
    def _format_srt_timestamp(self, seconds: float) -> str:
        """格式化SRT时间戳"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"

    def synthesize_dialogue_with_subtitles(self, dialogue_data: Dict[str, Any], voice_mapping: Dict[str, Dict[str, str]], output_file: str, subtitle_file: str):
        """生成对话音频和字幕文件（带时间戳校对）"""
        try:
            # 创建临时目录
            self.temp_dir = tempfile.mkdtemp(prefix="dialogue_tts_")
            
            # 获取当前事件循环或创建新的
            try:
                loop = asyncio.get_event_loop()
                if loop.is_closed():
                    raise RuntimeError("Event loop is closed")
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            # 生成音频片段和字幕
            result = loop.run_until_complete(
                self.synthesize_dialogue_segments_with_subtitles(dialogue_data, voice_mapping)
            )
            
            print(f"Synthesis result: segments={len(result.get('segment_files', []))}, subtitles={len(result.get('subtitles', []))}")
            
            # 合并音频文件
            merge_result = self._merge_audio_files([f['audio_path'] for f in result['segment_files']], output_file)
            if not merge_result['success']:
                raise Exception(f"音频合并失败: {merge_result['error']}")
            
            # 生成最终的SRT字幕
            final_srt = self.generate_srt_from_subtitles(result['subtitles'])
            print(f"Generated SRT content length: {len(final_srt)}")
            if final_srt:
                print(f"SRT content preview: {final_srt[:200] if final_srt else 'None'}")
            
            # 保存字幕文件
            with open(subtitle_file, 'w', encoding='utf-8') as f:
                f.write(final_srt)
            
            # 检查字幕文件是否正确创建
            if os.path.exists(subtitle_file):
                file_size = os.path.getsize(subtitle_file)
                print(f"Subtitle file created: {subtitle_file}, size: {file_size}")
                if file_size == 0:
                    print("Warning: Subtitle file is empty")
            else:
                print(f"Warning: Subtitle file not created: {subtitle_file}")
            
            # 清理临时音频文件
            for file_info in result['segment_files']:
                if os.path.exists(file_info['audio_path']):
                    os.remove(file_info['audio_path'])
            
            return {
                'success': True,
                'segments_count': len(result['segment_files']),
                'total_duration': result['total_duration'],
                'subtitle_entries': len(result['subtitles'])
            }
            
        except Exception as e:
            # 清理可能残留的临时文件
            if 'result' in locals() and 'segment_files' in result:
                for file_info in result['segment_files']:
                    if os.path.exists(file_info['audio_path']):
                        os.remove(file_info['audio_path'])
            return {
                'success': False,
                'error': str(e)
            }
        finally:
            # 清理临时目录
            self._cleanup_temp_files()
    
    def _synthesize_segment(
        self, 
        text: str, 
        voice_config: Dict[str, str], 
        output_file: str
    ) -> Dict[str, Any]:
        """
        合成单个片段的音频
        
        Args:
            text: 文本内容
            voice_config: 音色配置
            output_file: 输出文件路径
            
        Returns:
            合成结果
        """
        try:
            provider = voice_config.get("provider", "edge_tts")
            voice_name = voice_config.get("voice_name")
            
            if not voice_name:
                return {"success": False, "error": "音色配置中缺少voice_name"}
            
            if provider == "edge_tts":
                # 使用Edge TTS
                edge_text_to_speech(text, voice_name, output_file)
                
                # 检查文件是否成功生成
                if os.path.exists(output_file) and os.path.getsize(output_file) > 0:
                    return {"success": True}
                else:
                    return {"success": False, "error": "Edge TTS生成失败"}
            
            else:
                return {"success": False, "error": f"不支持的TTS提供商: {provider}，请使用edge_tts"}
                
        except Exception as e:
            return {"success": False, "error": f"片段合成错误: {str(e)}"}
    
    def _merge_audio_files(self, input_files: List[str], output_file: str) -> Dict[str, Any]:
        """
        合并多个音频文件
        
        Args:
            input_files: 输入文件列表
            output_file: 输出文件路径
            
        Returns:
            合并结果
        """
        try:
            # 确保输出目录存在
            output_path = Path(output_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # 创建concat文件
            concat_file = os.path.join(self.temp_dir, "concat_list.txt")
            with open(concat_file, "w", encoding="utf-8") as f:
                for audio_file in input_files:
                    # 转换为绝对路径并转义特殊字符
                    abs_path = os.path.abspath(audio_file)
                    escaped_path = abs_path.replace("\\", "\\\\").replace("'", "\\'")
                    f.write(f"file '{escaped_path}'\n")
            
            # 使用ffmpeg合并音频
            (
                ffmpeg
                .input(concat_file, format='concat', safe=0)
                .output(output_file, acodec='pcm_s16le', ar=22050)
                .overwrite_output()
                .run(quiet=True)
            )
            
            # 检查输出文件
            if os.path.exists(output_file) and os.path.getsize(output_file) > 0:
                return {"success": True}
            else:
                return {"success": False, "error": "合并后的文件为空或不存在"}
                
        except Exception as e:
            return {"success": False, "error": f"音频合并失败: {str(e)}"}
    
    def _cleanup_temp_files(self):
        """清理临时文件"""
        try:
            if self.temp_dir and os.path.exists(self.temp_dir):
                import shutil
                shutil.rmtree(self.temp_dir)
        except Exception as e:
            print(f"清理临时文件失败: {e}")
    
    def get_available_voices(self, provider: str = "edge_tts") -> List[Dict[str, str]]:
        """
        获取可用的音色列表
        
        Args:
            provider: TTS提供商
            
        Returns:
            音色列表
        """
        if provider == "edge_tts":
            try:
                # 从已有的edge_tts模块获取音色列表
                from .tts import edge_tts_volices
                voices = edge_tts_volices()
                
                # Edge TTS 中文音色名称映射
                edge_voice_mapping = {
                    "zh-CN-XiaoxiaoNeural": "晓晓 (女声)",
                    "zh-CN-YunxiNeural": "云希 (男声)",
                    "zh-CN-XiaoyiNeural": "晓伊 (女声)",
                    "zh-CN-YunyangNeural": "云扬 (男声)",
                    "zh-CN-XiaomengNeural": "晓梦 (女声)",
                    "zh-CN-YunjianNeural": "云健 (男声)",
                    "zh-CN-XiaomoNeural": "晓墨 (女声)",
                    "zh-CN-XiaoruiNeural": "晓睿 (女声)",
                    "zh-CN-XiaoshuangNeural": "晓双 (女声)",
                    "zh-CN-XiaoyouNeural": "晓悠 (女声)",
                    "zh-CN-YunyeNeural": "云野 (男声)",
                    "zh-CN-YunzeNeural": "云泽 (男声)",
                    "zh-CN-XiaochenNeural": "晓辰 (女声)",
                    "zh-CN-XiaohanNeural": "晓涵 (女声)",
                    "zh-CN-XiaomaoNeural": "晓猫 (女声)",
                    "zh-CN-XiaoqiuNeural": "晓秋 (女声)",
                    "zh-CN-XiaoyanNeural": "晓颜 (女声)",
                    "zh-CN-XiaozhenNeural": "晓甄 (女声)",
                    "zh-CN-YunfengNeural": "云枫 (男声)",
                    "zh-CN-YunhaoNeural": "云皓 (男声)",
                    "zh-CN-YunjieNeural": "云杰 (男声)",
                    "zh-CN-YunyuNeural": "云语 (男声)",
                    "zh-CN-XiaoxuanNeural": "晓萱 (女声)",
                    "zh-CN-YunxiaNeural": "云夏 (女声)",
                }
                
                chinese_voices = []
                for voice in voices:
                    if "zh-CN" in voice:
                        # 使用映射表中的中文名称，如果没有映射则使用原名称
                        display_name = edge_voice_mapping.get(voice, voice)
                        chinese_voices.append({"name": display_name, "value": voice})
                
                return chinese_voices
            except Exception:
                return []
        
        return []
    
    def create_voice_mapping_template(self, speakers: List[str]) -> Dict[str, Dict[str, str]]:
        """
        为说话者列表创建音色映射模板
        
        Args:
            speakers: 说话者列表
            
        Returns:
            音色映射模板
        """
        available_voices = self.get_available_voices("edge_tts")
        voice_mapping = {}
        
        for i, speaker in enumerate(speakers):
            # 为不同说话者分配不同的默认音色
            if i < len(available_voices):
                voice_mapping[speaker] = {
                    "provider": "edge_tts",
                    "voice_name": available_voices[i]["value"]
                }
            else:
                # 如果说话者多于可用音色，循环使用
                voice_index = i % len(available_voices)
                voice_mapping[speaker] = {
                    "provider": "edge_tts",
                    "voice_name": available_voices[voice_index]["value"]
                }
        
        return voice_mapping
    
    def estimate_audio_duration(self, dialogue_data: Dict[str, Any], wpm: int = 200) -> float:
        """
        估算音频时长
        
        Args:
            dialogue_data: 对话数据
            wpm: 每分钟单词数（用于估算）
            
        Returns:
            预估时长（秒）
        """
        total_chars = 0
        segments = dialogue_data.get("segments", [])
        
        for segment in segments:
            utterance = segment.get("utterance", "")
            total_chars += len(utterance)
        
        # 简单估算：中文平均每分钟200字符
        estimated_duration = (total_chars / 200) * 60
        return max(estimated_duration, 1.0)  # 最少1秒