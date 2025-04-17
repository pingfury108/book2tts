from django.urls import path

from . import views

urlpatterns = [
    path("", views.index, name="home"),
    path("audio/<int:segment_id>/", views.audio_detail, name="audio_detail"),
    path("book/<int:book_id>/", views.book_audio_list, name="book_audio_list"),
]
