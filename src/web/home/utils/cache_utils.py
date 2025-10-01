"""
缓存管理工具函数
"""
from django.core.cache import cache
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from workbench.models import AudioSegment


HOSTS_SUFFIX = "::hosts"


def _hosts_key(base_key: str) -> str:
    return f"{base_key}{HOSTS_SUFFIX}"


def register_rss_cache_key(base_key: str, full_key: str) -> None:
    """记录同一逻辑缓存下实际写入的 host 版本缓存键。"""
    hosts_key = _hosts_key(base_key)
    hosts = cache.get(hosts_key) or []
    if full_key not in hosts:
        hosts.append(full_key)
        cache.set(hosts_key, hosts, None)


def clear_cache_variants(base_key: str) -> None:
    """删除 base_key 及其 host 变体缓存。"""
    hosts_key = _hosts_key(base_key)
    hosts = cache.get(hosts_key) or []
    for key in hosts:
        cache.delete(key)
    cache.delete(base_key)
    cache.delete(hosts_key)


def clear_rss_cache_for_user(user_id):
    """清除特定用户的所有RSS缓存"""
    cache_keys = [
        f'rss_feed_user_{user_id}',
        'rss_feed_all',  # 全局RSS也需要清除
    ]
    
    # 清除基本缓存键
    for key in cache_keys:
        clear_cache_variants(key)
    
    # 清除用户相关的token和用户名缓存
    try:
        from workbench.models import UserProfile
        from django.contrib.auth.models import User
        
        # 获取用户信息
        user = User.objects.filter(id=user_id).first()
        if user:
            # 清除用户名缓存
            clear_cache_variants(f'rss_username_{user.username}')
            
        profile = UserProfile.objects.filter(user_id=user_id).first()
        if profile:
            # 清除用户token相关的缓存
            token_cache_keys = [
                f'rss_token_{profile.rss_token}_all',
            ]
            for key in token_cache_keys:
                clear_cache_variants(key)
    except Exception:
        pass


def clear_rss_cache_for_book(book_id, user_id=None):
    """清除特定书籍的RSS缓存"""
    if user_id:
        clear_rss_cache_for_user(user_id)
    
    # 清除书籍相关的缓存
    try:
        from workbench.models import UserProfile, Books
        book = Books.objects.filter(id=book_id).first()
        if book and book.user:
            profile = UserProfile.objects.filter(user=book.user).first()
            if profile:
                book_cache_keys = [
                    f'rss_book_{profile.rss_token}_{book_id}',
                    f'rss_token_{profile.rss_token}_{book_id}',
                ]
                for key in book_cache_keys:
                    clear_cache_variants(key)
    except Exception:
        pass


@receiver(post_save, sender=AudioSegment)
def clear_audio_segment_cache(sender, instance, created, **kwargs):
    """当音频片段保存时清除相关缓存"""
    if instance.book and instance.book.user:
        user_id = instance.book.user.id
        book_id = instance.book.id
        
        # 清除用户和书籍相关的缓存
        clear_rss_cache_for_user(user_id)
        clear_rss_cache_for_book(book_id, user_id)


@receiver(post_delete, sender=AudioSegment)
def clear_audio_segment_cache_on_delete(sender, instance, **kwargs):
    """当音频片段删除时清除相关缓存"""
    if instance.book and instance.book.user:
        user_id = instance.book.user.id
        book_id = instance.book.id
        
        # 清除用户和书籍相关的缓存
        clear_rss_cache_for_user(user_id)
        clear_rss_cache_for_book(book_id, user_id) 
