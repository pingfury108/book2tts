from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required

from ..models import Books, AudioSegment


@login_required
def book_details_htmx(request, book_id):
    """HTMX endpoint: returns details view for a specific book"""
    # Handle invalid book_id
    if not book_id or book_id == '0':
        return redirect('aggregated_audio_segments')
    
    try:
        # Get the book by ID
        target_book = Books.objects.get(id=book_id)
    except Books.DoesNotExist:
        return redirect('aggregated_audio_segments')
    
    # Get segments for this specific book
    book_segments = AudioSegment.objects.filter(
        user=request.user,
        book=target_book
    ).values('id', 'title', 'text', 'book_page', 'file', 'published', 'created_at', 'updated_at')
    
    # Convert file IDs to URLs
    segments = []
    for segment in book_segments:
        segment_data = dict(segment)
        segment_data['file_url'] = AudioSegment.objects.get(id=segment['id']).file.url
        segments.append(segment_data)
    
    # Return only the specific book's details
    context = {
        "book_name": target_book.name,
        "segments": segments,
        "is_htmx": True
    }
    return render(request, "book_details_htmx.html", context) 