from django.shortcuts import render
from django.urls import reverse
from django.shortcuts import redirect, get_object_or_404

# Create your views here.

from .forms import UploadFileForm
from .models import Books

from book2tts.ebook import open_ebook, ebook_toc, get_content_with_href, ebook_pages
from book2tts.pdf import open_pdf


def index(request, book_id):
    book = get_object_or_404(Books, pk=book_id)
    if book.file_type == ".pdf":
        pbook = open_pdf(book.file.path)
        return render(
            request,
            "index.html",
            {
                "book_id": book.id,
                "title": pbook.metadata.get("title") or book.name,
                "tocs": [
                    {"title": f"{toc[1]}", "href": toc[2]} for toc in pbook.get_toc()
                ],
            },
        )
    elif book.file_type == ".epub":
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


def toc(request, book_id):
    book = get_object_or_404(Books, pk=book_id)

    if book.file_type == ".pdf":
        pbook = open_pdf(book.file.path)
        return render(
            request,
            "toc.html",
            {
                "book_id": book.id,
                "title": book.name,
                "tocs": [
                    {"title": f"{toc[1]}", "href": toc[2]} for toc in pbook.get_toc()
                ],
            },
        )
    elif book.file_type == ".epub":
        ebook = open_ebook(book.file.path)
        return render(
            request,
            "toc.html",
            {
                "book_id": book.id,
                "title": ebook.title,
                "tocs": [
                    {"title": toc.get("title"), "href": toc.get("href").split("#")[0]}
                    for toc in ebook_toc(ebook)
                ],
            },
        )


def pages(request, book_id):
    book = get_object_or_404(Books, pk=book_id)
    if book.file_type == ".pdf":
        pbook = open_pdf(book.file.path)
        return render(
            request,
            "pages.html",
            {
                "book_id": book.id,
                "title": book.name,
                "pages": [
                    {"title": f"第{page.number+1}页", "href": page.number}
                    for page in pbook.pages()
                ],
            },
        )
    elif book.file_type == ".epub":
        ebook = open_ebook(book.file.path)
        return render(
            request,
            "pages.html",
            {
                "book_id": book.id,
                "title": ebook.title,
                "pages": ebook_pages(ebook),
            },
        )


def text_by_toc(request, book_id, name):
    book = get_object_or_404(Books, pk=book_id)
    texts = ""
    if book.file_type == ".pdf":
        pbook = open_pdf(book.file.path)
        texts = pbook[int(name)].get_text()
    elif book.file_type == ".epub":
        ebook = open_ebook(book.file.path)
        texts = get_content_with_href(ebook, name)

    return render(request, "text_by_toc.html", {"texts": texts})


def text_by_page(request, book_id, name):
    book = get_object_or_404(Books, pk=book_id)
    texts = ""

    if book.file_type == ".pdf":
        pbook = open_pdf(book.file.path)
        texts = pbook[int(name)].get_text()
    elif book.file_type == ".epub":
        ebook = open_ebook(book.file.path)
        texts = get_content_with_href(ebook, name)

    return render(request, "text_by_toc.html", {"texts": texts})
