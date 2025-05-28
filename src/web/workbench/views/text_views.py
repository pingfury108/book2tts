import time

from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.http import StreamingHttpResponse, HttpResponse


@login_required
@require_http_methods(["GET", "POST"])
def reformat(request):
    """Handle text reformatting with SSE streaming response"""
    # Handle POST request with text content
    if request.method == 'POST':
        texts = request.POST.get("texts", "")
        if not texts:
            return HttpResponse("No text content provided", status=400)
        
        # Create a response with SSE headers
        response = StreamingHttpResponse(
            streaming_content=format_text_stream(texts),
            content_type='text/event-stream'
        )
        response['Cache-Control'] = 'no-cache'
        response['X-Accel-Buffering'] = 'no'  # Disable nginx buffering
        return response
    
    # Handle GET request for SSE connection - this should never be called anymore
    # but we keep it for compatibility
    def empty_stream():
        yield "event: connected\ndata: [CONNECTED]\n\n"
    
    response = StreamingHttpResponse(
        streaming_content=empty_stream(),
        content_type='text/event-stream'
    )
    response['Cache-Control'] = 'no-cache'
    response['X-Accel-Buffering'] = 'no'  # Disable nginx buffering
    return response


def format_text_stream(texts):
    """Stream formatted text using SSE with proper event handling"""
    try:
        # Initialize LLM service
        from book2tts.ui import LLMService
        llm_service = LLMService()
        
        # System prompt for text formatting
        system_prompt = """
# Role: 我是一个专门用于排版文本内容的 AI 角色

## Constrains: 
- 保持原有语言
- 输出纯文本
- 去除页码(数字）之后行的文字
- 去页首，页尾这些文字，e.g: THE BIBLE STORY, BACK TO THE BEGINNING, PART ONE , STORY 2，BIRTHDAY OF A WORLD, THE BIBLE STORY
- 使用小写字母
- 缺失的标点符号补全
"""
        
        # Send start event
        yield "event: start\ndata: Starting text formatting...\n\n"
        
        # Process text in chunks
        chunk_size = 1000  # Process 1000 characters at a time
        for i in range(0, len(texts), chunk_size):
            chunk = texts[i:i + chunk_size]
            result = llm_service.process_text(
                system_prompt=system_prompt,
                user_content=chunk,
                temperature=0.7
            )
            
            # 直接提取result字段的文本内容
            if isinstance(result, dict) and result.get('success') and result.get('result'):
                formatted_text = result['result']
                # 修复SSE消息格式，处理多行文本
                # 在SSE协议中，data字段中的每个换行符前都需要加上"data: "前缀
                # 将文本中的换行符替换为换行+data前缀
                sse_formatted_text = formatted_text.replace('\n', '\ndata: ')
                # Send formatted text directly via SSE
                yield f"event: message\ndata: {sse_formatted_text}\n\n"
            else:
                # 处理错误情况
                error_message = "处理文本失败"
                if isinstance(result, dict) and result.get('error'):
                    error_message = result['error']
                yield f"event: error\ndata: {error_message}\n\n"
                break
            
            # Add a small delay to prevent overwhelming the client
            time.sleep(0.1)
            
        # Send completion event
        yield "event: complete\ndata: [DONE]\n\n"
        
    except Exception as e:
        # Send error event with proper event type
        error_msg = str(e)
        print(f"Error in format_text_stream: {error_msg}")  # Log the error
        yield f"event: error\ndata: [ERROR] {error_msg}\n\n" 