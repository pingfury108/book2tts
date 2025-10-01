from pathlib import Path
from django.utils import timezone
from django.db import models
from django.conf import settings
import uuid
import hashlib
import re
from django.db.models.signals import post_save
from django.dispatch import receiver

# Create your models here.


class Books(models.Model):
    PDF_TYPE_CHOICES = [
        ('unknown', '未检测'),
        ('text', '文本版'),
        ('scanned', '扫描版'),
    ]
    
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='books', null=True, blank=True)
    name = models.TextField(default="")
    file_type = models.TextField(default="")
    file = models.FileField(upload_to='books/%Y/%m/%d/')
    md5_hash = models.CharField(max_length=32, blank=True, db_index=True, help_text="文件的MD5哈希值，用于检测重复文件")
    pdf_type = models.CharField(max_length=20, choices=PDF_TYPE_CHOICES, default='unknown', help_text="PDF类型：文本版或扫描版")
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(default=timezone.now)

    def __str__(self) -> str:
        return self.name.__str__()
    
    def get_pdf_type_display_name(self):
        """获取PDF类型的显示名称"""
        return dict(self.PDF_TYPE_CHOICES).get(self.pdf_type, '未知')
    
    def should_use_ocr(self):
        """判断是否应该使用OCR"""
        return self.file_type == ".pdf" and self.pdf_type == 'scanned'
    
    def detect_and_update_pdf_type(self):
        """检测并更新PDF类型"""
        if self.file_type != ".pdf":
            return False
        
        try:
            from book2tts.pdf import detect_scanned_pdf
            detection_result = detect_scanned_pdf(self.file.path)
            
            self.pdf_type = 'scanned' if detection_result['is_scanned'] else 'text'
            self.save(update_fields=['pdf_type', 'updated_at'])
            return True
        except Exception as e:
            # 检测失败，保持unknown状态
            return False

    def calculate_md5(self):
        """计算文件的MD5哈希值"""
        if not self.file:
            return ""
        
        try:
            hash_md5 = hashlib.md5()
            self.file.seek(0)  # 确保从文件开头读取
            for chunk in iter(lambda: self.file.read(4096), b""):
                hash_md5.update(chunk)
            self.file.seek(0)  # 重置文件指针
            return hash_md5.hexdigest()
        except Exception:
            return ""

    def setkw(self, user):
        file = Path(self.file.path)
        self.user = user
        self.name = file.stem
        self.file_type = file.suffix
        # 计算并设置MD5哈希值
        if not self.md5_hash:
            self.md5_hash = self.calculate_md5()
        
        # 如果是PDF文件，自动检测类型
        if self.file_type == ".pdf":
            try:
                from book2tts.pdf import detect_scanned_pdf
                detection_result = detect_scanned_pdf(self.file.path)
                self.pdf_type = 'scanned' if detection_result['is_scanned'] else 'text'
            except Exception as e:
                # 检测失败，设置为unknown
                self.pdf_type = 'unknown'
        
        return

    def save(self, *args, **kwargs):
        if not self.id:
            self.created_at = timezone.now()
        self.updated_at = timezone.now()
        return super().save(*args, **kwargs)


class AudioSegment(models.Model):
    book = models.ForeignKey(Books, on_delete=models.CASCADE, related_name='audio_segments')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='audio_segments', null=True)
    title = models.CharField(max_length=255)
    text = models.TextField()
    book_page = models.CharField(max_length=255)
    file = models.FileField(upload_to='audio_segments/%Y/%m/%d/')
    subtitle_file = models.FileField(upload_to='subtitles/audio_segments/%Y/%m/%d/', null=True, blank=True, verbose_name='字幕文件')
    chapters = models.JSONField(default=list, blank=True, help_text="音频章节时间线")
    published = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(default=timezone.now)

    def __str__(self) -> str:
        return f"{self.title} - {self.book.name}"
        
    def save(self, *args, **kwargs):
        if not self.id:
            self.created_at = timezone.now()
        self.updated_at = timezone.now()
        return super().save(*args, **kwargs)


# Add UserProfile model
class UserProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='profile')
    rss_token = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)

    def __str__(self):
        return f'{self.user.username} Profile'

# Signal to create/update UserProfile whenever a User object is saved
@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    try:
        # 尝试获取用户的profile
        profile = instance.profile
    except UserProfile.DoesNotExist:
        # 如果用户没有profile，创建一个
        profile = UserProfile.objects.create(user=instance)
    profile.save()

class UserTask(models.Model):
    """用户任务模型，用于跟踪Celery异步任务"""
    TASK_STATUS_CHOICES = [
        ('pending', '等待中'),
        ('processing', '处理中'),
        ('success', '已完成'),
        ('failure', '失败'),
        ('revoked', '已取消'),
    ]
    
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='tasks')
    task_id = models.CharField(max_length=255, unique=True, db_index=True)
    task_type = models.CharField(max_length=50, default='audio_synthesis')  # 任务类型
    book = models.ForeignKey(Books, on_delete=models.CASCADE, null=True, blank=True)
    title = models.CharField(max_length=500, blank=True)
    status = models.CharField(max_length=20, choices=TASK_STATUS_CHOICES, default='pending')
    progress_message = models.TextField(blank=True)  # 进度消息
    result_data = models.JSONField(null=True, blank=True)  # 任务结果数据
    error_message = models.TextField(blank=True)  # 错误消息
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    # 任务相关的元数据
    metadata = models.JSONField(default=dict, blank=True)  # 存储额外的任务信息
    
    class Meta:
        ordering = ['-created_at']
        
    def __str__(self):
        return f"{self.user.username} - {self.task_type} - {self.status}"
    
    @property
    def duration(self):
        """计算任务执行时长"""
        if self.completed_at:
            return self.completed_at - self.created_at
        return None
    
    @property
    def is_finished(self):
        """检查任务是否已完成（无论成功还是失败）"""
        return self.status in ['success', 'failure', 'revoked']

