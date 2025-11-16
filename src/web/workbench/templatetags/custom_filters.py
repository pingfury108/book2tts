from django import template
import re

register = template.Library()

@register.filter
def replace(value, args):
    """
    Custom template filter to replace a substring with another substring.
    Usage: {{ value|replace:"old,new" }}
    """
    if args and "," in args:
        old, new = args.split(",", 1)
        return value.replace(old, new)
    return value


@register.filter
def dict_get(value, key):
    """从字典中安全获取键值。"""
    if isinstance(value, dict):
        return value.get(key, {})
    return {}


@register.filter
def format_seconds(value):
    """将秒数格式化为H:MM:SS或M:SS形式。"""
    try:
        seconds = float(value)
    except (TypeError, ValueError):
        return "0:00"

    seconds = max(0, int(seconds))
    hours, remainder = divmod(seconds, 3600)
    minutes, secs = divmod(remainder, 60)

    if hours:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes}:{secs:02d}"


@register.filter
def extract_script_tags(ads_script):
    """
    从广告脚本中提取所有 <script> 标签内容
    用于在 <head> 中加载脚本
    """
    if not ads_script:
        return ''

    # 匹配所有 <script> 标签，包括各种属性
    script_pattern = r'<script[^>]*>.*?</script>'
    script_matches = re.findall(script_pattern, ads_script, re.DOTALL | re.IGNORECASE)

    if script_matches:
        return '\n'.join(script_matches)

    return ''


@register.filter
def extract_div_tags(ads_script):
    """
    从广告脚本中提取所有 <div> 标签内容
    用于在 </body> 之前放置广告容器
    """
    if not ads_script:
        return ''

    # 匹配所有 <div> 标签，包括各种属性
    div_pattern = r'<div[^>]*>.*?</div>'
    div_matches = re.findall(div_pattern, ads_script, re.DOTALL | re.IGNORECASE)

    if div_matches:
        return '\n'.join(div_matches)

    return ''
