from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

from ..models import Books, AudioSegment, DialogueScript
from .audio_views import get_unified_audio_content


@login_required
def book_details_htmx(request, book_id):
    """HTMX endpoint: returns details view for a specific book with pagination"""
    # Handle invalid book_id
    if not book_id or book_id == '0':
        return redirect('aggregated_audio_segments')
    
    try:
        # Get the book by ID
        target_book = Books.objects.get(id=book_id)
    except Books.DoesNotExist:
        return redirect('aggregated_audio_segments')
    
    # Get page number from request
    page = request.GET.get('page', 1)
    
    # Get page size from request (default: 10, max: 50)
    try:
        page_size = int(request.GET.get('page_size', 10))
        page_size = min(max(page_size, 5), 50)  # Limit between 5 and 50
    except (ValueError, TypeError):
        page_size = 10
    
    # 使用统一的音频内容获取函数，包含AudioSegment和DialogueScript
    all_audio_items = get_unified_audio_content(
        user=request.user, 
        book=target_book, 
        published_only=False  # 显示所有音频，包括未发布的
    )
    
    # Create paginator for unified audio content
    paginator = Paginator(all_audio_items, page_size)
    
    try:
        segments_page = paginator.page(page)
    except PageNotAnInteger:
        # If page is not an integer, deliver first page
        segments_page = paginator.page(1)
    except EmptyPage:
        # If page is out of range, deliver last page
        segments_page = paginator.page(paginator.num_pages)
    
    # Convert to template-friendly format
    segments = []
    for item in segments_page:
        segment_data = {
            'id': item['id'],
            'type': item['type'],  # 'audio_segment' or 'dialogue_script'
            'title': item['title'],
            'text': item['text'],
            'book_page': item['book_page'],
            'file_url': item['file_url'],
            'published': item['published'],
            'created_at': item['created_at'],
            'updated_at': item['updated_at'],
        }
        # 添加对话脚本特有的字段
        if item['type'] == 'dialogue_script':
            segment_data.update({
                'audio_duration': item.get('audio_duration'),
                'speakers': item.get('speakers', []),
                'segment_count': item.get('segment_count', 0),
                'original_text': item.get('original_text', '')  # 添加原始文本字段
            })
        segments.append(segment_data)
    
    # Return only the specific book's details with pagination info
    context = {
        "book_name": target_book.name,
        "book_id": target_book.id,
        "segments": segments,
        "page_obj": segments_page,
        "paginator": paginator,
        "is_htmx": True,
        "total_segments": paginator.count,
        "page_size": page_size,
        "page_size_options": [5, 10, 20, 30, 50],
    }
    return render(request, "book_details_htmx.html", context) 