#!/usr/bin/env python3
"""
验证OCR积分扣除修复是否正确的简单测试脚本
"""

import sys
import os
import django

# 添加项目路径
sys.path.append('/Users/pingfury/codes/book2tts/src/web')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'book2tts.settings')

# 设置Django
django.setup()

from django.test import TestCase, RequestFactory
from django.contrib.auth.models import User
from workbench.models import Books
from workbench.views.book_views import check_and_deduct_points_for_ocr, deduct_points_for_ocr
from home.models import UserQuota, OperationRecord
from home.utils import PointsManager

def test_ocr_point_deduction_logic():
    """测试OCR积分扣除逻辑"""
    print("开始测试OCR积分扣除逻辑...")
    
    # 创建测试用户
    test_user = User.objects.create_user(
        username='testuser_ocr',
        password='testpass'
    )
    
    # 创建用户配额
    user_quota = UserQuota.objects.create(
        user=test_user,
        points=100
    )
    
    print(f"测试用户初始积分: {user_quota.points}")
    
    # 测试1: 检查积分是否足够
    print("\n测试1: 检查积分是否足够")
    result = check_and_deduct_points_for_ocr(test_user, 5, auto_ocr=True)
    expected_points = PointsManager.get_ocr_processing_points(5)
    print(f"处理5页需要积分: {expected_points}")
    print(f"检查结果: {result}")
    
    # 测试2: 扣除积分
    print("\n测试2: 扣除积分")
    success = deduct_points_for_ocr(test_user, 3, auto_ocr=True)
    print(f"扣除3页积分结果: {success}")
    
    # 检查积分是否正确扣除
    user_quota.refresh_from_db()
    expected_remaining = 100 - PointsManager.get_ocr_processing_points(3)
    print(f"预期剩余积分: {expected_remaining}")
    print(f"实际剩余积分: {user_quota.points}")
    print(f"积分扣除正确: {user_quota.points == expected_remaining}")
    
    # 检查操作记录
    operations = OperationRecord.objects.filter(user=test_user)
    print(f"\n操作记录数量: {operations.count()}")
    if operations.exists():
        op = operations.last()
        print(f"最新操作记录: {op.operation_type} - {op.operation_detail}")
        print(f"操作元数据: {op.metadata}")
    
    # 清理测试数据
    OperationRecord.objects.filter(user=test_user).delete()
    user_quota.delete()
    test_user.delete()
    
    print("\n测试完成!")

if __name__ == '__main__':
    test_ocr_point_deduction_logic()