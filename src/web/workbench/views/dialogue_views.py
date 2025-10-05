import json
import os
import asyncio
import tempfile
from typing import Dict, Any
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods, require_POST
from django.core.paginator import Paginator
from django.contrib import messages
from django.conf import settings

# Import our models
from ..models import Books, DialogueScript, DialogueSegment, UserTask, TTSProviderConfig

# Import dialogue services
import sys
sys.path.append(os.path.join(settings.BASE_DIR, 'src'))
from book2tts.dialogue_service import DialogueService
from book2tts.llm_service import LLMService
from book2tts.tts import edge_tts_volices, azure_text_to_speech
from book2tts.edgetts import EdgeTTS

# Import voice recommendation service
from ..services.voice_recommendation_service import VoiceRecommendationService

@login_required
def dialogue_list(request):
    """对话脚本列表页面"""
    scripts = DialogueScript.objects.filter(user=request.user).order_by('-created_at')
    
    # 分页
    paginator = Paginator(scripts, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'dialogue_list.html', {
        'page_obj': page_obj,
        'scripts': page_obj.object_list
    })

@login_required
def dialogue_create(request):
    """创建对话脚本页面"""
    if request.method == 'GET':
        books = Books.objects.filter(user=request.user).order_by('-created_at')
        return render(request, 'dialogue_create.html', {
            'books': books
        })
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)

@login_required
@csrf_exempt
@require_POST
def dialogue_segment_preview(request, segment_id):
    """同步生成单个对话片段的预览音频并直接返回音频数据"""
    try:
        segment = get_object_or_404(DialogueSegment, id=segment_id, script__user=request.user)
        text = (segment.utterance or '').strip()

        if not text:
            return JsonResponse({'success': False, 'error': '该片段没有可用内容'}, status=400)

        voice_config = segment.script.voice_settings.get(segment.speaker, {})

        default_provider = TTSProviderConfig.get_default_provider()
        provider = voice_config.get('provider') or default_provider or 'edge_tts'
        voice_name = voice_config.get('voice_name')

        if not voice_name:
            return JsonResponse({'success': False, 'error': '该片段尚未配置音色'}, status=400)

        temp_file = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
        temp_path = temp_file.name
        temp_file.close()

        audio_bytes = b''

        try:
            if provider == 'edge_tts':

                async def _synthesize():
                    tts = EdgeTTS(voice_name=voice_name)
                    return await tts.synthesize_with_subtitles_v2(
                        text=text,
                        output_file=temp_path,
                        subtitle_file=None
                    )

                try:
                    result = asyncio.run(_synthesize())
                except RuntimeError:
                    loop = asyncio.new_event_loop()
                    try:
                        asyncio.set_event_loop(loop)
                        result = loop.run_until_complete(_synthesize())
                    finally:
                        asyncio.set_event_loop(None)
                        loop.close()

                if not result.get('success'):
                    raise RuntimeError('音频生成失败，请稍后重试')

            elif provider == 'azure':
                azure_key = getattr(settings, 'AZURE_KEY', None) or os.getenv('AZURE_KEY')
                azure_region = getattr(settings, 'AZURE_REGION', None) or os.getenv('AZURE_REGION')

                if not azure_key or not azure_region:
                    raise RuntimeError('Azure 配置缺失，无法生成试听音频')

                azure_text_to_speech(
                    key=azure_key,
                    region=azure_region,
                    text=text,
                    output_file=temp_path,
                    voice_name=voice_name,
                )
            else:
                raise RuntimeError('当前音色暂未支持预览')

            if not os.path.exists(temp_path) or os.path.getsize(temp_path) == 0:
                raise RuntimeError('音频生成失败，请稍后重试')

            with open(temp_path, 'rb') as audio_file:
                audio_bytes = audio_file.read()

        finally:
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except OSError:
                    pass

        if not audio_bytes:
            return JsonResponse({'success': False, 'error': '预览音频生成失败，请稍后重试'}, status=500)

        response = HttpResponse(audio_bytes, content_type='audio/wav')
        response['Content-Disposition'] = 'inline; filename="segment_preview.wav"'
        response['Content-Length'] = str(len(audio_bytes))
        return response

    except Exception as e:
        return JsonResponse({'success': False, 'error': f'预览生成失败: {str(e)}'}, status=400)

