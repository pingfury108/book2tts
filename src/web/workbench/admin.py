from django.contrib import admin
from django.utils.html import format_html

# Register your models here.
from .models import (
    Books,
    AudioSegment,
    DialogueScript,
    DialogueSegment,
    UserProfile,
    OCRCache,
    TTSVoicePreview,
    TTSProviderConfig,
    TranslationCache,
)


class BooksAdmin(admin.ModelAdmin):
    list_display = ('name', 'user', 'file_type', 'pdf_type', 'md5_hash', 'created_at')
    list_filter = ('file_type', 'pdf_type', 'user')
    search_fields = ('name', 'md5_hash')
    readonly_fields = ('file_type', 'md5_hash', 'created_at', 'updated_at')
    
    def get_readonly_fields(self, request, obj=None):
        # PDF类型字段在编辑时可以修改，但创建时自动检测
        readonly = list(self.readonly_fields)
        if obj is None:  # 创建新对象时
            readonly.append('pdf_type')
        return readonly


class AudioSegmentAdmin(admin.ModelAdmin):
    list_display = ('title', 'book', 'book_page', 'created_at')
    list_filter = ('book',)
    search_fields = ('title', 'text')
    readonly_fields = ('book_page', 'created_at', 'updated_at')
    raw_id_fields = ('book',)


# 注册 Books 模型
admin.site.register(Books, BooksAdmin)
# 注册 AudioSegment 模型
admin.site.register(AudioSegment, AudioSegmentAdmin)

@admin.register(DialogueScript)
class DialogueScriptAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'book', 'segment_count', 'published', 'created_at')
    list_filter = ('published', 'user', 'created_at')
    search_fields = ('title', 'user__username')
    readonly_fields = ('segment_count', 'speakers', 'created_at', 'updated_at')
    
    def segment_count(self, obj):
        return obj.segment_count
    segment_count.short_description = "片段数量"


@admin.register(DialogueSegment)
class DialogueSegmentAdmin(admin.ModelAdmin):
    list_display = ('script', 'speaker', 'sequence', 'dialogue_type', 'created_at')
    list_filter = ('dialogue_type', 'speaker')
    search_fields = ('script__title', 'speaker', 'utterance')
    readonly_fields = ('created_at', 'updated_at')
    ordering = ['script', 'sequence']


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'rss_token', 'get_user_email', 'get_user_date_joined')
    list_filter = ('user',)
    search_fields = ('user__username', 'user__email', 'rss_token')
    readonly_fields = ('rss_token',)
    
    def get_user_email(self, obj):
        return obj.user.email
    get_user_email.short_description = "用户邮箱"
    
    def get_user_date_joined(self, obj):
        return obj.user.date_joined
    get_user_date_joined.short_description = "注册时间"


@admin.register(OCRCache)
class OCRCacheAdmin(admin.ModelAdmin):
    list_display = ('image_md5_short', 'source_type', 'text_preview', 'created_at')
    list_filter = ('source_type', 'created_at')
    search_fields = ('image_md5', 'ocr_text')
    readonly_fields = ('image_md5', 'created_at', 'updated_at')
    
    def image_md5_short(self, obj):
        return f"{obj.image_md5[:12]}..."
    image_md5_short.short_description = "图片MD5"
    
    def text_preview(self, obj):
        return obj.ocr_text[:50] + "..." if len(obj.ocr_text) > 50 else obj.ocr_text
    text_preview.short_description = "文本预览"


@admin.register(TTSVoicePreview)
class TTSVoicePreviewAdmin(admin.ModelAdmin):
    list_display = ('voice_name', 'tts_provider', 'file_link', 'last_generated_at', 'updated_at')
    list_filter = ('tts_provider',)
    search_fields = ('voice_name',)
    readonly_fields = ('created_at', 'updated_at', 'last_generated_at')
    actions = ['regenerate_selected_previews']

    def file_link(self, obj):
        if obj.file:
            return format_html('<a href="{}" target="_blank">预览</a>', obj.file.url)
        return '—'
    file_link.short_description = "音频文件"

    def regenerate_selected_previews(self, request, queryset):
        for preview in queryset:
            preview.file.delete(save=False)
            preview.file = ''
            preview.last_generated_at = None
            preview.save(update_fields=['file', 'last_generated_at', 'updated_at'])
        self.message_user(request, f"已清除 {queryset.count()} 条试听缓存，重新点击试听即可生成。")
    regenerate_selected_previews.short_description = "清除并重建所选试听缓存"


@admin.register(TTSProviderConfig)
class TTSProviderConfigAdmin(admin.ModelAdmin):
    list_display = ('default_provider', 'updated_at')
    list_filter = ('default_provider',)
    readonly_fields = ('created_at', 'updated_at')
    actions = []

    def has_add_permission(self, request):
        # 限制为单实例配置，已存在则禁止再新增
        if TTSProviderConfig.objects.exists():
            return False
        return super().has_add_permission(request)


@admin.register(TranslationCache)
class TranslationCacheAdmin(admin.ModelAdmin):
    list_display = ('text_md5_short', 'target_language', 'text_preview', 'hit_count', 'last_used_at', 'created_at')
    list_filter = ('target_language', 'source_language', 'created_at', 'last_used_at')
    search_fields = ('text_md5', 'original_text', 'translated_text')
    readonly_fields = ('text_md5', 'hit_count', 'created_at', 'updated_at', 'last_used_at')
    ordering = ['-last_used_at']

    def text_md5_short(self, obj):
        return f"{obj.text_md5[:12]}..."
    text_md5_short.short_description = "文本MD5"

    def text_preview(self, obj):
        preview = obj.original_text[:30] + "..." if len(obj.original_text) > 30 else obj.original_text
        return preview.replace('\n', ' ')
    text_preview.short_description = "原文预览"
