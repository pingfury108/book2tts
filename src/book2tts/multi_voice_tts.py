import os
import tempfile
import ffmpeg
from typing import Dict, List, Any, Optional
from pathlib import Path
import asyncio
from .tts import edge_text_to_speech
from .long_tts import LongTTS
from .edgetts import EdgeTTS

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