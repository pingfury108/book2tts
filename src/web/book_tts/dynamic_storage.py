from django.core.files.storage import Storage
from django.core.files.storage import FileSystemStorage
from django.conf import settings
import opendal
from urllib.parse import urljoin
import logging

logger = logging.getLogger(__name__)


class DynamicStorage(Storage):
    """
    动态存储后端 - 根据站点配置动态选择本地或S3存储
    """

    def __init__(self):
        self._storage = None
        self._last_config_hash = None

    def _get_storage(self):
        """获取当前存储后端实例"""
        from home.models import SiteConfig

        try:
            config = SiteConfig.get_config()
            current_hash = hash((
                config.s3_enabled,
                config.s3_access_key_id,
                config.s3_secret_access_key,
                config.s3_bucket_name,
                config.s3_region,
                config.s3_endpoint_url,
                config.s3_custom_domain,
            ))

            # 如果配置未变化，返回缓存的存储实例
            if self._storage and current_hash == self._last_config_hash:
                return self._storage

            # 配置变化，重新创建存储实例
            self._last_config_hash = current_hash

            if config.s3_enabled and all([
                config.s3_access_key_id,
                config.s3_secret_access_key,
                config.s3_bucket_name
            ]):
                # 使用S3存储
                self._storage = OpenDALS3Storage(config)
                logger.info("使用S3对象存储")
            else:
                # 使用本地存储
                self._storage = FileSystemStorage(
                    location=settings.MEDIA_ROOT,
                    base_url=settings.MEDIA_URL
                )
                logger.info("使用本地文件存储")

            return self._storage

        except Exception as e:
            logger.error(f"获取存储后端失败: {e}")
            # 出错时回退到本地存储
            return FileSystemStorage(
                location=settings.MEDIA_ROOT,
                base_url=settings.MEDIA_URL
            )

    def _open(self, name, mode='rb'):
        return self._get_storage()._open(name, mode)

    def _save(self, name, content):
        return self._get_storage()._save(name, content)

    def delete(self, name):
        return self._get_storage().delete(name)

    def exists(self, name):
        return self._get_storage().exists(name)

    def listdir(self, path):
        return self._get_storage().listdir(path)

    def size(self, name):
        return self._get_storage().size(name)

    def url(self, name):
        return self._get_storage().url(name)

    def get_accessed_time(self, name):
        return self._get_storage().get_accessed_time(name)

    def get_created_time(self, name):
        return self._get_storage().get_created_time(name)

    def get_modified_time(self, name):
        return self._get_storage().get_modified_time(name)


class OpenDALS3Storage(Storage):
    """基于OpenDAL的S3存储后端"""

    def __init__(self, config):
        self.config = config
        self.service = self._create_service()
        self.prefix = getattr(config, 's3_prefix', 'media/')

    def _create_service(self):
        """创建OpenDAL服务实例"""
        try:
            config = {
                "access_key_id": self.config.s3_access_key_id,
                "secret_access_key": self.config.s3_secret_access_key,
                "endpoint": self.config.s3_endpoint_url or "",
                "region": self.config.s3_region or "us-east-1",
                "bucket": self.config.s3_bucket_name,
            }

            # 过滤空配置
            config = {k: v for k, v in config.items() if v}

            return opendal.Operator("s3", **config)
        except Exception as e:
            logger.error(f"创建OpenDAL S3服务失败: {e}")
            raise

    def _get_full_path(self, name):
        """获取完整路径"""
        return f"{self.prefix}{name}" if self.prefix else name

    def _open(self, name, mode='rb'):
        try:
            content = self.service.read(self._get_full_path(name))
            from django.core.files.base import ContentFile
            return ContentFile(content, name)
        except Exception as e:
            raise FileNotFoundError(f"File {name} not found: {e}")

    def _save(self, name, content):
        full_path = self._get_full_path(name)
        self.service.write(full_path, content.read())
        return name

    def delete(self, name):
        try:
            self.service.delete(self._get_full_path(name))
        except Exception as e:
            logger.warning(f"删除文件失败: {e}")

    def exists(self, name):
        try:
            self.service.stat(self._get_full_path(name))
            return True
        except Exception:
            return False

    def size(self, name):
        try:
            meta = self.service.stat(self._get_full_path(name))
            return meta.content_length
        except Exception:
            return 0

    def url(self, name):
        """获取文件URL"""
        try:
            # 尝试生成预签名URL
            signed_url = self.service.presign_read(self._get_full_path(name), 3600)
            return signed_url
        except Exception:
            # 回退到直接URL
            if self.config.s3_custom_domain:
                base_url = f"https://{self.config.s3_custom_domain}/"
            else:
                region = self.config.s3_region or "us-east-1"
                base_url = f"https://{self.config.s3_bucket_name}.s3.{region}.amazonaws.com/"

            return urljoin(base_url, self._get_full_path(name))

    def get_accessed_time(self, name):
        """获取访问时间"""
        try:
            meta = self.service.stat(self._get_full_path(name))
            return meta.last_accessed
        except Exception:
            return None

    def get_created_time(self, name):
        """获取创建时间"""
        try:
            meta = self.service.stat(self._get_full_path(name))
            return meta.last_modified
        except Exception:
            return None

    def get_modified_time(self, name):
        """获取修改时间"""
        return self.get_created_time(name)