import requests
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


def verify_turnstile(token, remote_ip=None):
    """
    验证 Cloudflare Turnstile token
    
    Args:
        token: 从前端获取的 Turnstile token
        remote_ip: 用户的 IP 地址（可选）
    
    Returns:
        dict: 包含验证结果的字典
    """
    # 在 debug 模式下跳过验证
    if settings.DEBUG:
        logger.debug("Skipping Turnstile verification in DEBUG mode")
        return {"success": True, "message": "Verification skipped in DEBUG mode"}
    
    if not settings.TURNSTILE_SECRET_KEY:
        logger.warning("TURNSTILE_SECRET_KEY not configured")
        return {"success": True, "message": "Turnstile not configured"}
    
    if not token:
        return {"success": False, "message": "Turnstile token is required"}
    
    data = {
        "secret": settings.TURNSTILE_SECRET_KEY,
        "response": token,
    }
    
    if remote_ip:
        data["remoteip"] = remote_ip
    
    try:
        response = requests.post(
            settings.TURNSTILE_VERIFY_URL,
            data=data,
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            return {
                "success": result.get("success", False),
                "message": "Verification successful" if result.get("success") else "Verification failed",
                "error_codes": result.get("error-codes", [])
            }
        else:
            logger.error(f"Turnstile API returned status {response.status_code}")
            return {"success": False, "message": "Verification service unavailable"}
            
    except requests.RequestException as e:
        logger.error(f"Turnstile verification error: {e}")
        return {"success": False, "message": "Verification service error"}


def get_client_ip(request):
    """
    获取客户端真实 IP 地址
    """
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip 