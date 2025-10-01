from django import template

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
