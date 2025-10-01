from django.db import models
from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver
import django.core.validators

# Create your models here.

class UserQuota(models.Model):
    """用户积分配额模型"""
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='quota',
        verbose_name='用户'
    )
    
    # 用户积分
    points = models.PositiveIntegerField(
        default=1000,  # 默认1000积分
        verbose_name='用户积分',
        help_text='用户可用于音频生成和OCR处理的积分'
    )
    
    # 创建和更新时间
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    
    class Meta:
        verbose_name = '用户配额'
        verbose_name_plural = '用户配额'
        
    def __str__(self):
        return f'{self.user.username} - {self.points}积分'
    
    def can_consume_points(self, points_needed):
        """检查是否可以消耗指定积分"""
        return self.points >= points_needed
    
    def consume_points(self, points_needed):
        """消耗积分"""
        if self.can_consume_points(points_needed):
            self.points -= points_needed
            self.save()
            return True
        return False
    
    def consume_points_for_audio(self, duration_seconds):
        """消耗音频生成积分"""
        from .utils import PointsManager
        points_needed = PointsManager.get_audio_generation_points(duration_seconds)
        return self.consume_points(points_needed)
    
    def consume_points_for_ocr(self, image_count):
        """消耗OCR处理积分"""
        from .utils import PointsManager
        points_needed = PointsManager.get_ocr_processing_points(image_count)
        return self.consume_points(points_needed)
    
    def add_points(self, points_to_add):
        """增加积分"""
        self.points += points_to_add
        self.save()


class OperationRecord(models.Model):
    """操作记录模型"""
    
    # 操作类型选择
    OPERATION_TYPES = [
        ('audio_create', '音频创建'),
        ('audio_delete', '音频删除'),
        ('file_upload', '文件上传'),
        ('file_delete', '文件删除'),
        ('quota_consume', '配额消耗'),
        ('quota_add', '配额增加'),
        ('user_login', '用户登录'),
        ('user_logout', '用户登出'),
        ('system_operation', '系统操作'),
        ('other', '其他操作'),
    ]
    
    # 操作状态
    STATUS_CHOICES = [
        ('success', '成功'),
        ('failed', '失败'),
        ('pending', '进行中'),
        ('cancelled', '已取消'),
    ]
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='operation_records',
        verbose_name='用户',
        help_text='执行操作的用户'
    )
    
    operation_type = models.CharField(
        max_length=50,
        choices=OPERATION_TYPES,
        verbose_name='操作类型',
        help_text='操作的类型分类'
    )
    
    operation_object = models.CharField(
        max_length=200,
        verbose_name='操作对象',
        help_text='操作的目标对象，如文件名、音频ID等',
        blank=True,
        null=True
    )
    
    operation_detail = models.TextField(
        verbose_name='详细描述',
        help_text='操作的详细描述信息',
        blank=True,
        null=True
    )
    
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='success',
        verbose_name='操作状态'
    )
    
    # 额外的元数据信息（JSON格式）
    metadata = models.JSONField(
        default=dict,
        blank=True,
        verbose_name='元数据',
        help_text='操作相关的额外信息，如文件大小、音频时长等'
    )
    
    # IP地址
    ip_address = models.GenericIPAddressField(
        verbose_name='IP地址',
        blank=True,
        null=True,
        help_text='操作时的IP地址'
    )
    
    # 用户代理
    user_agent = models.TextField(
        verbose_name='用户代理',
        blank=True,
        null=True,
        help_text='操作时的浏览器信息'
    )
    
    # 创建时间
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='操作时间'
    )
    
    class Meta:
        verbose_name = '操作记录'
        verbose_name_plural = '操作记录'
        ordering = ['-created_at']  # 按时间倒序排列
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['operation_type', '-created_at']),
            models.Index(fields=['status', '-created_at']),
        ]
    
    def __str__(self):
        return f'{self.user.username} - {self.get_operation_type_display()} - {self.operation_object or "无对象"} - {self.created_at.strftime("%Y-%m-%d %H:%M:%S")}'
    
    def get_operation_summary(self):
        """获取操作摘要"""
        summary = f'{self.get_operation_type_display()}'
        if self.operation_object:
            summary += f' - {self.operation_object}'
        return summary
    
    def get_status_display_with_color(self):
        """获取带颜色的状态显示"""
        status_colors = {
            'success': '#28a745',
            'failed': '#dc3545',
            'pending': '#ffc107',
            'cancelled': '#6c757d',
        }
        color = status_colors.get(self.status, '#6c757d')
        return f'<span style="color: {color}; font-weight: bold;">{self.get_status_display()}</span>'


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


class PointsConfig(models.Model):
    """积分配置模型"""
    
    # 操作类型选择
    OPERATION_TYPES = [
        ('audio_generation', '音频生成'),
        ('ocr_processing', 'OCR处理'),
        ('llm_usage', 'LLM调用'),
    ]
    
    operation_type = models.CharField(
        max_length=50,
        choices=OPERATION_TYPES,
        unique=True,
        verbose_name='操作类型',
        help_text='选择要配置的操作类型'
    )
    
    points_per_unit = models.IntegerField(
        default=0,
        validators=[
            django.core.validators.MinValueValidator(0),
            django.core.validators.MaxValueValidator(10000)
        ],
        verbose_name='每单位积分',
        help_text='每个单位操作需要的积分数'
    )
    
    unit_name = models.CharField(
        max_length=50,
        default='次',
        verbose_name='单位名称',
        help_text='计费单位名称，如：秒、页、次等'
    )
    
    is_active = models.BooleanField(
        default=True,
        verbose_name='是否启用',
        help_text='是否启用此积分规则'
    )
    
    description = models.TextField(
        blank=True,
        verbose_name='规则描述',
        help_text='对此积分规则的详细描述'
    )
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    
    class Meta:
        verbose_name = '积分配置'
        verbose_name_plural = '积分配置'
        ordering = ['operation_type']
    
    def __str__(self):
        return f'{self.get_operation_type_display()} - {self.points_per_unit}积分/{self.unit_name}'
