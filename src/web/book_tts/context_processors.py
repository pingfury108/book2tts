from django.conf import settings


def css_version(request):
    """
    Context processor to make CSS_VERSION available in all templates
    for cache busting purposes. Only used in production (non-DEBUG) mode.
    """
    return {
        'CSS_VERSION': settings.CSS_VERSION if not settings.DEBUG else None
    } 

def language_alternates(request):
    """为 hreflang 提供当前页面在各语言下的绝对地址（SEO 用）。"""
    from django.conf import settings
    from django.urls import translate_url

    current = request.get_full_path()
    active = request.LANGUAGE_CODE
    items = []
    for code, name in settings.LANGUAGES:
        try:
            path = translate_url(current, code)
        except Exception:
            path = current
        items.append({
            "code": code,
            "name": name,               # 原生名称（不翻译），如 English / 简体中文
            "path": path,               # 目标语言下的路径，供切换器作为 next
            "hreflang": "zh-Hans" if code.lower().startswith("zh") else code,
            "url": request.build_absolute_uri(path),
            "active": code == active,
        })
    # x-default 指向默认语言（settings.LANGUAGE_CODE）
    default = next(
        (i["url"] for i in items if i["code"] == settings.LANGUAGE_CODE),
        items[0]["url"] if items else "",
    )
    return {"language_alternates": items, "language_x_default": default}
