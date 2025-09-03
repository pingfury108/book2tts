import hashlib
import tempfile
import time
import threading
from typing import Optional, Dict, Any
from django.conf import settings
from book2tts.ocr import ocr_volc
from ..models import OCRCache


# 全局QPS控制器
class OCRRateLimiter:
    def __init__(self):
        self.last_request_time = 0
        self.lock = threading.Lock()
        self.min_interval = 1.0  # 最小请求间隔1秒
    
    def wait_if_needed(self):
        """如果需要，等待以遵守QPS限制"""
        with self.lock:
            current_time = time.time()
            time_since_last = current_time - self.last_request_time
            
            if time_since_last < self.min_interval:
                wait_time = self.min_interval - time_since_last
                time.sleep(wait_time)
            
            self.last_request_time = time.time()


# 全局限流器实例
_rate_limiter = OCRRateLimiter()


def calculate_image_md5(image_data: bytes) -> str:
    """计算图片数据的MD5哈希值"""
    hash_md5 = hashlib.md5()
    hash_md5.update(image_data)
    return hash_md5.hexdigest()


def save_temp_image(image_data: bytes, suffix: str = '.jpg') -> str:
    """保存临时图片文件并返回文件路径"""
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as temp_file:
        temp_file.write(image_data)
        return temp_file.name


def get_cached_ocr_result(image_md5: str) -> Optional[str]:
    """从缓存中获取OCR结果"""
    try:
        cache_entry = OCRCache.objects.get(image_md5=image_md5)
        return cache_entry.ocr_text
    except OCRCache.DoesNotExist:
        return None


def cache_ocr_result(image_md5: str, ocr_text: str, source_type: str = 'page_image') -> None:
    """缓存OCR结果"""
    OCRCache.objects.update_or_create(
        image_md5=image_md5,
        defaults={
            'ocr_text': ocr_text,
            'source_type': source_type
        }
    )


def perform_ocr_with_cache(image_data: bytes, ak: str, sk: str, source_type: str = 'page_image') -> Dict[str, Any]:
    """
    执行OCR识别，带缓存功能和QPS控制
    
    Args:
        image_data: 图片二进制数据
        ak: 火山引擎Access Key
        sk: 火山引擎Secret Key
        source_type: 来源类型，'page_image' 或 'manual_upload'
    
    Returns:
        包含OCR结果和是否使用缓存的字典
    """
    # 计算图片MD5
    image_md5 = calculate_image_md5(image_data)
    
    # 尝试从缓存中获取结果
    cached_result = get_cached_ocr_result(image_md5)
    if cached_result is not None:
        return {
            'text': cached_result,
            'cached': True,
            'image_md5': image_md5
        }
    
    try:
        # 缓存未命中，执行OCR识别
        temp_image_path = save_temp_image(image_data)
        
        # QPS控制：等待必要的时间间隔
        _rate_limiter.wait_if_needed()
        
        # 调用OCR API
        ocr_text = ocr_volc(ak, sk, temp_image_path)
        
        # 清理临时文件
        import os
        try:
            os.unlink(temp_image_path)
        except:
            pass
        
        # 缓存结果
        if ocr_text:
            cache_ocr_result(image_md5, ocr_text, source_type)
        
        return {
            'text': ocr_text or '',
            'cached': False,
            'image_md5': image_md5
        }
        
    except Exception as e:
        return {
            'text': '',
            'cached': False,
            'image_md5': image_md5,
            'error': str(e)
        }


def perform_batch_ocr_with_cache(image_data_list: list, ak: str, sk: str, source_type: str = 'page_image') -> list:
    """
    批量执行OCR识别，自动遵守QPS限制
    
    Args:
        image_data_list: 图片数据列表 [{'data': bytes, 'page_num': int}, ...]
        ak: 火山引擎Access Key  
        sk: 火山引擎Secret Key
        source_type: 来源类型
    
    Returns:
        OCR结果列表
    """
    results = []
    
    for item in image_data_list:
        image_data = item['data']
        page_num = item.get('page_num', 0)
        
        try:
            # 执行OCR（已内置QPS控制）
            result = perform_ocr_with_cache(image_data, ak, sk, source_type)
            result['page_num'] = page_num
            results.append(result)
            
        except Exception as e:
            results.append({
                'page_num': page_num,
                'text': '',
                'cached': False,
                'image_md5': '',
                'error': str(e)
            })
    
    return results


def clear_ocr_cache(days_old: int = 30) -> int:
    """清理旧的OCR缓存记录"""
    from django.utils import timezone
    from datetime import timedelta
    
    cutoff_date = timezone.now() - timedelta(days=days_old)
    deleted_count, _ = OCRCache.objects.filter(created_at__lt=cutoff_date).delete()
    return deleted_count


def get_ocr_cache_stats() -> Dict[str, int]:
    """获取OCR缓存统计信息"""
    total_entries = OCRCache.objects.count()
    page_image_entries = OCRCache.objects.filter(source_type='page_image').count()
    manual_upload_entries = OCRCache.objects.filter(source_type='manual_upload').count()
    
    return {
        'total': total_entries,
        'page_images': page_image_entries,
        'manual_uploads': manual_upload_entries
    }