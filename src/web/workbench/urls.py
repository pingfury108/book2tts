from django.urls import path

from . import views
from .views import aggregated_audio_segments, get_voice_list, synthesize_audio

urlpatterns = [
    path("", views.upload, name="index"),
    path("book/<int:book_id>", views.index, name="index"),
    path("my/upload", views.my_upload_list, name="my_upload"),
    path(
        "book/<int:book_id>/text/toc/<str:name>", views.text_by_toc, name="text_by_toc"
    ),
    path(
        "book/<int:book_id>/text/page/<str:name>",
        views.text_by_page,
        name="text_by_page",
    ),
    path("book/<int:book_id>/toc", views.toc, name="toc"),
    path("book/<int:book_id>/page", views.pages, name="pages"),
    path("book/reformat", views.reformat, name="reformat"),
    path("book/reformat/<str:id>", views.reformat_sse, name="reformat_sse"),
    path("audio/books", aggregated_audio_segments, name="aggregated_audio_segments"),
    path('voices/', get_voice_list, name='voice_list'),
    path('synthesize-audio/', synthesize_audio, name='synthesize_audio'),
]
