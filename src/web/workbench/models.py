from pathlib import Path
from django.utils import timezone
from django.db import models
from django.conf import settings
import uuid
import hashlib
from django.db.models.signals import post_save
from django.dispatch import receiver

# Create your models here.


class Books(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='books', null=True, blank=True)
    name = models.TextField(default="")
    file_type = models.TextField(default="")
    file = models.FileField(upload_to='books/%Y/%m/%d/')
    md5_hash = models.CharField(max_length=32, blank=True, db_index=True, help_text="文件的MD5哈希值，用于检测重复文件")
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(default=timezone.now)

    def __str__(self) -> str:
        return self.name.__str__()

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

class VoiceRole(models.Model):
    """音色角色模型，用于管理对话中的角色和对应的TTS音色"""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='voice_roles')
    name = models.CharField(max_length=100, help_text="角色名称，如：主持人、嘉宾、旁白等")
    tts_provider = models.CharField(max_length=20, choices=[('edge_tts', 'Edge TTS'), ('azure', 'Azure TTS')], default='azure')
    voice_name = models.CharField(max_length=100, help_text="TTS语音模型名称")
    is_default = models.BooleanField(default=False, help_text="是否为默认角色")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['user', 'name']
        ordering = ['name']
    
    def __str__(self):
        return f"{self.user.username} - {self.name} ({self.voice_name})"


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
    voice_role = models.ForeignKey(VoiceRole, on_delete=models.SET_NULL, null=True, blank=True, help_text="分配的音色角色")
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
