from django.contrib import admin
from django import forms
from django.utils.html import format_html
from django.core.exceptions import ValidationError
import re
from .models import UserQuota

# Register your models here.

class UserQuotaAdminForm(forms.ModelForm):
    """自定义表单，提供友好的输入方式"""
    
    # 音频时长输入字段 - 支持多种格式
    audio_duration_input = forms.CharField(
        label='音频时长',
        required=False,
        help_text='支持格式：1h30m20s、90分钟、3600秒、1.5小时等',
        widget=forms.TextInput(attrs={
            'placeholder': '例如: 1h30m、90分钟、3600秒、1.5小时',
            'style': 'width: 300px;'
        })
    )
    
    # 存储空间输入字段 - 支持多种格式
    storage_input = forms.CharField(
        label='存储空间',
        required=False,
        help_text='支持格式：1GB、500MB、1024KB、2048字节等',
        widget=forms.TextInput(attrs={
            'placeholder': '例如: 1GB、500MB、1024KB',
            'style': 'width: 300px;'
        })
    )
    
    class Meta:
        model = UserQuota
        fields = ['user', 'remaining_audio_duration', 'available_storage_bytes', 'audio_duration_input', 'storage_input']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # 隐藏实际的模型字段，只显示我们的自定义输入字段
        if 'remaining_audio_duration' in self.fields:
            self.fields['remaining_audio_duration'].widget = forms.HiddenInput()
        if 'available_storage_bytes' in self.fields:
            self.fields['available_storage_bytes'].widget = forms.HiddenInput()
        
        # 如果是编辑现有记录，显示当前值的友好格式
        if self.instance and self.instance.pk:
            # 设置音频时长的友好显示
            self.fields['audio_duration_input'].initial = self._format_duration_for_input(
                self.instance.remaining_audio_duration
            )
            
            # 设置存储空间的友好显示
            self.fields['storage_input'].initial = self._format_storage_for_input(
                self.instance.available_storage_bytes
            )
    
    def _format_duration_for_input(self, total_seconds):
        """将秒数转换为友好的输入格式"""
        if total_seconds == 0:
            return "0秒"
        
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60
        
        parts = []
        if hours > 0:
            parts.append(f"{hours}小时")
        if minutes > 0:
            parts.append(f"{minutes}分钟")
        if seconds > 0:
            parts.append(f"{seconds}秒")
        
        return "".join(parts)
    
    def _format_storage_for_input(self, bytes_val):
        """将字节数转换为友好的输入格式"""
        if bytes_val >= 1073741824:  # GB
            value = bytes_val / 1073741824
            if value == int(value):
                return f"{int(value)}GB"
            else:
                return f"{value:.2f}GB"
        elif bytes_val >= 1048576:  # MB
            value = bytes_val / 1048576
            if value == int(value):
                return f"{int(value)}MB"
            else:
                return f"{value:.2f}MB"
        elif bytes_val >= 1024:  # KB
            value = bytes_val / 1024
            if value == int(value):
                return f"{int(value)}KB"
            else:
                return f"{value:.2f}KB"
        else:
            return f"{bytes_val}字节"
    
    def _parse_duration(self, duration_str):
        """解析时长字符串，返回总秒数"""
        if not duration_str:
            return 0
        
        duration_str = duration_str.strip().lower()
        total_seconds = 0
        
        # 匹配各种格式
        patterns = [
            # 1h30m20s 格式
            (r'(\d+(?:\.\d+)?)h', 3600),
            (r'(\d+(?:\.\d+)?)m(?!b)', 60),  # 避免与MB冲突
            (r'(\d+(?:\.\d+)?)s', 1),
            
            # 中文格式
            (r'(\d+(?:\.\d+)?)小时', 3600),
            (r'(\d+(?:\.\d+)?)分钟', 60),
            (r'(\d+(?:\.\d+)?)秒', 1),
            
            # 纯数字 + 单位
            (r'(\d+(?:\.\d+)?)\s*小时', 3600),
            (r'(\d+(?:\.\d+)?)\s*分钟', 60),
            (r'(\d+(?:\.\d+)?)\s*秒', 1),
        ]
        
        found_match = False
        for pattern, multiplier in patterns:
            matches = re.findall(pattern, duration_str)
            for match in matches:
                total_seconds += float(match) * multiplier
                found_match = True
        
        # 如果没有匹配到任何模式，尝试解析为纯数字（默认为秒）
        if not found_match:
            try:
                total_seconds = float(duration_str)
            except ValueError:
                raise ValidationError(f'无法解析时长格式: {duration_str}')
        
        return int(total_seconds)
    
    def _parse_storage(self, storage_str):
        """解析存储空间字符串，返回总字节数"""
        if not storage_str:
            return 0
        
        storage_str = storage_str.strip().lower()
        
        # 匹配各种格式
        patterns = [
            (r'(\d+(?:\.\d+)?)\s*gb', 1073741824),
            (r'(\d+(?:\.\d+)?)\s*mb', 1048576),
            (r'(\d+(?:\.\d+)?)\s*kb', 1024),
            (r'(\d+(?:\.\d+)?)\s*字节', 1),
            (r'(\d+(?:\.\d+)?)\s*bytes?', 1),
        ]
        
        for pattern, multiplier in patterns:
            match = re.search(pattern, storage_str)
            if match:
                return int(float(match.group(1)) * multiplier)
        
        # 如果没有匹配到任何模式，尝试解析为纯数字（默认为字节）
        try:
            return int(float(storage_str))
        except ValueError:
            raise ValidationError(f'无法解析存储空间格式: {storage_str}')
    
    def clean_audio_duration_input(self):
        """验证并转换音频时长输入"""
        duration_str = self.cleaned_data.get('audio_duration_input', '')
        if not duration_str:
            return 0
        
        try:
            return self._parse_duration(duration_str)
        except ValidationError:
            raise
        except Exception as e:
            raise ValidationError(f'音频时长格式错误: {str(e)}')
    
    def clean_storage_input(self):
        """验证并转换存储空间输入"""
        storage_str = self.cleaned_data.get('storage_input', '')
        if not storage_str:
            return 0
        
        try:
            return self._parse_storage(storage_str)
        except ValidationError:
            raise
        except Exception as e:
            raise ValidationError(f'存储空间格式错误: {str(e)}')
    
    def save(self, commit=True):
        """保存表单数据"""
        instance = super().save(commit=False)
        
        # 设置解析后的值
        if 'audio_duration_input' in self.cleaned_data:
            instance.remaining_audio_duration = self.cleaned_data['audio_duration_input']
        
        if 'storage_input' in self.cleaned_data:
            instance.available_storage_bytes = self.cleaned_data['storage_input']
        
        if commit:
            instance.save()
        
        return instance


