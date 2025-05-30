from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

from ..models import Books, AudioSegment


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
    
    # Get segments for this specific book, ordered by updated_at descending
    # Use select_related to optimize database queries
    book_segments_qs = AudioSegment.objects.filter(
        user=request.user,
        book=target_book
    ).select_related('book').order_by('-updated_at')
    
    # Create paginator
    paginator = Paginator(book_segments_qs, page_size)
    
    try:
        segments_page = paginator.page(page)
    except PageNotAnInteger:
        # If page is not an integer, deliver first page
        segments_page = paginator.page(1)
    except EmptyPage:
        # If page is out of range, deliver last page
        segments_page = paginator.page(paginator.num_pages)
    
    # Convert segments to include file URLs
    segments = []
    for segment in segments_page:
        segment_data = {
            'id': segment.id,
            'title': segment.title,
            'text': segment.text,
            'book_page': segment.book_page,
            'file_url': segment.file.url if segment.file else None,
            'published': segment.published,
            'created_at': segment.created_at,
            'updated_at': segment.updated_at,
        }
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