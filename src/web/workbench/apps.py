from django.apps import AppConfig


class WorkbenchConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "workbench"

    def ready(self):
        """
        Register hooks when app is ready
        """
        # Import here to avoid circular import
        from django.conf import settings
        
        # Add our authentication middleware to the middleware list if not already added
        middleware_path = "workbench.middleware.WorkbenchAuthenticationMiddleware"
        if middleware_path not in settings.MIDDLEWARE:
            # This is a bit of a hack since settings are generally immutable after startup
            # In a production environment, you should add this directly to the settings file
            settings.MIDDLEWARE.append(middleware_path)

        # 在 web 进程内启动后台任务线程（B2T_TASK_WORKER=0 关闭；
        # 若拆分为独立 worker 进程/容器部署，也用该开关关掉）
        from .task_worker import start_task_worker

        start_task_worker()
