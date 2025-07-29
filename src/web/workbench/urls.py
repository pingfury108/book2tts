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
from .views.audio_views import (
    task_queue,
    cancel_task,
    delete_task_record,
)
from .views.dialogue_views import (
    dialogue_list,
    dialogue_create,
    dialogue_convert_text,
    dialogue_detail,
    dialogue_configure_voices,
    dialogue_generate_audio,
    dialogue_publish,
    dialogue_delete,
    dialogue_update_title,
    dialogue_update_book,
    dialogue_segment_delete,
    dialogue_segment_update,
    dialogue_segment_preview,
    voice_roles_list,
    voice_role_create,
    voice_role_delete,
    task_status,
)

urlpatterns = [
    path("", views.upload, name="index"),
    path("book/<int:book_id>", views.index, name="index"),
    path("my/upload", views.my_upload_list, name="my_upload"),
    path(
        "book/<int:book_id>/text/toc/", views.text_by_toc, name="text_by_toc"
    ),
    path(
        "book/<int:book_id>/text/pages/",
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
    # 任务队列相关路由
    path("tasks/", task_queue, name="task_queue"),
    path("task/cancel/<str:task_id>/", cancel_task, name="cancel_task"),
    path("task/delete/<str:task_id>/", delete_task_record, name="delete_task_record"),
    
    # 对话功能相关路由
    path("dialogue/", dialogue_list, name="dialogue_list"),
    path("dialogue/create/", dialogue_create, name="dialogue_create"),
    path("dialogue/convert/", dialogue_convert_text, name="dialogue_convert_text"),
    path("dialogue/<int:script_id>/", dialogue_detail, name="dialogue_detail"),
    path("dialogue/<int:script_id>/configure-voices/", dialogue_configure_voices, name="dialogue_configure_voices"),
    path("dialogue/<int:script_id>/generate-audio/", dialogue_generate_audio, name="dialogue_generate_audio"),
    path("dialogue/<int:script_id>/publish/", dialogue_publish, name="dialogue_publish"),
    path("dialogue/<int:script_id>/delete/", dialogue_delete, name="dialogue_delete"),
    path("dialogue/<int:script_id>/update-title/", dialogue_update_title, name="dialogue_update_title"),
    path("dialogue/<int:script_id>/update-book/", dialogue_update_book, name="dialogue_update_book"),
    
    # 对话片段管理
    path("dialogue/segment/<int:segment_id>/delete/", dialogue_segment_delete, name="dialogue_segment_delete"),
    path("dialogue/segment/<int:segment_id>/update/", dialogue_segment_update, name="dialogue_segment_update"),
    path("dialogue/segment/<int:segment_id>/preview/", dialogue_segment_preview, name="dialogue_segment_preview"),
    
    # 音色角色管理
    path("voice-roles/", voice_roles_list, name="voice_roles_list"),
    path("voice-roles/create/", voice_role_create, name="voice_role_create"),
    path("voice-roles/<int:role_id>/delete/", voice_role_delete, name="voice_role_delete"),
    
    # 任务状态查询
    path("task/<str:task_id>/status/", task_status, name="task_status"),
]
