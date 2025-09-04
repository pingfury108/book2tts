# Import all views to maintain backward compatibility
from .book_views import (
    index,
    upload,
    my_upload_list,
    toc,
    pages,
    text_by_toc,
    text_by_page,
    update_book_name,
    update_pdf_type,
    detect_scanned_pdf,
    get_page_image,
    check_page_audio_status,
    delete_book,
)

from .audio_views import (
    aggregated_audio_segments,
    get_voice_list,
    get_user_quota,
    get_points_rules,
    synthesize_audio,
    check_task_status,
    delete_audio_segment,
    toggle_publish_audio_segment,
)

from .text_views import (
    reformat,
    format_text_stream,
)

from .htmx_views import (
    book_details_htmx,
)

# Export all views for easy import
__all__ = [
    # Book views
    'index',
    'upload',
    'my_upload_list',
    'toc',
    'pages',
    'text_by_toc',
    'text_by_page',
    'update_book_name',
    'update_pdf_type',
    'detect_scanned_pdf',
    'get_page_image',
    'check_page_audio_status',
    'delete_book',
    
    # Audio views
    'aggregated_audio_segments',
    'get_voice_list',
    'get_user_quota',
    'get_points_rules',
    'synthesize_audio',
    'check_task_status',
    'delete_audio_segment',
    'toggle_publish_audio_segment',
    
    # Text views
    'reformat',
    'format_text_stream',
    
    # HTMX views
    'book_details_htmx',
] 