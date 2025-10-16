"""
配置管理模块

提供多种配置获取方式，支持项目集成。
"""

import os
from django.conf import settings


class EnvironmentConfig:
    """环境变量配置类"""

    @classmethod
    def get_config(cls):
        """从环境变量获取配置"""
        class Config:
            s3_enabled = os.getenv('S3_ENABLED', '').lower() == 'true'
            s3_access_key_id = os.getenv('S3_ACCESS_KEY_ID', '')
            s3_secret_access_key = os.getenv('S3_SECRET_ACCESS_KEY', '')
            s3_bucket_name = os.getenv('S3_BUCKET_NAME', '')
            s3_region = os.getenv('S3_REGION', 'us-east-1')
            s3_endpoint_url = os.getenv('S3_ENDPOINT_URL', '')
            s3_custom_domain = os.getenv('S3_CUSTOM_DOMAIN', '')
            s3_prefix = os.getenv('S3_PREFIX', 'media/')

        return Config()


class SettingsConfig:
    """Django settings 配置类"""

    @classmethod
    def get_config(cls):
        """从 Django settings 获取配置"""
        class Config:
            s3_enabled = getattr(settings, 'S3_ENABLED', False)
            s3_access_key_id = getattr(settings, 'S3_ACCESS_KEY_ID', '')
            s3_secret_access_key = getattr(settings, 'S3_SECRET_ACCESS_KEY', '')
            s3_bucket_name = getattr(settings, 'S3_BUCKET_NAME', '')
            s3_region = getattr(settings, 'S3_REGION', 'us-east-1')
            s3_endpoint_url = getattr(settings, 'S3_ENDPOINT_URL', '')
            s3_custom_domain = getattr(settings, 'S3_CUSTOM_DOMAIN', '')
            s3_prefix = getattr(settings, 'S3_PREFIX', 'media/')

        return Config()


def create_config_callback(config_class_path):
    """
    创建配置回调函数

    Args:
        config_class_path: 配置类的导入路径

    Returns:
        callable: 配置获取回调函数
    """
    from django.utils.module_loading import import_string

    def config_callback():
        config_class = import_string(config_class_path)
        return config_class.get_config()

    return config_callback