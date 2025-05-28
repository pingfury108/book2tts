from django.urls import path
from . import views

urlpatterns = [
    path("", views.index, name="home"),
    path("audio/<int:segment_id>/", views.audio_detail, name="audio_detail"),
    path("book/<int:book_id>/", views.book_audio_list, name="book_audio_list"),
    path("rss/token/<uuid:token>/rss.xml", views.audio_rss_feed_by_token, name="token_audio_rss_feed"),
    path("rss/token/<uuid:token>/<int:book_id>/rss.xml", views.audio_rss_feed_by_token, name="token_book_audio_rss_feed"),
    path("profile/", views.profile, name="profile"),
    path("operation-records/", views.operation_records, name="operation_records"),
]
