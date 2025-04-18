from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse
from workbench.models import AudioSegment, Books, UserProfile
from django.urls import reverse
from django.utils.html import escape
import datetime
import uuid
import os
import re
import html
from feedgen.feed import FeedGenerator

# 辅助函数：估计音频时长
def estimate_audio_duration(audio_file):
    """使用ffmpeg获取音频文件时长"""
    if not audio_file:
        return 300, "0:05:00"  # 默认5分钟
    
    try:
        import ffmpeg
        # 使用ffmpeg探测文件获取音频信息
        probe = ffmpeg.probe(audio_file.path)
        
        # 查找音频流并获取时长
        audio_stream = next(
            (stream for stream in probe["streams"] if stream["codec_type"] == "audio"),
            None,
        )
        
        if audio_stream is not None:
            duration_seconds = int(float(audio_stream["duration"]))
            
            # 格式化为时:分:秒
            hours = duration_seconds // 3600
            minutes = (duration_seconds % 3600) // 60
            seconds = duration_seconds % 60
            
            if hours > 0:
                formatted_duration = f"{hours}:{minutes:02d}:{seconds:02d}"
            else:
                formatted_duration = f"{minutes}:{seconds:02d}"
            
            return duration_seconds, formatted_duration
    except (ImportError, Exception) as e:
        # 如果ffmpeg不可用或出错，回退到基于文件大小的估算
        print(f"使用文件大小估算音频时长: {str(e)}")
        
    # 回退方法: 使用文件大小估算时长
    # 假设平均比特率为128kbps
    bit_rate = 128 * 1024  # 比特/秒
    file_size = audio_file.size  # 字节
    
    # 估算时长（秒）
    duration_seconds = int((file_size * 8) / bit_rate)
    
    # 格式化为时:分:秒
    hours = duration_seconds // 3600
    minutes = (duration_seconds % 3600) // 60
    seconds = duration_seconds % 60
    
    if hours > 0:
        formatted_duration = f"{hours}:{minutes:02d}:{seconds:02d}"
    else:
        formatted_duration = f"{minutes}:{seconds:02d}"
    
    return duration_seconds, formatted_duration

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

# 添加一个XML清理函数
def clean_xml_output(xml_string):
    """
    清理XML输出，修复常见的XML错误
    """
    # 不再生成调试文件
    # debug_xml_file(xml_string, "debug_original_before_clean.xml")
    
    # 确保XML声明正确
    if xml_string.startswith('<?xml'):
        # 提取现有的XML声明
        xml_decl_end = xml_string.find('?>')
        if xml_decl_end > 0:
            # 移除现有的XML声明，稍后添加一个格式良好的声明
            xml_string = xml_string[xml_decl_end + 2:].strip()
    
    # 检测并修复无效的XML字符
    xml_string = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', xml_string)
    
    # 修复常见的XML属性构造错误
    xml_string = re.sub(r'&(?!amp;|lt;|gt;|quot;|apos;)', '&amp;', xml_string)
    
    # 修复URL中的特殊字符
    def fix_url_attribute(match):
        full_attr = match.group(0)
        attr_name = match.group(1)
        attr_value = match.group(2)
        
        # 只处理URL属性
        if attr_name.lower() in ['href', 'url', 'src']:
            # 对URL进行HTML转义，但保留基本URL编码字符
            safe_chars = "/?:@&=+$,;"
            for char in safe_chars:
                attr_value = attr_value.replace(char, f"_SAFE_{ord(char)}_")
            
            attr_value = html.escape(attr_value, quote=True)
            
            # 恢复安全字符
            for char in safe_chars:
                attr_value = attr_value.replace(f"_SAFE_{ord(char)}_", char)
            
            return f'{attr_name}="{attr_value}"'
        return full_attr
    
    # 修复所有属性中的特殊字符
    xml_string = re.sub(r'(\w+)="([^"]*)"', fix_url_attribute, xml_string)
    
    # 确保所有属性都有引号
    xml_string = re.sub(r'(\w+)=([^\s"][^\s>]*)', r'\1="\2"', xml_string)
    
    # 修复XML标签内不允许的字符
    xml_string = re.sub(r'<([^>]*)>', lambda m: '<' + re.sub(r'[^\w\s:=".\-/]', '', m.group(1)) + '>', xml_string)
    
    # 确保RSS根标签正确
    if '<rss ' in xml_string and ' version=' not in xml_string[:xml_string.find('>')]:
        xml_string = xml_string.replace('<rss ', '<rss version="2.0" ', 1)
    
    # 确保所有标签都正确关闭
    try:
        from lxml import etree
        parser = etree.XMLParser(recover=True, remove_blank_text=True)
        try:
            root = etree.fromstring(xml_string.encode('utf-8'), parser)
            # 使用lxml重新序列化，这会自动修复一些XML问题
            xml_string = etree.tostring(root, encoding='utf-8', xml_declaration=True).decode('utf-8')
        except Exception as e:
            # 如果lxml无法解析，回退到手动修复
            print(f"lxml parser failed, falling back to manual fixes: {e}")
            pass
    except ImportError:
        print("lxml not available, using manual XML fixes")
        pass
    
    # 进行手动修复，如果lxml不可用或失败
    if '</rss>' not in xml_string:
        # 确保有关闭的RSS标签
        xml_string += '\n</rss>'
    
    # 确保channel标签存在并正确关闭
    if '<channel>' in xml_string and '</channel>' not in xml_string:
        xml_string = xml_string.replace('</rss>', '</channel>\n</rss>')
    
    # 确保item标签正确关闭
    open_items = xml_string.count('<item>')
    close_items = xml_string.count('</item>')
    if open_items > close_items:
        # 添加缺失的关闭item标签
        for _ in range(open_items - close_items):
            # 找到最后一个item的位置
            last_item_pos = xml_string.rfind('<item>')
            channel_close_pos = xml_string.rfind('</channel>')
            
            if last_item_pos > 0 and channel_close_pos > last_item_pos:
                # 在channel关闭前添加item关闭标签
                xml_string = xml_string[:channel_close_pos] + '</item>\n' + xml_string[channel_close_pos:]
            elif '</rss>' in xml_string:
                # 如果找不到channel关闭标签，在rss关闭前添加
                xml_string = xml_string.replace('</rss>', '</item>\n</channel>\n</rss>')
    
    # 不再生成调试文件
    # debug_xml_file(xml_string, "debug_final_after_clean.xml")
    
    return xml_string

