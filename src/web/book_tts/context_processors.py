from django.conf import settings


def css_version(request):
    """
    Context processor to make CSS_VERSION available in all templates
    for cache busting purposes. Only used in production (non-DEBUG) mode.
    """
    return {
        'CSS_VERSION': settings.CSS_VERSION if not settings.DEBUG else None
    } 