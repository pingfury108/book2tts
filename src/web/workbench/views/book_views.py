from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse, HttpResponse
from django.core.paginator import Paginator
from django.conf import settings

from ..forms import UploadFileForm
from ..models import Books
from book2tts.ebook import open_ebook, ebook_toc, get_content_with_href, ebook_pages
from book2tts.pdf import open_pdf, detect_scanned_pdf, get_page_image_data
from ..utils.ocr_utils import perform_ocr_with_cache
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


def calculate_epub_toc_page_ranges(toc_list, all_pages):
    """
    计算EPUB TOC条目的页面范围
    参数:
        toc_list: TOC列表，格式为 [{"title": str, "href": str, "level": int}, ...]
        all_pages: 所有页面列表，格式为 [{"title": str, "href": str}, ...]
    返回:
        处理后的TOC列表，每个条目包含页面范围信息
    """
    if not toc_list or not all_pages:
        return []
    
    # 创建页面href到索引的映射
    page_href_to_index = {page["href"]: idx for idx, page in enumerate(all_pages)}
    
    toc_with_ranges = []
    
    for i, toc in enumerate(toc_list):
        title = toc["title"]
        href = toc["href"]
        level = toc["level"]
        
        # 找到当前TOC条目对应的页面索引
        start_page_index = page_href_to_index.get(href)
        if start_page_index is None:
            # 如果找不到对应页面，跳过这个TOC条目
            continue
        
        # 找到结束页面索引：查找下一个同级别或更高级别的条目
        end_page_index = len(all_pages) - 1  # 默认到文档末尾
        
        for j in range(i + 1, len(toc_list)):
            next_toc = toc_list[j]
            next_level = next_toc["level"]
            next_href = next_toc["href"]
            
            # 如果找到同级别或更高级别的条目
            if next_level <= level:
                next_page_index = page_href_to_index.get(next_href)
                if next_page_index is not None:
                    end_page_index = next_page_index - 1
                    break
        
        # 确保结束页面索引不小于起始页面索引
        end_page_index = max(start_page_index, end_page_index)
        
        # 获取页面范围内的所有页面href
        page_hrefs = [all_pages[idx]["href"] for idx in range(start_page_index, end_page_index + 1)]
        
        toc_with_ranges.append({
            "title": title,
            "href": ",".join(page_hrefs),  # 使用逗号分隔的多个页面href
            "start_page_index": start_page_index,
            "end_page_index": end_page_index,
            "level": level,
            "page_count": len(page_hrefs)
        })
    
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
                "book": book,  # Pass the entire book object for access to pdf_type
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
        all_pages = ebook_pages(ebook)
        toc_list = ebook_toc_with_level(ebook)
        toc_with_ranges = calculate_epub_toc_page_ranges(toc_list, all_pages)
        
        return render(
            request,
            "index.html",
            {
                "book": book,  # Pass the entire book object for access to pdf_type
                "book_id": book.id,
                "title": book.name,  # Always use the database book name
                "tocs": [
                    {
                        "title": toc.get("title"),
                        "href": toc.get("href").replace("/", "_"),  # 已经是逗号分隔的页面列表
                        "level": toc.get("level", 0),
                        "start_page_index": toc.get("start_page_index"),
                        "end_page_index": toc.get("end_page_index"),
                        "page_count": toc.get("page_count", 1)
                    }
                    for toc in toc_with_ranges
                ],
                "pages": all_pages,
            },
        )


