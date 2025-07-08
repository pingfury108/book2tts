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

from .models import Books, AudioSegment, DialogueScript, UserTask
from book2tts.edgetts import EdgeTTS
from book2tts.audio_utils import get_audio_duration, estimate_audio_duration_from_text
from home.models import UserQuota, OperationRecord
from book2tts.multi_voice_tts import MultiVoiceTTS

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