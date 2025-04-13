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

from book2tts.tts import edge_tts_volices, edge_text_to_speech
from book2tts.edgetts import EdgeTTS

# Create your views here.
from .forms import UploadFileForm
from .models import Books, AudioSegment

from book2tts.ebook import open_ebook, ebook_toc, get_content_with_href, ebook_pages
from book2tts.pdf import open_pdf


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


def upload(request):
    if request.method == "POST":
        form = UploadFileForm(request.POST, request.FILES)

        if form.is_valid():
            instance = form.save(commit=False)
            instance.setkw(request.session.get("uid", "admin"))
            instance.save()

            return redirect(reverse("index", args=[instance.id]))
    else:
        form = UploadFileForm()
    return render(request, "upload.html", {"form": form})


def my_upload_list(request):
    uid = request.session.get("uid", "admin")
    books = Books.objects.filter(uid=uid).all()
    books = [b for b in books]

    return render(request, "my_upload_list.html", {"books": books})


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


def text_by_toc(request, book_id, name):
    name = name.replace("_", "/")
    book = get_object_or_404(Books, pk=book_id)
    texts = ""
    if book.file_type == ".pdf":
        pbook = open_pdf(book.file.path)
        texts = pbook[int(name)].get_text()
    elif book.file_type == ".epub":
        ebook = open_ebook(book.file.path)
        texts = get_content_with_href(ebook, name)

    # Check if this is an HTMX request for just the text content
    if request.headers.get('HX-Target') == 'src-text':
        return render(request, "text_content.html", {"texts": texts})
    else:
        return render(request, "text_by_toc.html", {"texts": texts})


def text_by_page(request, book_id, name):
    name = name.replace("_", "/")
    book = get_object_or_404(Books, pk=book_id)
    texts = ""

    if book.file_type == ".pdf":
        pbook = open_pdf(book.file.path)
        texts = pbook[int(name)].get_text()
    elif book.file_type == ".epub":
        ebook = open_ebook(book.file.path)
        texts = get_content_with_href(ebook, name)

    # Check if this is an HTMX request for just the text content
    if request.headers.get('HX-Target') == 'src-text':
        return render(request, "text_content.html", {"texts": texts})
    else:
        return render(request, "text_by_toc.html", {"texts": texts})


@require_http_methods(["POST"])
def reformat(request):
    texts = request.POST["texts"]
    
    # Process the text directly instead of using SSE
    # Simple text reformatting: remove extra whitespace, normalize line breaks
    lines = [line.strip() for line in texts.splitlines() if line.strip()]
    reformatted_text = "\n".join(lines)  # Double line breaks between paragraphs
    
    # Always return just the text content using text_content.html
    return render(request, "text_content.html", {"texts": reformatted_text})

def aggregated_audio_segments(request):
    # 获取当前用户的音频片段
    uid = request.session.get("uid", "admin")
    audio_segments = AudioSegment.objects.filter(uid=uid)

    # 使用字典按book聚合
    aggregated_data = defaultdict(list)
    for segment in audio_segments:
        book_data = {
            "id": segment.id,  # 添加ID字段
            "title": segment.title,
            "text": segment.text,
            "book_page": segment.book_page,
            "file_url": segment.file.url,
        }
        aggregated_data[segment.book.name].append(book_data)

    # 转换为标准字典并传递给模板
    context = {"aggregated_data": dict(aggregated_data)}
    return render(request, "aggregated_audio_segments.html", context)


def book_details_htmx(request, book_slug):
    """HTMX端点：返回特定书籍的详情视图"""
    print(f"DEBUG: book_details_htmx called with book_slug={book_slug}")
    
    # 处理特殊情况
    if not book_slug or book_slug == 'unknown':
        print("DEBUG: Invalid book slug, returning to book list")
        # 如果slug无效，返回书籍列表
        uid = request.session.get("uid", "admin")
        audio_segments = AudioSegment.objects.filter(uid=uid)
        aggregated_data = defaultdict(list)
        for segment in audio_segments:
            book_data = {
                "id": segment.id,
                "title": segment.title,
                "text": segment.text,
                "book_page": segment.book_page,
                "file_url": segment.file.url,
            }
            aggregated_data[segment.book.name].append(book_data)
        return render(request, "aggregated_audio_segments.html", {"aggregated_data": dict(aggregated_data)})
    
    # 获取当前用户的音频片段
    uid = request.session.get("uid", "admin")
    audio_segments = AudioSegment.objects.filter(uid=uid)
    
    # 先尝试直接通过书籍名称找到书籍
    book_segments = []
    book_name = None
    
    # 使用字典按book聚合
    aggregated_data = defaultdict(list)
    for segment in audio_segments:
        book_data = {
            "id": segment.id,
            "title": segment.title,
            "text": segment.text,
            "book_page": segment.book_page,
            "file_url": segment.file.url,
        }
        aggregated_data[segment.book.name].append(book_data)
        
        # 根据slug匹配书籍
        from django.utils.text import slugify
        if slugify(segment.book.name) == book_slug:
            book_name = segment.book.name
            book_segments.append(book_data)
    
    # 如果上面的方法没找到，尝试其他方法
    if not book_name:
        print(f"DEBUG: Trying alternative slug matching for '{book_slug}'")
        for name in aggregated_data.keys():
            # 使用Django的slugify函数
            from django.utils.text import slugify
            name_slug = slugify(name)
            print(f"DEBUG: Comparing '{name_slug}' with '{book_slug}'")
            if name_slug == book_slug:
                book_name = name
                book_segments = aggregated_data[name]
                break
    
    if not book_name:
        print(f"DEBUG: Book not found for slug '{book_slug}'")
        # 如果找不到书籍，返回所有书籍列表
        return render(request, "aggregated_audio_segments.html", {"aggregated_data": dict(aggregated_data)})
    
    print(f"DEBUG: Found book '{book_name}' with {len(book_segments)} segments")
    
    # 只返回特定书籍的详情部分HTML
    context = {
        "book_name": book_name,
        "segments": book_segments,
        "is_htmx": True
    }
    return render(request, "book_details_htmx.html", context)


def get_voice_list(request):
    """Get available voices from edge_tts"""
    voices = edge_tts_volices()

    return render(request, "voice_list.html", {"voices": voices})


@require_http_methods(["POST"])
def synthesize_audio(request):
    """Synthesize audio using EdgeTTS and save to AudioSegment"""
    # Get data from request
    text = request.POST.get("text")
    voice_name = request.POST.get("voice_name")
    book_id = request.POST.get("book_id")
    title = request.POST.get("title", "")
    book_page = request.POST.get("book_page", "")
    
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
        
        # Create an AudioSegment instance
        audio_segment = AudioSegment(
            book=book,
            uid=request.session.get("uid", "admin"),
            title=title,
            text=text,
            book_page=book_page
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


@csrf_exempt
@require_http_methods(["POST"])
def update_book_name(request, book_id):
    """Update the name of a book"""
    # Get the book or return 404 if not found
    book = get_object_or_404(Books, pk=book_id)
    
    # Check if the user owns this book
    if book.uid != request.session.get("uid", "admin"):
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

@csrf_exempt
@require_http_methods(["DELETE"])
def delete_audio_segment(request, segment_id):
    """Delete an audio segment by its ID"""
    # Get the audio segment or return 404 if not found
    segment = get_object_or_404(AudioSegment, pk=segment_id)
    
    # Check if the user owns this audio segment
    if segment.uid != request.session.get("uid", "admin"):
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
            remaining_segments = AudioSegment.objects.filter(book=book, uid=request.session.get("uid", "admin")).count()
            
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
