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
from ebooklib import epub


def traverse_toc_with_level(items, toc, level=0):
    """
    遍历目录结构并保留层级信息
    基于原始 ebook_toc 的 traverse_toc 函数，添加层级支持
    参数:
        items: epub的目录项或其他目录结构
        toc: 目标列表，用于存储处理后的目录项
        level: 当前层级，从0开始
    """
    for item in items:
        if isinstance(item, tuple):
            section, children = item
            toc.append({
                "title": section.title,
                "href": section.href.split("#")[0],
                "level": level
            })
            # 递归处理子目录，层级加1
            traverse_toc_with_level(children, toc, level + 1)
        elif isinstance(item, epub.Link):
            toc.append({
                "title": item.title,
                "href": item.href.split("#")[0],
                "level": level
            })
    return



def ebook_toc_with_level(book):
    """
    获取epub书籍的目录结构，保留层级信息
    基于原始 ebook_toc 函数，添加层级支持
    """
    tocs = []
    traverse_toc_with_level(book.toc, tocs)

    seen = set()
    result = []

    for t in tocs:
        if t["href"] not in seen:
            seen.add(t["href"])
            result.append(t)
    return result


def calculate_toc_page_ranges(toc_list, total_pages):
    """
    计算TOC条目的页面范围
    参数:
        toc_list: 原始TOC列表，格式为 [[level, title, start_page], ...]
        total_pages: PDF总页数
    返回:
        处理后的TOC列表，每个条目包含 [level, title, start_page, end_page]
    """
    if not toc_list:
        return []
    
    toc_with_ranges = []
    
    for i, toc in enumerate(toc_list):
        level, title, start_page = toc[0], toc[1], toc[2]
        
        # 找到结束页：查找下一个同级别或更高级别的条目
        end_page = total_pages  # 默认到文档末尾
        
        for j in range(i + 1, len(toc_list)):
            next_toc = toc_list[j]
            next_level = next_toc[0]
            next_start_page = next_toc[2]
            
            # 如果找到同级别或更高级别的条目，结束页为其起始页减1
            if next_level <= level:
                end_page = next_start_page - 1
                break
        
        # 确保结束页不小于起始页
        end_page = max(start_page, end_page)
        
        toc_with_ranges.append([level, title, start_page, end_page])
    
    return toc_with_ranges


