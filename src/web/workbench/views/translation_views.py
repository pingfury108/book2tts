from django.contrib.admin.views.decorators import staff_member_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404
from django.views.decorators.http import require_http_methods
from django.contrib import messages
from django.utils import timezone
from datetime import timedelta

from ..models import TranslationCache


@staff_member_required
def translation_cache_list(request):
    """翻译缓存列表页面"""
    search_query = request.GET.get('q', '')
    language_filter = request.GET.get('lang', '')

    # 构建查询
    queryset = TranslationCache.objects.all()

    if search_query:
        queryset = queryset.filter(
            Q(original_text__icontains=search_query) |
            Q(translated_text__icontains=search_query) |
            Q(text_md5__icontains=search_query)
        )

    if language_filter:
        queryset = queryset.filter(target_language=language_filter)

    # 分页
    paginator = Paginator(queryset, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # 获取统计信息
    stats = TranslationCache.get_cache_stats()

    # 获取语言选项
    language_choices = TranslationCache.LANGUAGE_CHOICES

    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'language_filter': language_filter,
        'language_choices': language_choices,
        'stats': stats,
    }

    return render(request, 'admin/translation_cache_list.html', context)


@staff_member_required
def translation_cache_detail(request, cache_id):
    """翻译缓存详情页面"""
    cache = get_object_or_404(TranslationCache, id=cache_id)

    context = {
        'cache': cache,
    }

    return render(request, 'admin/translation_cache_detail.html', context)


@staff_member_required
@require_http_methods(["POST"])
def translation_cache_delete(request, cache_id):
    """删除翻译缓存"""
    cache = get_object_or_404(TranslationCache, id=cache_id)
    cache.delete()

    messages.success(request, f'已删除缓存记录 {cache.text_md5[:8]}...')

    return JsonResponse({'status': 'success', 'message': '删除成功'})


@staff_member_required
@require_http_methods(["POST"])
def translation_cache_cleanup(request):
    """批量清理翻译缓存"""
    days = int(request.POST.get('days', 30))

    if days < 1:
        return JsonResponse({'status': 'error', 'message': '天数必须大于0'})

    deleted_count = TranslationCache.cleanup_old_cache(days)

    messages.success(request, f'已清理 {deleted_count} 条 {days} 天前的缓存记录')

    return JsonResponse({
        'status': 'success',
        'message': f'清理完成，共删除 {deleted_count} 条记录',
        'deleted_count': deleted_count
    })


@staff_member_required
def translation_cache_stats_api(request):
    """获取翻译缓存统计信息API"""
    stats = TranslationCache.get_cache_stats()

    # 添加一些额外的统计信息
    recent_stats = TranslationCache.objects.filter(
        created_at__gte=timezone.now() - timedelta(days=7)
    ).count()

    stats['recent_week_count'] = recent_stats

    return JsonResponse(stats)


@staff_member_required
@require_http_methods(["POST"])
def translation_cache_bulk_delete(request):
    """批量删除翻译缓存"""
    cache_ids = request.POST.getlist('cache_ids')

    if not cache_ids:
        return JsonResponse({'status': 'error', 'message': '请选择要删除的缓存记录'})

    try:
        cache_ids = [int(id) for id in cache_ids]
        deleted_count = TranslationCache.objects.filter(id__in=cache_ids).delete()[0]

        messages.success(request, f'已删除 {deleted_count} 条缓存记录')

        return JsonResponse({
            'status': 'success',
            'message': f'删除完成，共删除 {deleted_count} 条记录',
            'deleted_count': deleted_count
        })
    except (ValueError, TypeError):
        return JsonResponse({'status': 'error', 'message': '无效的缓存ID'})