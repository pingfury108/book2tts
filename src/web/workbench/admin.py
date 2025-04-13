from django.contrib import admin

# Register your models here.
from .models import Books, AudioSegment


class BooksAdmin(admin.ModelAdmin):
    list_display = ('name', 'uid', 'file_type')
    list_filter = ('file_type', 'uid')
    search_fields = ('name', 'uid')
    readonly_fields = ('file_type',)


class AudioSegmentAdmin(admin.ModelAdmin):
    list_display = ('title', 'book', 'uid', 'book_page')
    list_filter = ('book', 'uid')
    search_fields = ('title', 'text', 'uid')
    readonly_fields = ('book_page',)
    raw_id_fields = ('book',)


# 注册 Books 模型
admin.site.register(Books, BooksAdmin)
# 注册 AudioSegment 模型
admin.site.register(AudioSegment, AudioSegmentAdmin)