@admin.register(UserQuota)
class UserQuotaAdmin(admin.ModelAdmin):
    form = UserQuotaAdminForm
    
    list_display = (
        'user', 
        'get_audio_duration_display', 
        'get_storage_display', 
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
        ('配额设置', {
            'fields': (
                'audio_duration_input',
                'storage_input',
            ),
            'description': '设置用户的音频时长和存储空间配额。支持多种输入格式，修改后点击保存按钮生效。'
        }),
        ('时间信息', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_audio_duration_display(self, obj):
        """在列表中显示友好的音频时长格式"""
        if obj and obj.pk:
            return obj.get_audio_duration_display()
        return '-'
    get_audio_duration_display.short_description = '剩余音频时长'
    
    def get_storage_display(self, obj):
        """在列表中显示友好的存储空间格式"""
        if obj and obj.pk:
            return obj.get_storage_display()
        return '-'
    get_storage_display.short_description = '可用存储空间'
    
    def get_current_values_display(self, obj):
        """显示当前配额的详细信息"""
        if obj and hasattr(obj, 'remaining_audio_duration') and hasattr(obj, 'available_storage_bytes'):
            audio_display = obj.get_audio_duration_display()
            storage_display = obj.get_storage_display()
            
            return format_html(
                '<div style="background: #f8f9fa; padding: 10px; border-radius: 4px; margin: 10px 0;">'
                '<h4 style="margin: 0 0 8px 0; color: #495057;">当前配额</h4>'
                '<p style="margin: 4px 0;"><strong>音频时长:</strong> {} <small style="color: #6c757d;">({} 秒)</small></p>'
                '<p style="margin: 4px 0;"><strong>存储空间:</strong> {} <small style="color: #6c757d;">({:,} 字节)</small></p>'
                '</div>',
                audio_display,
                obj.remaining_audio_duration,
                storage_display,
                obj.available_storage_bytes
            )
        return format_html(
            '<div style="background: #fff3cd; padding: 10px; border-radius: 4px; margin: 10px 0;">'
            '<p style="margin: 0; color: #856404;">保存后将显示当前配额信息</p>'
            '</div>'
        )
    get_current_values_display.short_description = '当前配额信息'
    
    # 保留有用的批量操作
    actions = ['reset_to_default', 'add_one_hour_audio', 'add_one_gb_storage']
    
    def reset_to_default(self, request, queryset):
        """重置为默认配额（1小时音频 + 1GB存储）"""
        updated = queryset.update(
            remaining_audio_duration=3600,
            available_storage_bytes=1073741824
        )
        self.message_user(request, f'成功重置 {updated} 个用户的配额为默认值（1小时音频 + 1GB存储）')
    reset_to_default.short_description = '重置为默认配额'
    
    def add_one_hour_audio(self, request, queryset):
        """为选中用户增加1小时音频配额"""
        for quota in queryset:
            quota.add_audio_duration(3600)
        self.message_user(request, f'成功为 {queryset.count()} 个用户增加1小时音频配额')
    add_one_hour_audio.short_description = '增加1小时音频配额'
    
    def add_one_gb_storage(self, request, queryset):
        """为选中用户增加1GB存储配额"""
        for quota in queryset:
            quota.add_storage(1073741824)
        self.message_user(request, f'成功为 {queryset.count()} 个用户增加1GB存储配额')
    add_one_gb_storage.short_description = '增加1GB存储配额'
