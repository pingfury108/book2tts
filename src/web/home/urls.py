from django.urls import path

from . import views

urlpatterns = [
    path("", views.index, name="home"),
    path("audio/<int:segment_id>/", views.audio_detail, name="audio_detail"),
]
