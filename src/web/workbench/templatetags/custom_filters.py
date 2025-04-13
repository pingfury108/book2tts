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
