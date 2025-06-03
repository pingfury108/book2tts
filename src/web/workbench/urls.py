from django.urls import path

from . import views
from .views import (
    aggregated_audio_segments,
    get_voice_list,
    get_user_quota,
    synthesize_audio,
    check_task_status,
    delete_audio_segment,
    book_details_htmx,
    update_book_name,
    delete_book,
    toggle_publish_audio_segment,
)

urlpatterns = [
    path("", views.upload, name="index"),
    path("book/<int:book_id>", views.index, name="index"),
    path("my/upload", views.my_upload_list, name="my_upload"),
    path(
        "book/<int:book_id>/text/toc/<str:name>", views.text_by_toc, name="text_by_toc"
    ),
    path(
        "book/<int:book_id>/text/pages/<str:name>",
        views.text_by_page,
        name="text_by_page",
    ),
    path("book/<int:book_id>/toc", views.toc, name="toc"),
    path("book/<int:book_id>/page", views.pages, name="pages"),
    path("book/reformat", views.reformat, name="reformat"),
    path("audio/books", aggregated_audio_segments, name="aggregated_audio_segments"),
    path(
        "audio/book-details/<int:book_id>/", book_details_htmx, name="book_details_htmx"
    ),
    path("voices/", get_voice_list, name="voice_list"),
    path("quota/", get_user_quota, name="get_user_quota"),
    path("synthesize-audio/", synthesize_audio, name="synthesize_audio"),
    path("task-status/<str:task_id>/", check_task_status, name="check_task_status"),
    path(
        "audio/delete/<int:segment_id>/",
        delete_audio_segment,
        name="delete_audio_segment",
    ),
    path(
        "audio/publish/<int:segment_id>/",
        toggle_publish_audio_segment,
        name="toggle_publish_audio_segment",
    ),
    path("book/<int:book_id>/update-name/", update_book_name, name="update_book_name"),
    path("book/<int:book_id>/delete/", delete_book, name="delete_book"),
]
