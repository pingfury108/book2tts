import ffmpeg
import os


def get_audio_duration(file_path, fallback_text=""):
    """
    获取音频文件的时长（秒）
    
    Args:
        file_path (str): 音频文件路径
        fallback_text (str): 当无法获取时长时，用于估算的文本内容
        
    Returns:
        int: 音频时长（秒）
    """
    if not file_path or not os.path.exists(file_path):
        # 如果文件不存在，使用文本估算
        if fallback_text:
            word_count = len(fallback_text.split())
            return max(1, int(word_count / 2.5))  # 150 words/min = 2.5 words/sec
        return 0
    
    try:
        # 使用ffmpeg探测文件获取音频信息
        probe = ffmpeg.probe(file_path)
        
        # 查找音频流并获取时长
        audio_stream = next(
            (stream for stream in probe["streams"] if stream["codec_type"] == "audio"),
            None,
        )
        
        if audio_stream is not None:
            return int(float(audio_stream["duration"]))
        else:
            # 没有找到音频流，使用文本估算
            if fallback_text:
                word_count = len(fallback_text.split())
                return max(1, int(word_count / 2.5))
            return 0
            
    except Exception as e:
        print(f"Error getting audio duration from {file_path}: {str(e)}")
        # 出错时使用文本估算
        if fallback_text:
            word_count = len(fallback_text.split())
            return max(1, int(word_count / 2.5))
        return 0


def estimate_audio_duration_from_text(text):
    """
    根据文本内容估算音频时长
    
    Args:
        text (str): 文本内容
        
    Returns:
        int: 估算的音频时长（秒）
    """
    if not text:
        return 0
    
    word_count = len(text.split())
    # 假设平均语速为150词/分钟 = 2.5词/秒
    return max(1, int(word_count / 2.5)) 