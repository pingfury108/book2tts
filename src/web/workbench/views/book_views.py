from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse, HttpResponse
from django.core.paginator import Paginator

from ..forms import UploadFileForm
from ..models import Books
from book2tts.ebook import open_ebook, ebook_toc, get_content_with_href, ebook_pages
from book2tts.pdf import open_pdf


@login_required
def index(request, book_id):
    """Display book index with table of contents and pages"""
    book = get_object_or_404(Books, pk=book_id)
    if book.file_type == ".pdf":
        pbook = open_pdf(book.file.path)
        return render(
            request,
            "index.html",
            {
                "book_id": book.id,
                "title": book.name,  # Always use the database book name
                "tocs": [
                    {"title": f"{toc[1]}", "href": toc[2]} for toc in pbook.get_toc()
                ],
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
            "index.html",
            {
                "book_id": book.id,
                "title": book.name,  # Always use the database book name
                "tocs": [
                    {
                        "title": toc.get("title"),
                        "href": toc.get("href").split("#")[0].replace("/", "_"),
                    }
                    for toc in ebook_toc(ebook)
                ],
                "pages": ebook_pages(ebook),
            },
        )


@login_required
def upload(request):
    """Handle book file upload"""
    if request.method == "POST":
        form = UploadFileForm(request.POST, request.FILES)

        if form.is_valid():
            instance = form.save(commit=False)
            instance.setkw(request.user)
            instance.save()

            return redirect(reverse("index", args=[instance.id]))
    else:
        form = UploadFileForm()
    return render(request, "upload.html", {"form": form})


@login_required
def my_upload_list(request):
    """Display user's uploaded books list with pagination"""
    # Get page size from request, default to 10
    page_size = int(request.GET.get('page_size', 10))
    page_size_options = [5, 10, 20, 50]
    
    # Ensure page_size is valid
    if page_size not in page_size_options:
        page_size = 10
    
    books = Books.objects.filter(user=request.user).order_by('-created_at')
    
    # Setup pagination
    paginator = Paginator(books, page_size)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    return render(request, "my_upload_list.html", {
        "books": page_obj,
        "paginator": paginator,
        "page_obj": page_obj,
        "page_size": page_size,
        "page_size_options": page_size_options,
    })


@login_required
def toc(request, book_id):
    """Display book table of contents"""
    book = get_object_or_404(Books, pk=book_id)

    if book.file_type == ".pdf":
        pbook = open_pdf(book.file.path)
        return render(
            request,
            "toc.html",
            {
                "book_id": book.id,
                "title": book.name,  # Already using database book name
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
                "title": book.name,  # Use database book name instead of ebook.title
                "tocs": [
                    {"title": toc.get("title"), "href": toc.get("href")}
                    for toc in ebook_toc(ebook)
                ],
            },
        )


@login_required
def pages(request, book_id):
    """Display book pages list"""
    book = get_object_or_404(Books, pk=book_id)
    if book.file_type == ".pdf":
        pbook = open_pdf(book.file.path)
        return render(
            request,
            "pages.html",
            {
                "book_id": book.id,
                "title": book.name,  # Already using database book name
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
                "title": book.name,  # Use database book name instead of ebook.title
                "pages": ebook_pages(ebook),
            },
        )


@login_required
def text_by_toc(request, book_id, name):
    """Extract text content by table of contents"""
    name = name.replace("_", "/")
    book = get_object_or_404(Books, pk=book_id)
    texts = ""
    if book.file_type == ".pdf":
        try:
            pbook = open_pdf(book.file.path)
            texts = pbook[int(name)].get_text()
        except Exception as e:
            texts = f"Error extracting text: {str(e)}"
    elif book.file_type == ".epub":
        try:
            ebook = open_ebook(book.file.path)
            # 检查是否有 toc 查询参数，如果有就使用它而不是 name
            toc_param = request.GET.get('toc')
            if toc_param:
                href_to_use = toc_param
            else:
                href_to_use = name
            texts = get_content_with_href(ebook, href_to_use)
        except Exception as e:
            texts = f"Error extracting text: {str(e)}"

    # Check if this is an HTMX request for just the text content
    if request.headers.get('HX-Target') == 'src-text':
        return render(request, "text_content.html", {"texts": texts})
    else:
        return render(request, "text_by_toc.html", {"texts": texts})


@login_required
def text_by_page(request, book_id, name):
    """Extract text content by page with filtering options"""
    book = get_object_or_404(Books, pk=book_id)
    texts = ""
    
    # Get line filtering parameters from query string
    head_cut = int(request.GET.get('head_cut', 0))  # Lines to remove from beginning (default: 0)
    tail_cut = int(request.GET.get('tail_cut', 0))  # Lines to remove from end (default: 0)
    line_count = request.GET.get('line_count')  # Total lines to keep (optional)
    if line_count:
        line_count = int(line_count)
    
    # Support multiple names separated by comma
    names = name.split(',')
    combined_texts = []
    
    for page_name in names:
        page_name = page_name.replace("_", "/")
        
        if book.file_type == ".pdf":
            try:
                pbook = open_pdf(book.file.path)
                page_text = pbook[int(page_name)].get_text()
                
                # Apply line filtering to individual page content
                if head_cut > 0 or tail_cut > 0 or line_count:
                    lines = page_text.splitlines()
                    total_lines = len(lines)
                    
                    # Calculate start and end indices
                    start_idx = min(head_cut, total_lines)
                    
                    if line_count:
                        # If line_count is specified, use it to calculate end_idx
                        end_idx = min(start_idx + line_count, total_lines)
                    else:
                        # Otherwise, remove tail_cut lines from the end
                        end_idx = max(start_idx, total_lines - tail_cut)
                    
                    # Get the filtered lines
                    filtered_lines = lines[start_idx:end_idx]
                    page_text = "\n".join(filtered_lines)
                
                combined_texts.append(page_text)
            except Exception as e:
                combined_texts.append(f"Error extracting text for page {page_name}: {str(e)}")
        elif book.file_type == ".epub":
            try:
                ebook = open_ebook(book.file.path)
                page_param = request.GET.get('page')
                if page_param:
                    href_to_use = page_param
                else:
                    href_to_use = page_name
                    
                page_text = get_content_with_href(ebook, href_to_use)
                
                # Apply line filtering to individual page content
                if head_cut > 0 or tail_cut > 0 or line_count:
                    lines = page_text.splitlines()
                    total_lines = len(lines)
                    
                    # Calculate start and end indices
                    start_idx = min(head_cut, total_lines)
                    
                    if line_count:
                        # If line_count is specified, use it to calculate end_idx
                        end_idx = min(start_idx + line_count, total_lines)
                    else:
                        # Otherwise, remove tail_cut lines from the end
                        end_idx = max(start_idx, total_lines - tail_cut)
                    
                    # Get the filtered lines
                    filtered_lines = lines[start_idx:end_idx]
                    page_text = "\n".join(filtered_lines)
                
                combined_texts.append(page_text)
            except Exception as e:
                combined_texts.append(f"Error extracting text for page {page_name}: {str(e)}")
    
    # Combine all texts without a separator
    texts = "\n\n".join(combined_texts)
    
    # Check if this is an HTMX request for just the text content
    if request.headers.get('HX-Target') == 'src-text':
        return render(request, "text_content.html", {"texts": texts})
    else:
        return render(request, "text_by_toc.html", {"texts": texts})


@login_required
@csrf_exempt
@require_http_methods(["POST"])
def update_book_name(request, book_id):
    """Update the name of a book"""
    # Get the book or return 404 if not found
    book = get_object_or_404(Books, pk=book_id)
    
    # Check if the user owns this book
    if book.user != request.user:
        return JsonResponse({"status": "error", "message": "You don't have permission to update this book"}, status=403)
    
    try:
        # Get the new name from the request
        new_name = request.POST.get("name")
        if not new_name or new_name.strip() == "":
            return JsonResponse({"status": "error", "message": "Book name cannot be empty"}, status=400)
        
        # Update the book name
        book.name = new_name.strip()
        book.save()
        
        # Check if this is an HTMX request
        if request.headers.get('HX-Request') == 'true':
            # Return the updated input field with the new book name
            return JsonResponse({
                "name": book.name,
                "status": "success"
            })
        else:
            # For non-HTMX requests, return JSON
            return JsonResponse({"status": "success", "message": "Book name updated successfully", "name": book.name})
    
    except Exception as e:
        print(f"Error in update_book_name: {str(e)}")
        if request.headers.get('HX-Request') == 'true':
            # For HTMX requests, return error message
            return HttpResponse(f"更新失败: {str(e)}", status=500)
        else:
            # For non-HTMX requests, return JSON
            return JsonResponse({"status": "error", "message": str(e)}, status=500)


@login_required
@csrf_exempt
@require_http_methods(["POST"])
def delete_book(request, book_id):
    """Delete a book and all its associated data"""
    # Get the book or return 404 if not found
    book = get_object_or_404(Books, pk=book_id)
    
    # Check if the user owns this book
    if book.user != request.user:
        return JsonResponse({"status": "error", "message": "You don't have permission to delete this book"}, status=403)
    
    try:
        # Get book name for response before deletion
        book_name = book.name
        
        # Delete the physical file if it exists
        try:
            if book.file and hasattr(book.file, 'path'):
                import os
                if os.path.exists(book.file.path):
                    os.remove(book.file.path)
        except Exception as file_error:
            # Log the error but don't stop the deletion process
            print(f"Warning: Could not delete file {book.file.path}: {str(file_error)}")
        
        # Delete the book (cascade will delete related AudioSegments)
        book.delete()
        
        # Return success response
        return JsonResponse({
            "status": "success", 
            "message": f"书籍 '{book_name}' 已成功删除",
            "book_id": book_id
        })
    
    except Exception as e:
        print(f"Error in delete_book: {str(e)}")
        return JsonResponse({"status": "error", "message": f"删除失败: {str(e)}"}, status=500) 