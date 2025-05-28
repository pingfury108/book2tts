from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse
from workbench.models import AudioSegment, Books, UserProfile
from django.urls import reverse
import uuid
from feedgen.feed import FeedGenerator
from home.utils.rss_utils import (
    estimate_audio_duration, 
    ensure_rss_token, 
    clean_xml_output, 
    create_podcast_feed, 
    add_podcast_entry, 
    postprocess_rss
)
from django.contrib.auth.decorators import login_required

# Create your views here.


def index(request):
    context = {}
    
    # 如果用户已登录，获取已发布的音频片段
    if request.user.is_authenticated:
        # 确保用户有一个有效的RSS token
        ensure_rss_token(request.user)
        
        published_audio_segments = AudioSegment.objects.filter(
            book__user=request.user,
            published=True
        ).order_by('-id')  # 按ID降序排列（最新的在前）
        
        context['audio_segments'] = published_audio_segments
    
    return render(request, "home/index.html", context)


def audio_detail(request, segment_id):
    # 获取音频片段对象，确保它存在且已发布
    segment = get_object_or_404(AudioSegment, id=segment_id, published=True)
    
    # 如果用户已登录，确保用户只能访问自己的音频片段
    # 修改逻辑：允许未登录用户访问已发布的音频片段（从RSS访问）
    if request.user.is_authenticated and request.user != segment.book.user:
        from django.http import Http404
        raise Http404("您没有权限访问此页面")
    
    # 确保音频作者有一个有效的RSS token
    if segment.book.user:  # 检查确保用户存在
        ensure_rss_token(segment.book.user)
    
    context = {
        'segment': segment
    }
    
    return render(request, "home/audio_detail.html", context)


def book_audio_list(request, book_id):
    # 获取书籍对象，确保它存在
    book = get_object_or_404(Books, id=book_id)
    
    # 确保已登录用户只能访问自己的书籍
    # 修改逻辑：允许未登录用户通过RSS访问已发布的书籍
    if request.user.is_authenticated and request.user != book.user:
        from django.http import Http404
        raise Http404("您没有权限访问此页面")
    
    # 确保用户有一个有效的RSS token
    if book.user:  # 确保用户存在
        ensure_rss_token(book.user)
    
    # 获取该书籍下已发布的音频片段
    book_audio_segments = AudioSegment.objects.filter(
        book=book,
        published=True
    ).order_by('-id')  # 按ID降序排列（最新的在前）
    
    context = {
        'book': book,
        'audio_segments': book_audio_segments,
        'display_title': f'《{book.name}》的音频列表'
    }
    
    return render(request, "home/index.html", context)


def audio_rss_feed(request, user_id=None):
    """Generate an RSS feed for all published audio segments.
    If user_id is provided, only show that user's audio segments."""
    
    if user_id:
        # Fetch the user or return 404
        from django.contrib.auth.models import User
        user = get_object_or_404(User, id=user_id)
        title = f"{user.username}的Book2TTS音频"
        description = f"来自{user.username}在Book2TTS上发布的最新音频。"
        author_name = user.username
        author_email = user.email if user.email else ""
        
        # Filter segments for this specific user
        segments = AudioSegment.objects.filter(
            published=True, 
            book__user__id=user_id
        ).order_by('-updated_at')[:50]  # Limit to 50 items
    else:
        # Original behavior for all users
        title = "Book2TTS 公开发布的音频"
        description = "来自 Book2TTS 的最新公开发布音频。"
        author_name = "Book2TTS"
        author_email = ""
        
        # Fetch all published audio segments, ordered by most recent first
        segments = AudioSegment.objects.filter(
            published=True
        ).order_by('-updated_at')[:50]  # Limit to 50 items

    link = request.build_absolute_uri(reverse('home'))  # Link to the homepage
    # 站点图标URL
    image_url = request.build_absolute_uri('/static/images/logo.png')

    # 获取站点语言
    language = "zh"  # 简化语言代码

    # 创建feed
    feed = create_podcast_feed(
        title=title,
        link=link,
        description=description,
        language=language,
        author_name=author_name,
        image_url=image_url,
        author_email=author_email
    )

    for segment in segments:
        # 使用音频文件直接URL而不是网页URL
        audio_url = request.build_absolute_uri(segment.file.url) if segment.file else None
        # 备用页面链接，如果没有音频文件
        item_link = audio_url or request.build_absolute_uri(reverse('audio_detail', args=[segment.id]))
        
        # 估计音频时长
        duration_seconds, formatted_duration = estimate_audio_duration(segment.file if segment.file else None)
        
        # 尝试获取段落的图片（如果有）或使用书籍的封面图
        image_url = None
        if hasattr(segment.book, 'cover_image') and segment.book.cover_image:
            image_url = request.build_absolute_uri(segment.book.cover_image.url)
        else:
            image_url = request.build_absolute_uri('/static/images/default_cover.png')
        
        # 准备简短文本描述
        description = segment.text or ''
        # 截取文本，保留前300个字符
        short_description = description[:300] + ('...' if len(description) > 300 else '')
        
        # 添加条目
        add_podcast_entry(
            feed=feed,
            title=f"{segment.book.name} - {segment.title}",
            audio_url=audio_url,
            audio_size=segment.file.size if segment.file else 0,
            link=item_link,
            description=short_description,
            pubdate=segment.updated_at,
            author=segment.book.user.username if segment.book.user else "未知作者",
            duration_formatted=formatted_duration,
            duration_seconds=duration_seconds,
            image_url=image_url,
            episode_number=segment.id,
            season_number=segment.book.id if segment.book else None,
            unique_id=str(segment.id)
        )

    # 生成XML
    xml_string = feed.rss_str(pretty=True).decode('utf-8')
    
    # 后处理添加自定义标签
    xml_string = postprocess_rss(xml_string)
    
    # 应用清理
    cleaned_xml = clean_xml_output(xml_string)
    
    response = HttpResponse(cleaned_xml, content_type='application/xml')
    return response


