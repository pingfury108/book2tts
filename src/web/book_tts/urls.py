"""
URL configuration for book_tts project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.contrib.sitemaps.views import sitemap
from django.urls import path, include
from django.conf import settings
from django.conf.urls.i18n import i18n_patterns
from django.conf.urls.static import static
from django.contrib.auth import logout
from django.shortcuts import render
from .views import TurnstileLoginView, TurnstileRegisterView
from home.sitemaps import (
    StaticViewSitemap,
    AudioSegmentSitemap,
    DialogueScriptSitemap,
    BookSitemap,
    DiscussionTopicSitemap,
)

sitemaps = {
    "static": StaticViewSitemap,
    "audio": AudioSegmentSitemap,
    "dialogue": DialogueScriptSitemap,
    "book": BookSitemap,
    "discussion": DiscussionTopicSitemap,
}

# Custom logout view to ensure proper session cleanup
def logout_view(request):
    # Completely log out the user
    logout(request)
    # Clear any session data
    request.session.flush()
    # Render the logged_out template
    return render(request, 'registration/logged_out.html')

urlpatterns = [
    # 不参与语言前缀的 URL：机器读取的端点（sitemap/robots/ads.txt/RSS 在 app 内定义）
    path(
        "sitemap.xml",
        sitemap,
        {"sitemaps": sitemaps},
        name="django.contrib.sitemaps.views.sitemap",
    ),
    path("i18n/", include("django.conf.urls.i18n")),
]

# 面向用户的页面走语言前缀：默认语言（en）不带前缀，中文走 /zh-hans/...
urlpatterns += i18n_patterns(
    path("", include("home.urls")),
    path('workbench/', include('workbench.urls')),
    path("admin/", admin.site.urls),
    path("__reload__/", include("django_browser_reload.urls")),

    # Authentication URLs with Turnstile
    path('login/', TurnstileLoginView.as_view(), name='login'),
    path('logout/', logout_view, name='logout'),
    path('register/', TurnstileRegisterView.as_view(), name='register'),
    prefix_default_language=False,
)

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
