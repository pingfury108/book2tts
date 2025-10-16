"""
Django OpenDAL Storage Module

一个基于 OpenDAL 的 Django 动态存储后端，支持本地存储和多种 S3 兼容存储服务。
"""

__version__ = "0.1.0"
__author__ = "Book2TTS Team"

from .storage import DynamicStorage, OpenDALS3Storage

__all__ = [
    'DynamicStorage',
    'OpenDALS3Storage',
]