def audio_rss_feed_by_username(request, username):
    """Generate an RSS feed for a specific user's published audio segments by username."""
    from django.contrib.auth.models import User
    user = get_object_or_404(User, username=username)
    return audio_rss_feed(request, user_id=user.id)


def audio_rss_feed_by_book(request, token, book_id):
    """Generate an RSS feed for a specific book based on user's RSS token and book ID."""
    from workbench.models import UserProfile, Books
    
    try:
        # Get the user profile by token
        profile = get_object_or_404(UserProfile, rss_token=token)
        user = profile.user
        
        # Get the book, ensuring it belongs to the user
        book = get_object_or_404(Books, id=book_id, user=user)
        
        # Set feed title and description
        title = f"《{book.name}》的Book2TTS音频"
        description = f"《{book.name}》在Book2TTS上发布的音频。"
        author_name = user.username
        author_email = user.email if user.email else ""
        
        # Filter segments for this specific book
        segments = AudioSegment.objects.filter(
            published=True, 
            book=book
        ).order_by('-updated_at')[:50]  # Limit to 50 items
        
    except Exception as e:
        # Return 404 if any error occurs
        from django.http import Http404
        raise Http404("找不到该RSS订阅源")

    link = request.build_absolute_uri(reverse('home'))  # Link to homepage
    
    # 尝试获取书籍的封面图片
    image_url = None
    if hasattr(book, 'cover_image') and book.cover_image:
        image_url = request.build_absolute_uri(book.cover_image.url)
    else:
        image_url = request.build_absolute_uri('/static/images/default_cover.png')

    # 获取站点语言
    language = "zh"  # 简化语言代码

    # 创建feed
    feed = create_podcast_feed(
        title=title,
        link=link,
        description=description,
        language=language,
        author_name=author_name,
        image_url=image_url,
        author_email=author_email
    )

    for segment in segments:
        # 使用音频文件直接URL而不是网页URL
        audio_url = request.build_absolute_uri(segment.file.url) if segment.file else None
        # 备用页面链接，如果没有音频文件
        item_link = audio_url or request.build_absolute_uri(reverse('audio_detail', args=[segment.id]))

        # 估计音频时长
        duration_seconds, formatted_duration = estimate_audio_duration(segment.file if segment.file else None)

        # 准备简短文本描述
        description = segment.text or ''
        # 截取文本，保留前300个字符
        short_description = description[:300] + ('...' if len(description) > 300 else '')

        # 添加条目
        add_podcast_entry(
            feed=feed,
            title=f"{segment.book.name} - {segment.title}",
            audio_url=audio_url,
            audio_size=segment.file.size if segment.file else 0,
            link=item_link,
            description=short_description,
            pubdate=segment.updated_at,
            author=user.username,
            duration_formatted=formatted_duration,
            duration_seconds=duration_seconds,
            image_url=image_url,
            episode_number=segment.id,
            season_number=segment.book.id if segment.book else None,
            unique_id=str(segment.id)
        )

    # 生成XML
    xml_string = feed.rss_str(pretty=True).decode('utf-8')
    
    # 后处理添加自定义标签
    xml_string = postprocess_rss(xml_string)
    
    # 应用清理
    cleaned_xml = clean_xml_output(xml_string)
    
    response = HttpResponse(cleaned_xml, content_type='application/xml')
    return response


