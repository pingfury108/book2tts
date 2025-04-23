import time
import hashlib
import edge_tts
import os
import tempfile
import json

from django.shortcuts import render
from django.urls import reverse
from django.shortcuts import redirect, get_object_or_404
from django.http import StreamingHttpResponse, JsonResponse, HttpResponse
from django.views.decorators.http import require_http_methods
from django.core.cache import cache
from django.views import View
from django.core.files.base import ContentFile
from django.conf import settings
from collections import defaultdict
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required

from book2tts.tts import edge_tts_volices, edge_text_to_speech
from book2tts.edgetts import EdgeTTS

# Create your views here.
from .forms import UploadFileForm
from .models import Books, AudioSegment

from book2tts.ebook import open_ebook, ebook_toc, get_content_with_href, ebook_pages
from book2tts.pdf import open_pdf

@login_required
def index(request, book_id):
    book = get_object_or_404(Books, pk=book_id)
    if book.file_type == ".pdf":
        pbook = open_pdf(book.file.path)
        return render(
            request,
            "index.html",
            {
                "book_id": book.id,
                "title": book.name,  # Always use the database book name
                "tocs": [
                    {"title": f"{toc[1]}", "href": toc[2]} for toc in pbook.get_toc()
                ],
                "pages": [
                    {"title": f"第{page.number+1}页", "href": page.number}
                    for page in pbook.pages()
                ],
            },
        )
    elif book.file_type == ".epub":
        ebook = open_ebook(book.file.path)
        return render(
            request,
            "index.html",
            {
                "book_id": book.id,
                "title": book.name,  # Always use the database book name
                "tocs": [
                    {
                        "title": toc.get("title"),
                        "href": toc.get("href").split("#")[0].replace("/", "_"),
                    }
                    for toc in ebook_toc(ebook)
                ],
                "pages": ebook_pages(ebook),
            },
        )


@login_required
def upload(request):
    if request.method == "POST":
        form = UploadFileForm(request.POST, request.FILES)

        if form.is_valid():
            instance = form.save(commit=False)
            instance.setkw(request.user)
            instance.save()

            return redirect(reverse("index", args=[instance.id]))
    else:
        form = UploadFileForm()
    return render(request, "upload.html", {"form": form})


@login_required
def my_upload_list(request):
    books = Books.objects.filter(user=request.user).all()
    books = [b for b in books]

    return render(request, "my_upload_list.html", {"books": books})


@login_required
def toc(request, book_id):
    book = get_object_or_404(Books, pk=book_id)

    if book.file_type == ".pdf":
        pbook = open_pdf(book.file.path)
        return render(
            request,
            "toc.html",
            {
                "book_id": book.id,
                "title": book.name,  # Already using database book name
                "tocs": [
                    {"title": f"{toc[1]}", "href": toc[2]} for toc in pbook.get_toc()
                ],
            },
        )
    elif book.file_type == ".epub":
        ebook = open_ebook(book.file.path)
        return render(
            request,
            "toc.html",
            {
                "book_id": book.id,
                "title": book.name,  # Use database book name instead of ebook.title
                "tocs": [
                    {"title": toc.get("title"), "href": toc.get("href")}
                    for toc in ebook_toc(ebook)
                ],
            },
        )


@login_required
def pages(request, book_id):
    book = get_object_or_404(Books, pk=book_id)
    if book.file_type == ".pdf":
        pbook = open_pdf(book.file.path)
        return render(
            request,
            "pages.html",
            {
                "book_id": book.id,
                "title": book.name,  # Already using database book name
                "pages": [
                    {"title": f"第{page.number+1}页", "href": page.number}
                    for page in pbook.pages()
                ],
            },
        )
    elif book.file_type == ".epub":
        ebook = open_ebook(book.file.path)
        return render(
            request,
            "pages.html",
            {
                "book_id": book.id,
                "title": book.name,  # Use database book name instead of ebook.title
                "pages": ebook_pages(ebook),
            },
        )


@login_required
def text_by_toc(request, book_id, name):
    name = name.replace("_", "/")
    book = get_object_or_404(Books, pk=book_id)
    texts = ""
    if book.file_type == ".pdf":
        try:
            pbook = open_pdf(book.file.path)
            texts = pbook[int(name)].get_text()
        except Exception as e:
            texts = f"Error extracting text: {str(e)}"
    elif book.file_type == ".epub":
        try:
            ebook = open_ebook(book.file.path)
            texts = get_content_with_href(ebook, name)
        except Exception as e:
            texts = f"Error extracting text: {str(e)}"

    # Check if this is an HTMX request for just the text content
    if request.headers.get('HX-Target') == 'src-text':
        return render(request, "text_content.html", {"texts": texts})
    else:
        return render(request, "text_by_toc.html", {"texts": texts})


