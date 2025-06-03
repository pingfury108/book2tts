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
from django.db import transaction

from ..models import Books, AudioSegment
from ..tasks import synthesize_audio_task
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
    # Get the current user's audio segments, ordered by created_at descending
    audio_segments = AudioSegment.objects.filter(user=request.user).order_by('-created_at')

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
    """使用异步任务合成音频"""
    # 获取请求数据
    text = request.POST.get("text")
    voice_name = request.POST.get("voice_name")
    book_id = request.POST.get("book_id")
    title = request.POST.get("title", "")
    book_page = request.POST.get("book_page", "")
    page_display_name = request.POST.get("page_display_name", "")
    audio_title = request.POST.get("audio_title", "")
    
    if not text or not voice_name or not book_id:
        return JsonResponse({"status": "error", "message": "Missing required parameters"}, status=400)
    
    # 验证书籍存在
    book = get_object_or_404(Books, pk=book_id)
    
    # 获取或创建用户配额
    user_quota, created = UserQuota.objects.get_or_create(user=request.user)
    
    # 估算音频时长来进行前置检查
    estimated_duration_seconds = estimate_audio_duration_from_text(text)
    
    # 预检查配额（提前告知用户配额不足）
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
    
    try:
        # 启动异步任务
        task = synthesize_audio_task.delay(
            user_id=request.user.id,
            text=text,
            voice_name=voice_name,
            book_id=book_id,
            title=title,
            book_page=book_page,
            page_display_name=page_display_name,
            audio_title=audio_title,
            ip_address=get_client_ip(request),
            user_agent=get_user_agent(request)
        )
        
        # 返回任务ID供前端轮询状态
        return JsonResponse({
            "status": "started", 
            "message": "音频合成任务已启动",
            "task_id": task.id
        })
    
    except Exception as e:
        # 记录启动任务失败的操作
        OperationRecord.objects.create(
            user=request.user,
            operation_type='audio_create',
            operation_object=f'{book.name} - {title or page_display_name}',
            operation_detail=f'启动音频合成任务失败：{str(e)}',
            status='failed',
            metadata={
                'book_id': book_id,
                'book_name': book.name,
                'estimated_duration': estimated_duration_seconds,
                'text_length': len(text),
                'voice_name': voice_name,
                'error_reason': 'task_start_failed',
                'exception_message': str(e)
            },
            ip_address=get_client_ip(request),
            user_agent=get_user_agent(request)
        )
        print(f"Error starting synthesize_audio task: {str(e)}")
        return JsonResponse({"status": "error", "message": f"启动音频合成任务失败：{str(e)}"}, status=500)


@login_required
@require_http_methods(["GET"])
def check_task_status(request, task_id):
    """检查Celery任务状态"""
    from celery.result import AsyncResult
    
    try:
        # 获取任务结果
        task_result = AsyncResult(task_id)
        
        if task_result.state == 'PENDING':
            # 任务还在等待执行
            response = {
                'status': 'pending',
                'message': '任务等待执行中...'
            }
        elif task_result.state == 'PROCESSING':
            # 任务正在执行
            response = {
                'status': 'processing',
                'message': task_result.info.get('message', '正在处理...')
            }
        elif task_result.state == 'SUCCESS':
            # 任务成功完成
            result = task_result.info
            response = {
                'status': 'success',
                'message': result.get('message', '音频合成完成'),
                'audio_url': result.get('audio_url'),
                'audio_id': result.get('audio_id'),
                'audio_duration': result.get('audio_duration'),
                'remaining_quota': result.get('remaining_quota')
            }
        elif task_result.state == 'FAILURE':
            # 任务失败
            error_info = task_result.info or {}
            response = {
                'status': 'failure',
                'message': error_info.get('message', '音频合成失败'),
                'error': error_info.get('error', str(task_result.info))
            }
        else:
            # 其他状态
            response = {
                'status': task_result.state.lower(),
                'message': f'任务状态：{task_result.state}'
            }
        
        return JsonResponse(response)
    
    except Exception as e:
        print(f"Error checking task status: {str(e)}")
        return JsonResponse({
            'status': 'error',
            'message': f'检查任务状态失败：{str(e)}'
        }, status=500)


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