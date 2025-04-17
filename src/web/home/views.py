from django.shortcuts import render
from django.http import HttpResponse
from workbench.models import AudioSegment

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