@login_required
def text_by_page(request, book_id, name):
    book = get_object_or_404(Books, pk=book_id)
    texts = ""
    
    # Get line filtering parameters from query string
    head_cut = int(request.GET.get('head_cut', 0))  # Lines to remove from beginning (default: 0)
    tail_cut = int(request.GET.get('tail_cut', 0))  # Lines to remove from end (default: 0)
    line_count = request.GET.get('line_count')  # Total lines to keep (optional)
    if line_count:
        line_count = int(line_count)
    
    # Support multiple names separated by comma
    names = name.split(',')
    combined_texts = []
    
    for page_name in names:
        page_name = page_name.replace("_", "/")
        
        if book.file_type == ".pdf":
            try:
                pbook = open_pdf(book.file.path)
                page_text = pbook[int(page_name)].get_text()
                
                # Apply line filtering to individual page content
                if head_cut > 0 or tail_cut > 0 or line_count:
                    lines = page_text.splitlines()
                    total_lines = len(lines)
                    
                    # Calculate start and end indices
                    start_idx = min(head_cut, total_lines)
                    
                    if line_count:
                        # If line_count is specified, use it to calculate end_idx
                        end_idx = min(start_idx + line_count, total_lines)
                    else:
                        # Otherwise, remove tail_cut lines from the end
                        end_idx = max(start_idx, total_lines - tail_cut)
                    
                    # Get the filtered lines
                    filtered_lines = lines[start_idx:end_idx]
                    page_text = "\n".join(filtered_lines)
                
                combined_texts.append(page_text)
            except Exception as e:
                combined_texts.append(f"Error extracting text for page {page_name}: {str(e)}")
        elif book.file_type == ".epub":
            try:
                ebook = open_ebook(book.file.path)
                page_param = request.GET.get('page')
                if page_param:
                    href_to_use = page_param
                else:
                    href_to_use = page_name
                    
                page_text = get_content_with_href(ebook, href_to_use)
                
                # Apply line filtering to individual page content
                if head_cut > 0 or tail_cut > 0 or line_count:
                    lines = page_text.splitlines()
                    total_lines = len(lines)
                    
                    # Calculate start and end indices
                    start_idx = min(head_cut, total_lines)
                    
                    if line_count:
                        # If line_count is specified, use it to calculate end_idx
                        end_idx = min(start_idx + line_count, total_lines)
                    else:
                        # Otherwise, remove tail_cut lines from the end
                        end_idx = max(start_idx, total_lines - tail_cut)
                    
                    # Get the filtered lines
                    filtered_lines = lines[start_idx:end_idx]
                    page_text = "\n".join(filtered_lines)
                
                combined_texts.append(page_text)
            except Exception as e:
                combined_texts.append(f"Error extracting text for page {page_name}: {str(e)}")
    
    # Combine all texts without a separator
    texts = "\n\n".join(combined_texts)
    
    # Remove the global line filtering logic as it's now applied per page
    
    # Check if this is an HTMX request for just the text content
    if request.headers.get('HX-Target') == 'src-text':
        return render(request, "text_content.html", {"texts": texts})
    else:
        return render(request, "text_by_toc.html", {"texts": texts})


@login_required
@require_http_methods(["POST"])
def reformat(request):
    texts = request.POST["texts"]
    
    # Process the text directly instead of using SSE
    # Simple text reformatting: remove extra whitespace, normalize line breaks
    lines = [line.strip() for line in texts.splitlines() if line.strip()]
    reformatted_text = "\n".join(lines)  # Double line breaks between paragraphs
    
    # Always return just the text content using text_content.html
    return render(request, "text_content.html", {"texts": reformatted_text})

