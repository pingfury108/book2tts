from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse
from workbench.models import AudioSegment, Books

# Create your views here.


def index(request):
    context = {}
    
    # 如果用户已登录，获取已发布的音频片段
    if request.user.is_authenticated:
        published_audio_segments = AudioSegment.objects.filter(
            user=request.user,
            published=True
        ).order_by('-id')  # 按ID降序排列（最新的在前）
        
        context['audio_segments'] = published_audio_segments
    
    return render(request, "home/index.html", context)


def audio_detail(request, segment_id):
    # 获取音频片段对象，确保它存在且已发布
    segment = get_object_or_404(AudioSegment, id=segment_id, published=True)
    
    # 确保用户只能访问自己的音频片段
    if request.user != segment.user:
        from django.http import Http404
        raise Http404("您没有权限访问此页面")
    
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
    
    # 获取该书籍下已发布的音频片段
    book_audio_segments = AudioSegment.objects.filter(
        book=book,
        user=request.user,
        published=True
    ).order_by('-id')  # 按ID降序排列（最新的在前）
    
    context = {
        'book': book,
        'audio_segments': book_audio_segments,
        'display_title': f'《{book.name}》的音频列表'
    }
    
    return render(request, "home/index.html", context)
