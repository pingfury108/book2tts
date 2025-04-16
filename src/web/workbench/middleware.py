from django.shortcuts import redirect
from django.urls import resolve, reverse
from django.conf import settings


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
            # If user is not authenticated, redirect to login page
            if not request.user.is_authenticated:
                # Get the login URL with the current path as the next parameter
                login_url = f"{reverse('login')}?next={path}"
                return redirect(login_url)
                
        # Continue with the regular middleware chain
        response = self.get_response(request)
        return response 