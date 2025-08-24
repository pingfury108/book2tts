import json
import os
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
from ..models import Books, DialogueScript, DialogueSegment, VoiceRole, UserTask

# Import dialogue services
import sys
sys.path.append(os.path.join(settings.BASE_DIR, 'src'))
from book2tts.dialogue_service import DialogueService
from book2tts.multi_voice_tts import MultiVoiceTTS
from book2tts.llm_service import LLMService

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
    
    # 获取用户的音色角色
    voice_roles = VoiceRole.objects.filter(user=request.user).order_by('name')
    
    # 获取用户的书籍列表
    books = Books.objects.filter(user=request.user).order_by('name')
    
    # 获取可用音色列表
    multi_voice_tts = MultiVoiceTTS()
    edge_voices = multi_voice_tts.get_available_voices('edge_tts')
    
    return render(request, 'dialogue_detail.html', {
        'script': script,
        'segments': segments,
        'voice_roles': voice_roles,
        'books': books,
        'edge_voices_json': json.dumps(edge_voices),
        'speakers': script.speakers
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
        
        # 更新对话片段的音色配置
        for speaker, voice_config in voice_mapping.items():
            voice_role_id = voice_config.get('voice_role_id')
            voice_role = None
            
            if voice_role_id:
                try:
                    voice_role = VoiceRole.objects.get(id=voice_role_id, user=request.user)
                except VoiceRole.DoesNotExist:
                    pass
            
            # 更新该说话者的所有片段
            script.segments.filter(speaker=speaker).update(voice_role=voice_role)
        
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
        voice_mapping = {}
        
        for segment in segments:
            speaker = segment.speaker
            if speaker not in voice_mapping:
                if segment.voice_role:
                    voice_mapping[speaker] = {
                        'provider': segment.voice_role.tts_provider,
                        'voice_name': segment.voice_role.voice_name
                    }
                else:
                    return JsonResponse({
                        'success': False,
                        'error': f'说话者 "{speaker}" 尚未配置音色'
                    })
        
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
def voice_roles_list(request):
    """音色角色管理页面"""
    voice_roles = VoiceRole.objects.filter(user=request.user).order_by('name')
    
    # 获取可用音色列表
    multi_voice_tts = MultiVoiceTTS()
    edge_voices = multi_voice_tts.get_available_voices('edge_tts')
    
    # Azure音色列表（静态定义常用的中文音色）
    azure_voices = [
        {"name": "晓晓 (女声)", "value": "zh-CN-XiaoxiaoNeural"},
        {"name": "云希 (男声)", "value": "zh-CN-YunxiNeural"},
        {"name": "晓伊 (女声)", "value": "zh-CN-XiaoyiNeural"},
        {"name": "云扬 (男声)", "value": "zh-CN-YunyangNeural"},
        {"name": "晓梦 (女声)", "value": "zh-CN-XiaomengNeural"},
        {"name": "云健 (男声)", "value": "zh-CN-YunjianNeural"},
        {"name": "晓墨 (女声)", "value": "zh-CN-XiaomoNeural"},
        {"name": "晓睿 (女声)", "value": "zh-CN-XiaoruiNeural"},
        {"name": "晓双 (女声)", "value": "zh-CN-XiaoshuangNeural"},
        {"name": "晓悠 (女声)", "value": "zh-CN-XiaoyouNeural"},
        {"name": "云野 (男声)", "value": "zh-CN-YunyeNeural"},
        {"name": "云泽 (男声)", "value": "zh-CN-YunzeNeural"},
    ]
    
    return render(request, 'voice_roles.html', {
        'voice_roles': voice_roles,
        'edge_voices_json': json.dumps(edge_voices),
        'azure_voices_json': json.dumps(azure_voices)
    })

@login_required
@csrf_exempt
@require_POST
def voice_role_create(request):
    """创建音色角色"""
    try:
        data = json.loads(request.body)
        name = data.get('name', '').strip()
        tts_provider = data.get('tts_provider', 'azure')
        voice_name = data.get('voice_name', '').strip()
        is_default = data.get('is_default', False)
        
        if not name or not voice_name:
            return JsonResponse({'success': False, 'error': '角色名称和音色名称不能为空'})
        
        # 检查是否已存在同名角色
        if VoiceRole.objects.filter(user=request.user, name=name).exists():
            return JsonResponse({'success': False, 'error': f'角色 "{name}" 已存在'})
        
        # 如果设为默认，先取消其他默认角色
        if is_default:
            VoiceRole.objects.filter(user=request.user, is_default=True).update(is_default=False)
        
        voice_role = VoiceRole.objects.create(
            user=request.user,
            name=name,
            tts_provider=tts_provider,
            voice_name=voice_name,
            is_default=is_default
        )
        
        return JsonResponse({
            'success': True,
            'voice_role': {
                'id': voice_role.id,
                'name': voice_role.name,
                'tts_provider': voice_role.tts_provider,
                'voice_name': voice_role.voice_name,
                'is_default': voice_role.is_default
            }
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': '无效的JSON数据'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': f'创建失败: {str(e)}'})

@login_required
@csrf_exempt
@require_POST
def voice_role_delete(request, role_id):
    """删除音色角色"""
    try:
        voice_role = get_object_or_404(VoiceRole, id=role_id, user=request.user)
        voice_role.delete()
        
        return JsonResponse({
            'success': True,
            'message': '音色角色已删除'
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': f'删除失败: {str(e)}'})

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

@login_required
@csrf_exempt
@require_POST
def dialogue_segment_preview(request, segment_id):
    """预览单个对话片段的音频"""
    try:
        segment = get_object_or_404(DialogueSegment, id=segment_id, script__user=request.user)
        
        if not segment.voice_role:
            return JsonResponse({
                'success': False,
                'error': '该片段尚未配置音色角色'
            })
        
        # 创建异步任务生成预览音频
        from ..tasks import generate_segment_preview_task
        
        task_result = generate_segment_preview_task.delay(
            segment_id=segment.id,
            voice_config={
                'provider': segment.voice_role.tts_provider,
                'voice_name': segment.voice_role.voice_name
            }
        )
        
        # 创建用户任务记录
        user_task = UserTask.objects.create(
            user=request.user,
            task_id=task_result.id,
            task_type='segment_preview',
            book=segment.script.book,
            title=f'片段预览: {segment.text[:30]}...',
            status='pending',
            metadata={
                'segment_id': segment.id,
                'text': segment.text,
                'speaker': segment.speaker
            }
        )
        
        return JsonResponse({
            'success': True,
            'task_id': user_task.task_id,
            'message': '预览音频生成中...'
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': f'预览生成失败: {str(e)}'}) 