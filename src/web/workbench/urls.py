from django.urls import path

from . import views

urlpatterns = [
    path("", views.upload, name="index"),
    path("book/<int:book_id>", views.index, name="index"),
    path("my/upload", views.my_upload_list, name="my_upload"),
    path("book/<int:book_id>/text/toc/<str:name>", views.text_by_toc, name="text_by_toc"),

]