@login_required
def aggregated_audio_segments(request):
    # Get the current user's audio segments
    audio_segments = AudioSegment.objects.filter(user=request.user)

    # Aggregate by book
    aggregated_data = defaultdict(list)
    book_ids = {}  # Track book IDs for each book name
    
    for segment in audio_segments:
        book_data = {
            "id": segment.id,
            "title": segment.title,
            "text": segment.text,
            "book_page": segment.book_page,
            "file_url": segment.file.url,
            "published": segment.published,
            "created_at": segment.created_at
        }
        aggregated_data[segment.book.name].append(book_data)
        book_ids[segment.book.name] = segment.book.id  # Store book ID
        
    # Prepare data structure with book IDs
    books_with_ids = {}
    for book_name, segments in aggregated_data.items():
        books_with_ids[book_name] = {
            "segments": segments,
            "book_id": book_ids[book_name]  # Use book ID instead of slug
        }

    # Convert to standard dictionary and pass to template
    context = {
        "books_with_ids": books_with_ids,
        "aggregated_data": dict(aggregated_data)
    }
    return render(request, "aggregated_audio_segments.html", context)


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


@login_required
def get_voice_list(request):
    """Get available voices from edge_tts"""
    voices = edge_tts_volices()

    return render(request, "voice_list.html", {"voices": voices})


@login_required
@require_http_methods(["POST"])
def synthesize_audio(request):
    """Synthesize audio using EdgeTTS and save to AudioSegment"""
    # Get data from request
    text = request.POST.get("text")
    voice_name = request.POST.get("voice_name")
    book_id = request.POST.get("book_id")
    title = request.POST.get("title", "")
    book_page = request.POST.get("book_page", "")
    page_display_name = request.POST.get("page_display_name", "")
    audio_title = request.POST.get("audio_title", "")
    
    if not text or not voice_name or not book_id:
        return JsonResponse({"status": "error", "message": "Missing required parameters"}, status=400)
    
    # Get book
    book = get_object_or_404(Books, pk=book_id)
    
    # Create a temporary file for the audio
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
        temp_path = temp_file.name
    
    try:
        # Use EdgeTTS to synthesize the audio
        tts = EdgeTTS(voice_name=voice_name)
        success = tts.synthesize_long_text(text=text, output_file=temp_path)
        
        if not success:
            return JsonResponse({"status": "error", "message": "Failed to synthesize audio"}, status=500)
        
        # Use custom audio title if provided, otherwise use page display name or default title
        segment_title = audio_title if audio_title else (page_display_name if page_display_name else title)
        
        # Create an AudioSegment instance
        audio_segment = AudioSegment(
            book=book,
            user=request.user,
            title=segment_title,
            text=text,
            book_page=book_page,
            published=False
        )
        
        # Ensure media directory exists
        media_root = settings.MEDIA_ROOT
        upload_dir = os.path.join(media_root, 'audio_segments', time.strftime('%Y/%m/%d'))
        os.makedirs(upload_dir, exist_ok=True)
        
        # Generate a unique filename
        filename = f"audio_{book_id}_{int(time.time())}.wav"
        
        # Save the audio file to the AudioSegment
        with open(temp_path, "rb") as f:
            audio_segment.file.save(filename, ContentFile(f.read()))
        
        # Save the AudioSegment
        audio_segment.save()
        
        return JsonResponse({
            "status": "success", 
            "message": "Audio synthesized successfully",
            "audio_url": audio_segment.file.url,
            "audio_id": audio_segment.id
        })
    
    except Exception as e:
        print(f"Error in synthesize_audio: {str(e)}")
        return JsonResponse({"status": "error", "message": str(e)}, status=500)
    
    finally:
        # Clean up the temporary file
        if os.path.exists(temp_path):
            os.remove(temp_path)


@login_required
@csrf_exempt
@require_http_methods(["POST"])
def update_book_name(request, book_id):
    """Update the name of a book"""
    # Get the book or return 404 if not found
    book = get_object_or_404(Books, pk=book_id)
    
    # Check if the user owns this book
    if book.user != request.user:
        return JsonResponse({"status": "error", "message": "You don't have permission to update this book"}, status=403)
    
    try:
        # Get the new name from the request
        new_name = request.POST.get("name")
        if not new_name or new_name.strip() == "":
            return JsonResponse({"status": "error", "message": "Book name cannot be empty"}, status=400)
        
        # Update the book name
        book.name = new_name.strip()
        book.save()
        
        # Check if this is an HTMX request
        if request.headers.get('HX-Request') == 'true':
            # Return the updated input field with the new book name
            return JsonResponse({
                "name": book.name,
                "status": "success"
            })
        else:
            # For non-HTMX requests, return JSON
            return JsonResponse({"status": "success", "message": "Book name updated successfully", "name": book.name})
    
    except Exception as e:
        print(f"Error in update_book_name: {str(e)}")
        if request.headers.get('HX-Request') == 'true':
            # For HTMX requests, return error message
            return HttpResponse(f"更新失败: {str(e)}", status=500)
        else:
            # For non-HTMX requests, return JSON
            return JsonResponse({"status": "error", "message": str(e)}, status=500)

