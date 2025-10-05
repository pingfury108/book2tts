from django.urls import path

from . import views
from .views import (
    aggregated_audio_segments,
    get_voice_list,
    preview_tts_voice,
    get_user_quota,
    get_points_rules,
    synthesize_audio,
    check_task_status,
    delete_audio_segment,
    book_details_htmx,
    update_book_name,
    update_pdf_type,
    detect_scanned_pdf,
    get_page_image,
    check_page_audio_status,
    delete_book,
    get_original_content,
    get_epub_asset,
    toggle_publish_audio_segment,
)
from .views.text_views import translate
from .views.translation_views import (
    translation_cache_list,
    translation_cache_detail,
    translation_cache_delete,
    translation_cache_cleanup,
    translation_cache_stats_api,
    translation_cache_bulk_delete,
)
from .views.audio_views import (
    task_queue,
    cancel_task,
    delete_task_record,
    download_audio,
    download_subtitle,
    generate_audio_chapters,
)
from .views.dialogue_views import (
    dialogue_list,
    dialogue_create,
    dialogue_convert_text,
    dialogue_detail,
    dialogue_configure_voices,
    dialogue_generate_audio,
    dialogue_generate_chapters,
    dialogue_publish,
    dialogue_delete,
    dialogue_update_title,
    dialogue_update_book,
    dialogue_segment_delete,
    dialogue_segment_update,
    dialogue_segment_preview,
    dialogue_ai_recommend_voices,
    task_status,
)
from .views.ocr_views import (
    detect_pdf_scanned,
    ocr_pdf_page,
    ocr_pdf_pages_batch,
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
    path("book/translate", translate, name="translate"),
    path("book/<int:book_id>/original/", get_original_content, name="get_original_content"),
    path("book/<int:book_id>/original/asset/", get_epub_asset, name="get_epub_asset"),
    path("audio/books", aggregated_audio_segments, name="aggregated_audio_segments"),
    path(
        "audio/book-details/<int:book_id>/", book_details_htmx, name="book_details_htmx"
    ),
    path("voices/", get_voice_list, name="voice_list"),
    path("tts/preview/", preview_tts_voice, name="tts_preview"),
    path("quota/", get_user_quota, name="get_user_quota"),
    path("points/rules/", get_points_rules, name="get_points_rules"),
    path("synthesize-audio/", synthesize_audio, name="synthesize_audio"),
    path("audio/<int:segment_id>/generate-chapters/", generate_audio_chapters, name="generate_audio_chapters"),
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
    path(
        "audio/download/<str:segment_type>/<int:segment_id>/",
        download_audio,
        name="download_audio",
    ),
    path(
        "audio/subtitle/<str:segment_type>/<int:segment_id>/",
        download_subtitle,
        name="download_subtitle",
    ),
    path("book/<int:book_id>/update-name/", update_book_name, name="update_book_name"),
    path("book/<int:book_id>/update-pdf-type/", update_pdf_type, name="update_pdf_type"),
    path("book/<int:book_id>/detect-scanned/", detect_scanned_pdf, name="detect_scanned_pdf"),
    path("book/<int:book_id>/page-image/<int:page_number>/", get_page_image, name="get_page_image"),
    path("book/<int:book_id>/check-audio-status/", check_page_audio_status, name="check_page_audio_status"),
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
    path("dialogue/<int:script_id>/generate-chapters/", dialogue_generate_chapters, name="dialogue_generate_chapters"),
    path("dialogue/<int:script_id>/publish/", dialogue_publish, name="dialogue_publish"),
    path("dialogue/<int:script_id>/delete/", dialogue_delete, name="dialogue_delete"),
    path("dialogue/<int:script_id>/update-title/", dialogue_update_title, name="dialogue_update_title"),
    path("dialogue/<int:script_id>/update-book/", dialogue_update_book, name="dialogue_update_book"),
    
    # 对话片段管理
    path("dialogue/segment/<int:segment_id>/delete/", dialogue_segment_delete, name="dialogue_segment_delete"),
    path("dialogue/segment/<int:segment_id>/update/", dialogue_segment_update, name="dialogue_segment_update"),
    path("dialogue/segment/<int:segment_id>/preview/", dialogue_segment_preview, name="dialogue_segment_preview"),

    # AI音色推荐
    path("dialogue/<int:script_id>/ai-recommend-voices/", dialogue_ai_recommend_voices, name="dialogue_ai_recommend_voices"),

    # 任务状态查询
    path("task/<str:task_id>/status/", task_status, name="task_status"),
    
    # OCR功能路由
    path("book/<int:book_id>/ocr/page/", ocr_pdf_page, name="ocr_pdf_page"),
    path("book/<int:book_id>/ocr/batch/", ocr_pdf_pages_batch, name="ocr_pdf_pages_batch"),

    # 翻译缓存管理路由 (工作台管理员)
    path("translation-cache/", translation_cache_list, name="translation_cache_list"),
    path("translation-cache/<int:cache_id>/", translation_cache_detail, name="translation_cache_detail"),
    path("translation-cache/<int:cache_id>/delete/", translation_cache_delete, name="translation_cache_delete"),
    path("translation-cache/cleanup/", translation_cache_cleanup, name="translation_cache_cleanup"),
    path("translation-cache/stats/", translation_cache_stats_api, name="translation_cache_stats"),
    path("translation-cache/bulk-delete/", translation_cache_bulk_delete, name="translation_cache_bulk_delete"),
]
