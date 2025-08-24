import os
import time
from django.core.files.base import ContentFile
from django.conf import settings

def convert_vtt_to_srt(vtt_content):
    """将VTT字幕转换为SRT格式"""
    if not vtt_content:
        return ""

    lines = vtt_content.strip().split('\n')
    srt_lines = []
    entry_count = 1

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
            # 转换时间戳格式（VTT使用.分隔毫秒，SRT使用,分隔毫秒）
            timestamp_line = line.replace('.', ',')

            # 获取字幕文本
            i += 1
            subtitle_text = []
            while i < len(lines) and lines[i].strip() != '':
                text_line = lines[i].strip()
                # 清理多余空格
                text_line = clean_subtitle_text(text_line)
                subtitle_text.append(text_line)
                i += 1

            # 添加到SRT内容
            if subtitle_text:
                srt_lines.append(str(entry_count))
                srt_lines.append(timestamp_line)
                srt_lines.extend(subtitle_text)
                srt_lines.append('')  # 空行分隔
                entry_count += 1
            else:
                i += 1
        else:
            i += 1

    return '\n'.join(srt_lines)


def clean_subtitle_text(text):
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


def parse_vtt_time(time_str):
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

def format_srt_time(seconds):
    """将秒数格式化为SRT时间戳格式 (HH:MM:SS,mmm)"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millisecs = int((seconds % 1) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millisecs:03d}"

def adjust_subtitle_timestamps(subtitles, time_offset):
    """调整字幕时间戳，添加时间偏移"""
    adjusted_subtitles = []
    for subtitle in subtitles:
        adjusted_subtitles.append({
            'start_time': subtitle['start_time'] + time_offset,
            'end_time': subtitle['end_time'] + time_offset,
            'text': subtitle['text']
        })
    return adjusted_subtitles

def generate_srt_from_subtitles(subtitles):
    """从字幕条目列表生成SRT格式内容"""
    if not subtitles:
        return ""

    srt_lines = []
    for i, subtitle in enumerate(subtitles):
        srt_lines.append(str(i + 1))
        srt_lines.append(f"{format_srt_time(subtitle['start_time'])} --> {format_srt_time(subtitle['end_time'])}")
        srt_lines.append(subtitle['text'])
        srt_lines.append("")  # 空行分隔
    return '\n'.join(srt_lines)

def save_srt_subtitle(model_instance, srt_content, subtitle_field_name='subtitle_file'):
    """保存SRT字幕到模型实例"""
    if not srt_content:
        return

    # 生成文件名
    timestamp = int(time.time())
    filename = f"subtitle_{model_instance.id}_{timestamp}.srt"

    # 保存到模型字段
    file_field = getattr(model_instance, subtitle_field_name)
    file_field.save(filename, ContentFile(srt_content.encode('utf-8')))
    model_instance.save(update_fields=[subtitle_field_name])

def parse_vtt_subtitles(vtt_content):
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
            start_time = parse_vtt_time(start_time_str.strip())
            end_time = parse_vtt_time(end_time_str.strip())

            # 获取字幕文本
            i += 1
            subtitle_text = []
            while i < len(lines) and lines[i].strip() != '':
                subtitle_text.append(lines[i].strip())
                i += 1

            if subtitle_text:
                subtitles.append({
                    'start_time': start_time,
                    'end_time': end_time,
                    'text': '\n'.join(subtitle_text)
                })
            else:
                i += 1
        else:
            i += 1

    return subtitles