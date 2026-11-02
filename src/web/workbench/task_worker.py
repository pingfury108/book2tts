"""进程内任务 worker：把 django_tasks_db 的执行循环跑在 web 进程的后台线程里。

- 领取任务走 exclusive_transaction（SQLite 下为 BEGIN EXCLUSIVE），
  多线程/多 gunicorn worker 均不会重复执行同一任务
- 环境变量 B2T_TASK_WORKER=0 可关闭（例如想把 worker 拆成独立进程/容器部署时）
"""
import logging
import os
import threading
import time
from django.db.utils import OperationalError

logger = logging.getLogger(__name__)

_started = False
_start_lock = threading.Lock()


def start_task_worker() -> None:
    """在当前进程启动一个后台任务线程（幂等；B2T_TASK_WORKER=0 关闭）。"""
    global _started
    if os.getenv("B2T_TASK_WORKER", "1").strip().lower() in ("0", "false", "no", "off"):
        logger.info("任务 worker 已通过 B2T_TASK_WORKER=0 关闭")
        return
    with _start_lock:
        if _started:
            return
        _started = True
    threading.Thread(target=_loop, name="task-worker", daemon=True).start()
    logger.info("任务 worker 线程已启动")


def _reset_orphan_running_tasks() -> None:
    """把长时间停留在 RUNNING 的任务复位为 READY（进程被杀时的兜底）。

    单任务执行上限约 30 分钟，超过 45 分钟仍为 RUNNING 视为孤儿。
    """
    from datetime import timedelta

    from django.utils import timezone
    from django_tasks_db.compat import TaskResultStatus
    from django_tasks_db.models import DBTaskResult

    cutoff = timezone.now() - timedelta(minutes=45)
    stalled = DBTaskResult.objects.filter(
        status=TaskResultStatus.RUNNING, started_at__lt=cutoff
    )
    for result in stalled:
        result.status = TaskResultStatus.READY
        result.started_at = None
        result.worker_id = ""
        result.save()
        logger.warning("孤儿任务已复位: %s", result.id)


def _loop() -> None:
    from django.apps import apps

    # 等 AppConfig.ready() 全部执行完再碰数据库，
    # 避免 "Accessing the database during app initialization" 警告
    waited = 0.0
    while not apps.ready and waited < 30:
        time.sleep(0.5)
        waited += 0.5

    table_missing_logged = False
    while True:
        try:
            from django_tasks_db.compat import DEFAULT_TASK_BACKEND_ALIAS
            from django_tasks_db.management.commands.db_worker import Worker

            _reset_orphan_running_tasks()
            Worker(
                queue_names=["default"],
                interval=5.0,
                batch=False,
                backend_name=DEFAULT_TASK_BACKEND_ALIAS,
                startup_delay=True,
                max_tasks=None,
                worker_id=f"web-{os.getpid()}-{threading.get_ident()}",
                excluded_queue_names=[],
            ).run()
        except OperationalError as e:
            # 典型场景：尚未 migrate，任务表不存在。只提示一次，避免刷屏
            if "no such table" in str(e):
                if not table_missing_logged:
                    logger.warning("任务表尚未创建（先运行 manage.py migrate），10 秒后自动重试")
                    table_missing_logged = True
                time.sleep(10)
            else:
                logger.warning("任务 worker 数据库异常: %s", e)
                time.sleep(10)
        except Exception:  # pylint: disable=broad-except
            logger.exception("任务 worker 异常，30 秒后重启循环")
            time.sleep(30)
