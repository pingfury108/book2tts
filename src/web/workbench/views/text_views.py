import logging
import time

from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.http import StreamingHttpResponse, HttpResponse

from home.models import OperationRecord
from web.workbench.utils.points_utils import deduct_llm_points


def _get_client_meta(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip_address = x_forwarded_for.split(',')[0].strip()
    else:
        ip_address = request.META.get('REMOTE_ADDR')
    user_agent = request.META.get('HTTP_USER_AGENT')
    return ip_address, user_agent


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
        ip_address, user_agent = _get_client_meta(request)
        response = StreamingHttpResponse(
            streaming_content=format_text_stream(request.user, texts, ip_address, user_agent),
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


def format_text_stream(user, texts, ip_address=None, user_agent=None):
    """Stream formatted text using SSE with proper event handling"""
    try:
        # Initialize LLM service
        from book2tts.ui import LLMService
        llm_service = LLMService()
        
        # System prompt for text formatting
        system_prompt = """
# Role: 我是一个专门用于排版文本内容的 AI 角色

## Goal: 将输入的文本内容，重新排版后输出，只输出排版后的文本内容

## Constrains:
- 严格保持原有语言，不进行任何语言转换（如中文保持中文，英文保持英文）
- 输出纯文本
- 去除页码(数字）之后行的文字
- 去页首，页尾不相关的文字
- 去除引文标注（如[1]、[2]、(1)、(2)等数字标注）
- 去除文本末尾的注释说明（如[1] 弗朗西斯·鲍蒙特...这类详细的注释说明）
- 缺失的标点符号补全
- 不去理解输，阐述输入内容，让输入内容，除过排版问题，都保持原样

## outputs
- 只输出排版后的文本，不要输出任何解释说明
- 纯文本格式，不适用 markdown 格式
"""
        
        total_chars = len(texts)
        chunk_size = 1000
        chunk_count = 0
        total_prompt_tokens = 0
        total_completion_tokens = 0
        total_tokens = 0
        success = False
        error_message = None
        models_used = set()

        # Send start event
        yield "event: start\ndata: Starting text formatting...\n\n"

        for i in range(0, total_chars, chunk_size):
            chunk = texts[i:i + chunk_size]
            chunk_count += 1
            result = llm_service.process_text(
                system_prompt=system_prompt,
                user_content=chunk,
                temperature=0.7
            )

            # 直接提取result字段的文本内容
            if isinstance(result, dict) and result.get('success') and result.get('result'):
                formatted_text = result['result']
                usage = result.get('usage') or {}
                prompt_tokens = usage.get('prompt_tokens') or 0
                completion_tokens = usage.get('completion_tokens') or 0
                total_prompt_tokens += prompt_tokens
                total_completion_tokens += completion_tokens
                total_tokens += usage.get('total_tokens') or (prompt_tokens + completion_tokens)
                model_name = result.get('model')
                if model_name:
                    models_used.add(model_name)
                # 修复SSE消息格式，处理多行文本
                # 在SSE协议中，data字段中的每个换行符前都需要加上"data: "前缀
                # 将文本中的换行符替换为换行+data前缀
                sse_formatted_text = formatted_text.replace('\n', '\ndata: ')
                # Send formatted text directly via SSE
                yield f"event: message\ndata: {sse_formatted_text}\n\n"
            else:
                # 处理错误情况
                error_message = result.get('error') if isinstance(result, dict) else '处理文本失败'
                if isinstance(result, dict) and result.get('error'):
                    error_message = result['error']
                yield f"event: error\ndata: {error_message}\n\n"
                break

            # Add a small delay to prevent overwhelming the client
            time.sleep(0.1)
        else:
            success = True

        if success:
            yield "event: complete\ndata: [DONE]\n\n"

    except Exception as e:
        # Send error event with proper event type
        error_message = str(e)
        logger.error("Error in format_text_stream: %s", error_message)
        yield f"event: error\ndata: [ERROR] {error_message}\n\n"

    finally:
        try:
            metadata = {
                'total_chars': len(texts),
                'chunk_size': 1000,
                'chunks_processed': chunk_count,
                'prompt_tokens': total_prompt_tokens,
                'completion_tokens': total_completion_tokens,
                'total_tokens': total_tokens,
                'llm_models': sorted(models_used),
            }
            detail = '自动排版完成' if success else f"自动排版失败：{error_message or '未知错误'}"
            OperationRecord.objects.create(
                user=user,
                operation_type='system_operation',
                operation_object='自动排版',
                operation_detail=detail,
                status='success' if success else 'failed',
                metadata=metadata,
                ip_address=ip_address,
                user_agent=user_agent,
            )
            deduction_metadata = {
                'prompt_tokens': total_prompt_tokens,
                'completion_tokens': total_completion_tokens,
                'total_tokens': total_tokens,
                'llm_models': sorted(models_used),
            }
            deduct_llm_points(
                user=user,
                total_tokens=total_tokens,
                operation_object='自动排版 LLM',
                metadata=deduction_metadata,
                ip_address=ip_address,
                user_agent=user_agent,
            )
        except Exception:
            pass


@login_required
@require_http_methods(["GET", "POST"])
def translate(request):
    """Handle text translation with SSE streaming response"""
    # Handle POST request with text content and target language
    if request.method == 'POST':
        texts = request.POST.get("texts", "")
        target_language = request.POST.get("target_language", "")
        if not texts:
            return HttpResponse("No text content provided", status=400)
        if not target_language:
            return HttpResponse("No target language provided", status=400)

        # Create a response with SSE headers
        ip_address, user_agent = _get_client_meta(request)
        response = StreamingHttpResponse(
            streaming_content=translate_text_stream(request.user, texts, target_language, ip_address, user_agent),
            content_type='text/event-stream'
        )
        response['Cache-Control'] = 'no-cache'
        response['X-Accel-Buffering'] = 'no'  # Disable nginx buffering
        return response

    # Handle GET request for SSE connection
    def empty_stream():
        yield "event: connected\ndata: [CONNECTED]\n\n"

    response = StreamingHttpResponse(
        streaming_content=empty_stream(),
        content_type='text/event-stream'
    )
    response['Cache-Control'] = 'no-cache'
    response['X-Accel-Buffering'] = 'no'  # Disable nginx buffering
    return response


def translate_text_stream(user, texts, target_language, ip_address=None, user_agent=None):
    """Stream translated text using SSE with proper event handling and caching"""
    try:
        # Initialize LLM service
        from book2tts.ui import LLMService
        from ..models import TranslationCache

        llm_service = LLMService()

        # Map language codes to display names for system prompt
        language_map = {
            'en': '英文',
            'zh': '中文',
            'ja': '日文',
            'ko': '韩文',
            'fr': '法文',
            'de': '德文',
            'es': '西班牙文',
            'ru': '俄文',
            'it': '意大利文',
            'pt': '葡萄牙文'
        }

        target_lang_name = language_map.get(target_language, target_language)

        # System prompt for text translation
        system_prompt = f"""
# Role: 我是一个专门用于翻译文本内容的 AI 角色

## Goal: 将输入的文本内容翻译为{target_lang_name}，只输出翻译后的文本内容

## Constrains:
- 准确翻译输入文本到{target_lang_name}
- 保持原文的格式和结构
- 保持原文的语气和风格
- 输出纯文本
- 不要添加任何解释说明
- 不要理解或阐述输入内容，只进行翻译
- 保持段落结构不变

## outputs
- 只输出翻译后的文本，不要输出任何解释说明
- 纯文本格式，不使用 markdown 格式
"""

        total_chars = len(texts)
        chunk_size = 1000
        estimated_total_chunks = max(1, (total_chars + chunk_size - 1) // chunk_size)

        def iter_line_chunks(text, max_chunk_size):
            if not text:
                return

            buffer = []
            current_len = 0

            for line in text.splitlines(keepends=True):
                line_len = len(line)

                # 针对超长单行，直接按阈值切分
                if line_len >= max_chunk_size:
                    if buffer:
                        yield ''.join(buffer)
                        buffer = []
                        current_len = 0

                    start = 0
                    while start < line_len:
                        end = start + max_chunk_size
                        yield line[start:end]
                        start = end
                    continue

                # 缓冲区即将超出阈值，则先输出
                if buffer and current_len + line_len > max_chunk_size:
                    yield ''.join(buffer)
                    buffer = []
                    current_len = 0

                buffer.append(line)
                current_len += line_len

            if buffer:
                yield ''.join(buffer)

        chunk_iterator = iter_line_chunks(texts, chunk_size)
        cached_chunks = 0
        new_chunks = 0
        chunk_index = 0
        total_prompt_tokens = 0
        total_completion_tokens = 0
        total_tokens = 0
        error_occurred = False
        error_message = None
        models_used = set()

        # Send start event
        yield "event: start\ndata: Starting text translation...\n\n"

        for chunk in chunk_iterator:
            if not chunk:
                continue

            chunk_index += 1

            # Check cache first
            cache_result, needs_translation = TranslationCache.get_or_create_cache(chunk, target_language)

            if not needs_translation and cache_result:
                cached_chunks += 1
                translated_text = cache_result.translated_text
                progress_msg = f"[缓存命中 {chunk_index}/{estimated_total_chunks}] 使用缓存翻译..."
                yield f"event: progress\ndata: {progress_msg}\n\n"
                sse_formatted_text = translated_text.replace('\n', '\ndata: ')
                yield f"event: message\ndata: {sse_formatted_text}\n\n"
            else:
                new_chunks += 1
                progress_msg = f"[翻译中 {chunk_index}/{estimated_total_chunks}] 正在生成翻译..."
                yield f"event: progress\ndata: {progress_msg}\n\n"

                result = llm_service.process_text(
                    system_prompt=system_prompt,
                    user_content=chunk,
                    temperature=0.3
                )

                if isinstance(result, dict) and result.get('success') and result.get('result'):
                    translated_text = result['result']
                    usage = result.get('usage') or {}
                    prompt_tokens = usage.get('prompt_tokens') or 0
                    completion_tokens = usage.get('completion_tokens') or 0
                    total_prompt_tokens += prompt_tokens
                    total_completion_tokens += completion_tokens
                    total_tokens += usage.get('total_tokens') or (prompt_tokens + completion_tokens)
                    model_name = result.get('model')
                    if model_name:
                        models_used.add(model_name)

                    try:
                        TranslationCache.create_cache(chunk, target_language, translated_text)
                    except Exception as cache_error:
                        print(f"Error saving translation cache: {cache_error}")

                    sse_formatted_text = translated_text.replace('\n', '\ndata: ')
                    yield f"event: message\ndata: {sse_formatted_text}\n\n"
                else:
                    error_message = result.get('error') if isinstance(result, dict) else '翻译文本失败'
                    yield f"event: error\ndata: {error_message}\n\n"
                    error_occurred = True
                    break

        if not error_occurred:
            stats_msg = (
                f"翻译完成！共处理 {chunk_index} 个片段，其中 {cached_chunks} 个来自缓存，"
                f"{new_chunks} 个新生成。"
            )
            yield f"event: complete\ndata: {stats_msg}\n\n"

    except Exception as e:
        # Send error event with proper event type
        error_message = str(e)
        error_occurred = True
        logger.error("Error in translate_text_stream: %s", error_message)
        yield f"event: error\ndata: [ERROR] {error_message}\n\n"
    finally:
        try:
            success = not error_occurred and error_message is None
            metadata = {
                'total_chars': len(texts),
                'chunk_size': 1000,
                'total_chunks': chunk_index,
                'cached_chunks': cached_chunks,
                'new_chunks': new_chunks,
                'prompt_tokens': total_prompt_tokens,
                'completion_tokens': total_completion_tokens,
                'total_tokens': total_tokens,
                'target_language': target_language,
                'llm_models': sorted(models_used),
            }
            detail = '文本翻译完成' if success else f"文本翻译失败：{error_message or '未知错误'}"
            OperationRecord.objects.create(
                user=user,
                operation_type='system_operation',
                operation_object=f'文本翻译 -> {target_lang_name}',
                operation_detail=detail,
                status='success' if success else 'failed',
                metadata=metadata,
                ip_address=ip_address,
                user_agent=user_agent,
            )
            deduction_metadata = {
                'prompt_tokens': total_prompt_tokens,
                'completion_tokens': total_completion_tokens,
                'target_language': target_language,
                'total_tokens': total_tokens,
                'llm_models': sorted(models_used),
            }
            deduct_llm_points(
                user=user,
                total_tokens=total_tokens,
                operation_object=f'文本翻译 LLM -> {target_lang_name}',
                metadata=deduction_metadata,
                ip_address=ip_address,
                user_agent=user_agent,
            )
        except Exception:
            pass
logger = logging.getLogger(__name__)
