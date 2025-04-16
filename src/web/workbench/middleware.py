from django.shortcuts import redirect
from django.urls import resolve, reverse
from django.conf import settings
from django.contrib.auth.models import AnonymousUser


class WorkbenchAuthenticationMiddleware:
    """
    Middleware to ensure users are authenticated before accessing
    any URL patterns under the workbench app.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        
    def __call__(self, request):
        # Get current path info
        path = request.path_info
        
        # Check if the path belongs to workbench app
        if path.startswith('/workbench/'):
            # 强制验证认证状态
            if request.user is None or isinstance(request.user, AnonymousUser) or not request.user.is_authenticated:
                # Force logout to ensure session is clean
                request.session.flush()
                # Get the login URL with the current path as the next parameter
                login_url = f"{reverse('login')}?next={path}"
                return redirect(login_url)
                
        # Continue with the regular middleware chain
        response = self.get_response(request)
        return response 