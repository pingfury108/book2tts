# Vendored from django-tasks-db @ 5c7cbd1d015bd6cc6bbc1c7f35ff2cef839d2f13
# 修补：Django 6.1 核心 Task / TaskResult 不支持泛型下标（仅类型注解用途），
# 已移除对 django-stubs-ext 的运行时 monkeypatch 依赖。
__version__ = "0.13.0"

from .backend import DatabaseBackend

__all__ = [
    "DatabaseBackend",
    "__version__",
]
