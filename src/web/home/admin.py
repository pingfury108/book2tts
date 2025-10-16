from django.contrib import admin
from django import forms
from django.utils.html import format_html
from django.core.exceptions import ValidationError
from django.db import transaction
import re
from .models import UserQuota, OperationRecord, PointsConfig, SiteConfig

# Register your models here.


@admin.register(UserQuota)
class UserQuotaAdmin(admin.ModelAdmin):
    """用户积分配额管理"""
    
    list_display = (
        'user', 
        'points',
        'created_at', 
        'updated_at'
    )
    list_filter = ('created_at', 'updated_at')
    search_fields = ('user__username', 'user__email', 'user__first_name', 'user__last_name')
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('用户信息', {
            'fields': ('user',)
        }),
        ('积分管理', {
            'fields': ('points',),
            'description': '用户积分系统：积分可用于音频生成和OCR处理，具体扣分规则可在积分配置中设置'
        }),
        ('时间信息', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    # 保留有用的批量操作
    actions = ['add_100_points', 'add_500_points', 'add_1000_points', 'reset_points']
    
    def add_100_points(self, request, queryset):
        """为选中用户增加100积分"""
        try:
            with transaction.atomic():
                updated_count = 0
                for quota in queryset:
                    quota.add_points(100)
                    quota.save()
                    updated_count += 1
                
                # 记录批量操作
                OperationRecord.objects.create(
                    user=request.user,
                    operation_type='points_add',
                    operation_object='批量用户积分管理',
                    operation_detail=f'管理员批量为 {updated_count} 个用户增加100积分',
                    status='success',
                    metadata={
                        'action': 'add_100_points',
                        'user_count': updated_count,
                        'points_per_user': 100,
                        'total_points_added': updated_count * 100,
                        'admin_user': request.user.username
                    }
                )
                
            self.message_user(request, f'成功为 {updated_count} 个用户增加100积分')
        except Exception as e:
            self.message_user(request, f'增加积分失败：{str(e)}', level='error')
    add_100_points.short_description = '增加100积分'
    
    def add_500_points(self, request, queryset):
        """为选中用户增加500积分"""
        try:
            with transaction.atomic():
                updated_count = 0
                for quota in queryset:
                    quota.add_points(500)
                    quota.save()
                    updated_count += 1
                
                # 记录批量操作
                OperationRecord.objects.create(
                    user=request.user,
                    operation_type='points_add',
                    operation_object='批量用户积分管理',
                    operation_detail=f'管理员批量为 {updated_count} 个用户增加500积分',
                    status='success',
                    metadata={
                        'action': 'add_500_points',
                        'user_count': updated_count,
                        'points_per_user': 500,
                        'total_points_added': updated_count * 500,
                        'admin_user': request.user.username
                    }
                )
                
            self.message_user(request, f'成功为 {updated_count} 个用户增加500积分')
        except Exception as e:
            self.message_user(request, f'增加积分失败：{str(e)}', level='error')
    add_500_points.short_description = '增加500积分'
    
    def add_1000_points(self, request, queryset):
        """为选中用户增加1000积分"""
        try:
            with transaction.atomic():
                updated_count = 0
                for quota in queryset:
                    quota.add_points(1000)
                    quota.save()
                    updated_count += 1
                
                # 记录批量操作
                OperationRecord.objects.create(
                    user=request.user,
                    operation_type='points_add',
                    operation_object='批量用户积分管理',
                    operation_detail=f'管理员批量为 {updated_count} 个用户增加1000积分',
                    status='success',
                    metadata={
                        'action': 'add_1000_points',
                        'user_count': updated_count,
                        'points_per_user': 1000,
                        'total_points_added': updated_count * 1000,
                        'admin_user': request.user.username
                    }
                )
                
            self.message_user(request, f'成功为 {updated_count} 个用户增加1000积分')
        except Exception as e:
            self.message_user(request, f'增加积分失败：{str(e)}', level='error')
    add_1000_points.short_description = '增加1000积分'
    
    def reset_points(self, request, queryset):
        """重置选中用户的积分为默认值（1000积分）"""
        try:
            with transaction.atomic():
                updated = queryset.update(points=1000)
                
                # 记录批量操作
                OperationRecord.objects.create(
                    user=request.user,
                    operation_type='points_reset',
                    operation_object='批量用户积分管理',
                    operation_detail=f'管理员批量重置 {updated} 个用户的积分为默认值1000',
                    status='success',
                    metadata={
                        'action': 'reset_points',
                        'user_count': updated,
                        'new_points_value': 1000,
                        'admin_user': request.user.username
                    }
                )
                
            self.message_user(request, f'成功重置 {updated} 个用户的积分为默认值（1000积分）')
        except Exception as e:
            self.message_user(request, f'重置积分失败：{str(e)}', level='error')
    reset_points.short_description = '重置积分为默认值'


class OperationRecordAdmin(admin.ModelAdmin):
    """操作记录管理 - 只读模式"""
    
    # 列表显示字段
    list_display = (
        'user',
        'get_operation_summary',
        'get_status_display_colored',
        'operation_object',
        'ip_address',
        'created_at'
    )
    
    # 列表过滤器
    list_filter = (
        'operation_type',
        'status',
        'created_at',
        ('user', admin.RelatedOnlyFieldListFilter),
    )
    
    # 搜索字段
    search_fields = (
        'user__username',
        'user__email',
        'operation_object',
        'operation_detail',
        'ip_address'
    )
    
    # 只读字段 - 所有字段都设为只读
    readonly_fields = (
        'user',
        'operation_type',
        'operation_object',
        'operation_detail',
        'status',
        'metadata',
        'ip_address',
        'user_agent',
        'created_at',
        'get_metadata_display',
        'get_user_agent_display'
    )
    
    # 字段集
    fieldsets = (
        ('基本信息', {
            'fields': (
                'user',
                'operation_type',
                'operation_object',
                'status',
                'created_at'
            )
        }),
        ('详细信息', {
            'fields': (
                'operation_detail',
                'get_metadata_display',
            ),
            'classes': ('collapse',)
        }),
        ('技术信息', {
            'fields': (
                'ip_address',
                'get_user_agent_display',
            ),
            'classes': ('collapse',)
        }),
    )
    
    # 排序
    ordering = ['-created_at']
    
    # 每页显示数量
    list_per_page = 50
    
    # 禁用添加权限
    def has_add_permission(self, request):
        return False
    
    # 禁用修改权限
    def has_change_permission(self, request, obj=None):
        return False
    
    # 禁用删除权限
    def has_delete_permission(self, request, obj=None):
        return False
    
    def get_operation_summary(self, obj):
        """获取操作摘要"""
        return obj.get_operation_summary()
    get_operation_summary.short_description = '操作摘要'
    
    def get_status_display_colored(self, obj):
        """获取带颜色的状态显示"""
        return format_html(obj.get_status_display_with_color())
    get_status_display_colored.short_description = '状态'
    
    def get_metadata_display(self, obj):
        """格式化显示元数据"""
        if not obj.metadata:
            return '无'
        
        html_parts = ['<div style="background: #f8f9fa; padding: 10px; border-radius: 4px;">']
        for key, value in obj.metadata.items():
            html_parts.append(f'<p style="margin: 2px 0;"><strong>{key}:</strong> {value}</p>')
        html_parts.append('</div>')
        
        return format_html(''.join(html_parts))
    get_metadata_display.short_description = '元数据'
    
    def get_user_agent_display(self, obj):
        """格式化显示用户代理"""
        if not obj.user_agent:
            return '无'
        
        # 截断过长的用户代理字符串
        if len(obj.user_agent) > 100:
            truncated = obj.user_agent[:100] + '...'
            return format_html(
                '<div style="word-break: break-all; max-width: 400px;" title="{}">{}</div>',
                obj.user_agent,
                truncated
            )
        else:
            return format_html(
                '<div style="word-break: break-all; max-width: 400px;">{}</div>',
                obj.user_agent
            )
    get_user_agent_display.short_description = '用户代理'


@admin.register(PointsConfig)
class PointsConfigAdmin(admin.ModelAdmin):
    """积分配置管理"""
    
    list_display = (
        'operation_type',
        'get_operation_type_display',
        'points_per_unit',
        'unit_name',
        'is_active',
        'updated_at'
    )
    
    list_editable = ('points_per_unit', 'unit_name', 'is_active')
    
    list_filter = ('is_active', 'operation_type', 'updated_at')
    
    search_fields = ('operation_type', 'description')
    
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('基本信息', {
            'fields': ('operation_type', 'points_per_unit', 'unit_name', 'is_active')
        }),
        ('规则描述', {
            'fields': ('description',),
            'classes': ('collapse',)
        }),
        ('时间信息', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def save_model(self, request, obj, form, change):
        """保存模型"""
        super().save_model(request, obj, form, change)




# 注册操作记录管理
admin.site.register(OperationRecord, OperationRecordAdmin)


@admin.register(SiteConfig)
class SiteConfigAdmin(admin.ModelAdmin):
    """站点配置管理"""

    # 使用自定义模板
    change_form_template = "admin/site_config_form.html"

    # 列表显示字段
    list_display = (
        'google_ads_enabled',
        's3_enabled',
        'site_description_preview',
        'site_keywords_preview',
        'updated_at'
    )

    # 字段集
    fieldsets = (
        ('Google Ads 配置', {
            'fields': (
                'google_ads_enabled',
                'google_ads_script',
                'ads_txt_content',
            ),
            'description': '配置 Google Ads 相关设置，启用后会在网站头部添加广告脚本'
        }),
        ('S3 对象存储配置', {
            'fields': (
                's3_enabled',
                's3_access_key_id',
                's3_secret_access_key',
                's3_bucket_name',
                's3_region',
                's3_endpoint_url',
                's3_custom_domain',
                's3_prefix',
            ),
            'description': '配置 S3 对象存储，启用后文件将上传到 S3 存储桶'
        }),
        ('SEO 配置', {
            'fields': (
                'site_description',
                'site_keywords',
            ),
            'description': '配置站点的 SEO 信息，这些信息会添加到页面的 meta 标签中'
        }),
        ('时间信息', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    # 只读字段
    readonly_fields = ('created_at', 'updated_at')

    # 禁用添加权限（单例模式）
    def has_add_permission(self, request):
        return False

    # 禁用删除权限（单例模式）
    def has_delete_permission(self, request, obj=None):
        return False

    def site_description_preview(self, obj):
        """站点描述预览"""
        if obj.site_description:
            if len(obj.site_description) > 50:
                return f'{obj.site_description[:50]}...'
            return obj.site_description
        return '未设置'
    site_description_preview.short_description = '站点描述'

    def site_keywords_preview(self, obj):
        """站点关键词预览"""
        if obj.site_keywords:
            if len(obj.site_keywords) > 50:
                return f'{obj.site_keywords[:50]}...'
            return obj.site_keywords
        return '未设置'
    site_keywords_preview.short_description = '站点关键词'
