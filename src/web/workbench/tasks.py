import os
import time
import tempfile
import asyncio
from celery import shared_task
from celery.utils.log import get_task_logger
from django.conf import settings
from django.core.files.base import ContentFile
from django.contrib.auth.models import User
from django.db import transaction
from django.utils import timezone

from .models import Books, AudioSegment, DialogueScript, UserTask, DialogueSegment
from book2tts.edgetts import EdgeTTS
from book2tts.audio_utils import get_audio_duration, estimate_audio_duration_from_text
from home.models import UserQuota, OperationRecord
from home.utils.utils import PointsManager
from book2tts.multi_voice_tts import MultiVoiceTTS
from .utils.subtitle_utils import convert_vtt_to_srt, save_srt_subtitle

# Import dialogue services - use lazy import to avoid circular imports
def get_dialogue_service():
    """延迟导入对话服务以避免循环导入"""
    import os
    import sys
    sys.path.insert(0, os.path.join(settings.BASE_DIR, '..'))
    from book2tts.dialogue_service import DialogueService
    from book2tts.llm_service import LLMService
    return DialogueService, LLMService

# Get a logger instance for the tasks
logger = get_task_logger(__name__)


def _generate_simple_subtitle(text: str, duration: float) -> str:
    """生成简单的单条字幕"""
    if not text or duration <= 0:
        return ""
    
    return f"""1
00:00:00,000 --> {_format_srt_time(duration)}
{text}

"""


def _generate_fallback_subtitle(text: str, duration: float) -> str:
    """生成回退字幕（基于文本分段）"""
    if not text or duration <= 0:
        return ""
    
    # 简单按句子分割
    sentences = [s.strip() for s in text.split('。') if s.strip()]
    if not sentences:
        sentences = [text]
    
    # 计算每个句子的时长
    time_per_sentence = duration / len(sentences)
    
    srt_lines = []
    for i, sentence in enumerate(sentences):
        start_time = i * time_per_sentence
        end_time = (i + 1) * time_per_sentence
        
        srt_lines.extend([
            str(i + 1),
            f"{_format_srt_time(start_time)} --> {_format_srt_time(end_time)}",
            sentence + "。" if not sentence.endswith('。') else sentence,
            ""
        ])
    
    return "\n".join(srt_lines)


