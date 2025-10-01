from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction

from ..models import Books
from ..utils.ocr_utils import perform_ocr_with_cache, perform_batch_ocr_with_cache
from book2tts.pdf import detect_scanned_pdf, get_page_image_data
from home.models import UserQuota, OperationRecord
from home.utils import PointsManager


def _get_client_meta(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip_address = x_forwarded_for.split(',')[0].strip()
    else:
        ip_address = request.META.get('REMOTE_ADDR')
    user_agent = request.META.get('HTTP_USER_AGENT')
    return ip_address, user_agent


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
        # 获取用户配额检查积分
        user_quota, created = UserQuota.objects.get_or_create(user=request.user)
        
        # 检查是否有足够的积分（使用PointsManager获取配置值）
        required_points = PointsManager.get_ocr_processing_points(1)
        if not user_quota.can_consume_points(required_points):
            return JsonResponse({
                "status": "error",
                "message": f"积分不足，OCR单页需要{required_points}积分，当前剩余：{user_quota.points}积分"
            }, status=400)
        
        # 获取页面图像数据
        image_data = get_page_image_data(book.file.path, page_num)
        
        # 执行OCR识别（带缓存和QPS控制）
        ocr_result = perform_ocr_with_cache(image_data, ak, sk, 'page_image')
        
        if 'error' in ocr_result:
            OperationRecord.objects.create(
                user=request.user,
                operation_type='ocr_process',
                operation_object=f'{book.name} - 第{page_num}页',
                operation_detail=f"OCR识别失败：{ocr_result['error']}",
                status='failed',
                metadata={
                    'book_id': book_id,
                    'book_name': book.name,
                    'page_num': page_num,
                },
                ip_address=ip_address,
                user_agent=user_agent,
            )
            return JsonResponse({
                "status": "error",
                "message": f"OCR识别失败: {ocr_result['error']}"
            }, status=500)

        # 如果使用了缓存结果，不扣除积分
        if not ocr_result.get('cached', False):
            try:
                with transaction.atomic():
                    # 确保使用最新的配额数据
                    user_quota.refresh_from_db()
                    
                    # 扣除积分
                    points_to_consume = PointsManager.get_ocr_processing_points(1)
                    if not user_quota.consume_points(points_to_consume):
                        # 积分扣除失败（理论上不应该发生，因为之前已经检查过）
                        OperationRecord.objects.create(
                            user=request.user,
                            operation_type='ocr_process',
                            operation_object=f'{book.name} - 第{page_num}页',
                            operation_detail='OCR识别失败：积分扣除失败',
                            status='failed',
                            metadata={
                                'book_id': book_id,
                                'book_name': book.name,
                                'page_num': page_num,
                                'points_required': points_to_consume,
                            },
                            ip_address=ip_address,
                            user_agent=user_agent,
                        )
                        return JsonResponse({
                            "status": "error",
                            "message": "积分扣除失败，请稍后重试"
                        }, status=500)
                    user_quota.refresh_from_db()
                    points_consumed = points_to_consume
            except Exception as e:
                OperationRecord.objects.create(
                    user=request.user,
                    operation_type='ocr_process',
                    operation_object=f'{book.name} - 第{page_num}页',
                    operation_detail=f"OCR识别失败：积分扣除异常 {str(e)}",
                    status='failed',
                    metadata={
                        'book_id': book_id,
                        'book_name': book.name,
                        'page_num': page_num,
                        'cached': False,
                    },
                    ip_address=ip_address,
                    user_agent=user_agent,
                )
                return JsonResponse({
                    "status": "error",
                    "message": f"积分扣除失败：{str(e)}"
                }, status=500)
        else:
            points_consumed = 0

        # 获取当前积分配置信息
        ocr_config = PointsManager.get_points_config('ocr_processing')
        points_per_page = ocr_config['points_per_unit']

        # 确保使用最新的积分值
        if not ocr_result.get('cached', False):
            user_quota.refresh_from_db()
        remaining_points = user_quota.points

        OperationRecord.objects.create(
            user=request.user,
            operation_type='ocr_process',
            operation_object=f'{book.name} - 第{page_num}页',
            operation_detail='OCR识别成功（使用缓存结果）' if ocr_result.get('cached', False) else f'OCR识别成功，消耗{points_consumed}积分，剩余{remaining_points}积分',
            status='success',
            metadata={
                'book_id': book_id,
                'book_name': book.name,
                'page_num': page_num,
                'points_consumed': points_consumed,
                'remaining_points': remaining_points,
                'cached': ocr_result.get('cached', False),
                'image_md5': ocr_result.get('image_md5'),
            },
            ip_address=ip_address,
            user_agent=user_agent,
        )

        return JsonResponse({
            "status": "success",
            "page_num": page_num,
            "text": ocr_result['text'],
            "cached": ocr_result['cached'],
            "image_md5": ocr_result['image_md5'],
            "message": "OCR识别完成" + ("（使用缓存结果，不消耗积分）" if ocr_result['cached'] else f"，已扣除{points_per_page}积分"),
            "remaining_points": remaining_points if not ocr_result.get('cached', False) else None,
            "points_per_page": points_per_page
        })
        
    except IndexError as e:
        OperationRecord.objects.create(
            user=request.user,
            operation_type='ocr_process',
            operation_object=f'{book.name} - 第{page_num_str}页',
            operation_detail=f'OCR识别失败：{str(e)}',
            status='failed',
            metadata={'book_id': book_id, 'book_name': book.name},
            ip_address=ip_address,
            user_agent=user_agent,
        )
        return JsonResponse({
            "status": "error",
            "message": str(e)
        }, status=400)
    except Exception as e:
        OperationRecord.objects.create(
            user=request.user,
            operation_type='ocr_process',
            operation_object=f'{book.name} - 第{page_num_str}页',
            operation_detail=f'OCR识别失败：{str(e)}',
            status='failed',
            metadata={'book_id': book_id, 'book_name': book.name},
            ip_address=ip_address,
            user_agent=user_agent,
        )
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
    ip_address, user_agent = _get_client_meta(request)
    
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
        # 获取用户配额检查积分
        user_quota, created = UserQuota.objects.get_or_create(user=request.user)
        
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
        
        # 计算需要OCR的实际页面数（排除缓存结果）
        new_pages_count = len(page_nums)
        required_points = PointsManager.get_ocr_processing_points(new_pages_count)
        
        # 检查是否有足够的积分
        if not user_quota.can_consume_points(required_points):
            return JsonResponse({
                "status": "error",
                "message": f"积分不足，批量OCR需要{required_points}积分（每页{PointsManager.get_points_config('ocr_processing')['points_per_unit']}积分），当前剩余：{user_quota.points}积分"
            }, status=400)
        
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
        actual_new_ocr_count = 0
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
                
                # 统计实际新增的OCR（非缓存结果）
                if not ocr_result.get('cached', False):
                    actual_new_ocr_count += 1
                
                results.append(ocr_result)
        
        # 扣除积分（仅扣除实际执行OCR的页面）
        actual_points_consumed = 0
        if actual_new_ocr_count > 0:
            actual_points_consumed = PointsManager.get_ocr_processing_points(actual_new_ocr_count)
            try:
                with transaction.atomic():
                    # 确保使用最新的配额数据
                    user_quota.refresh_from_db()
                    
                    if user_quota.points < actual_points_consumed:
                        OperationRecord.objects.create(
                            user=request.user,
                            operation_type='ocr_process',
                            operation_object=f'{book.name} - 批量OCR {len(page_nums)}页',
                            operation_detail='批量OCR识别失败：积分不足',
                            status='failed',
                            metadata={
                                'book_id': book_id,
                                'book_name': book.name,
                                'total_pages': len(page_nums),
                                'new_ocr_pages': actual_new_ocr_count,
                            },
                            ip_address=ip_address,
                            user_agent=user_agent,
                        )
                        return JsonResponse({
                            "status": "error",
                            "message": "积分不足，无法完成OCR操作"
                        }, status=400)
                    
                    user_quota.consume_points(actual_points_consumed)
                    user_quota.save()
                    user_quota.refresh_from_db()
            except Exception as e:
                OperationRecord.objects.create(
                    user=request.user,
                    operation_type='ocr_process',
                    operation_object=f'{book.name} - 批量OCR {len(page_nums)}页',
                    operation_detail=f'批量OCR识别失败：积分扣除异常 {str(e)}',
                    status='failed',
                    metadata={
                        'book_id': book_id,
                        'book_name': book.name,
                        'total_pages': len(page_nums),
                        'new_ocr_pages': actual_new_ocr_count,
                    },
                    ip_address=ip_address,
                    user_agent=user_agent,
                )
                return JsonResponse({
                    "status": "error",
                    "message": f"积分扣除失败：{str(e)}"
                }, status=500)

        remaining_points = user_quota.points

        # 记录操作（无论是否全部来自缓存）
        OperationRecord.objects.create(
            user=request.user,
            operation_type='ocr_process',
            operation_object=f'{book.name} - 批量OCR {len(page_nums)}页',
            operation_detail=(
                '批量OCR识别成功（全部使用缓存结果）'
                if actual_new_ocr_count == 0
                else f'批量OCR识别成功，实际消耗{actual_points_consumed}积分（{actual_new_ocr_count}页新识别），剩余{remaining_points}积分'
            ),
            status='success',
            metadata={
                'book_id': book_id,
                'book_name': book.name,
                'total_pages': len(page_nums),
                'new_ocr_pages': actual_new_ocr_count,
                'cached_pages': len(page_nums) - actual_new_ocr_count,
                'points_consumed': actual_points_consumed,
                'remaining_points': remaining_points,
            },
            ip_address=ip_address,
            user_agent=user_agent,
        )
        
        # 统计结果
        success_count = sum(1 for r in results if not r.get('error'))
        cached_count = sum(1 for r in results if r.get('cached'))
        
        # 确保使用最新的积分值（如果执行了OCR操作）
        if actual_new_ocr_count > 0:
            user_quota.refresh_from_db()
        
        return JsonResponse({
            "status": "success",
            "total_pages": len(results),
            "success_count": success_count,
            "cached_count": cached_count,
            "results": results,
            "actual_points_consumed": actual_points_consumed if actual_new_ocr_count > 0 else 0,
            "remaining_points": user_quota.points,
            "message": f"批量OCR识别完成，成功 {success_count}/{len(results)} 页" + 
                      (f"，已扣除{actual_points_consumed}积分" if actual_new_ocr_count > 0 else "，全部使用缓存结果")
        })
        
    except ValueError as e:
        OperationRecord.objects.create(
            user=request.user,
            operation_type='ocr_process',
            operation_object=f'{book.name} - 批量OCR {page_range}',
            operation_detail=f'批量OCR识别失败：页面范围格式错误 {str(e)}',
            status='failed',
            metadata={'book_id': book_id, 'book_name': book.name},
            ip_address=ip_address,
            user_agent=user_agent,
        )
        return JsonResponse({
            "status": "error",
            "message": f"页面范围格式错误: {str(e)}"
        }, status=400)
    except Exception as e:
        OperationRecord.objects.create(
            user=request.user,
            operation_type='ocr_process',
            operation_object=f'{book.name} - 批量OCR {page_range}',
            operation_detail=f'批量OCR识别失败：{str(e)}',
            status='failed',
            metadata={'book_id': book_id, 'book_name': book.name},
            ip_address=ip_address,
            user_agent=user_agent,
        )
        return JsonResponse({
            "status": "error",
            "message": f"批量OCR识别失败: {str(e)}"
        }, status=500)
