"""
Utility functions for generating and managing RSS feeds.
"""
import re
import html
import uuid
from typing import List

from bs4 import BeautifulSoup
from feedgen.feed import FeedGenerator
from workbench.models import UserProfile


def estimate_audio_duration(audio_file):
    """使用ffmpeg获取音频文件时长"""
    if not audio_file:
        return 300, "0:05:00"  # 默认5分钟
    
    # 格式化时长为时:分:秒字符串
    def format_duration(seconds):
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60
        
        if hours > 0:
            return f"{hours}:{minutes:02d}:{secs:02d}"
        else:
            return f"{minutes}:{secs:02d}"
    
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
            return duration_seconds, format_duration(duration_seconds)
    except (ImportError, Exception) as e:
        # 如果ffmpeg不可用或出错，回退到基于文件大小的估算
        print(f"使用文件大小估算音频时长: {str(e)}")
        
    # 回退方法: 使用文件大小估算时长
    # 假设平均比特率为128kbps
    bit_rate = 128 * 1024  # 比特/秒
    file_size = audio_file.size  # 字节
    
    # 估算时长（秒）
    duration_seconds = int((file_size * 8) / bit_rate)
    return duration_seconds, format_duration(duration_seconds)


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


def clean_xml_output(xml_string):
    """
    清理XML输出，修复常见的XML错误
    """
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
    xml_string = re.sub(r'<([^>]*)>', lambda m: '<' + re.sub(r'[^\w\s:=".\-/+]', '', m.group(1)) + '>', xml_string)
    
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
    
    return xml_string


def create_podcast_feed(title, link, description, language, author_name, image_url, author_email=""):
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
                     episode_number=None, season_number=None, unique_id=None,
                     subtitle_url=None, chapters_url=None, chapters_html=None):
    """
    向podcast feed添加一个条目（支持字幕）
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
    
    # 注释掉字幕附件，RSS feed不需要包含字幕
    # if subtitle_url:
    #     # 为字幕创建单独的enclosure
    #     fe.enclosure(subtitle_url, 0, 'application/x-subrip')
    
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

    if chapters_url:
        if not hasattr(feed, '_chapters_map'):
            feed._chapters_map = {}
        key = unique_id if unique_id else link
        feed._chapters_map[key] = chapters_url

    if chapters_html:
        if not hasattr(feed, '_chapters_html_map'):
            feed._chapters_html_map = {}
        key = unique_id if unique_id else link
        feed._chapters_html_map[key] = chapters_html

    content_fragments: List[str] = []
    if description:
        if chapters_html:
            chapter_text = BeautifulSoup(chapters_html, "html.parser").get_text('\n', strip=True)
            if chapter_text:
                content_fragments.append(f"章节:\n{chapter_text}")
        description_text = html.unescape(description).strip()
        if description_text:
            content_fragments.append(description_text)

    if content_fragments:
        combined_text = '\n\n'.join(content_fragments)
        fe.content(combined_text)

    return fe


def postprocess_rss(xml_string, chapters_map=None):
    """在生成的RSS XML中添加缺失的Podcast Index命名空间标签"""
    chapters_map = chapters_map or {}
    
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

    if chapters_map:
        def _replace_item(match):
            item_xml = match.group(0)
            if '<podcast:chapters' in item_xml:
                return item_xml
            guid_match = re.search(r'<guid[^>]*>(.*?)</guid>', item_xml)
            link_match = re.search(r'<link>(.*?)</link>', item_xml)
            key_candidates = []
            if guid_match:
                key_candidates.append(guid_match.group(1).strip())
            if link_match:
                key_candidates.append(link_match.group(1).strip())

            chapters_url = None
            for candidate in key_candidates:
                if candidate in chapters_map:
                    chapters_url = chapters_map[candidate]
                    break

            if not chapters_url:
                return item_xml

            insertion = f'  <podcast:chapters url="{chapters_url}" type="application/json+chapters" />\n'
            if '</item>' in item_xml:
                return item_xml.replace('</item>', insertion + '</item>')
            return item_xml + insertion

        xml_string = re.sub(r'<item>.*?</item>', _replace_item, xml_string, flags=re.DOTALL)

    return xml_string 
