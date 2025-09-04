"""
测试积分扣除逻辑的正确性
验证从硬编码到PointsManager的转换是否正确
"""

from django.test import TestCase
from django.contrib.auth.models import User
from home.models import UserQuota, PointsConfig
from home.utils import PointsManager


class PointsIntegrationTest(TestCase):
    """积分扣除逻辑集成测试"""

    def setUp(self):
        """设置测试数据"""
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.user_quota, _ = UserQuota.objects.get_or_create(user=self.user)
        
        # 初始化默认配置
        PointsManager.initialize_default_configs()

    def test_audio_generation_points_calculation(self):
        """测试音频生成积分计算"""
        # 测试默认配置
        duration_10_seconds = 10
        expected_points = 10 * 2  # 默认2积分/秒
        
        actual_points = PointsManager.get_audio_generation_points(duration_10_seconds)
        self.assertEqual(actual_points, expected_points)

    def test_ocr_processing_points_calculation(self):
        """测试OCR处理积分计算"""
        # 测试默认配置
        image_count = 3
        expected_points = 3 * 5  # 默认5积分/页
        
        actual_points = PointsManager.get_ocr_processing_points(image_count)
        self.assertEqual(actual_points, expected_points)

    def test_user_quota_audio_check(self):
        """测试用户配额音频检查"""
        self.user_quota.points = 100
        self.user_quota.save()
        
        # 应该能够创建50秒的音频（50 * 2 = 100积分）
        from home.utils import PointsManager
        self.assertTrue(self.user_quota.can_consume_points(PointsManager.get_audio_generation_points(50)))
        
        # 不应该能够创建51秒的音频
        self.assertFalse(self.user_quota.can_consume_points(PointsManager.get_audio_generation_points(51)))

    def test_user_quota_ocr_check(self):
        """测试用户配额OCR检查"""
        self.user_quota.points = 15
        self.user_quota.save()
        
        # 应该能够处理3页OCR（3 * 5 = 15积分）
        from home.utils import PointsManager
        self.assertTrue(self.user_quota.can_consume_points(PointsManager.get_ocr_processing_points(3)))
        
        # 不应该能够处理4页OCR
        self.assertFalse(self.user_quota.can_consume_points(PointsManager.get_ocr_processing_points(4)))

    def test_points_consumption(self):
        """测试积分消耗"""
        self.user_quota.points = 100
        self.user_quota.save()
        
        # 消耗音频积分
        duration = 10
        expected_cost = 10 * 2
        self.assertTrue(self.user_quota.consume_points_for_audio(duration))
        self.user_quota.refresh_from_db()
        self.assertEqual(self.user_quota.points, 100 - expected_cost)
        
        # 消耗OCR积分
        image_count = 3
        expected_cost = 3 * 5
        self.user_quota.points = 100  # 重置
        self.user_quota.save()
        
        self.assertTrue(self.user_quota.consume_points_for_ocr(image_count))
        self.user_quota.refresh_from_db()
        self.assertEqual(self.user_quota.points, 100 - expected_cost)

    def test_configurable_points(self):
        """测试可配置积分"""
        # 修改音频生成积分为3积分/秒
        audio_config = PointsConfig.objects.get(operation_type='audio_generation')
        audio_config.points_per_unit = 3
        audio_config.save()
        
        # 清除缓存
        PointsManager.clear_cache('audio_generation')
        
        # 测试新配置
        duration = 10
        expected_points = 10 * 3
        actual_points = PointsManager.get_audio_generation_points(duration)
        self.assertEqual(actual_points, expected_points)

    def test_zero_duration_handling(self):
        """测试零时长处理"""
        # 零时长应该返回0积分
        self.assertEqual(PointsManager.get_audio_generation_points(0), 0)
        self.assertEqual(PointsManager.get_ocr_processing_points(0), 0)

    def test_negative_value_handling(self):
        """测试负值处理"""
        # 负值应该返回0积分或处理为0
        self.assertEqual(PointsManager.get_audio_generation_points(-1), 0)
        self.assertEqual(PointsManager.get_ocr_processing_points(-1), 0)