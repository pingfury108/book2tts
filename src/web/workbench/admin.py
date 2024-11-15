from django.contrib import admin

# Register your models here.

from .models import Books

# 注册 Books 模型
admin.site.register(Books)
