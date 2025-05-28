"""
URL configuration for book_tts project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import logout
from django.shortcuts import render
from .views import TurnstileLoginView, TurnstileRegisterView

# Custom logout view to ensure proper session cleanup
def logout_view(request):
    # Completely log out the user
    logout(request)
    # Clear any session data
    request.session.flush()
    # Render the logged_out template
    return render(request, 'registration/logged_out.html')

urlpatterns = [
    path("", include("home.urls")),
    path("workbench/", include("workbench.urls")),
    path("admin/", admin.site.urls),
    path("__reload__/", include("django_browser_reload.urls")),
    
    # Authentication URLs with Turnstile
    path('login/', TurnstileLoginView.as_view(), name='login'),
    path('logout/', logout_view, name='logout'),
    path('register/', TurnstileRegisterView.as_view(), name='register'),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