# 使用feedgen库生成podcast feed
def create_podcast_feed(title, link, description, language, author_name, image_url, author_email="example@example.com"):
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

def add_podcast_entry(feed, title, audio_url, audio_size, link, description, pubdate, 
                     author, duration_formatted, duration_seconds, image_url=None, 
                     episode_number=None, season_number=None, unique_id=None):
    """
    向podcast feed添加一个条目
    """
    fe = feed.add_entry()
    fe.id(unique_id if unique_id else link)
    fe.title(title)
    fe.description(description)
    fe.link(href=link)
    fe.published(pubdate)
    
    # 添加音频附件
    if audio_url:
        fe.enclosure(audio_url, str(audio_size), 'audio/mpeg')
    
    # 添加iTunes特定元数据
    fe.podcast.itunes_author(author)
    fe.podcast.itunes_summary(description)
    fe.podcast.itunes_duration(duration_formatted)
    if image_url:
        fe.podcast.itunes_image(image_url)
    fe.podcast.itunes_explicit('no')  # 修改为 'no'，这是feedgen库支持的值
    
    # 在生成XML时，我们会处理Podcast Index命名空间元素
    # 这里存储这些值，以便稍后手动添加
    fe.podcast._custom_tags = {}
    
    if episode_number:
        fe.podcast._custom_tags['episode'] = str(episode_number)
    if season_number:
        fe.podcast._custom_tags['season'] = str(season_number)
    fe.podcast._custom_tags['duration'] = str(duration_seconds)
    
    return fe

# 添加钩子来修改生成的RSS以添加自定义标签
def postprocess_rss(xml_string):
    """在生成的RSS XML中添加缺失的Podcast Index命名空间标签"""
    
    # 使用完整的命名空间声明替换RSS标签
    rss_pattern = r'<rss[^>]*>'
    namespaces = ' xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd"'
    namespaces += ' xmlns:podcast="https://github.com/Podcasting-org/podcast-namespace/blob/main/docs/1.0.md"'
    namespaces += ' xmlns:atom="http://www.w3.org/2005/Atom"'
    namespaces += ' xmlns:content="http://purl.org/rss/1.0/modules/content/"'
    namespaces += ' version="2.0"'
    
    if re.search(rss_pattern, xml_string):
        xml_string = re.sub(rss_pattern, f'<rss{namespaces}>', xml_string)
    else:
        # 如果没有找到RSS标签，添加一个
        xml_string = f'<rss{namespaces}>\n<channel>\n' + xml_string
        if '</channel>' not in xml_string:
            xml_string += '\n</channel>'
        if '</rss>' not in xml_string:
            xml_string += '\n</rss>'
    
    # 添加podcast:locked标签
    if '<podcast:locked>' not in xml_string:
        idx = xml_string.find('</channel>')
        if idx > 0:
            xml_string = xml_string[:idx] + '  <podcast:locked>false</podcast:locked>\n  <podcast:medium>audiobook</podcast:medium>\n' + xml_string[idx:]
    
    # 处理条目级别的标签
    # 这种方法不够精确，但在无法直接添加标签的情况下可以使用
    for tag_name in ['episode', 'season', 'duration']:
        tag_pattern = f'<podcast:{tag_name}>'
        if tag_pattern not in xml_string:
            item_ends = [m.start() for m in re.finditer('</item>', xml_string)]
            for pos in item_ends:
                # 找出该项目的唯一ID
                item_start = xml_string.rfind('<item>', 0, pos)
                item_content = xml_string[item_start:pos]
                
                # 根据自定义标签添加Podcast Index标签
                # 这里的实现非常简化，实际应用中需要更精确的处理
                if f'<{tag_name}>' in item_content:
                    tag_value = re.search(f'<{tag_name}>(.*?)</{tag_name}>', item_content)
                    if tag_value:
                        insert_point = pos
                        xml_string = xml_string[:insert_point] + f'  <podcast:{tag_name}>{tag_value.group(1)}</podcast:{tag_name}>\n' + xml_string[insert_point:]
    
    return xml_string

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
        image_url=image_url
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
        image_url=image_url
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
        image_url=image_url
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
        image_url=image_url
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
