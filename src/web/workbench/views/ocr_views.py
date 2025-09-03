from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.conf import settings
from django.core.exceptions import ValidationError

from ..models import Books
from ..utils.ocr_utils import perform_ocr_with_cache, perform_batch_ocr_with_cache
from book2tts.pdf import detect_scanned_pdf, get_page_image_data


@login_required
@csrf_exempt
@require_http_methods(["POST"])
def detect_pdf_scanned(request, book_id):
    """检测PDF是否为扫描版本"""
    book = get_object_or_404(Books, pk=book_id, user=request.user)
    
    if book.file_type != ".pdf":
        return JsonResponse({
            "status": "error",
            "message": "只支持PDF文件的扫描检测"
        }, status=400)
    
    try:
        # 检测PDF是否为扫描版
        detection_result = detect_scanned_pdf(book.file.path)
        
        return JsonResponse({
            "status": "success",
            "is_scanned": detection_result['is_scanned'],
            "scanned_ratio": detection_result['scanned_ratio'],
            "total_pages": detection_result['total_pages'],
            "sample_pages": detection_result['sample_pages'],
            "message": "扫描版PDF，建议使用OCR识别" if detection_result['is_scanned'] else "文本版PDF，可直接提取文本"
        })
        
    except Exception as e:
        return JsonResponse({
            "status": "error",
            "message": f"检测失败: {str(e)}"
        }, status=500)


@login_required
@csrf_exempt 
@require_http_methods(["POST"])
def ocr_pdf_page(request, book_id):
    """对PDF页面执行OCR识别"""
    book = get_object_or_404(Books, pk=book_id, user=request.user)
    
    if book.file_type != ".pdf":
        return JsonResponse({
            "status": "error", 
            "message": "只支持PDF文件的OCR识别"
        }, status=400)
    
    # 获取页码
    page_num_str = request.POST.get('page_num')
    if not page_num_str:
        return JsonResponse({
            "status": "error",
            "message": "缺少page_num参数"
        }, status=400)
        
    try:
        page_num = int(page_num_str)
        if page_num < 0:
            raise ValueError("页码不能为负数")
    except ValueError:
        return JsonResponse({
            "status": "error", 
            "message": "page_num必须是有效的页码数字"
        }, status=400)
    
    # 检查OCR配置
    ak = getattr(settings, 'VOLCENGINE_ACCESS_KEY', None)
    sk = getattr(settings, 'VOLCENGINE_SECRET_KEY', None)
    
    if not ak or not sk:
        return JsonResponse({
            "status": "error",
            "message": "OCR服务未配置，请联系管理员设置火山引擎密钥"
        }, status=500)
    
    try:
        # 获取页面图像数据
        image_data = get_page_image_data(book.file.path, page_num)
        
        # 执行OCR识别（带缓存和QPS控制）
        ocr_result = perform_ocr_with_cache(image_data, ak, sk, 'page_image')
        
        if 'error' in ocr_result:
            return JsonResponse({
                "status": "error",
                "message": f"OCR识别失败: {ocr_result['error']}"
            }, status=500)
        
        return JsonResponse({
            "status": "success",
            "page_num": page_num,
            "text": ocr_result['text'],
            "cached": ocr_result['cached'],
            "image_md5": ocr_result['image_md5'],
            "message": "OCR识别完成" + ("（使用缓存结果）" if ocr_result['cached'] else "")
        })
        
    except IndexError as e:
        return JsonResponse({
            "status": "error",
            "message": str(e)
        }, status=400)
    except Exception as e:
        return JsonResponse({
            "status": "error", 
            "message": f"OCR识别失败: {str(e)}"
        }, status=500)


@login_required
@csrf_exempt
@require_http_methods(["POST"]) 
def ocr_pdf_pages_batch(request, book_id):
    """批量对PDF页面执行OCR识别（自动QPS控制）"""
    book = get_object_or_404(Books, pk=book_id, user=request.user)
    
    if book.file_type != ".pdf":
        return JsonResponse({
            "status": "error",
            "message": "只支持PDF文件的OCR识别" 
        }, status=400)
    
    # 获取页面范围
    page_range = request.POST.get('page_range', '')
    if not page_range:
        return JsonResponse({
            "status": "error",
            "message": "缺少page_range参数，格式如: 1-5 或 1,3,5"
        }, status=400)
    
    # 检查OCR配置
    ak = getattr(settings, 'VOLCENGINE_ACCESS_KEY', None)
    sk = getattr(settings, 'VOLCENGINE_SECRET_KEY', None)
    
    if not ak or not sk:
        return JsonResponse({
            "status": "error",
            "message": "OCR服务未配置，请联系管理员设置火山引擎密钥"
        }, status=500)
    
    try:
        # 解析页面范围
        page_nums = []
        if '-' in page_range:
            # 范围格式: 1-5
            start, end = map(int, page_range.split('-'))
            page_nums = list(range(start, end + 1))
        elif ',' in page_range:
            # 列表格式: 1,3,5
            page_nums = [int(x.strip()) for x in page_range.split(',')]
        else:
            # 单页格式: 5
            page_nums = [int(page_range)]
        
        # 验证页码
        for page_num in page_nums:
            if page_num < 0:
                raise ValueError(f"页码 {page_num} 不能为负数")
        
        # 准备图像数据列表
        image_data_list = []
        for page_num in page_nums:
            try:
                image_data = get_page_image_data(book.file.path, page_num)
                image_data_list.append({
                    'data': image_data,
                    'page_num': page_num
                })
            except Exception as e:
                image_data_list.append({
                    'data': None,
                    'page_num': page_num,
                    'error': str(e)
                })
        
        # 批量OCR识别（自动遵守QPS限制）
        results = []
        for item in image_data_list:
            if item.get('error'):
                results.append({
                    'page_num': item['page_num'],
                    'text': '',
                    'cached': False,
                    'image_md5': '',
                    'error': item['error']
                })
            else:
                ocr_result = perform_ocr_with_cache(item['data'], ak, sk, 'page_image')
                ocr_result['page_num'] = item['page_num']
                results.append(ocr_result)
        
        # 统计结果
        success_count = sum(1 for r in results if not r.get('error'))
        cached_count = sum(1 for r in results if r.get('cached'))
        
        return JsonResponse({
            "status": "success",
            "total_pages": len(results),
            "success_count": success_count,
            "cached_count": cached_count,
            "results": results,
            "message": f"批量OCR识别完成，成功 {success_count}/{len(results)} 页"
        })
        
    except ValueError as e:
        return JsonResponse({
            "status": "error",
            "message": f"页面范围格式错误: {str(e)}"
        }, status=400)
    except Exception as e:
        return JsonResponse({
            "status": "error",
            "message": f"批量OCR识别失败: {str(e)}"
        }, status=500)