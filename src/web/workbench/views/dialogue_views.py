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
    """将文本转换为对话脚本的API接口"""
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
        
        # 初始化对话服务
        try:
            llm_service = LLMService()
            dialogue_service = DialogueService(llm_service)
        except Exception as e:
            return JsonResponse({
                'success': False, 
                'error': f'LLM服务初始化失败: {str(e)}'
            })
        
        # 转换文本为对话
        if len(text) > 3000:
            # 长文本分段处理
            text_chunks = dialogue_service.split_long_text(text, max_length=3000)
            all_segments = []
            
            for i, chunk in enumerate(text_chunks):
                result = dialogue_service.text_to_dialogue(
                    chunk, 
                    custom_prompt if custom_prompt else None
                )
                
                if not result['success']:
                    return JsonResponse({
                        'success': False,
                        'error': f'第{i+1}段转换失败: {result["error"]}'
                    })
                
                chunk_segments = result['dialogue_data'].get('segments', [])
                all_segments.extend(chunk_segments)
            
            # 合并所有段落
            dialogue_data = {
                'title': title,
                'segments': all_segments
            }
        else:
            # 短文本直接处理
            result = dialogue_service.text_to_dialogue(
                text, 
                custom_prompt if custom_prompt else None
            )
            
            if not result['success']:
                return JsonResponse(result)
            
            dialogue_data = result['dialogue_data']
        
        # 验证对话数据
        validation = dialogue_service.validate_dialogue_data(dialogue_data)
        if not validation['is_valid']:
            return JsonResponse({
                'success': False,
                'error': f'对话数据验证失败: {"; ".join(validation["errors"])}'
            })
        
        # 保存到数据库
        book = None
        if book_id:
            try:
                book = Books.objects.get(id=book_id, user=request.user)
            except Books.DoesNotExist:
                pass
        
        script = DialogueScript.objects.create(
            user=request.user,
            book=book,
            title=dialogue_data.get('title', title),
            original_text=text,
            script_data=dialogue_data
        )
        
        # 创建对话片段记录（用于后续音色配置）
        segments = dialogue_data.get('segments', [])
        for i, segment_data in enumerate(segments):
            DialogueSegment.objects.create(
                script=script,
                speaker=segment_data.get('speaker', '未知'),
                sequence=i + 1,
                utterance=segment_data.get('utterance', ''),
                dialogue_type=segment_data.get('type', 'dialogue')
            )
        
        return JsonResponse({
            'success': True,
            'script_id': script.id,
            'title': script.title,
            'segments_count': len(segments),
            'speakers': dialogue_service.get_speakers_from_dialogue(dialogue_data)
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': '无效的JSON数据'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': f'转换过程中发生错误: {str(e)}'})

@login_required
def dialogue_detail(request, script_id):
    """对话脚本详情页面"""
    script = get_object_or_404(DialogueScript, id=script_id, user=request.user)
    segments = script.segments.all().order_by('sequence')
    
    # 获取用户的音色角色
    voice_roles = VoiceRole.objects.filter(user=request.user).order_by('name')
    
    # 获取可用音色列表
    multi_voice_tts = MultiVoiceTTS()
    edge_voices = multi_voice_tts.get_available_voices('edge_tts')
    
    return render(request, 'dialogue_detail.html', {
        'script': script,
        'segments': segments,
        'voice_roles': voice_roles,
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
    
    return render(request, 'voice_roles.html', {
        'voice_roles': voice_roles,
        'edge_voices_json': json.dumps(edge_voices)
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