def tts_preview_upload_to(instance, filename):
    """生成固定的试听文件路径，避免重复文件。"""
    safe_voice = re.sub(r'[^A-Za-z0-9._-]+', '_', instance.voice_name or 'voice')
    return f"tts_previews/{instance.tts_provider}/{safe_voice}.wav"


TTS_PROVIDER_CHOICES = [
    ('edge_tts', 'Edge TTS'),
    ('azure', 'Azure TTS'),
]


class TTSVoicePreview(models.Model):
    """缓存不同提供商音色的试听音频文件。"""

    tts_provider = models.CharField(max_length=20, choices=TTS_PROVIDER_CHOICES)
    voice_name = models.CharField(max_length=100)
    file = models.FileField(upload_to=tts_preview_upload_to, blank=True)
    last_generated_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('tts_provider', 'voice_name')
        ordering = ['tts_provider', 'voice_name']

    def __str__(self) -> str:
        return f"{self.get_tts_provider_display()} - {self.voice_name}"


class TTSProviderConfig(models.Model):
    """全局 TTS 供应商配置，允许后台管理默认供应商。"""

    default_provider = models.CharField(max_length=20, choices=TTS_PROVIDER_CHOICES, default='edge_tts')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "TTS 供应商配置"
        verbose_name_plural = "TTS 供应商配置"

    def __str__(self) -> str:
        return f"默认供应商：{self.get_default_provider_display()}"

    @classmethod
    def get_default_provider(cls) -> str:
        return (
            cls.objects.order_by('-updated_at')
            .values_list('default_provider', flat=True)
            .first()
            or 'edge_tts'
        )

class DialogueScript(models.Model):
    """对话脚本模型，存储LLM转换后的对话脚本"""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='dialogue_scripts')
    book = models.ForeignKey(Books, on_delete=models.CASCADE, related_name='dialogue_scripts', null=True, blank=True)
    title = models.CharField(max_length=500, help_text="对话脚本标题")
    original_text = models.TextField(help_text="原始文本内容")
    script_data = models.JSONField(help_text="LLM解析后的JSON格式对话数据")
    
    # 音频生成相关
    audio_file = models.FileField(upload_to='dialogue_audio/%Y/%m/%d/', null=True, blank=True)
    subtitle_file = models.FileField(upload_to='subtitles/dialogue_scripts/%Y/%m/%d/', null=True, blank=True, verbose_name='字幕文件')
    audio_duration = models.FloatField(null=True, blank=True, help_text="音频时长（秒）")
    chapters = models.JSONField(default=list, blank=True, help_text="音频章节时间线")
    published = models.BooleanField(default=False, help_text="是否发布到成品")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.title} - {self.user.username}"
    
    @property
    def segment_count(self):
        """获取对话段落数量"""
        if self.script_data and 'segments' in self.script_data:
            return len(self.script_data['segments'])
        return 0
    
    @property
    def speakers(self):
        """获取对话中的所有说话者"""
        speakers = set()
        if self.script_data and 'segments' in self.script_data:
            for segment in self.script_data['segments']:
                speakers.add(segment.get('speaker', ''))
        return list(speakers)

    def get_voice_settings(self) -> dict:
        """获取脚本内保存的音色配置。"""
        data = self.script_data or {}
        voice_settings = data.get('voice_settings', {})
        return voice_settings if isinstance(voice_settings, dict) else {}

    @property
    def voice_settings(self) -> dict:
        return self.get_voice_settings()
    
    def sync_script_data_with_segments(self):
        """同步script_data与DialogueSegment表数据"""
        segments = self.segments.all().order_by('sequence')
        
        if not segments.exists():
            # 如果没有片段，清空script_data
            self.script_data = {'segments': []}
            self.save(update_fields=['script_data'])
            return
        
        # 重建script_data中的segments数组
        segments_data = []
        for segment in segments:
            segments_data.append({
                'speaker': segment.speaker,
                'utterance': segment.utterance,  # 使用正确的字段名
                'dialogue_type': segment.dialogue_type
            })
        
        # 更新script_data
        if not self.script_data:
            self.script_data = {}
        
        self.script_data['segments'] = segments_data
        self.save(update_fields=['script_data'])


class DialogueSegment(models.Model):
    """对话片段模型，用于存储角色音色配置"""
    script = models.ForeignKey(DialogueScript, on_delete=models.CASCADE, related_name='segments')
    speaker = models.CharField(max_length=100, help_text="说话者名称")
    sequence = models.IntegerField(help_text="片段顺序")
    utterance = models.TextField(help_text="说话内容")
    dialogue_type = models.CharField(max_length=20, choices=[('dialogue', '对话'), ('narration', '旁白')], default='dialogue')
    
    # 音频相关
    audio_file = models.FileField(upload_to='dialogue_segments/%Y/%m/%d/', null=True, blank=True)
    audio_duration = models.FloatField(null=True, blank=True, help_text="片段音频时长（秒）")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['script', 'sequence']
        unique_together = ['script', 'sequence']
    
    def __str__(self):
        return f"{self.script.title} - {self.speaker} (#{self.sequence})"


class OCRCache(models.Model):
    """OCR缓存模型，基于图片MD5存储OCR识别结果"""
    image_md5 = models.CharField(max_length=32, unique=True, db_index=True, help_text="图片的MD5哈希值")
    ocr_text = models.TextField(help_text="OCR识别的文本内容")
    source_type = models.CharField(max_length=20, choices=[('page_image', '页面图片'), ('manual_upload', '手动上传')], default='page_image')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"OCR Cache {self.image_md5[:8]}..."
