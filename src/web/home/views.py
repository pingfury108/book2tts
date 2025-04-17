from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse
from workbench.models import AudioSegment, Books, UserProfile
from django.utils.feedgenerator import Rss201rev2Feed
from django.urls import reverse
from django.utils.html import escape
import datetime
import uuid

# 确保用户有一个有效的rss_token
def ensure_rss_token(user):
    """确保用户有一个有效的RSS token，如果不存在则创建一个"""
    try:
        # 尝试获取用户的profile
        profile = user.profile
        # 如果profile存在但token为空，生成一个新token
        if not profile.rss_token:
            profile.rss_token = uuid.uuid4()
            profile.save()
        return profile.rss_token
    except (UserProfile.DoesNotExist, AttributeError):
        # 如果用户没有profile，创建一个
        profile = UserProfile.objects.create(user=user, rss_token=uuid.uuid4())
        profile.save()
        return profile.rss_token

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
    
    # 确保用户只能访问自己的音频片段
    if request.user != segment.book.user:
        from django.http import Http404
        raise Http404("您没有权限访问此页面")
    
    # 确保音频作者有一个有效的RSS token
    ensure_rss_token(segment.book.user)
    
    context = {
        'segment': segment
    }
    
    return render(request, "home/audio_detail.html", context)


def book_audio_list(request, book_id):
    # 获取书籍对象，确保它存在
    book = get_object_or_404(Books, id=book_id)
    
    # 确保用户只能访问自己的书籍
    if request.user != book.user:
        from django.http import Http404
        raise Http404("您没有权限访问此页面")
    
    # 确保用户有一个有效的RSS token
    ensure_rss_token(request.user)
    
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
        
        # Filter segments for this specific user
        segments = AudioSegment.objects.filter(
            published=True, 
            book__user__id=user_id
        ).order_by('-updated_at')[:50]  # Limit to 50 items
    else:
        # Original behavior for all users
        title = "Book2TTS 公开发布的音频"
        description = "来自 Book2TTS 的最新公开发布音频。"
        
        # Fetch all published audio segments, ordered by most recent first
        segments = AudioSegment.objects.filter(
            published=True
        ).order_by('-updated_at')[:50]  # Limit to 50 items

    link = request.build_absolute_uri(reverse('home'))  # Link to the homepage

    feed = Rss201rev2Feed(
        title=title,
        link=link,
        description=description,
        language="zh-cn",
    )

    for segment in segments:
        item_link = request.build_absolute_uri(reverse('audio_detail', args=[segment.id]))
        # Note: audio_detail view currently requires login. 
        # If the RSS feed is public, the detail view might need adjustment 
        # or the link should perhaps point directly to the audio file if detail view isn't public.
        # For now, linking to detail view assuming it *could* be made public or changed.
        
        # Ensure we have a full URL for the audio file
        audio_url = request.build_absolute_uri(segment.file.url) if segment.file else None

        feed.add_item(
            title=f"{segment.book.name} - {segment.title}",
            link=item_link, 
            description=escape(segment.text or ''),
            pubdate=segment.updated_at,
            unique_id=str(segment.id),
            enclosure={"url": audio_url, "length": str(segment.file.size), "mime_type": "audio/mpeg"} if audio_url else None,
            author_name=segment.book.user.username if segment.book.user else "未知作者"
        )

    # Return the RSS feed as an XML response
    response = HttpResponse(feed.writeString('utf-8'), content_type='application/rss+xml; charset=utf-8')
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

    feed = Rss201rev2Feed(
        title=title,
        link=link,
        description=description,
        language="zh-cn",
    )

    for segment in segments:
        item_link = request.build_absolute_uri(reverse('audio_detail', args=[segment.id]))
        
        # Ensure audio file URL is complete
        audio_url = request.build_absolute_uri(segment.file.url) if segment.file else None

        feed.add_item(
            title=f"{segment.book.name} - {segment.title}",
            link=item_link, 
            description=escape(segment.text or ''),
            pubdate=segment.updated_at,
            unique_id=str(segment.id),
            enclosure={"url": audio_url, "length": str(segment.file.size), "mime_type": "audio/mpeg"} if audio_url else None,
            author_name=user.username
        )

    # Return RSS feed as XML response
    response = HttpResponse(feed.writeString('utf-8'), content_type='application/rss+xml; charset=utf-8')
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
            # 筛选该用户特定书籍的已发布音频片段
            segments = AudioSegment.objects.filter(
                published=True, 
                book__user=user,
                book_id=book_id
            ).order_by('-updated_at')[:50]  # 限制为50条
        else:
            title = f"{user.username}的Book2TTS音频"
            description = f"来自{user.username}在Book2TTS上发布的最新音频。"
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

    feed = Rss201rev2Feed(
        title=title,
        link=link,
        description=description,
        language="zh-cn",
    )

    for segment in segments:
        item_link = request.build_absolute_uri(reverse('audio_detail', args=[segment.id]))
        
        audio_url = request.build_absolute_uri(segment.file.url) if segment.file else None

        feed.add_item(
            title=f"{segment.book.name} - {segment.title}",
            link=item_link, 
            description=escape(segment.text or ''),
            pubdate=segment.updated_at,
            unique_id=str(segment.id),
            enclosure={"url": audio_url, "length": str(segment.file.size), "mime_type": "audio/mpeg"} if audio_url else None,
            author_name=user.username
        )

    response = HttpResponse(feed.writeString('utf-8'), content_type='application/rss+xml; charset=utf-8')
    return response
