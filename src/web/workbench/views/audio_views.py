import os
import time
import tempfile
from collections import defaultdict

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse, HttpResponse
from django.core.files.base import ContentFile
from django.conf import settings

from ..models import Books, AudioSegment
from book2tts.tts import edge_tts_volices
from book2tts.edgetts import EdgeTTS
from book2tts.audio_utils import get_audio_duration, estimate_audio_duration_from_text
from home.models import UserQuota, OperationRecord


def get_client_ip(request):
    """获取客户端IP地址"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def get_user_agent(request):
    """获取用户代理"""
    return request.META.get('HTTP_USER_AGENT', '')


@login_required
def aggregated_audio_segments(request):
    """Display aggregated audio segments grouped by book"""
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
def get_voice_list(request):
    """Get available voices from edge_tts"""
    voices = edge_tts_volices()
    return render(request, "voice_list.html", {"voices": voices})


@login_required
def get_user_quota(request):
    """Get user quota information"""
    user_quota, created = UserQuota.objects.get_or_create(user=request.user)
    
    # Calculate quota display information
    remaining_seconds = user_quota.remaining_audio_duration
    hours = remaining_seconds // 3600
    minutes = (remaining_seconds % 3600) // 60
    seconds = remaining_seconds % 60
    
    # Calculate percentage (based on default 3600 seconds = 1 hour)
    default_quota = 3600
    percentage = min(100, (remaining_seconds * 100) / default_quota)
    
    # Determine quota status and color
    if remaining_seconds > 1800:  # More than 30 minutes
        status_class = "text-success"
        status_icon = "✅"
        progress_class = "bg-success"
    elif remaining_seconds > 300:  # More than 5 minutes
        status_class = "text-warning"
        status_icon = "⚠️"
        progress_class = "bg-warning"
    else:  # Less than 5 minutes
        status_class = "text-error"
        status_icon = "❌"
        progress_class = "bg-error"
    
    context = {
        "user_quota": user_quota,
        "remaining_seconds": remaining_seconds,
        "hours": hours,
        "minutes": minutes,
        "seconds": seconds,
        "status_class": status_class,
        "status_icon": status_icon,
        "progress_class": progress_class,
        "percentage": round(percentage, 1),
        "is_over_quota": remaining_seconds > default_quota,
    }
    
    return render(request, "quota_info.html", context)


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
    
    # Get or create user quota
    user_quota, created = UserQuota.objects.get_or_create(user=request.user)
    
    # Estimate audio duration from text BEFORE synthesis
    estimated_duration_seconds = estimate_audio_duration_from_text(text)
    
    # Check if user has enough quota BEFORE synthesis
    if not user_quota.can_create_audio(estimated_duration_seconds):
        # 记录配额不足的操作
        OperationRecord.objects.create(
            user=request.user,
            operation_type='audio_create',
            operation_object=f'{book.name} - {title or page_display_name}',
            operation_detail=f'音频合成失败：配额不足。预估需要 {estimated_duration_seconds} 秒，剩余 {user_quota.remaining_audio_duration} 秒',
            status='failed',
            metadata={
                'book_id': book_id,
                'book_name': book.name,
                'estimated_duration': estimated_duration_seconds,
                'remaining_quota': user_quota.remaining_audio_duration,
                'text_length': len(text),
                'voice_name': voice_name,
                'error_reason': 'insufficient_quota'
            },
            ip_address=get_client_ip(request),
            user_agent=get_user_agent(request)
        )
        return JsonResponse({
            "status": "error", 
            "message": f"配额不足。预估需要 {estimated_duration_seconds} 秒，剩余 {user_quota.remaining_audio_duration} 秒"
        }, status=400)
    
    # Create a temporary file for the audio
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
        temp_path = temp_file.name
    
    try:
        # Use EdgeTTS to synthesize the audio
        tts = EdgeTTS(voice_name=voice_name)
        success = tts.synthesize_long_text(text=text, output_file=temp_path)
        
        if not success:
            # 记录合成失败的操作
            OperationRecord.objects.create(
                user=request.user,
                operation_type='audio_create',
                operation_object=f'{book.name} - {title or page_display_name}',
                operation_detail=f'音频合成失败：EdgeTTS合成失败',
                status='failed',
                metadata={
                    'book_id': book_id,
                    'book_name': book.name,
                    'estimated_duration': estimated_duration_seconds,
                    'text_length': len(text),
                    'voice_name': voice_name,
                    'error_reason': 'tts_synthesis_failed'
                },
                ip_address=get_client_ip(request),
                user_agent=get_user_agent(request)
            )
            return JsonResponse({"status": "error", "message": "Failed to synthesize audio"}, status=500)
        
        # Get actual audio duration using utility function
        actual_duration_seconds = get_audio_duration(temp_path, text)
        
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
        
        # Refresh user quota to get latest data before deduction
        user_quota.refresh_from_db()
        
        # Force deduct user quota (consume actual audio duration, reduce to 0 if insufficient)
        user_quota.force_consume_audio_duration(actual_duration_seconds)
        
        # 记录成功的音频创建操作
        OperationRecord.objects.create(
            user=request.user,
            operation_type='audio_create',
            operation_object=f'{book.name} - {segment_title}',
            operation_detail=f'成功创建音频片段：{segment_title}，时长 {actual_duration_seconds} 秒，消耗配额 {actual_duration_seconds} 秒',
            status='success',
            metadata={
                'book_id': book_id,
                'book_name': book.name,
                'audio_segment_id': audio_segment.id,
                'actual_duration': actual_duration_seconds,
                'estimated_duration': estimated_duration_seconds,
                'consumed_quota': actual_duration_seconds,
                'remaining_quota_after': user_quota.remaining_audio_duration,
                'text_length': len(text),
                'voice_name': voice_name,
                'file_path': audio_segment.file.name,
                'file_size': os.path.getsize(temp_path) if os.path.exists(temp_path) else 0
            },
            ip_address=get_client_ip(request),
            user_agent=get_user_agent(request)
        )
        
        return JsonResponse({
            "status": "success", 
            "message": "Audio synthesized successfully",
            "audio_url": audio_segment.file.url,
            "audio_id": audio_segment.id,
            "audio_duration": actual_duration_seconds,
            "remaining_quota": user_quota.remaining_audio_duration
        })
    
    except Exception as e:
        # 记录异常的操作
        OperationRecord.objects.create(
            user=request.user,
            operation_type='audio_create',
            operation_object=f'{book.name} - {title or page_display_name}',
            operation_detail=f'音频合成异常：{str(e)}',
            status='failed',
            metadata={
                'book_id': book_id,
                'book_name': book.name,
                'estimated_duration': estimated_duration_seconds,
                'text_length': len(text),
                'voice_name': voice_name,
                'error_reason': 'exception',
                'exception_message': str(e)
            },
            ip_address=get_client_ip(request),
            user_agent=get_user_agent(request)
        )
        print(f"Error in synthesize_audio: {str(e)}")
        return JsonResponse({"status": "error", "message": str(e)}, status=500)
    
    finally:
        # Clean up the temporary file
        if os.path.exists(temp_path):
            os.remove(temp_path)


@login_required
@csrf_exempt
@require_http_methods(["DELETE"])
def delete_audio_segment(request, segment_id):
    """Delete an audio segment by its ID"""
    # Get the audio segment or return 404 if not found
    segment = get_object_or_404(AudioSegment, pk=segment_id)
    
    # Check if the user owns this audio segment
    if segment.user != request.user:
        # 记录权限不足的操作
        OperationRecord.objects.create(
            user=request.user,
            operation_type='audio_delete',
            operation_object=f'音频片段ID: {segment_id}',
            operation_detail=f'删除音频片段失败：权限不足，尝试删除不属于自己的音频片段',
            status='failed',
            metadata={
                'segment_id': segment_id,
                'segment_owner': segment.user.username,
                'error_reason': 'permission_denied'
            },
            ip_address=get_client_ip(request),
            user_agent=get_user_agent(request)
        )
        return JsonResponse({"status": "error", "message": "You don't have permission to delete this audio segment"}, status=403)
    
    # 保存删除前的信息用于记录
    segment_title = segment.title
    book_name = segment.book.name
    book_id = segment.book.id
    
    try:
        # Get the file path and calculate audio duration before deletion
        file_path = segment.file.path if segment.file else None
        
        # Get audio duration to return quota using utility function
        # Must do this BEFORE deleting the file
        audio_duration_seconds = get_audio_duration(file_path, segment.text)
        
        # Store book reference before deletion
        book = segment.book
        
        # Delete the audio segment from the database first
        segment.delete()
        
        # Delete the file from storage if it exists
        if file_path and os.path.exists(file_path):
            os.remove(file_path)
        
        # Return quota to user
        if audio_duration_seconds > 0:
            user_quota, created = UserQuota.objects.get_or_create(user=request.user)
            user_quota.add_audio_duration(audio_duration_seconds)
        
        # 记录成功的删除操作
        OperationRecord.objects.create(
            user=request.user,
            operation_type='audio_delete',
            operation_object=f'{book_name} - {segment_title}',
            operation_detail=f'成功删除音频片段：{segment_title}，时长 {audio_duration_seconds} 秒，返还配额 {audio_duration_seconds} 秒',
            status='success',
            metadata={
                'segment_id': segment_id,
                'book_id': book_id,
                'book_name': book_name,
                'segment_title': segment_title,
                'audio_duration': audio_duration_seconds,
                'returned_quota': audio_duration_seconds,
                'file_path': file_path
            },
            ip_address=get_client_ip(request),
            user_agent=get_user_agent(request)
        )
        
        # 检查是否是HTMX请求
        if request.headers.get('HX-Request') == 'true':
            # 检查是否是该书籍的最后一个音频片段
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
            return JsonResponse({
                "status": "success", 
                "message": "Audio segment deleted successfully",
                "returned_quota": audio_duration_seconds
            })
    
    except Exception as e:
        # 记录删除失败的操作
        OperationRecord.objects.create(
            user=request.user,
            operation_type='audio_delete',
            operation_object=f'{book_name} - {segment_title}',
            operation_detail=f'删除音频片段异常：{str(e)}',
            status='failed',
            metadata={
                'segment_id': segment_id,
                'book_id': book_id,
                'book_name': book_name,
                'segment_title': segment_title,
                'error_reason': 'exception',
                'exception_message': str(e)
            },
            ip_address=get_client_ip(request),
            user_agent=get_user_agent(request)
        )
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