def _format_srt_time(seconds: float) -> str:
    """格式化SRT时间戳"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds % 1) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def get_client_ip_from_task(task_kwargs):
    """从任务参数中获取客户端IP地址"""
    return task_kwargs.get('ip_address', '127.0.0.1')


def get_user_agent_from_task(task_kwargs):
    """从任务参数中获取用户代理"""
    return task_kwargs.get('user_agent', '')


def start_audio_synthesis_on_commit(user_id, text, voice_name, book_id, **kwargs):
    """
    在数据库事务提交后启动音频合成任务的辅助函数
    
    这是使用 delay_on_commit 的推荐方式，确保任务只在数据库事务成功提交后执行
    """
    def _start_task():
        return synthesize_audio_task.delay(
            user_id=user_id,
            text=text,
            voice_name=voice_name,
            book_id=book_id,
            **kwargs
        )
    
    # 使用 transaction.on_commit 确保任务在事务提交后执行
    transaction.on_commit(_start_task)
    
    # 注意：这种方式不能返回 task_id，因为任务还没有真正启动
    # 如果需要 task_id 用于状态跟踪，应该使用其他机制，比如数据库记录ID
    logger.info(f"Scheduled audio synthesis task for user {user_id} to start after transaction commit")


@shared_task(bind=True)
def synthesize_audio_task(self, user_id, text, voice_name, book_id, title="", book_page="", page_display_name="", audio_title="", ip_address="127.0.0.1", user_agent=""):
    """异步音频合成任务（支持字幕生成）"""
    try:
        # 更新任务状态为开始处理
        self.update_state(state='PROCESSING', meta={'message': '开始音频合成和字幕生成...'})
        logger.info(f"Starting audio synthesis task for user {user_id}, book {book_id}")
        
        # 获取用户和书籍对象
        try:
            user = User.objects.get(pk=user_id)
            book = Books.objects.get(pk=book_id)
        except (User.DoesNotExist, Books.DoesNotExist) as e:
            error_msg = f"用户或书籍不存在: {str(e)}"
            logger.error(error_msg)
            OperationRecord.objects.create(
                user_id=user_id,
                operation_type='audio_create',
                operation_object=f'Book ID: {book_id} - {title or page_display_name}',
                operation_detail=f'音频合成任务失败：{error_msg}',
                status='failed',
                metadata={
                    'book_id': book_id,
                    'error_reason': 'object_not_found',
                    'exception_message': str(e)
                },
                ip_address=ip_address,
                user_agent=user_agent
            )
            raise Exception(error_msg)
        
        # 获取或创建用户配额
        user_quota, created = UserQuota.objects.get_or_create(user=user)
        
        # 估算音频时长
        estimated_duration_seconds = estimate_audio_duration_from_text(text)
        
        # 计算需要的积分
        required_points = PointsManager.get_audio_generation_points(estimated_duration_seconds)
        
        # 检查积分是否足够
        if not user_quota.can_consume_points(required_points):
            error_msg = f"积分不足。预估需要 {required_points} 积分，剩余 {user_quota.points} 积分"
            logger.warning(f"Insufficient points for user {user_id}: {error_msg}")
            OperationRecord.objects.create(
                user=user,
                operation_type='audio_create',
                operation_object=f'{book.name} - {title or page_display_name}',
                operation_detail=f'音频合成任务失败：{error_msg}',
                status='failed',
                metadata={
                    'book_id': book_id,
                    'book_name': book.name,
                    'estimated_duration': estimated_duration_seconds,
                    'required_points': required_points,
                    'remaining_points': user_quota.points,
                    'text_length': len(text),
                    'voice_name': voice_name,
                    'error_reason': 'insufficient_points'
                },
                ip_address=ip_address,
                user_agent=user_agent
            )
            raise Exception(error_msg)
        
        # 更新任务状态
        self.update_state(state='PROCESSING', meta={'message': '正在生成音频和字幕文件...'})
        
        # 创建临时文件
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as audio_file:
            audio_path = audio_file.name
        
        with tempfile.NamedTemporaryFile(suffix=".vtt", delete=False) as subtitle_file:
            subtitle_path = subtitle_file.name
        
        try:
            # 使用改进的EdgeTTS合成音频和字幕
            logger.info(f"Starting TTS synthesis with voice {voice_name}")
            
            # 获取当前事件循环或创建新的
            try:
                loop = asyncio.get_event_loop()
                if loop.is_closed():
                    raise RuntimeError("Event loop is closed")
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            # 使用改进的字幕生成方法
            tts = EdgeTTS(voice_name=voice_name)
            synthesis_result = loop.run_until_complete(
                tts.synthesize_with_subtitles_v2(
                    text=text, 
                    output_file=audio_path, 
                    subtitle_file=subtitle_path,
                    words_in_cue=8  # 每个字幕条目8个词
                )
            )
            
            # 详细的结果验证和日志
            logger.info(f"Synthesis result: {synthesis_result}")
            
            if not synthesis_result["success"]:
                error_details = []
                if not synthesis_result["audio_generated"]:
                    error_details.append("音频生成失败")
                if not synthesis_result["subtitle_generated"]:
                    error_details.append("字幕生成失败")
                
                error_msg = f"TTS合成失败: {', '.join(error_details)}"
                logger.error(error_msg)
                OperationRecord.objects.create(
                    user=user,
                    operation_type='audio_create',
                    operation_object=f'{book.name} - {title or page_display_name}',
                    operation_detail=f'音频合成任务失败：{error_msg}',
                    status='failed',
                    metadata={
                        'book_id': book_id,
                        'book_name': book.name,
                        'estimated_duration': estimated_duration_seconds,
                        'text_length': len(text),
                        'voice_name': voice_name,
                        'error_reason': 'tts_synthesis_failed',
                        'synthesis_details': synthesis_result
                    },
                    ip_address=ip_address,
                    user_agent=user_agent
                )
                raise Exception(error_msg)
            
            # 字幕文件处理 - 增加多重验证
            vtt_content = ""
            srt_content = ""
            
            if os.path.exists(subtitle_path):
                file_size = os.path.getsize(subtitle_path)
                logger.info(f"Subtitle file found: {subtitle_path}, size: {file_size}")
                
                if file_size > 0:
                    with open(subtitle_path, 'r', encoding='utf-8') as f:
                        vtt_content = f.read()
                        logger.info(f"VTT content length: {len(vtt_content)}")
                        
                    # 转换为SRT并验证
                    srt_content = convert_vtt_to_srt(vtt_content) if vtt_content else ""
                    logger.info(f"SRT content length: {len(srt_content)}")
                    
                    if not srt_content:
                        logger.warning("VTT to SRT conversion resulted in empty content")
                else:
                    logger.warning("Subtitle file exists but is empty")
            else:
                logger.warning(f"Subtitle file not found: {subtitle_path}")
            
            # 如果字幕仍然为空，尝试生成基础字幕
            if not srt_content:
                logger.info("No subtitle content found, generating fallback subtitle from text")
                actual_duration_seconds = get_audio_duration(audio_path, text)
                srt_content = _generate_fallback_subtitle(text, actual_duration_seconds)
                logger.info(f"Generated fallback subtitle length: {len(srt_content)}")
            
            # 读取生成的VTT字幕（保留原逻辑作为备用）
            if not vtt_content and os.path.exists(subtitle_path):
                with open(subtitle_path, 'r', encoding='utf-8') as f:
                    vtt_content = f.read()
            
            # 转换为SRT格式（如果还没转换）
            if not srt_content and vtt_content:
                srt_content = convert_vtt_to_srt(vtt_content)
            
            # 确保有字幕内容
            if not srt_content:
                logger.warning("Still no subtitle content after all attempts, generating simple subtitle")
                actual_duration_seconds = get_audio_duration(audio_path, text)
                srt_content = _generate_simple_subtitle(text, actual_duration_seconds)
                logger.info(f"Generated simple subtitle length: {len(srt_content)}")
            
            # 更新任务状态
            self.update_state(state='PROCESSING', meta={'message': '音频和字幕生成完成，正在保存...'})
            
            # 获取实际音频时长
            actual_duration_seconds = get_audio_duration(audio_path, text)
            logger.info(f"Audio synthesis completed. Duration: {actual_duration_seconds} seconds")
            
            # 使用自定义音频标题或默认标题
            segment_title = audio_title if audio_title else (page_display_name if page_display_name else title)
            
            # 使用事务确保数据一致性
            with transaction.atomic():
                # 创建 AudioSegment 实例
                audio_segment = AudioSegment(
                    book=book,
                    user=user,
                    title=segment_title,
                    text=text,
                    book_page=book_page,
                    published=False
                )
                
                # 确保媒体目录存在
                media_root = settings.MEDIA_ROOT
                upload_dir = os.path.join(media_root, 'audio_segments', time.strftime('%Y/%m/%d'))
                os.makedirs(upload_dir, exist_ok=True)
                
                # 生成唯一文件名
                filename = f"audio_{book_id}_{int(time.time())}.wav"
                
                # 保存音频文件到 AudioSegment
                with open(audio_path, "rb") as f:
                    audio_segment.file.save(filename, ContentFile(f.read()))
                
                # 保存字幕文件 - 确保总是保存字幕
                if srt_content:
                    logger.info(f"Saving subtitle with {len(srt_content)} characters")
                    save_srt_subtitle(audio_segment, srt_content, 'subtitle_file')
                else:
                    logger.warning("No subtitle content to save - this should not happen")
                    # 作为最后的保证，创建一个基本字幕
                    simple_srt = _generate_simple_subtitle(text, actual_duration_seconds)
                    if simple_srt:
                        save_srt_subtitle(audio_segment, simple_srt, 'subtitle_file')
                        logger.info("Saved emergency fallback subtitle")
                
                # 保存 AudioSegment
                audio_segment.save()
                
                # 刷新用户配额以获取最新数据
                user_quota.refresh_from_db()
                
                # 扣除用户积分
                required_points = PointsManager.get_audio_generation_points(actual_duration_seconds)
                user_quota.consume_points(required_points)
                
                # 记录成功的音频创建操作
                OperationRecord.objects.create(
                    user=user,
                    operation_type='audio_create',
                    operation_object=f'{book.name} - {segment_title}',
                    operation_detail=f'成功创建音频片段：{segment_title}，时长 {actual_duration_seconds} 秒，消耗积分 {required_points} 分',
                    status='success',
                    metadata={
                        'book_id': book_id,
                        'book_name': book.name,
                        'audio_segment_id': audio_segment.id,
                        'actual_duration': actual_duration_seconds,
                        'estimated_duration': estimated_duration_seconds,
                        'consumed_points': required_points,
                        'remaining_points_after': user_quota.points,
                        'text_length': len(text),
                        'voice_name': voice_name,
                        'file_path': audio_segment.file.name,
                        'file_size': os.path.getsize(audio_path) if os.path.exists(audio_path) else 0
                    },
                    ip_address=ip_address,
                    user_agent=user_agent
                )
            
            logger.info(f"Audio synthesis task completed successfully for user {user_id}")
            
            # 返回成功结果
            return {
                'status': 'SUCCESS',
                'message': '音频和字幕合成完成',
                'audio_url': audio_segment.file.url,
                'subtitle_url': audio_segment.subtitle_file.url if audio_segment.subtitle_file else None,
                'audio_id': audio_segment.id,
                'audio_duration': actual_duration_seconds,
                'remaining_points': user_quota.points,
                'subtitle_generated': bool(audio_segment.subtitle_file),
                'synthesis_method': synthesis_result.get('method', 'unknown')
            }
            
        finally:
            # 清理临时文件
            for path in [audio_path, subtitle_path]:
                if os.path.exists(path):
                    os.remove(path)
    
    except Exception as e:
        logger.error(f"Audio synthesis task failed for user {user_id}: {str(e)}")
        # 记录异常的操作
        OperationRecord.objects.create(
            user_id=user_id,
            operation_type='audio_create',
            operation_object=f'Book ID: {book_id} - {title or page_display_name}',
            operation_detail=f'音频合成任务异常：{str(e)}',
            status='failed',
            metadata={
                'book_id': book_id,
                'estimated_duration': estimated_duration_seconds if 'estimated_duration_seconds' in locals() else 0,
                'text_length': len(text),
                'voice_name': voice_name,
                'error_reason': 'task_exception',
                'exception_message': str(e)
            },
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        # 更新任务状态为失败
        self.update_state(
            state='FAILURE',
            meta={
                'message': f'音频合成失败：{str(e)}',
                'error': str(e)
            }
        )
        raise Exception(f'音频合成失败：{str(e)}')


@shared_task(bind=True, ignore_result=True)
def cleanup_old_audio_files(self):
    """
    清理过期的音频文件的定期任务示例
    
    这是一个可以用于定期维护的任务示例
    """
    logger.info("Starting cleanup of old audio files")
    
    # 这里可以添加清理逻辑
    # 例如：删除超过30天的未发布音频文件
    
    return "Cleanup task completed"


@shared_task(bind=True)
def convert_text_to_dialogue_task(self, user_id, text, title, book_id=None, custom_prompt=None):
    """将文本转换为对话脚本的异步任务"""
    try:
        # 更新任务状态
        self.update_state(state='PROCESSING', meta={'message': '开始处理文本转换...'})
        logger.info(f"Starting text to dialogue conversion for user {user_id}")
        
        # 获取用户对象
        try:
            user = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            error_msg = f"用户不存在: {user_id}"
            logger.error(error_msg)
            raise Exception(error_msg)
        
        # 获取书籍对象（如果提供）
        book = None
        if book_id:
            try:
                book = Books.objects.get(pk=book_id, user=user)
            except Books.DoesNotExist:
                logger.warning(f"Book not found: {book_id}")
        
        # 更新用户任务状态
        try:
            user_task = UserTask.objects.get(task_id=self.request.id)
            user_task.status = 'processing'
            user_task.progress_message = '正在初始化AI服务...'
            user_task.save()
        except UserTask.DoesNotExist:
            logger.warning(f"UserTask not found for task {self.request.id}")
        
        # 初始化对话服务
        try:
            DialogueService, LLMService = get_dialogue_service()
            llm_service = LLMService()
            dialogue_service = DialogueService(llm_service)
        except Exception as e:
            error_msg = f'LLM服务初始化失败: {str(e)}'
            logger.error(error_msg)
            raise Exception(error_msg)
        
        # 文本预处理 - 计算长度和分段
        total_length = len(text)
        logger.info(f"Processing text of length: {total_length}")
        
        # 更新任务状态
        self.update_state(state='PROCESSING', meta={'message': '正在分析文本结构...'})
        if 'user_task' in locals():
            user_task.progress_message = '正在分析文本结构...'
            user_task.save()
        
        # 分段处理逻辑
        if total_length > 3000:
            # 长文本分段处理
            chunk_size = 3000
            text_chunks = dialogue_service.split_long_text(text, max_length=chunk_size)
            total_chunks = len(text_chunks)
            
            logger.info(f"Split text into {total_chunks} chunks for processing")
            all_segments = []
            
            for i, chunk in enumerate(text_chunks):
                progress_percent = int((i / total_chunks) * 100)
                progress_message = f'正在处理第 {i+1}/{total_chunks} 段文本...'
                
                # 更新任务进度
                self.update_state(
                    state='PROCESSING', 
                    meta={
                        'message': progress_message,
                        'progress': progress_percent,
                        'chunk': i + 1,
                        'total_chunks': total_chunks
                    }
                )
                if 'user_task' in locals():
                    user_task.progress_message = progress_message
                    user_task.metadata['progress'] = progress_percent
                    user_task.metadata['chunk'] = i + 1
                    user_task.metadata['total_chunks'] = total_chunks
                    user_task.save()
                
                # 转换当前段
                result = dialogue_service.text_to_dialogue(
                    chunk, 
                    custom_prompt if custom_prompt else None
                )
                
                if not result['success']:
                    error_msg = f'第{i+1}段转换失败: {result["error"]}'
                    logger.error(error_msg)
                    raise Exception(error_msg)
                
                chunk_segments = result['dialogue_data'].get('segments', [])
                all_segments.extend(chunk_segments)
            
            # 合并所有段落
            dialogue_data = {
                'title': title,
                'segments': all_segments,
                'total_chunks': total_chunks,
                'original_length': total_length
            }
            
        else:
            # 短文本直接处理
            self.update_state(state='PROCESSING', meta={'message': '正在转换文本为对话...'})
            if 'user_task' in locals():
                user_task.progress_message = '正在转换文本为对话...'
                user_task.save()
            
            result = dialogue_service.text_to_dialogue(
                text, 
                custom_prompt if custom_prompt else None
            )
            
            if not result['success']:
                logger.error(f"Text conversion failed: {result['error']}")
                raise Exception(f"文本转换失败: {result['error']}")
            
            dialogue_data = result['dialogue_data']
            dialogue_data['original_length'] = total_length
        
        # 验证对话数据
        self.update_state(state='PROCESSING', meta={'message': '正在验证对话数据...'})
        if 'user_task' in locals():
            user_task.progress_message = '正在验证对话数据...'
            user_task.save()
        
        validation = dialogue_service.validate_dialogue_data(dialogue_data)
        if not validation['is_valid']:
            error_msg = f'对话数据验证失败: {"; ".join(validation["errors"])}'
            logger.error(error_msg)
            raise Exception(error_msg)
        
        # 保存到数据库
        self.update_state(state='PROCESSING', meta={'message': '正在保存对话脚本...'})
        if 'user_task' in locals():
            user_task.progress_message = '正在保存对话脚本...'
            user_task.save()
        
        with transaction.atomic():
            script = DialogueScript.objects.create(
                user=user,
                book=book,
                title=dialogue_data.get('title', title),
                original_text=text,
                script_data=dialogue_data
            )
            
            # 创建对话片段记录
            segments = dialogue_data.get('segments', [])
            for i, segment_data in enumerate(segments):
                DialogueSegment.objects.create(
                    script=script,
                    speaker=segment_data.get('speaker', '未知'),
                    sequence=i + 1,
                    utterance=segment_data.get('utterance', ''),
                    dialogue_type=segment_data.get('type', 'dialogue')
                )
            
            # 获取说话者列表
            speakers = dialogue_service.get_speakers_from_dialogue(dialogue_data)
            
            # 更新用户任务为成功状态
            if 'user_task' in locals():
                user_task.status = 'success'
                user_task.progress_message = '对话脚本创建完成'
                user_task.result_data = {
                    'script_id': script.id,
                    'title': script.title,
                    'segments_count': len(segments),
                    'speakers': speakers,
                    'original_length': total_length
                }
                user_task.completed_at = timezone.now()
                user_task.save()
        
        logger.info(f"Text to dialogue conversion completed for user {user_id}, script {script.id}")
        
        return {
            'success': True,
            'script_id': script.id,
            'title': script.title,
            'segments_count': len(segments),
            'speakers': speakers
        }
        
    except Exception as e:
        error_msg = f"文本转换对话失败: {str(e)}"
        logger.error(error_msg)
        
        # 更新用户任务为失败状态
        try:
            user_task = UserTask.objects.get(task_id=self.request.id)
            user_task.status = 'failure'
            user_task.error_message = error_msg
            user_task.completed_at = timezone.now()
            user_task.save()
        except UserTask.DoesNotExist:
            pass
        
        self.update_state(
            state='FAILURE',
            meta={'error': error_msg}
        )
        raise


@shared_task(bind=True)
def generate_dialogue_audio_task(self, script_id, voice_mapping):
    """生成对话音频的异步任务（支持字幕生成和时间戳校对）"""
    try:
        # 更新任务状态
        self.update_state(state='PROCESSING', meta={'message': '开始生成对话音频和字幕...'})
        logger.info(f"Starting dialogue audio generation for script {script_id}")
        
        # 获取对话脚本
        try:
            script = DialogueScript.objects.get(pk=script_id)
        except DialogueScript.DoesNotExist:
            error_msg = f"对话脚本不存在: {script_id}"
            logger.error(error_msg)
            raise Exception(error_msg)
        
        # 获取用户和用户配额
        user = script.user
        user_quota, created = UserQuota.objects.get_or_create(user=user)
        
        # 更新用户任务状态
        try:
            user_task = UserTask.objects.get(task_id=self.request.id)
            user_task.status = 'processing'
            user_task.progress_message = '正在生成对话音频和字幕...'
            user_task.save()
        except UserTask.DoesNotExist:
            logger.warning(f"UserTask not found for task {self.request.id}")
        
        # 预估音频时长以检查积分
        try:
            multi_voice_tts = MultiVoiceTTS()
            estimated_duration = multi_voice_tts.estimate_audio_duration(script.script_data)
            logger.info(f"Estimated audio duration: {estimated_duration} seconds")
            
            # 检查用户积分是否充足
            from home.utils import PointsManager
            required_points = PointsManager.get_audio_generation_points(estimated_duration)
            
            if not user_quota.can_consume_points(required_points):
                error_msg = f"积分不足，需要 {required_points} 积分，当前可用 {user_quota.points} 积分"
                logger.error(error_msg)
                
                # 更新用户任务为失败状态
                if 'user_task' in locals():
                    user_task.status = 'failure'
                    user_task.error_message = error_msg
                    user_task.save()
                
                raise Exception(error_msg)
                
            logger.info(f"Points check passed: need {required_points}, have {user_quota.points}")
            
        except Exception as e:
            if "积分不足" in str(e):
                raise e
            logger.warning(f"Failed to estimate duration or check points: {e}")
            # 如果预估失败，继续执行，在实际完成后检查积分
        multi_voice_tts = MultiVoiceTTS()
        
        # 创建临时输出文件
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as audio_file:
            temp_output_path = audio_file.name
        
        with tempfile.NamedTemporaryFile(suffix=".srt", delete=False) as subtitle_file:
            temp_subtitle_path = subtitle_file.name
        
        try:
            # 更新任务状态
            self.update_state(state='PROCESSING', meta={'message': '正在合成多角色音频和字幕...'})
            
            # 使用改进的方法生成对话音频和字幕（已包含时间戳校对）
            synthesis_result = multi_voice_tts.synthesize_dialogue_with_subtitles_v2(
                dialogue_data=script.script_data,
                voice_mapping=voice_mapping,
                output_file=temp_output_path,
                subtitle_file=temp_subtitle_path
            )
            
            if not synthesis_result['success']:
                error_msg = f"对话音频合成失败: {synthesis_result['error']}"
                logger.error(error_msg)
                
                # 更新用户任务为失败状态
                if 'user_task' in locals():
                    user_task.status = 'failure'
                    user_task.error_message = error_msg
                    user_task.save()
                
                raise Exception(error_msg)
            
            # 更新任务状态
            self.update_state(state='PROCESSING', meta={'message': '音频和字幕生成完成，正在保存...'})
            
            # 保存音频文件到对话脚本
            filename = f"dialogue_{script_id}_{int(time.time())}.wav"
            
            with open(temp_output_path, "rb") as f:
                script.audio_file.save(filename, ContentFile(f.read()))
            
            # 保存字幕文件到对话脚本
            try:
                logger.info(f"Checking subtitle file: {temp_subtitle_path}")
                logger.info(f"Subtitle file exists: {os.path.exists(temp_subtitle_path)}")
                
                if os.path.exists(temp_subtitle_path):
                    logger.info(f"Subtitle file size: {os.path.getsize(temp_subtitle_path)}")
                
                with open(temp_subtitle_path, "r", encoding='utf-8') as f:
                    srt_content = f.read()
                
                logger.info(f"Read subtitle content, length: {len(srt_content) if srt_content else 0}")
                if srt_content:
                    logger.info(f"Subtitle content preview: {srt_content[:200] if srt_content else 'None'}")
                
                if srt_content and srt_content.strip():
                    subtitle_filename = f"dialogue_subtitle_{script_id}_{int(time.time())}.srt"
                    logger.info(f"Saving subtitle file: {subtitle_filename}")
                    script.subtitle_file.save(subtitle_filename, ContentFile(srt_content.encode('utf-8')))
                    # 重要：保存后需要刷新实例以确保字段正确更新
                    script.save(update_fields=['subtitle_file'])
                    script.refresh_from_db()
                    logger.info(f"Subtitle file saved: {script.subtitle_file.url if script.subtitle_file else 'None'}")
                    logger.info(f"Subtitle file name: {script.subtitle_file.name if script.subtitle_file else 'None'}")
                else:
                    logger.warning("No subtitle content to save or content is empty")
                    # 检查临时文件内容
                    if os.path.exists(temp_subtitle_path):
                        with open(temp_subtitle_path, "rb") as f:
                            raw_content = f.read()
                            logger.warning(f"Raw subtitle file content (bytes): {raw_content[:200] if raw_content else 'None'}")
            except Exception as e:
                logger.error(f"Error reading or saving subtitle file: {e}", exc_info=True)
            
            # 获取音频时长
            try:
                audio_duration = get_audio_duration(temp_output_path, "")
                script.audio_duration = audio_duration
            except Exception as e:
                logger.warning(f"Failed to get audio duration: {e}")
                script.audio_duration = multi_voice_tts.estimate_audio_duration(script.script_data)
            
            script.save()
            
            # 扣除用户积分
            try:
                # 刷新用户配额以获取最新数据
                user_quota.refresh_from_db()
                
                # 获取实际音频时长并计算所需积分
                actual_duration_seconds = script.audio_duration
                required_points = PointsManager.get_audio_generation_points(actual_duration_seconds)
                
                # 扣除积分
                user_quota.consume_points(required_points)
                
                # 记录成功的音频创建操作
                OperationRecord.objects.create(
                    user=user,
                    operation_type='audio_create',
                    operation_object=f'对话脚本 - {script.title}',
                    operation_detail=f'成功创建对话音频：{script.title}，时长 {actual_duration_seconds} 秒，消耗积分 {required_points} 分',
                    status='success',
                    metadata={
                        'script_id': script_id,
                        'audio_duration': actual_duration_seconds,
                        'points_consumed': required_points
                    }
                )
                
                logger.info(f"Successfully consumed {required_points} points for dialogue audio generation")
                
            except Exception as e:
                logger.error(f"Failed to deduct points for dialogue audio: {e}", exc_info=True)
                # 积分扣除失败不影响任务成功状态，但需要记录错误
            
            # 更新用户任务为成功状态
            if 'user_task' in locals():
                user_task.status = 'success'
                user_task.progress_message = '对话音频和字幕生成完成'
                user_task.result_data = {
                    'audio_file': script.audio_file.url if script.audio_file else None,
                    'subtitle_file': script.subtitle_file.url if script.subtitle_file else None,
                    'audio_duration': script.audio_duration,
                    'segments_count': synthesis_result.get('segments_count', 0),
                    'subtitle_entries': synthesis_result.get('subtitle_entries', 0)
                }
                user_task.completed_at = timezone.now()
                user_task.save()
            
            logger.info(f"Dialogue audio generation with subtitles completed for script {script_id}")
            
            # 确保返回正确的URL
            audio_file_url = script.audio_file.url if script.audio_file else None
            subtitle_file_url = script.subtitle_file.url if script.subtitle_file else None
            
            logger.info(f"Returning - Audio file: {audio_file_url}")
            logger.info(f"Returning - Subtitle file: {subtitle_file_url}")
            
            return {
                'success': True,
                'script_id': script_id,
                'audio_file': audio_file_url,
                'subtitle_file': subtitle_file_url,
                'audio_duration': script.audio_duration
            }
            
        finally:
            # 清理临时文件
            for path in [temp_output_path, temp_subtitle_path]:
                if os.path.exists(path):
                    try:
                        os.unlink(path)
                    except Exception as e:
                        logger.warning(f"Failed to cleanup temp file {path}: {e}")
    
    except Exception as e:
        error_msg = f"对话音频生成任务失败: {str(e)}"
        logger.error(error_msg)
        
        # 更新用户任务为失败状态
        try:
            user_task = UserTask.objects.get(task_id=self.request.id)
            user_task.status = 'failure'
            user_task.error_message = error_msg
            user_task.completed_at = timezone.now()
            user_task.save()
        except UserTask.DoesNotExist:
            pass
        
        self.update_state(
            state='FAILURE',
            meta={'error': error_msg}
        )
        raise 