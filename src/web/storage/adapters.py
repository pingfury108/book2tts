"""
适配器模块 - 用于与现有项目集成
"""


def site_config_adapter():
    """
    SiteConfig 适配器回调函数

    用于与现有的 SiteConfig 模型集成
    """
    try:
        from home.models import SiteConfig
        return SiteConfig.get_config()
    except ImportError:
        # 如果 SiteConfig 不存在，返回 None 使用默认存储
        return None