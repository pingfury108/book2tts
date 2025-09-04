from django.core.cache import cache
from home.models import PointsConfig
import logging

logger = logging.getLogger(__name__)

class PointsManager:
    """积分配置管理器 - 提供统一的积分配置访问接口"""
    
    CACHE_KEY_PREFIX = 'points_config_'
    CACHE_TIMEOUT = 300  # 5分钟缓存
    
    @classmethod
    def get_points_config(cls, operation_type, default_points=None):
        """
        获取指定操作类型的积分配置
        
        Args:
            operation_type: 操作类型
            default_points: 默认积分值（如果配置不存在）
        
        Returns:
            dict: 包含points_per_unit和unit_name的配置信息
        """
        cache_key = f"{cls.CACHE_KEY_PREFIX}{operation_type}"
        
        # 先尝试从缓存获取
        config = cache.get(cache_key)
        if config:
            return config
        
        # 从数据库获取
        try:
            points_config = PointsConfig.objects.get(
                operation_type=operation_type,
                is_active=True
            )
            config = {
                'points_per_unit': points_config.points_per_unit,
                'unit_name': points_config.unit_name,
                'description': points_config.description
            }
        except PointsConfig.DoesNotExist:
            # 使用默认值
            defaults = {
                'audio_generation': 2,
                'ocr_processing': 7,
            }
            
            config = {
                'points_per_unit': default_points or defaults.get(operation_type, 0),
                'unit_name': '次',
                'description': '系统默认值'
            }
            
            # 如果配置不存在且没有提供默认值，创建默认配置
            if default_points is None and operation_type in defaults:
                PointsConfig.objects.create(
                    operation_type=operation_type,
                    points_per_unit=defaults[operation_type],
                    unit_name='秒' if operation_type == 'audio_generation' else '页' if operation_type == 'ocr_processing' else '次',
                    description='系统自动创建的默认配置'
                )
                logger.info(f"Created default PointsConfig for {operation_type}")
        
        # 缓存配置
        cache.set(cache_key, config, cls.CACHE_TIMEOUT)
        return config
    
    @classmethod
    def get_audio_generation_points(cls, duration_seconds):
        """获取音频生成的积分消耗"""
        if duration_seconds < 0:
            return 0
        config = cls.get_points_config('audio_generation')
        return config['points_per_unit'] * duration_seconds
    
    @classmethod
    def get_ocr_processing_points(cls, image_count):
        """获取OCR处理的积分消耗"""
        if image_count < 0:
            return 0
        config = cls.get_points_config('ocr_processing')
        return config['points_per_unit'] * image_count
    
    @classmethod
    def get_config_for_display(cls, operation_type):
        """获取用于显示的配置信息"""
        config = cls.get_points_config(operation_type)
        return f"{config['points_per_unit']}积分/{config['unit_name']}"
    
    @classmethod
    def clear_cache(cls, operation_type=None):
        """清除缓存"""
        if operation_type:
            cache_key = f"{cls.CACHE_KEY_PREFIX}{operation_type}"
            cache.delete(cache_key)
        else:
            # 对于LocMemCache，我们无法列出所有键，所以直接删除我们知道的两个键
            cache.delete(f"{cls.CACHE_KEY_PREFIX}audio_generation")
            cache.delete(f"{cls.CACHE_KEY_PREFIX}ocr_processing")
    
    @classmethod
    def get_all_active_configs(cls):
        """获取所有启用的积分配置"""
        configs = PointsConfig.objects.filter(is_active=True)
        return {
            config.operation_type: {
                'points_per_unit': config.points_per_unit,
                'unit_name': config.unit_name,
                'description': config.description
            }
            for config in configs
        }
    
    @classmethod
    def initialize_default_configs(cls):
        """初始化默认积分配置"""
        defaults = {
            'audio_generation': {
                'points_per_unit': 2,
                'unit_name': '秒',
                'description': '音频生成积分消耗：每秒钟2积分'
            },
            'ocr_processing': {
                'points_per_unit': 7,
                'unit_name': '页',
                'description': 'OCR处理积分消耗：每页图片7积分'
            }
        }
        
        created_count = 0
        for operation_type, config_data in defaults.items():
            config, created = PointsConfig.objects.get_or_create(
                operation_type=operation_type,
                defaults=config_data
            )
            if created:
                created_count += 1
                logger.info(f"Created PointsConfig for {operation_type}")
        
        if created_count > 0:
            cls.clear_cache()
            logger.info(f"Initialized {created_count} default PointsConfig entries")