def dialogue_convert_text(request):
    """将文本转换为对话脚本的API接口（异步版本）"""
    try:
        data = json.loads(request.body)
        text = data.get('text', '').strip()
        title = data.get('title', '').strip()
        book_id = data.get('book_id')
        custom_prompt = data.get('custom_prompt', '').strip()
        
        if not text:
            return JsonResponse({'success': False, 'error': '文本内容不能为空'})
        
        if not title:
            title = f"对话脚本 - {text[:50]}..."
        
        # 创建异步任务
        from ..tasks import convert_text_to_dialogue_task
        
        task_result = convert_text_to_dialogue_task.delay(
            user_id=request.user.id,
            text=text,
            title=title,
            book_id=book_id,
            custom_prompt=custom_prompt if custom_prompt else None
        )
        
        # 创建用户任务记录
        user_task = UserTask.objects.create(
            user=request.user,
            task_id=task_result.id,
            task_type='dialogue_text_conversion',
            book=Books.objects.get(id=book_id) if book_id else None,
            title=f'对话转换: {title}',
            status='pending',
            metadata={
                'text_length': len(text),
                'title': title,
                'book_id': book_id,
                'has_custom_prompt': bool(custom_prompt)
            }
        )
        
        return JsonResponse({
            'success': True,
            'task_id': user_task.task_id,
            'message': '对话转换任务已提交，正在后台处理...'
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': '无效的JSON数据'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': f'任务提交失败: {str(e)}'})

@login_required
def dialogue_detail(request, script_id):
    """对话脚本详情页面"""
    script = get_object_or_404(DialogueScript, id=script_id, user=request.user)
    segments = script.segments.all().order_by('sequence')

    # 获取用户的书籍列表
    books = Books.objects.filter(user=request.user).order_by('name')

    # 获取可用音色列表，与工作台保持一致
    voices = edge_tts_volices() or []
    available_voices = [
        {
            'value': voice,
            'name': voice,
        }
        for voice in voices
    ]

    voice_settings = script.voice_settings
    default_provider = TTSProviderConfig.get_default_provider()

    return render(request, 'dialogue_detail.html', {
        'script': script,
        'segments': segments,
        'books': books,
        'available_voices_json': json.dumps(available_voices),
        'voice_settings_json': json.dumps(voice_settings),
        'voice_settings': voice_settings,
        'default_provider': default_provider,
        'speakers': script.speakers,
        'speakers_json': json.dumps(script.speakers),
    })

@login_required
@csrf_exempt
@require_POST
def dialogue_configure_voices(request, script_id):
    """配置对话脚本的音色设置"""
    try:
        script = get_object_or_404(DialogueScript, id=script_id, user=request.user)
        data = json.loads(request.body)
        voice_mapping = data.get('voice_mapping', {})
        script_data = script.script_data or {}
        voice_settings = script.voice_settings.copy()
        updated = False
        default_provider = TTSProviderConfig.get_default_provider()

        for speaker, voice_config in voice_mapping.items():
            voice_name = (voice_config.get('voice_name') or '').strip()

            if voice_name:
                new_config = {
                    'provider': default_provider,
                    'voice_name': voice_name,
                }
                if voice_settings.get(speaker) != new_config:
                    voice_settings[speaker] = new_config
                    updated = True
            elif speaker in voice_settings:
                voice_settings.pop(speaker)
                updated = True

        if updated:
            script_data['voice_settings'] = voice_settings
            script.script_data = script_data
            script.save(update_fields=['script_data', 'updated_at'])
        
        return JsonResponse({
            'success': True,
            'message': '音色配置已保存'
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': '无效的JSON数据'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': f'配置保存失败: {str(e)}'})

@login_required
@csrf_exempt
@require_POST
def dialogue_generate_audio(request, script_id):
    """生成对话音频的API接口"""
    try:
        script = get_object_or_404(DialogueScript, id=script_id, user=request.user)
        
        # 检查是否已配置音色
        segments = script.segments.all()
        configured_voices = script.voice_settings
        default_provider = TTSProviderConfig.get_default_provider()

        voice_mapping: Dict[str, Dict[str, str]] = {}
        for segment in segments:
            speaker = segment.speaker
            config = configured_voices.get(speaker, {}) if configured_voices else {}

            provider = config.get('provider') or default_provider or 'edge_tts'
            voice_name = config.get('voice_name')

            if not voice_name:
                return JsonResponse({
                    'success': False,
                    'error': f'说话者 "{speaker}" 尚未配置音色'
                })

            voice_mapping[speaker] = {
                'provider': provider,
                'voice_name': voice_name
            }

        # 创建异步任务
        from ..tasks import generate_dialogue_audio_task

        task_result = generate_dialogue_audio_task.delay(
            script_id=script.id,
            voice_mapping=voice_mapping
        )
        
        # 创建用户任务记录
        user_task = UserTask.objects.create(
            user=request.user,
            task_id=task_result.id,
            task_type='dialogue_audio_synthesis',
            book=script.book,
            title=f'对话音频生成: {script.title}',
            status='pending',
            metadata={
                'script_id': script.id,
                'speakers': list(voice_mapping.keys())
            }
        )
        
        return JsonResponse({
            'success': True,
            'task_id': user_task.task_id,
            'message': '音频生成任务已开始，请在任务队列中查看进度'
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': '无效的JSON数据'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': f'任务创建失败: {str(e)}'})


