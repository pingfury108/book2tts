from django.db import models
from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver

# Create your models here.

class UserQuota(models.Model):
    """用户用量控制模型"""
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='quota',
        verbose_name='用户'
    )
    
    # 剩余可用音频制作时长（秒）
    remaining_audio_duration = models.PositiveIntegerField(
        default=3600,  # 默认1小时 = 3600秒
        verbose_name='剩余音频时长(秒)',
        help_text='用户剩余可用的音频制作时长，单位为秒'
    )
    
    # 可用存储空间大小（字节）
    available_storage_bytes = models.PositiveBigIntegerField(
        default=1073741824,  # 默认1GB = 1024*1024*1024字节
        verbose_name='可用存储空间(字节)',
        help_text='用户可用的存储空间大小，单位为字节'
    )
    
    # 创建和更新时间
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    
    class Meta:
        verbose_name = '用户配额'
        verbose_name_plural = '用户配额'
        
    def __str__(self):
        return f'{self.user.username} - 音频时长:{self.remaining_audio_duration}秒, 存储:{self.get_storage_display()}'
    
    def get_storage_display(self):
        """获取存储空间的友好显示格式"""
        bytes_val = self.available_storage_bytes
        if bytes_val >= 1073741824:  # GB
            return f'{bytes_val / 1073741824:.2f} GB'
        elif bytes_val >= 1048576:  # MB
            return f'{bytes_val / 1048576:.2f} MB'
        elif bytes_val >= 1024:  # KB
            return f'{bytes_val / 1024:.2f} KB'
        else:
            return f'{bytes_val} 字节'
    
    def get_audio_duration_display(self):
        """获取音频时长的友好显示格式"""
        seconds = self.remaining_audio_duration
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60
        
        if hours > 0:
            return f'{hours}小时{minutes}分钟{secs}秒'
        elif minutes > 0:
            return f'{minutes}分钟{secs}秒'
        else:
            return f'{secs}秒'
    
    def can_create_audio(self, duration_seconds):
        """检查是否可以创建指定时长的音频"""
        return self.remaining_audio_duration >= duration_seconds
    
    def can_store_file(self, file_size_bytes):
        """检查是否可以存储指定大小的文件"""
        return self.available_storage_bytes >= file_size_bytes
    
    def consume_audio_duration(self, duration_seconds):
        """消耗音频时长"""
        if self.can_create_audio(duration_seconds):
            self.remaining_audio_duration -= duration_seconds
            self.save()
            return True
        return False
    
    def consume_storage(self, file_size_bytes):
        """消耗存储空间"""
        if self.can_store_file(file_size_bytes):
            self.available_storage_bytes -= file_size_bytes
            self.save()
            return True
        return False
    
    def add_audio_duration(self, duration_seconds):
        """增加音频时长配额"""
        self.remaining_audio_duration += duration_seconds
        self.save()
    
    def add_storage(self, storage_bytes):
        """增加存储空间配额"""
        self.available_storage_bytes += storage_bytes
        self.save()


# 信号处理器：当用户创建时自动创建对应的配额记录
@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_user_quota(sender, instance, created, **kwargs):
    """当用户创建时，自动创建用户配额记录"""
    if created:
        UserQuota.objects.create(user=instance)

@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def save_user_quota(sender, instance, **kwargs):
    """保存用户时，确保配额记录存在"""
    try:
        instance.quota.save()
    except UserQuota.DoesNotExist:
        UserQuota.objects.create(user=instance)
