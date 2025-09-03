from django.contrib import admin

# Register your models here.
from .models import Books, AudioSegment, VoiceRole, DialogueScript, DialogueSegment, UserProfile, OCRCache


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

@admin.register(VoiceRole)
class VoiceRoleAdmin(admin.ModelAdmin):
    list_display = ('name', 'user', 'tts_provider', 'voice_name', 'is_default', 'created_at')
    list_filter = ('tts_provider', 'is_default', 'user')
    search_fields = ('name', 'voice_name', 'user__username')
    readonly_fields = ('created_at', 'updated_at')


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
    list_display = ('script', 'speaker', 'voice_role', 'sequence', 'dialogue_type', 'created_at')
    list_filter = ('dialogue_type', 'speaker', 'voice_role')
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
