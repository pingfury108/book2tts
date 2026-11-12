"""站点级中间件。"""

from django.conf import settings
from django.utils import translation


class ForceDefaultLanguageOnUnprefixed:
    """无语言前缀的 URL 永远使用默认语言（en），避免与 /zh-hans/ 重复内容。

    必须放在 LocaleMiddleware 之后：LocaleMiddleware 会按 session/cookie/
    Accept-Language 激活语言，本中间件把无前缀路径强制回默认语言，
    保证每个语义页面只有一个规范 URL（配合 hreflang + canonical）。
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if translation.get_language_from_path(request.path_info) is None:
            translation.activate(settings.LANGUAGE_CODE)
        return self.get_response(request)