@login_required
def upload(request):
    """Handle book file upload"""
    if request.method == "POST":
        form = UploadFileForm(request.POST, request.FILES, user=request.user)

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
        form = UploadFileForm(user=request.user)
    
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
    
    # 过滤掉虚拟类型的书籍，只显示真实上传的书籍
    books = Books.objects.filter(user=request.user).exclude(file_type='.virtual').order_by('-created_at')
    
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
        all_pages = ebook_pages(ebook)
        toc_list = ebook_toc_with_level(ebook)
        toc_with_ranges = calculate_epub_toc_page_ranges(toc_list, all_pages)
        
        return render(
            request,
            "toc.html",
            {
                "book_id": book.id,
                "title": book.name,  # Use database book name instead of ebook.title
                "tocs": [
                    {
                        "title": toc.get("title"), 
                        "href": toc.get("href"),  # 已经是逗号分隔的页面列表
                        "level": toc.get("level", 0),
                        "start_page_index": toc.get("start_page_index"),
                        "end_page_index": toc.get("end_page_index"),
                        "page_count": toc.get("page_count", 1)
                    }
                    for toc in toc_with_ranges
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
    """Extract text content by table of contents with OCR support"""
    book = get_object_or_404(Books, pk=book_id)
    
    # Get names from POST data
    names_param = request.POST.get('names', '')
    if not names_param:
        return JsonResponse({
            "status": "error",
            "message": "No names provided"
        }, status=400)
    
    # Check OCR settings
    # Priority: 1. Manual user request, 2. Book's pdf_type setting
    use_ocr_manual = request.POST.get('use_ocr', '').lower() == 'true'
    use_ocr_auto = book.should_use_ocr()  # Based on pdf_type field
    
    # Use OCR if either manual request or auto-detection suggests it
    use_ocr = use_ocr_manual or use_ocr_auto
    
    # Support multiple names separated by comma, maintain order
    names = names_param.split(',')
    combined_texts = []
    ocr_results = []  # Store OCR metadata
    
    for single_name in names:
        text_content = ""
        
        if book.file_type == ".pdf":
            try:
                # Check if OCR should be used
                if use_ocr:
                    ak = getattr(settings, 'VOLC_AK', None)
                    sk = getattr(settings, 'VOLC_SK', None)
                    
                    if ak and sk:
                        try:
                            # 检查是否是页面范围格式 (start-end)
                            if '-' in single_name:
                                start_page, end_page = map(int, single_name.split('-'))
                                # 获取页面范围内所有页面的OCR文本
                                page_texts = []
                                for page_num in range(start_page, end_page + 1):
                                    try:
                                        # Get page image data and perform OCR
                                        image_data = get_page_image_data(book.file.path, page_num)
                                        ocr_result = perform_ocr_with_cache(image_data, ak, sk, 'page_image')
                                        
                                        if 'error' not in ocr_result:
                                            page_text = ocr_result.get('text', '')
                                            if page_text.strip():  # 只添加非空页面
                                                page_texts.append(page_text)
                                            ocr_results.append({
                                                'page': page_num,
                                                'cached': ocr_result.get('cached', False),
                                                'image_md5': ocr_result.get('image_md5', ''),
                                                'auto_ocr': use_ocr_auto
                                            })
                                        else:
                                            # Fall back to regular text extraction on OCR error
                                            pbook = open_pdf(book.file.path)
                                            fallback_text = pbook[page_num].get_text()
                                            if fallback_text.strip():
                                                page_texts.append(fallback_text)
                                            ocr_results.append({
                                                'page': page_num,
                                                'error': ocr_result['error'],
                                                'auto_ocr': use_ocr_auto
                                            })
                                    except IndexError:
                                        # 如果页面不存在，跳过
                                        continue
                                    except Exception as page_error:
                                        # Fall back to regular text extraction on error
                                        try:
                                            pbook = open_pdf(book.file.path)
                                            fallback_text = pbook[page_num].get_text()
                                            if fallback_text.strip():
                                                page_texts.append(fallback_text)
                                        except:
                                            pass
                                        ocr_results.append({
                                            'page': page_num,
                                            'error': str(page_error),
                                            'auto_ocr': use_ocr_auto
                                        })
                                text_content = "\n\n".join(page_texts)
                            else:
                                # 单页模式
                                page_num = int(single_name)
                                image_data = get_page_image_data(book.file.path, page_num)
                                ocr_result = perform_ocr_with_cache(image_data, ak, sk, 'page_image')
                                
                                if 'error' not in ocr_result:
                                    text_content = ocr_result.get('text', '')
                                    ocr_results.append({
                                        'page': single_name,
                                        'cached': ocr_result.get('cached', False),
                                        'image_md5': ocr_result.get('image_md5', ''),
                                        'auto_ocr': use_ocr_auto
                                    })
                                else:
                                    # Fall back to regular text extraction on OCR error
                                    pbook = open_pdf(book.file.path)
                                    text_content = pbook[int(single_name)].get_text()
                                    ocr_results.append({
                                        'page': single_name,
                                        'error': ocr_result['error'],
                                        'auto_ocr': use_ocr_auto
                                    })
                        except Exception as ocr_error:
                            # Fall back to regular text extraction on OCR error
                            pbook = open_pdf(book.file.path)
                            if '-' in single_name:
                                start_page, end_page = map(int, single_name.split('-'))
                                page_texts = []
                                for page_num in range(start_page, end_page + 1):
                                    try:
                                        page_text = pbook[page_num].get_text()
                                        if page_text.strip():
                                            page_texts.append(page_text)
                                    except IndexError:
                                        continue
                                text_content = "\n\n".join(page_texts)
                            else:
                                text_content = pbook[int(single_name)].get_text()
                            ocr_results.append({
                                'page': single_name,
                                'error': str(ocr_error),
                                'auto_ocr': use_ocr_auto
                            })
                    else:
                        # OCR not configured, use regular extraction
                        pbook = open_pdf(book.file.path)
                        if '-' in single_name:
                            start_page, end_page = map(int, single_name.split('-'))
                            page_texts = []
                            for page_num in range(start_page, end_page + 1):
                                try:
                                    page_text = pbook[page_num].get_text()
                                    if page_text.strip():
                                        page_texts.append(page_text)
                                except IndexError:
                                    continue
                            text_content = "\n\n".join(page_texts)
                        else:
                            text_content = pbook[int(single_name)].get_text()
                        if use_ocr_auto:
                            ocr_results.append({
                                'page': single_name,
                                'error': 'OCR credentials not configured',
                                'auto_ocr': True
                            })
                else:
                    # Regular text extraction
                    pbook = open_pdf(book.file.path)
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
                # 检查是否是多页面格式（逗号分隔）
                if ',' in single_name:
                    # 多页面模式：获取多个页面的内容
                    page_hrefs = single_name.split(',')
                    page_texts = []
                    for href in page_hrefs:
                        page_text = get_content_with_href(ebook, href.strip())
                        if page_text.strip():  # 只添加非空页面
                            page_texts.append(page_text)
                    text_content = "\n\n".join(page_texts)
                else:
                    # 单页面模式（保持向后兼容）
                    text_content = get_content_with_href(ebook, single_name)
            except Exception as e:
                text_content = f"Error extracting text: {str(e)}"
        
        combined_texts.append(text_content)
    
    # Join all texts with double newlines
    texts = "\n\n".join(combined_texts)
    
    # Prepare response data
    response_data = {
        "status": "success",
        "texts": texts,
        "count": len(names)
    }
    
    # Add OCR metadata if OCR was used
    if use_ocr and (ocr_results or use_ocr_auto):
        response_data["ocr_used"] = True
        response_data["auto_ocr"] = use_ocr_auto  # Indicate if OCR was used automatically
        response_data["manual_ocr"] = use_ocr_manual  # Indicate if OCR was requested manually
        if ocr_results:
            response_data["ocr_results"] = ocr_results
            response_data["cached_count"] = sum(1 for r in ocr_results if r.get('cached', False))
    
    # Return JSON response
    return JsonResponse(response_data)


@login_required
@csrf_exempt
@require_http_methods(["POST"])
def text_by_page(request, book_id):
    """Extract text content by page with filtering options and OCR support"""
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
    
    # Check OCR settings
    # Priority: 1. Manual user request, 2. Book's pdf_type setting
    use_ocr_manual = request.POST.get('use_ocr', '').lower() == 'true'
    use_ocr_auto = book.should_use_ocr()  # Based on pdf_type field
    
    # Use OCR if either manual request or auto-detection suggests it
    use_ocr = use_ocr_manual or use_ocr_auto
    
    # Support multiple names separated by comma, maintain order
    names = names_param.split(',')
    combined_texts = []
    ocr_results = []  # Store OCR metadata
    
    for page_name in names:
        page_text = ""
        
        if book.file_type == ".pdf":
            try:
                # Check if OCR should be used
                if use_ocr:
                    ak = getattr(settings, 'VOLC_AK', None)
                    sk = getattr(settings, 'VOLC_SK', None)
                    
                    if ak and sk:
                        try:
                            page_num = int(page_name)
                            # Get page image data and perform OCR
                            image_data = get_page_image_data(book.file.path, page_num)
                            ocr_result = perform_ocr_with_cache(image_data, ak, sk, 'page_image')
                            
                            if 'error' not in ocr_result:
                                page_text = ocr_result.get('text', '')
                                ocr_results.append({
                                    'page': page_name,
                                    'cached': ocr_result.get('cached', False),
                                    'image_md5': ocr_result.get('image_md5', ''),
                                    'auto_ocr': use_ocr_auto  # Mark if OCR was used automatically
                                })
                            else:
                                # Fall back to regular text extraction on OCR error
                                pbook = open_pdf(book.file.path)
                                page_text = pbook[int(page_name)].get_text()
                                ocr_results.append({
                                    'page': page_name,
                                    'error': ocr_result['error'],
                                    'auto_ocr': use_ocr_auto
                                })
                        except Exception as ocr_error:
                            # Fall back to regular text extraction on OCR error
                            pbook = open_pdf(book.file.path)
                            page_text = pbook[int(page_name)].get_text()
                            ocr_results.append({
                                'page': page_name,
                                'error': str(ocr_error),
                                'auto_ocr': use_ocr_auto
                            })
                    else:
                        # OCR not configured, use regular extraction
                        pbook = open_pdf(book.file.path)
                        page_text = pbook[int(page_name)].get_text()
                        if use_ocr_auto:
                            # Add note that OCR was suggested but not available
                            ocr_results.append({
                                'page': page_name,
                                'error': 'OCR credentials not configured',
                                'auto_ocr': True
                            })
                else:
                    # Regular text extraction
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
                # 检查是否是多页面格式（逗号分隔）
                if ',' in page_name:
                    # 多页面模式：获取多个页面的内容
                    page_hrefs = page_name.split(',')
                    combined_page_texts = []
                    for href in page_hrefs:
                        individual_page_text = get_content_with_href(ebook, href.strip())
                        if individual_page_text.strip():  # 只添加非空页面
                            combined_page_texts.append(individual_page_text)
                    page_text = "\n\n".join(combined_page_texts)
                else:
                    # 单页面模式（保持向后兼容）
                    page_text = get_content_with_href(ebook, page_name)
                
                # Apply line filtering to combined page content
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
    
    # Prepare response data
    response_data = {
        "status": "success",
        "texts": texts,
        "count": len(names)
    }
    
    # Add OCR metadata if OCR was used
    if use_ocr and (ocr_results or use_ocr_auto):
        response_data["ocr_used"] = True
        response_data["auto_ocr"] = use_ocr_auto  # Indicate if OCR was used automatically
        response_data["manual_ocr"] = use_ocr_manual  # Indicate if OCR was requested manually
        if ocr_results:
            response_data["ocr_results"] = ocr_results
            response_data["cached_count"] = sum(1 for r in ocr_results if r.get('cached', False))
    
    # Return JSON response
    return JsonResponse(response_data)


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
def update_pdf_type(request, book_id):
    """Update the PDF type of a book"""
    # Get the book or return 404 if not found
    book = get_object_or_404(Books, pk=book_id)
    
    # Check if the user owns this book
    if book.user != request.user:
        return JsonResponse({"status": "error", "message": "You don't have permission to update this book"}, status=403)
    
    # Check if it's a PDF file
    if book.file_type != ".pdf":
        return JsonResponse({"status": "error", "message": "This is not a PDF file"}, status=400)
    
    try:
        import json
        
        # Get the new PDF type from the request
        if request.content_type == 'application/json':
            data = json.loads(request.body)
            new_pdf_type = data.get("pdf_type")
        else:
            new_pdf_type = request.POST.get("pdf_type")
        
        # Validate the PDF type
        valid_types = [choice[0] for choice in Books.PDF_TYPE_CHOICES]
        if new_pdf_type not in valid_types:
            return JsonResponse({"status": "error", "message": f"Invalid PDF type. Must be one of: {valid_types}"}, status=400)
        
        # Update the PDF type
        old_pdf_type = book.pdf_type
        book.pdf_type = new_pdf_type
        book.save(update_fields=['pdf_type', 'updated_at'])
        
        # If type is set to 'unknown', try to auto-detect
        if new_pdf_type == 'unknown':
            try:
                book.detect_and_update_pdf_type()
                # Get the updated type after auto-detection
                book.refresh_from_db()
                new_pdf_type = book.pdf_type
            except Exception as e:
                # Auto-detection failed, keep as unknown
                pass
        
        # Return success response
        return JsonResponse({
            "status": "success", 
            "message": f"PDF类型已从'{book.get_pdf_type_display_name()}更新为'{dict(Books.PDF_TYPE_CHOICES)[new_pdf_type]}'",
            "old_type": old_pdf_type,
            "new_type": new_pdf_type,
            "display_name": dict(Books.PDF_TYPE_CHOICES)[new_pdf_type]
        })
    
    except json.JSONDecodeError:
        return JsonResponse({"status": "error", "message": "Invalid JSON data"}, status=400)
    except Exception as e:
        print(f"Error in update_pdf_type: {str(e)}")
        return JsonResponse({"status": "error", "message": f"更新失败: {str(e)}"}, status=500)


@login_required
@csrf_exempt  
@require_http_methods(["POST"])
def detect_scanned_pdf(request, book_id):
    """Detect if a PDF is scanned or text-based"""
    # Get the book or return 404 if not found
    book = get_object_or_404(Books, pk=book_id)
    
    # Check if the user owns this book
    if book.user != request.user:
        return JsonResponse({"status": "error", "message": "You don't have permission to access this book"}, status=403)
    
    # Check if it's a PDF file
    if book.file_type != ".pdf":
        return JsonResponse({"status": "error", "message": "This is not a PDF file"}, status=400)
    
    try:
        from book2tts.pdf import detect_scanned_pdf as detect_scanned
        
        # Perform detection
        result = detect_scanned(book.file.path, sample_pages=5)
        
        # Update book's pdf_type if it was previously unknown
        if book.pdf_type == 'unknown':
            book.pdf_type = 'scanned' if result['is_scanned'] else 'text'
            book.save(update_fields=['pdf_type', 'updated_at'])
        
        # Return detection result
        return JsonResponse({
            "status": "success",
            "is_scanned": result['is_scanned'],
            "scanned_ratio": result['scanned_ratio'],
            "sample_pages": result['sample_pages'],
            "current_type": book.pdf_type,
            "message": f"检测完成：{'扫描版' if result['is_scanned'] else '文本版'}PDF"
        })
    
    except Exception as e:
        print(f"Error in detect_scanned_pdf: {str(e)}")
        return JsonResponse({"status": "error", "message": f"检测失败: {str(e)}"}, status=500)


@login_required
@csrf_exempt
@require_http_methods(["GET"])
def get_page_image(request, book_id, page_number):
    """Get page image for scanned PDF viewing"""
    book = get_object_or_404(Books, pk=book_id)
    
    # Check if the user owns this book
    if book.user != request.user:
        return JsonResponse({"status": "error", "message": "You don't have permission to access this book"}, status=403)
    
    # Check if it's a PDF file
    if book.file_type != ".pdf":
        return JsonResponse({"status": "error", "message": "This is not a PDF file"}, status=400)
    
    try:
        from book2tts.pdf import get_page_image_data
        import base64
        
        # Convert page_number to int
        page_num = int(page_number)
        
        # Get page image data
        image_data = get_page_image_data(book.file.path, page_num, resolution=200)  # Higher resolution for viewing
        
        # Convert to base64 for web display
        image_base64 = base64.b64encode(image_data).decode('utf-8')
        
        return JsonResponse({
            "status": "success",
            "image_data": f"data:image/png;base64,{image_base64}",
            "page_number": page_num,
            "book_name": book.name
        })
    
    except Exception as e:
        print(f"Error getting page image: {str(e)}")
        return JsonResponse({"status": "error", "message": f"获取页面图片失败: {str(e)}"}, status=500)


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


@login_required
@csrf_exempt
@require_http_methods(["GET"])
def check_page_audio_status(request, book_id):
    """检查页面是否已经生成过音频"""
    book = get_object_or_404(Books, pk=book_id)
    
    # Check if the user owns this book
    if book.user != request.user:
        return JsonResponse({"status": "error", "message": "You don't have permission to access this book"}, status=403)
    
    # Get page parameter
    page_ids = request.GET.get('page_ids', '').strip()
    if not page_ids:
        return JsonResponse({"status": "error", "message": "No page IDs provided"}, status=400)
    
    try:
        from ..models import AudioSegment
        
        # Split page IDs and check each one
        page_list = [p.strip() for p in page_ids.split(',') if p.strip()]
        audio_status = {}
        total_count = 0
        
        for page_id in page_list:
            # Check if audio exists for this page
            audio_segments = AudioSegment.objects.filter(
                book=book,
                user=request.user,
                book_page=page_id
            ).order_by('-created_at')
            
            if audio_segments.exists():
                segment = audio_segments.first()
                audio_status[page_id] = {
                    'has_audio': True,
                    'title': segment.title,
                    'created_at': segment.created_at.strftime('%Y-%m-%d %H:%M'),
                    'published': segment.published,
                    'audio_id': segment.id
                }
                total_count += 1
            else:
                audio_status[page_id] = {'has_audio': False}
        
        return JsonResponse({
            "status": "success",
            "audio_status": audio_status,
            "total_pages": len(page_list),
            "pages_with_audio": total_count,
            "coverage_rate": round((total_count / len(page_list)) * 100, 1) if page_list else 0
        })
    
    except Exception as e:
        return JsonResponse({"status": "error", "message": f"检查音频状态失败: {str(e)}"}, status=500) 