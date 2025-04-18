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
            title = f"{user.username}的Book2TTS音频 - {book.name}"
            description = f"来自{user.username}在Book2TTS上发布的{book.name}的最新音频。"
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
            title = f"{user.username}的Book2TTS音频"
            description = f"来自{user.username}在Book2TTS上发布的最新音频。"
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
        item_link = audio_url or request.build_absolute_uri(reverse('public_rss_audio_detail', args=[segment.id]))

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

# 新增加的不需要登录的RSS音频资源函数
def public_audio_file(request, segment_id):
    """直接提供音频文件，不需要用户登录，通过segment_id访问"""
    # 获取音频片段对象，确保它存在且已发布
    segment = get_object_or_404(AudioSegment, id=segment_id, published=True)
    
    # 确保音频文件存在
    if not segment.file:
        from django.http import Http404
        raise Http404("音频文件不存在")
    
    # 直接返回音频文件的URL，而不是渲染HTML页面
    audio_url = request.build_absolute_uri(segment.file.url)
    return HttpResponse(f'<audio controls autoplay><source src="{audio_url}" type="audio/mpeg"></audio>', content_type='text/html')

def public_rss_audio_detail(request, segment_id):
    """提供RSS音频详情页面，不需要用户登录"""
    # 获取音频片段对象，确保它存在且已发布
    segment = get_object_or_404(AudioSegment, id=segment_id, published=True)
    
    context = {
        'segment': segment,
        'from_rss': True  # 标记是从RSS访问的
    }
    
    return render(request, "home/audio_detail.html", context)

def public_rss_book_audio(request, book_id):
    """提供书籍音频列表，不需要用户登录"""
    # 获取书籍对象，确保它存在
    book = get_object_or_404(Books, id=book_id)
    
    # 获取该书籍下已发布的音频片段
    book_audio_segments = AudioSegment.objects.filter(
        book=book,
        published=True
    ).order_by('-id')  # 按ID降序排列（最新的在前）
    
    context = {
        'book': book,
        'audio_segments': book_audio_segments,
        'display_title': f'《{book.name}》的音频列表',
        'from_rss': True  # 标记是从RSS访问的
    }
    
    return render(request, "home/index.html", context)

def public_rss_feed_by_token(request, token, book_id=None):
    """Generate a public RSS feed for a specific user based on their RSS token.
    No authentication required for this endpoint."""
    from workbench.models import UserProfile
    from django.contrib.auth.models import User
    
    try:
        # 尝试获取对应token的用户profile
        profile = get_object_or_404(UserProfile, rss_token=token)
        user = profile.user
        
        # 设置feed标题和描述
        if book_id:
            book = get_object_or_404(Books, id=book_id, user=user)
            title = f"{user.username}的Book2TTS音频 - {book.name}"
            description = f"来自{user.username}在Book2TTS上发布的{book.name}的最新音频。"
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
            title = f"{user.username}的Book2TTS音频"
            description = f"来自{user.username}在Book2TTS上发布的最新音频。"
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
        item_link = audio_url or request.build_absolute_uri(reverse('public_rss_audio_detail', args=[segment.id]))

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
