from django.contrib import admin

# Register your models here.
from .models import Books, AudioSegment


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