@login_required
@csrf_exempt
@require_http_methods(["DELETE"])
def delete_audio_segment(request, segment_id):
    """Delete an audio segment by its ID"""
    # Get the audio segment or return 404 if not found
    segment = get_object_or_404(AudioSegment, pk=segment_id)
    
    # Check if the user owns this audio segment
    if segment.user != request.user:
        return JsonResponse({"status": "error", "message": "You don't have permission to delete this audio segment"}, status=403)
    
    try:
        # Get the file path to delete the file from storage
        file_path = segment.file.path
        
        # Delete the audio segment from the database
        segment.delete()
        
        # Delete the file from storage if it exists
        if os.path.exists(file_path):
            os.remove(file_path)
        
        # 检查是否是HTMX请求
        if request.headers.get('HX-Request') == 'true':
            # 检查是否是该书籍的最后一个音频片段
            book = segment.book
            remaining_segments = AudioSegment.objects.filter(book=book, user=request.user).count()
            
            if remaining_segments == 0:
                # 如果是最后一个片段，返回空状态HTML
                empty_state_html = '''
                <div class="alert alert-info shadow-lg" data-segment-id="{segment_id}">
                    <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" class="stroke-current shrink-0 w-6 h-6">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>
                    </svg>
                    <span>该书籍下没有任何音频片段。</span>
                </div>
                '''.format(segment_id=segment_id)
                return HttpResponse(empty_state_html)
            else:
                # 否则返回空内容，让元素被删除
                return HttpResponse(status=200)
        else:
            # 对于非HTMX请求，返回JSON响应
            return JsonResponse({"status": "success", "message": "Audio segment deleted successfully"})
    
    except Exception as e:
        print(f"Error in delete_audio_segment: {str(e)}")
        if request.headers.get('HX-Request') == 'true':
            # 对于HTMX请求，返回错误消息
            return HttpResponse(f"删除失败: {str(e)}", status=500)
        else:
            # 对于非HTMX请求，返回JSON响应
            return JsonResponse({"status": "error", "message": str(e)}, status=500)

@login_required
@csrf_exempt
@require_http_methods(["POST"])
def toggle_publish_audio_segment(request, segment_id):
    """Toggle the published state of an audio segment"""
    # Get the audio segment or return 404 if not found
    segment = get_object_or_404(AudioSegment, pk=segment_id)
    
    # Check if the user owns this audio segment
    if segment.user != request.user:
        return JsonResponse({"status": "error", "message": "You don't have permission to modify this audio segment"}, status=403)
    
    try:
        # Toggle the published state
        segment.published = not segment.published
        segment.save()
        
        # Check if this is an HTMX request
        if request.headers.get('HX-Request') == 'true':
            # Return the updated button based on the new state
            if segment.published:
                button_html = '''
                <button class="btn btn-warning flex-1" 
                        title="取消发布"
                        hx-post="/workbench/audio/publish/{{ segment.id }}/"
                        hx-target="this" 
                        hx-swap="outerHTML">
                    <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M18.364 18.364A9 9 0 005.636 5.636m12.728 12.728A9 9 0 015.636 5.636m12.728 12.728L5.636 5.636" />
                    </svg>
                    取消发布
                </button>
                '''.replace('{{ segment.id }}', str(segment_id))
            else:
                button_html = '''
                <button class="btn btn-success flex-1" 
                        title="发布"
                        hx-post="/workbench/audio/publish/{{ segment.id }}/"
                        hx-target="this" 
                        hx-swap="outerHTML">
                    <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                    发布
                </button>
                '''.replace('{{ segment.id }}', str(segment_id))
            
            return HttpResponse(button_html)
        else:
            # For non-HTMX requests, return JSON
            return JsonResponse({
                "status": "success", 
                "message": f"Audio segment {'published' if segment.published else 'unpublished'} successfully",
                "published": segment.published
            })
    
    except Exception as e:
        print(f"Error in toggle_publish_audio_segment: {str(e)}")
        if request.headers.get('HX-Request') == 'true':
            # For HTMX requests, return error message
            return HttpResponse(f"操作失败: {str(e)}", status=500)
        else:
            # For non-HTMX requests, return JSON
            return JsonResponse({"status": "error", "message": str(e)}, status=500)
