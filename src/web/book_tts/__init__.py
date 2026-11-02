# Django 6.1+ 内置 Tasks 框架（django.tasks + django_tasks_db 的 DATABASE backend）
# 替代 Celery：worker 由 `python manage.py db_worker` 提供。
#
# 兼容垫片：django-tasks-db(0.13.0) 的 core 模式在注解里用 `Task[P, T]` /
# `TaskResult[P, T]` 泛型下标，而 Django 6.1 的 Task / TaskResult 是普通
# dataclass（上游 #53 已声明支持 6.1，等上游发版适配后移除本垫片）。
from django.tasks import base as _tasks_base

for _cls in (_tasks_base.Task, _tasks_base.TaskResult):
    if not getattr(_cls, "__class_getitem__", None):
        _cls.__class_getitem__ = classmethod(lambda cls, item: cls)
