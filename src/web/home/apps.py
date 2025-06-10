from django.apps import AppConfig


class HomeConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "home"
    
    def ready(self):
        # 导入缓存工具以注册信号处理器
        from .utils import cache_utils
