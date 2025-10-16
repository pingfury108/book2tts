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


class SiteConfig(models.Model):
    """站点配置模型（单例模式）"""

    # Google Ads 配置
    google_ads_enabled = models.BooleanField(
        default=False,
        verbose_name='启用 Google Ads',
        help_text='是否在网站中启用 Google Ads 脚本'
    )

    google_ads_script = models.TextField(
        blank=True,
        verbose_name='Google Ads 脚本',
        help_text='Google Ads 的 JavaScript 脚本代码'
    )

    # ads.txt 内容
    ads_txt_content = models.TextField(
        blank=True,
        verbose_name='ads.txt 内容',
        help_text='ads.txt 文件的内容，用于广告验证'
    )

    # SEO 配置
    site_description = models.TextField(
        blank=True,
        verbose_name='站点描述',
        help_text='站点的 meta description，用于 SEO'
    )

    site_keywords = models.TextField(
        blank=True,
        verbose_name='站点关键词',
        help_text='站点的 meta keywords，用于 SEO'
    )

    # S3 对象存储配置
    s3_enabled = models.BooleanField(
        default=False,
        verbose_name='启用 S3 对象存储',
        help_text='是否启用 S3 对象存储（启用后文件将上传到S3）'
    )

    s3_access_key_id = models.CharField(
        max_length=255,
        blank=True,
        verbose_name='S3 Access Key ID',
        help_text='S3 访问密钥 ID'
    )

    s3_secret_access_key = models.CharField(
        max_length=255,
        blank=True,
        verbose_name='S3 Secret Access Key',
        help_text='S3 秘密访问密钥'
    )

    s3_bucket_name = models.CharField(
        max_length=255,
        blank=True,
        verbose_name='S3 存储桶名称',
        help_text='S3 存储桶名称'
    )

    s3_region = models.CharField(
        max_length=50,
        blank=True,
        default='us-east-1',
        verbose_name='S3 区域',
        help_text='S3 存储区域（如：us-east-1, cn-north-1）'
    )

    s3_endpoint_url = models.CharField(
        max_length=255,
        blank=True,
        verbose_name='S3 端点URL',
        help_text='S3 兼容服务的端点URL（如使用其他S3兼容服务）'
    )

    s3_custom_domain = models.CharField(
        max_length=255,
        blank=True,
        verbose_name='S3 自定义域名',
        help_text='S3 自定义域名（用于CDN加速）'
    )

    s3_prefix = models.CharField(
        max_length=100,
        blank=True,
        default='media/',
        verbose_name='S3 路径前缀',
        help_text='S3 存储路径前缀'
    )

    # 创建和更新时间
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        verbose_name = '站点配置'
        verbose_name_plural = '站点配置'

    def __str__(self):
        return '站点配置'

    def save(self, *args, **kwargs):
        """确保只有一个站点配置实例"""
        if not self.pk and SiteConfig.objects.exists():
            # 如果已经存在实例，更新现有实例而不是创建新实例
            existing = SiteConfig.objects.first()
            existing.google_ads_enabled = self.google_ads_enabled
            existing.google_ads_script = self.google_ads_script
            existing.ads_txt_content = self.ads_txt_content
            existing.site_description = self.site_description
            existing.site_keywords = self.site_keywords
            existing.s3_enabled = self.s3_enabled
            existing.s3_access_key_id = self.s3_access_key_id
            existing.s3_secret_access_key = self.s3_secret_access_key
            existing.s3_bucket_name = self.s3_bucket_name
            existing.s3_region = self.s3_region
            existing.s3_endpoint_url = self.s3_endpoint_url
            existing.s3_custom_domain = self.s3_custom_domain
            existing.s3_prefix = self.s3_prefix
            existing.save()
            return existing
        return super().save(*args, **kwargs)

    @classmethod
    def get_config(cls):
        """获取站点配置（单例）"""
        config, created = cls.objects.get_or_create(pk=1)
        return config


