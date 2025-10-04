from .models import SiteConfig


def site_config(request):
    """
    上下文处理器：将站点配置注入到所有模板中
    """
    config = SiteConfig.get_config()

    return {
        'site_config': config,
        'google_ads_enabled': config.google_ads_enabled,
        'google_ads_script': config.google_ads_script,
        'site_description': config.site_description,
        'site_keywords': config.site_keywords,
    }