def audio_rss_feed_by_token(request, token, book_id=None):
    """Generate an RSS feed for a specific user based on their RSS token."""
    from workbench.models import UserProfile
    from django.contrib.auth.models import User
    
    try:
        # 尝试获取对应token的用户profile
        profile = get_object_or_404(UserProfile, rss_token=token)
        user = profile.user
        
        # 设置feed标题和描述
        if book_id:
            book = get_object_or_404(Books, id=book_id, user=user)
            title = f"{user.username} - 《{book.name}》有声书"
            description = f"{book.name}的有声书内容，由{user.username}朗读制作。"
            # 尝试获取书籍的封面图片
            if hasattr(book, 'cover_image') and book.cover_image:
                image_url = request.build_absolute_uri(book.cover_image.url)
            else:
                image_url = request.build_absolute_uri('/static/images/default_cover.png')
            
            # 筛选该用户特定书籍的已发布音频片段
            segments = AudioSegment.objects.filter(
                published=True, 
                book__user=user,
                book_id=book_id
            ).order_by('-updated_at')[:50]  # 限制为50条
        else:
            title = f"{user.username}的有声书合集"
            description = f"{user.username}的有声书作品集"
            image_url = request.build_absolute_uri('/static/images/logo.png')
            # 筛选该用户的已发布音频片段
            segments = AudioSegment.objects.filter(
                published=True, 
                book__user=user
            ).order_by('-updated_at')[:50]  # 限制为50条
        
        # 如果找不到音频片段，仍然返回空的feed
        if not segments.exists():
            segments = []
    except Exception as e:
        from django.http import Http404
        raise Http404("找不到该RSS订阅源")

    link = request.build_absolute_uri(reverse('home'))  # 链接到首页

    # 获取站点语言
    language = "zh"  # 简化语言代码

    # 创建feed
    feed = create_podcast_feed(
        title=title,
        link=link,
        description=description,
        language=language,
        author_name=user.username,
        image_url=image_url,
        author_email=user.email if user.email else ""
    )

    for segment in segments:
        # 使用音频文件直接URL而不是网页URL
        audio_url = request.build_absolute_uri(segment.file.url) if segment.file else None
        # 备用页面链接，如果没有音频文件
        item_link = audio_url or request.build_absolute_uri(reverse('audio_detail', args=[segment.id]))

        # 估计音频时长
        duration_seconds, formatted_duration = estimate_audio_duration(segment.file if segment.file else None)
        
        # 准备简短文本描述
        description = segment.text or ''
        # 截取文本，保留前300个字符
        short_description = description[:300] + ('...' if len(description) > 300 else '')
        
        # 尝试获取段落的图片或使用书籍的封面图
        item_image_url = None
        if hasattr(segment.book, 'cover_image') and segment.book.cover_image:
            item_image_url = request.build_absolute_uri(segment.book.cover_image.url)
        else:
            item_image_url = image_url

        # 添加条目
        add_podcast_entry(
            feed=feed,
            title=f"{segment.book.name} - {segment.title}",
            audio_url=audio_url,
            audio_size=segment.file.size if segment.file else 0,
            link=item_link,
            description=short_description,
            pubdate=segment.updated_at,
            author=user.username,
            duration_formatted=formatted_duration,
            duration_seconds=duration_seconds,
            image_url=item_image_url,
            episode_number=segment.id,
            season_number=segment.book.id if segment.book else None,
            unique_id=str(segment.id)
        )

    # 生成XML
    xml_string = feed.rss_str(pretty=True).decode('utf-8')
    
    # 后处理添加自定义标签
    xml_string = postprocess_rss(xml_string)
    
    # 应用清理
    cleaned_xml = clean_xml_output(xml_string)
    
    response = HttpResponse(cleaned_xml, content_type='application/xml')
    return response


