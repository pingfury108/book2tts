from django.shortcuts import render
from django.urls import reverse
from django.shortcuts import redirect

# Create your views here.

from .forms import UploadFileForm
from .models import Books

from book2tts.ebook import open_ebook, ebook_toc, get_content_with_href


def index(request, book_id):
    book = Books.objects.get(pk=book_id)
    ebook = open_ebook(book.file.path)

    return render(
        request,
        "index.html",
        {
            "book_id": book.id,
            "title": ebook.title,
            "tocs": [
                {"title": toc.get("title"), "href": toc.get("href").split("#")[0]}
                for toc in ebook_toc(ebook)
            ],
        },
    )


def upload(request):
    if request.method == "POST":
        form = UploadFileForm(request.POST, request.FILES)

        if form.is_valid():
            instance = form.save(commit=False)
            instance.setkw(request.session.get("uid", "admin"))
            instance.save()

            return redirect(reverse("index", args=[instance.id]))
    else:
        form = UploadFileForm()
    return render(request, "upload.html", {"form": form})


def my_upload_list(request):
    uid = request.session.get("uid", "admin")
    books = Books.objects.filter(uid=uid).all()
    books = [b for b in books]

    return render(request, "my_upload_list.html", {"books": books})


def text_by_toc(request, book_id, name):
    book = Books.objects.get(pk=book_id)
    ebook = open_ebook(book.file.path)
    texts = get_content_with_href(ebook, name)

    return render(request, "text_by_toc.html", {"texts": texts})