@login_required
@require_POST
def dialogue_generate_chapters(request, script_id):
    """触发对话脚本章节生成任务"""
    script = get_object_or_404(DialogueScript, id=script_id, user=request.user)

    try:
        payload = json.loads(request.body or '{}')
    except json.JSONDecodeError:
        payload = {}

    force = bool(payload.get('force', False))

    if not script.subtitle_file or not script.subtitle_file.name:
        return JsonResponse({'success': False, 'error': '该脚本尚无字幕文件，无法生成章节'}, status=400)

    from ..tasks import generate_chapters_task

    task_result = generate_chapters_task.delay('dialogue', script.id, force)

    UserTask.objects.create(
        user=request.user,
        task_id=task_result.id,
        task_type='chapter_generation',
        book=script.book,
        title=f'章节生成：{script.title}',
        status='pending',
        metadata={
            'segment_type': 'dialogue',
            'segment_id': script.id,
            'force': force,
        }
    )

    return JsonResponse({
        'success': True,
        'task_id': task_result.id,
        'message': '章节生成任务已提交'
    })

@login_required
def task_status(request, task_id):
    """查询任务状态的API接口"""
    try:
        user_task = get_object_or_404(UserTask, task_id=task_id, user=request.user)
        
        return JsonResponse({
            'success': True,
            'task': {
                'task_id': user_task.task_id,
                'task_type': user_task.task_type,
                'status': user_task.status,
                'title': user_task.title,
                'progress_message': user_task.progress_message,
                'error_message': user_task.error_message,
                'result_data': user_task.result_data,
                'created_at': user_task.created_at.isoformat(),
                'updated_at': user_task.updated_at.isoformat(),
                'completed_at': user_task.completed_at.isoformat() if user_task.completed_at else None,
                'metadata': user_task.metadata
            }
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@login_required
@require_POST
def dialogue_publish(request, script_id):
    """发布对话音频到成品"""
    try:
        script = get_object_or_404(DialogueScript, id=script_id, user=request.user)
        
        if not script.audio_file:
            messages.error(request, '该对话脚本尚未生成音频，无法发布')
            return redirect('dialogue_detail', script_id=script.id)
        
        script.published = True
        script.save()
        
        messages.success(request, f'对话音频 "{script.title}" 已发布到成品')
        return redirect('dialogue_detail', script_id=script.id)
        
    except Exception as e:
        messages.error(request, f'发布失败: {str(e)}')
        return redirect('dialogue_detail', script_id=script.id)

@login_required
@csrf_exempt
@require_POST
def dialogue_delete(request, script_id):
    """删除对话脚本"""
    try:
        script = get_object_or_404(DialogueScript, id=script_id, user=request.user)
        script_title = script.title
        script.delete()
        
        return JsonResponse({
            'success': True,
            'message': f'对话脚本 "{script_title}" 已删除'
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': f'删除失败: {str(e)}'})

@login_required
@csrf_exempt
@require_POST
def dialogue_update_title(request, script_id):
    """更新对话脚本标题"""
    try:
        script = get_object_or_404(DialogueScript, id=script_id, user=request.user)
        data = json.loads(request.body)
        new_title = data.get('title', '').strip()
        
        if not new_title:
            return JsonResponse({'success': False, 'error': '标题不能为空'})
        
        script.title = new_title
        script.save()
        
        return JsonResponse({
            'success': True,
            'message': '标题已更新',
            'title': script.title
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': '无效的JSON数据'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': f'更新失败: {str(e)}'})

@login_required
@csrf_exempt
@require_POST
def dialogue_update_book(request, script_id):
    """更新对话脚本关联书籍"""
    try:
        script = get_object_or_404(DialogueScript, id=script_id, user=request.user)
        data = json.loads(request.body)
        book_id = data.get('book_id')
        
        if book_id:
            # 验证书籍是否属于当前用户
            book = get_object_or_404(Books, id=book_id, user=request.user)
            script.book = book
        else:
            script.book = None
        
        script.save()
        
        return JsonResponse({
            'success': True,
            'message': '关联书籍已更新',
            'book_name': script.book.name if script.book else None
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': '无效的JSON数据'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': f'更新失败: {str(e)}'})

@login_required
@csrf_exempt
@require_POST
def dialogue_ai_recommend_voices(request, script_id):
    """AI智能推荐音色"""
    try:
        script = get_object_or_404(DialogueScript, id=script_id, user=request.user)

        # 获取对话脚本数据
        script_data = script.script_data
        if not script_data or 'segments' not in script_data:
            return JsonResponse({'success': False, 'error': '对话脚本数据为空'})

        # 使用AI推荐音色
        recommendation_service = VoiceRecommendationService()
        recommendations = recommendation_service.recommend_voices_for_script(script_data)

        if not recommendations:
            return JsonResponse({'success': False, 'error': '未能生成音色推荐'})

        return JsonResponse({
            'success': True,
            'recommendations': recommendations,
            'message': f'已为 {len(recommendations)} 个角色推荐音色'
        })

    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"AI音色推荐失败: {e}")
        return JsonResponse({'success': False, 'error': f'AI推荐失败: {str(e)}'})

@login_required
@csrf_exempt
@require_POST
def dialogue_segment_delete(request, segment_id):
    """删除对话片段"""
    try:
        segment = get_object_or_404(DialogueSegment, id=segment_id, script__user=request.user)
        script = segment.script
        
        # 获取要删除的片段信息
        segment_sequence = segment.sequence
        
        # 删除片段
        segment.delete()
        
        # 使用同步方法确保数据一致性
        script.sync_script_data_with_segments()
        
        # 注释掉之前的手动同步逻辑，因为sync_script_data_with_segments已经处理了
        # # 同步更新 script_data 中的 segments
        # if script.script_data and 'segments' in script.script_data:
        #     segments_data = script.script_data['segments']
        #     
        #     # 找到并删除对应的片段数据
        #     # 由于sequence可能不连续，我们需要找到对应的片段
        #     segments_to_keep = []
        #     deleted_found = False
        #     
        #     for i, segment_data in enumerate(segments_data):
        #         # 跳过要删除的片段（基于sequence匹配）
        #         if not deleted_found and i + 1 == segment_sequence:
        #             deleted_found = True
        #             continue
        #         segments_to_keep.append(segment_data)
        #     
        #     # 更新script_data
        #     script.script_data['segments'] = segments_to_keep
        #     script.save(update_fields=['script_data'])
        
        # 更新剩余片段的sequence，确保连续性
        remaining_segments = script.segments.all().order_by('sequence')
        for index, seg in enumerate(remaining_segments, 1):
            if seg.sequence != index:
                seg.sequence = index
                seg.save(update_fields=['sequence'])
        
        # 再次同步以确保sequence更新后的一致性
        script.sync_script_data_with_segments()
        
        return JsonResponse({
            'success': True,
            'message': '片段已删除'
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': f'删除失败: {str(e)}'})

@login_required
@csrf_exempt
@require_POST
def dialogue_segment_update(request, segment_id):
    """更新对话片段"""
    try:
        segment = get_object_or_404(DialogueSegment, id=segment_id, script__user=request.user)
        data = json.loads(request.body)
        
        old_speaker = segment.speaker
        old_text = segment.utterance  # 使用正确的字段名
        script_data_updated = False
        
        # 更新允许字段
        if 'speaker' in data:
            segment.speaker = data['speaker'].strip()
        if 'text' in data:
            segment.utterance = data['text'].strip()  # 更新正确的字段
        if 'sequence' in data:
            segment.sequence = int(data['sequence'])
        
        segment.save()
        
        # 同步更新 script_data 中的对应片段
        script = segment.script
        if script.script_data and 'segments' in script.script_data:
            segments_data = script.script_data['segments']
            
            # 找到对应的片段数据并更新
            for i, segment_data in enumerate(segments_data):
                # 通过sequence匹配片段（注意：数组索引从0开始，sequence从1开始）
                if i + 1 == segment.sequence:
                    if 'speaker' in data:
                        segment_data['speaker'] = segment.speaker
                        script_data_updated = True
                    if 'text' in data:
                        segment_data['utterance'] = segment.utterance  # 使用正确的字段名
                        script_data_updated = True
                    break
            
            # 如果有更新，保存script_data
            if script_data_updated:
                script.save(update_fields=['script_data'])
        
        return JsonResponse({
            'success': True,
            'message': '片段已更新',
            'segment': {
                'id': segment.id,
                'speaker': segment.speaker,
                'text': segment.utterance,  # 返回给前端时仍使用text字段名
                'sequence': segment.sequence
            }
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': '无效的JSON数据'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': f'更新失败: {str(e)}'})