@login_required
def index(request, book_id):
    """Display book index with table of contents and pages"""
    book = get_object_or_404(Books, pk=book_id)
    if book.file_type == ".pdf":
        pbook = open_pdf(book.file.path)
        # 计算TOC页面范围
        toc_list = pbook.get_toc()
        total_pages = len(list(pbook.pages()))
        toc_with_ranges = calculate_toc_page_ranges(toc_list, total_pages)
        
        return render(
            request,
            "index.html",
            {
                "book_id": book.id,
                "title": book.name,  # Always use the database book name
                "tocs": [
                    {
                        "title": f"{toc[1]}", 
                        "href": f"{toc[2]}-{toc[3]}",
                        "start_page": toc[2],
                        "end_page": toc[3],
                        "level": toc[0] - 1 if toc[0] > 0 else 0  # PDF层级从1开始，转换为从0开始
                    } for toc in toc_with_ranges
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
                        "level": toc.get("level", 0)  # 添加层级信息
                    }
                    for toc in ebook_toc_with_level(ebook)  # 使用新的层级函数
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
            try:
                instance = form.save(commit=False)
                instance.setkw(request.user)
                instance.save()

                # 成功上传后跳转到书籍详情页
                return redirect(reverse("index", args=[instance.id]))
            
            except Exception as e:
                # 处理保存过程中的其他错误
                form.add_error(None, f"上传失败：{str(e)}")
                
        # 如果表单无效或保存失败，重新显示表单和错误
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
        # 计算TOC页面范围
        toc_list = pbook.get_toc()
        total_pages = len(list(pbook.pages()))
        toc_with_ranges = calculate_toc_page_ranges(toc_list, total_pages)
        
        return render(
            request,
            "toc.html",
            {
                "book_id": book.id,
                "title": book.name,  # Already using database book name
                "tocs": [
                    {
                        "title": f"{toc[1]}", 
                        "href": f"{toc[2]}-{toc[3]}",
                        "start_page": toc[2],
                        "end_page": toc[3],
                        "level": toc[0] - 1 if toc[0] > 0 else 0  # PDF层级从1开始，转换为从0开始
                    } for toc in toc_with_ranges
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
                    {
                        "title": toc.get("title"), 
                        "href": toc.get("href"),
                        "level": toc.get("level", 0)  # 添加层级信息
                    }
                    for toc in ebook_toc_with_level(ebook)  # 使用新的层级函数
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
@csrf_exempt
@require_http_methods(["POST"])
def text_by_toc(request, book_id):
    """Extract text content by table of contents"""
    book = get_object_or_404(Books, pk=book_id)
    
    # Get names from POST data
    names_param = request.POST.get('names', '')
    if not names_param:
        return JsonResponse({
            "status": "error",
            "message": "No names provided"
        }, status=400)
    
    # Support multiple names separated by comma, maintain order
    names = names_param.split(',')
    combined_texts = []
    
    for single_name in names:
        text_content = ""
        
        if book.file_type == ".pdf":
            try:
                pbook = open_pdf(book.file.path)
                
                # 检查是否是页面范围格式 (start-end)
                if '-' in single_name:
                    start_page, end_page = map(int, single_name.split('-'))
                    # 获取页面范围内所有页面的文本
                    page_texts = []
                    for page_num in range(start_page, end_page + 1):
                        try:
                            page_text = pbook[page_num].get_text()
                            if page_text.strip():  # 只添加非空页面
                                page_texts.append(page_text)
                        except IndexError:
                            # 如果页面不存在，跳过
                            continue
                    text_content = "\n\n".join(page_texts)
                else:
                    # 单页模式（保持向后兼容）
                    text_content = pbook[int(single_name)].get_text()
                    
            except Exception as e:
                text_content = f"Error extracting text: {str(e)}"
        elif book.file_type == ".epub":
            try:
                ebook = open_ebook(book.file.path)
                text_content = get_content_with_href(ebook, single_name)
            except Exception as e:
                text_content = f"Error extracting text: {str(e)}"
        
        combined_texts.append(text_content)
    
    # Join all texts with double newlines
    texts = "\n\n".join(combined_texts)
    
    # Return JSON response
    return JsonResponse({
        "status": "success",
        "texts": texts,
        "count": len(names)
    })


@login_required
@csrf_exempt
@require_http_methods(["POST"])
def text_by_page(request, book_id):
    """Extract text content by page with filtering options"""
    book = get_object_or_404(Books, pk=book_id)
    
    # Get names from POST data
    names_param = request.POST.get('names', '')
    if not names_param:
        return JsonResponse({
            "status": "error",
            "message": "No names provided"
        }, status=400)
    
    # Get line filtering parameters from POST data
    head_cut = int(request.POST.get('head_cut', 0))  # Lines to remove from beginning (default: 0)
    tail_cut = int(request.POST.get('tail_cut', 0))  # Lines to remove from end (default: 0)
    line_count = request.POST.get('line_count')  # Total lines to keep (optional)
    if line_count:
        line_count = int(line_count)
    
    # Support multiple names separated by comma, maintain order
    names = names_param.split(',')
    combined_texts = []
    
    for page_name in names:
        page_text = ""
        
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
                
            except Exception as e:
                page_text = f"Error extracting text for page {page_name}: {str(e)}"
        elif book.file_type == ".epub":
            try:
                ebook = open_ebook(book.file.path)
                page_text = get_content_with_href(ebook, page_name)
                
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
                
            except Exception as e:
                page_text = f"Error extracting text for page {page_name}: {str(e)}"
        
        combined_texts.append(page_text)
    
    # Combine all texts with double newlines
    texts = "\n\n".join(combined_texts)
    
    # Return JSON response
    return JsonResponse({
        "status": "success",
        "texts": texts,
        "count": len(names)
    })


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