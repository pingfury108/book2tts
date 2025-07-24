import os
import time
import tempfile
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
from book2tts.multi_voice_tts import MultiVoiceTTS

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
    """异步音频合成任务"""
    try:
        # 更新任务状态为开始处理
        self.update_state(state='PROCESSING', meta={'message': '开始音频合成...'})
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
        
        # 检查配额
        if not user_quota.can_create_audio(estimated_duration_seconds):
            error_msg = f"配额不足。预估需要 {estimated_duration_seconds} 秒，剩余 {user_quota.remaining_audio_duration} 秒"
            logger.warning(f"Insufficient quota for user {user_id}: {error_msg}")
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
                    'remaining_quota': user_quota.remaining_audio_duration,
                    'text_length': len(text),
                    'voice_name': voice_name,
                    'error_reason': 'insufficient_quota'
                },
                ip_address=ip_address,
                user_agent=user_agent
            )
            raise Exception(error_msg)
        
        # 更新任务状态
        self.update_state(state='PROCESSING', meta={'message': '正在生成音频文件...'})
        
        # 创建临时文件
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
            temp_path = temp_file.name
        
        try:
            # 使用 EdgeTTS 合成音频
            logger.info(f"Starting TTS synthesis with voice {voice_name}")
            tts = EdgeTTS(voice_name=voice_name)
            success = tts.synthesize_long_text(text=text, output_file=temp_path)
            
            if not success:
                error_msg = "EdgeTTS合成失败"
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
                        'error_reason': 'tts_synthesis_failed'
                    },
                    ip_address=ip_address,
                    user_agent=user_agent
                )
                raise Exception(error_msg)
            
            # 更新任务状态
            self.update_state(state='PROCESSING', meta={'message': '音频生成完成，正在保存...'})
            
            # 获取实际音频时长
            actual_duration_seconds = get_audio_duration(temp_path, text)
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
                with open(temp_path, "rb") as f:
                    audio_segment.file.save(filename, ContentFile(f.read()))
                
                # 保存 AudioSegment
                audio_segment.save()
                
                # 刷新用户配额以获取最新数据
                user_quota.refresh_from_db()
                
                # 强制扣除用户配额
                user_quota.force_consume_audio_duration(actual_duration_seconds)
                
                # 记录成功的音频创建操作
                OperationRecord.objects.create(
                    user=user,
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
                    ip_address=ip_address,
                    user_agent=user_agent
                )
            
            logger.info(f"Audio synthesis task completed successfully for user {user_id}")
            
            # 返回成功结果
            return {
                'status': 'SUCCESS',
                'message': '音频合成完成',
                'audio_url': audio_segment.file.url,
                'audio_id': audio_segment.id,
                'audio_duration': actual_duration_seconds,
                'remaining_quota': user_quota.remaining_audio_duration
            }
            
        finally:
            # 清理临时文件
            if os.path.exists(temp_path):
                os.remove(temp_path)
    
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
    """生成对话音频的异步任务"""
    try:
        # 更新任务状态
        self.update_state(state='PROCESSING', meta={'message': '开始生成对话音频...'})
        logger.info(f"Starting dialogue audio generation for script {script_id}")
        
        # 获取对话脚本
        try:
            script = DialogueScript.objects.get(pk=script_id)
        except DialogueScript.DoesNotExist:
            error_msg = f"对话脚本不存在: {script_id}"
            logger.error(error_msg)
            raise Exception(error_msg)
        
        # 更新用户任务状态
        try:
            user_task = UserTask.objects.get(task_id=self.request.id)
            user_task.status = 'processing'
            user_task.progress_message = '正在生成对话音频...'
            user_task.save()
        except UserTask.DoesNotExist:
            logger.warning(f"UserTask not found for task {self.request.id}")
        
        # 初始化多音色TTS服务
        multi_voice_tts = MultiVoiceTTS()
        
        # 创建临时输出文件
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
            temp_output_path = temp_file.name
        
        try:
            # 更新任务状态
            self.update_state(state='PROCESSING', meta={'message': '正在合成多角色音频...'})
            
            # 生成对话音频
            synthesis_result = multi_voice_tts.synthesize_dialogue(
                dialogue_data=script.script_data,
                voice_mapping=voice_mapping,
                output_file=temp_output_path
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
            self.update_state(state='PROCESSING', meta={'message': '音频生成完成，正在保存...'})
            
            # 保存音频文件到对话脚本
            filename = f"dialogue_{script_id}_{int(time.time())}.wav"
            
            with open(temp_output_path, "rb") as f:
                script.audio_file.save(filename, ContentFile(f.read()))
            
            # 获取音频时长
            try:
                audio_duration = get_audio_duration(temp_output_path, "")
                script.audio_duration = audio_duration
            except Exception as e:
                logger.warning(f"Failed to get audio duration: {e}")
                script.audio_duration = multi_voice_tts.estimate_audio_duration(script.script_data)
            
            script.save()
            
            # 更新用户任务为成功状态
            if 'user_task' in locals():
                user_task.status = 'success'
                user_task.progress_message = '对话音频生成完成'
                user_task.result_data = {
                    'audio_file': script.audio_file.url if script.audio_file else None,
                    'audio_duration': script.audio_duration,
                    'segments_count': synthesis_result.get('segments_count', 0),
                    'speakers': synthesis_result.get('speakers', [])
                }
                user_task.completed_at = timezone.now()
                user_task.save()
            
            logger.info(f"Dialogue audio generation completed for script {script_id}")
            
            return {
                'success': True,
                'script_id': script_id,
                'audio_file': script.audio_file.url if script.audio_file else None,
                'audio_duration': script.audio_duration
            }
            
        finally:
            # 清理临时文件
            if os.path.exists(temp_output_path):
                try:
                    os.unlink(temp_output_path)
                except Exception as e:
                    logger.warning(f"Failed to cleanup temp file {temp_output_path}: {e}")
    
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