from django.contrib import admin

# Register your models here.
from .models import Books, AudioSegment, VoiceRole, DialogueScript, DialogueSegment


class BooksAdmin(admin.ModelAdmin):
    list_display = ('name', 'user', 'file_type', 'md5_hash', 'created_at')
    list_filter = ('file_type', 'user')
    search_fields = ('name', 'md5_hash')
    readonly_fields = ('file_type', 'md5_hash', 'created_at', 'updated_at')


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
