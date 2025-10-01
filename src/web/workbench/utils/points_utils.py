import logging
from typing import Dict, Optional

from django.db import transaction

from home.models import UserQuota, OperationRecord
from home.utils import PointsManager


logger = logging.getLogger(__name__)


def deduct_llm_points(
    user,
    total_tokens: int,
    operation_object: str,
    metadata: Optional[Dict] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
):
    """按千 token 扣除 LLM 调用积分并记录操作日志。

    Args:
        user: Django 用户对象。
        total_tokens: 本次操作累计的 token 数。
        operation_object: 操作对象描述，用于操作记录。
        metadata: 额外的元数据字典，将合并写入操作记录。
        ip_address: 可选 IP 地址。
        user_agent: 可选用户代理。
    """
    if total_tokens is None or total_tokens <= 0:
        return {
            'deducted': False,
            'points': 0,
            'remaining': None,
            'token_units': 0,
            'reason': 'no_tokens',
        }

    points_required, token_units = PointsManager.get_llm_usage_points(total_tokens)
    if points_required <= 0:
        return {
            'deducted': False,
            'points': 0,
            'remaining': None,
            'token_units': token_units,
            'reason': 'zero_cost',
        }

    metadata = metadata.copy() if metadata else {}
    metadata.update(
        {
            'total_tokens': total_tokens,
            'token_units': token_units,
            'points_required': points_required,
        }
    )

    try:
        with transaction.atomic():
            quota, _ = UserQuota.objects.get_or_create(user=user)
            quota = UserQuota.objects.select_for_update().get(pk=quota.pk)
            remaining_before = quota.points

            if quota.consume_points(points_required):
                remaining_after = quota.points
                metadata['remaining_points'] = remaining_after
                OperationRecord.objects.create(
                    user=user,
                    operation_type='quota_consume',
                    operation_object=operation_object,
                    operation_detail=(
                        f'LLM 调用扣除 {points_required} 积分（{token_units}×千token），'
                        f'剩余 {remaining_after} 积分'
                    ),
                    status='success',
                    metadata=metadata,
                    ip_address=ip_address,
                    user_agent=user_agent,
                )
                return {
                    'deducted': True,
                    'points': points_required,
                    'remaining': remaining_after,
                    'token_units': token_units,
                    'reason': 'success',
                }

            remaining_after = quota.points
            metadata['remaining_points'] = remaining_after
            OperationRecord.objects.create(
                user=user,
                operation_type='quota_consume',
                operation_object=operation_object,
                operation_detail=(
                    f'LLM 调用扣除失败：所需 {points_required} 积分，剩余 {remaining_after} 积分'
                ),
                status='failed',
                metadata=metadata,
                ip_address=ip_address,
                user_agent=user_agent,
            )
            return {
                'deducted': False,
                'points': points_required,
                'remaining': remaining_after,
                'token_units': token_units,
                'reason': 'insufficient_points',
            }
    except Exception as exc:  # pylint: disable=broad-except
        logger.warning("Failed to deduct LLM points: %s", exc, exc_info=True)
        return {
            'deducted': False,
            'points': points_required,
            'remaining': None,
            'token_units': token_units,
            'reason': 'exception',
        }