@login_required
def profile(request):
    """用户个人资料页面"""
    from home.models import UserQuota
    from workbench.models import UserProfile
    
    # 确保用户有一个有效的RSS token
    ensure_rss_token(request.user)
    
    # 获取或创建用户配额
    user_quota, created = UserQuota.objects.get_or_create(user=request.user)
    
    # 获取用户profile
    user_profile, profile_created = UserProfile.objects.get_or_create(user=request.user)
    
    # 计算配额显示信息
    remaining_seconds = user_quota.remaining_audio_duration
    hours = remaining_seconds // 3600
    minutes = (remaining_seconds % 3600) // 60
    seconds = remaining_seconds % 60
    
    # 计算百分比（基于默认3600秒 = 1小时）
    default_quota = 3600
    percentage = min(100, (remaining_seconds * 100) / default_quota)
    
    # 确定配额状态和颜色
    if remaining_seconds > 1800:  # 超过30分钟
        status_class = "text-success"
        status_icon = "✅"
        progress_class = "bg-success"
        status_text = "充足"
    elif remaining_seconds > 300:  # 超过5分钟
        status_class = "text-warning"
        status_icon = "⚠️"
        progress_class = "bg-warning"
        status_text = "一般"
    else:  # 少于5分钟
        status_class = "text-error"
        status_icon = "❌"
        progress_class = "bg-error"
        status_text = "不足"
    
    # 存储空间信息
    storage_bytes = user_quota.available_storage_bytes
    storage_display = user_quota.get_storage_display()
    
    # 统计用户数据
    from workbench.models import Books, AudioSegment
    total_books = Books.objects.filter(user=request.user).count()
    total_audio_segments = AudioSegment.objects.filter(book__user=request.user).count()
    published_audio_segments = AudioSegment.objects.filter(book__user=request.user, published=True).count()
    unpublished_audio_segments = total_audio_segments - published_audio_segments
    
    context = {
        'user_quota': user_quota,
        'user_profile': user_profile,
        'remaining_seconds': remaining_seconds,
        'hours': hours,
        'minutes': minutes,
        'seconds': seconds,
        'status_class': status_class,
        'status_icon': status_icon,
        'progress_class': progress_class,
        'percentage': round(percentage, 1),
        'status_text': status_text,
        'storage_display': storage_display,
        'storage_bytes': storage_bytes,
        'total_books': total_books,
        'total_audio_segments': total_audio_segments,
        'published_audio_segments': published_audio_segments,
        'unpublished_audio_segments': unpublished_audio_segments,
    }
    
    return render(request, "home/profile.html", context)


@login_required
def operation_records(request):
    """用户操作记录页面"""
    from home.models import OperationRecord
    from django.core.paginator import Paginator
    
    # 获取用户的操作记录，按时间倒序排列
    records = OperationRecord.objects.filter(user=request.user).order_by('-created_at')
    
    # 分页处理
    paginator = Paginator(records, 20)  # 每页显示20条记录
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'records': page_obj.object_list,
    }
    
    return render(request, "home/operation_records.html", context)

# 创建RSS Feed的助手函数
def create_podcast_feed(title, link, description, language, author_name, image_url=None, author_email=None):
    """
    使用feedgen库创建一个podcast feed
    """
    fg = FeedGenerator()
    fg.load_extension('podcast')
    
    # 基本RSS feed信息
    fg.title(title)
    fg.link(href=link, rel='alternate')
    fg.description(description)
    fg.language(language)
    fg.author({'name': author_name, 'email': author_email})
    fg.logo(image_url)
    fg.image(image_url)
    
    # Apple Podcasts和Podcast Index标准所需信息
    fg.podcast.itunes_author(author_name)
    fg.podcast.itunes_summary(description)
    fg.podcast.itunes_subtitle(description[:255] if description else '')
    fg.podcast.itunes_owner(author_name, author_email)
    fg.podcast.itunes_explicit('no')  # 修改为 'no'，这是feedgen库支持的值
    fg.podcast.itunes_category('Arts', 'Books')
    fg.podcast.itunes_type('episodic')
    fg.podcast.itunes_image(image_url)
    
    return fg
