#!/usr/bin/env python
"""
初始化积分配置的命令行工具
确保所有积分配置都有默认值，支持向后兼容
"""

from django.core.management.base import BaseCommand
from home.utils.utils import PointsManager


class Command(BaseCommand):
    help = 'Initialize default points configuration'

    def handle(self, *args, **options):
        """初始化默认积分配置"""
        try:
            created_count = PointsManager.initialize_default_configs()
            if created_count > 0:
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Successfully initialized {created_count} default points configurations'
                    )
                )
            else:
                self.stdout.write(
                    self.style.SUCCESS('All points configurations already exist')
                )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error initializing points configurations: {str(e)}')
            )