class DiscussionTopic(models.Model):
    """独立讨论主题模型"""

    # 主题分类
    CATEGORY_CHOICES = [
        ('general', '综合讨论'),
        ('technical', '技术交流'),
        ('feedback', '反馈建议'),
        ('help', '求助问答'),
        ('announcement', '公告通知'),
        ('other', '其他话题'),
    ]

    title = models.CharField(
        max_length=200,
        verbose_name='主题标题',
        help_text='讨论主题的标题'
    )

    content = models.TextField(
        verbose_name='主题内容',
        help_text='主题的详细描述和内容'
    )

    category = models.CharField(
        max_length=20,
        choices=CATEGORY_CHOICES,
        default='general',
        verbose_name='主题分类',
        help_text='选择主题的分类'
    )

    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='discussion_topics',
        verbose_name='创建者',
        help_text='创建此主题的用户'
    )

    # 主题状态
    is_pinned = models.BooleanField(
        default=False,
        verbose_name='是否置顶',
        help_text='是否将此主题置顶显示'
    )

    is_closed = models.BooleanField(
        default=False,
        verbose_name='是否关闭',
        help_text='是否关闭此主题，关闭后不能回复'
    )

    # 统计信息
    view_count = models.PositiveIntegerField(
        default=0,
        verbose_name='查看次数',
        help_text='主题被查看的次数'
    )

    reply_count = models.PositiveIntegerField(
        default=0,
        verbose_name='回复数量',
        help_text='主题下的回复数量'
    )

    last_reply_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='最后回复时间',
        help_text='最后一条回复的时间'
    )

    # 创建和更新时间
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        verbose_name = '讨论主题'
        verbose_name_plural = '讨论主题'
        ordering = ['-is_pinned', '-last_reply_at', '-created_at']
        indexes = [
            models.Index(fields=['category', '-created_at']),
            models.Index(fields=['author', '-created_at']),
            models.Index(fields=['is_pinned', '-created_at']),
            models.Index(fields=['-last_reply_at']),
        ]

    def __str__(self):
        return f'{self.title} - {self.author.username}'

    def get_absolute_url(self):
        """获取主题的绝对URL"""
        from django.urls import reverse
        return reverse('discussion_topic_detail', kwargs={'topic_id': self.id})

    def increment_view_count(self, user=None):
        """增加查看次数，如果提供了用户且用户是作者则不增加"""
        # 如果提供了用户且用户是作者，则不增加查看次数
        if user and user == self.author:
            return

        self.view_count += 1
        self.save(update_fields=['view_count'])

    def update_reply_stats(self):
        """更新回复统计信息"""
        from django.contrib.contenttypes.models import ContentType
        from .models import Comment

        content_type = ContentType.objects.get_for_model(DiscussionTopic)
        self.reply_count = Comment.objects.filter(
            content_type=content_type,
            object_id=self.id
        ).count()

        last_reply = Comment.objects.filter(
            content_type=content_type,
            object_id=self.id
        ).order_by('-created_at').first()

        if last_reply:
            self.last_reply_at = last_reply.created_at

        self.save(update_fields=['reply_count', 'last_reply_at'])


class Comment(models.Model):
    """通用留言模型 - 支持关联任何对象和独立主题"""

    # 留言内容
    content = models.TextField(
        verbose_name='留言内容',
        help_text='留言的具体内容'
    )

    # 留言者
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='comments',
        verbose_name='留言者',
        help_text='发表留言的用户'
    )

    # 通用外键关联（支持任何模型）
    content_type = models.ForeignKey(
        'contenttypes.ContentType',
        on_delete=models.CASCADE,
        verbose_name='关联模型',
        help_text='留言关联的模型类型'
    )

    object_id = models.PositiveIntegerField(
        verbose_name='关联对象ID',
        help_text='留言关联的对象ID'
    )

    # 父级留言（支持回复）
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='replies',
        verbose_name='父级留言',
        help_text='如果是回复留言，则指向被回复的留言'
    )

    # 创建和更新时间
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        verbose_name = '留言'
        verbose_name_plural = '留言'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['content_type', 'object_id', '-created_at']),
            models.Index(fields=['author', '-created_at']),
            models.Index(fields=['parent', '-created_at']),
        ]

    def __str__(self):
        return f'{self.author.username} - {self.content[:50]}...'

    def get_associated_object(self):
        """获取关联的对象"""
        return self.content_type.get_object_for_this_type(id=self.object_id)

    def is_reply(self):
        """判断是否为回复留言"""
        return self.parent is not None

    def get_reply_count(self):
        """获取回复数量"""
        return self.replies.count()
