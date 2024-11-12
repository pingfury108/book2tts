from django.shortcuts import render
from django.http import HttpResponse

# Create your views here.

from .forms import UploadFileForm
from .models import Books


def index(request, book_id):
    book = Books.objects.get(pk=book_id)
    print(book.uid, book.file.name)
    return render(request, "index.html", {})


def upload(request):
    if request.method == "POST":
        print(request.POST.get("file"))
        form = UploadFileForm(request.POST, request.FILES)

        if form.is_valid():
            form.save()
            return HttpResponse(b"ok")
    else:
        form = UploadFileForm()
    return render(request, "upload.html", {"form": form})


def my_upload_list(request):
    uid = request.session.get('uid', "admin")
    books = Books.objects.filter(uid=uid).all()
    books = [b for b in books]
    print(books)
    return render(request, "my_upload_list.html", {"books": books})
