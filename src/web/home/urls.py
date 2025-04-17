from django.urls import path
from . import views

urlpatterns = [
    path("", views.index, name="home"),
    path("audio/<int:segment_id>/", views.audio_detail, name="audio_detail"),
    path("book/<int:book_id>/", views.book_audio_list, name="book_audio_list"),
    path("rss/token/<uuid:token>/rss.xml", views.audio_rss_feed_by_token, name="token_audio_rss_feed"),
    path("rss/token/<uuid:token>/<int:book_id>/rss.xml", views.audio_rss_feed_by_token, name="token_book_audio_rss_feed"),
    
    # 新增不需要登录的公开RSS相关URL
    path("public/rss/token/<uuid:token>/rss.xml", views.public_rss_feed_by_token, name="public_token_audio_rss_feed"),
    path("public/rss/token/<uuid:token>/<int:book_id>/rss.xml", views.public_rss_feed_by_token, name="public_token_book_audio_rss_feed"),
    path("public/audio/<int:segment_id>/", views.public_rss_audio_detail, name="public_rss_audio_detail"),
    path("public/audio/file/<int:segment_id>/", views.public_audio_file, name="public_audio_file"),
    path("public/book/<int:book_id>/", views.public_rss_book_audio, name="public_rss_book_audio"),
]
