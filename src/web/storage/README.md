# Django OpenDAL Storage

一个基于 OpenDAL 的 Django 动态存储后端，支持本地存储和多种 S3 兼容存储服务。

## 特性

- ✅ 基于 OpenDAL，支持多种云存储协议
- ✅ 动态配置切换，无需重启服务
- ✅ 支持本地存储和 S3 兼容存储
- ✅ 错误回退机制
- ✅ 多种配置方式
- ✅ 标准 Django Storage 接口

## 安装

```bash
# 确保已安装 opendal
pip install opendal
```

## 快速开始

### 方式1：使用环境变量配置

```python
# settings.py
DEFAULT_FILE_STORAGE = 'storage.DynamicStorage'

# 环境变量
S3_ENABLED=true
S3_ACCESS_KEY_ID=your-access-key
S3_SECRET_ACCESS_KEY=your-secret-key
S3_BUCKET_NAME=your-bucket
S3_REGION=us-east-1
```

### 方式2：使用 Django settings 配置

```python
# settings.py
DEFAULT_FILE_STORAGE = 'storage.DynamicStorage'

# 存储配置
S3_ENABLED = True
S3_ACCESS_KEY_ID = 'your-access-key'
S3_SECRET_ACCESS_KEY = 'your-secret-key'
S3_BUCKET_NAME = 'your-bucket'
S3_REGION = 'us-east-1'
S3_ENDPOINT_URL = ''  # 可选，用于 S3 兼容服务
S3_CUSTOM_DOMAIN = ''  # 可选，自定义域名
S3_PREFIX = 'media/'  # 可选，存储路径前缀
```

### 方式3：使用自定义配置类

```python
# settings.py
DEFAULT_FILE_STORAGE = 'storage.DynamicStorage'
STORAGE_CONFIG_CLASS = 'myapp.config.MyStorageConfig'

# myapp/config.py
class MyStorageConfig:
    @classmethod
    def get_config(cls):
        class Config:
            s3_enabled = True
            s3_access_key_id = 'your-access-key'
            s3_secret_access_key = 'your-secret-key'
            s3_bucket_name = 'your-bucket'
            s3_region = 'us-east-1'
            s3_endpoint_url = ''
            s3_custom_domain = ''
            s3_prefix = 'media/'

        return Config()
```

### 方式4：使用回调函数（最灵活）

```python
# settings.py
from storage import DynamicStorage
from myapp.config import get_storage_config

DEFAULT_FILE_STORAGE = DynamicStorage(config_callback=get_storage_config)
```

## 支持的存储服务

- AWS S3
- 阿里云 OSS
- 腾讯云 COS
- 华为云 OBS
- 七牛云 Kodo
- 其他 S3 兼容服务

## 配置参数

| 参数 | 类型 | 默认值 | 描述 |
|------|------|--------|------|
| s3_enabled | bool | False | 是否启用 S3 存储 |
| s3_access_key_id | str | '' | S3 Access Key ID |
| s3_secret_access_key | str | '' | S3 Secret Access Key |
| s3_bucket_name | str | '' | 存储桶名称 |
| s3_region | str | 'us-east-1' | 存储区域 |
| s3_endpoint_url | str | '' | S3 兼容服务端点 |
| s3_custom_domain | str | '' | 自定义域名 |
| s3_prefix | str | 'media/' | 存储路径前缀 |

## 高级用法

### 动态配置切换

存储后端会自动检测配置变化，无需重启服务即可切换存储方式。

### 错误回退

如果 S3 配置错误或连接失败，会自动回退到本地文件存储。

### 自定义存储后端

```python
from storage import OpenDALS3Storage

# 直接使用 S3 存储
s3_storage = OpenDALS3Storage(config)
```

## 许可证

MIT