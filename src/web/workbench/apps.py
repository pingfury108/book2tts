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
