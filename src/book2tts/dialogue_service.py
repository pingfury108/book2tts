import json
import re
from typing import Dict, List, Any, Optional
from .llm_service import LLMService

class DialogueService:
    """对话转换服务类，用于将文本内容转换为对话脚本"""
    
    # 默认的对话转换提示词模板
    DEFAULT_DIALOGUE_PROMPT = """请将以下文本解析为 JSON 格式的播客对话记录。JSON 结构应包含以下字段：

*   `title` (字符串): 播客剧集的标题 (如果文本中明显存在)。如果没有，可以设置为 "无标题"。
*   `segments` (数组): 一个包含多个对话片段的数组。每个对话片段应包含以下字段：
    *   `speaker` (字符串):  说话者的名称。如果是旁白，则设置为 "旁白"。如果文本中没有明确的说话者信息，则设置为 "未知"。
    *   `utterance` (字符串): 说话者所说的内容。
    *   `type` (字符串): 对话类型。可选值为 "dialogue" (对话) 或 "narration" (旁白)。根据上下文判断类型。

**解析规则：**

1.  **说话者识别：** 尝试从文本中识别说话者。常见的标识符包括：
    *   名称后跟冒号 (例如 "主持人: 你好")
    *   使用粗体或斜体文本标记说话者 (请注意，您无法直接处理格式，但可以尝试根据上下文推断)
    *   如果同一说话者连续说话，则不必重复 `speaker` 字段，直到出现新的说话者或旁白。

2.  **旁白识别：** 将描述场景、动作或说话者情绪的文本视为旁白。旁白通常不属于任何特定说话者。 例如： `[场景：咖啡馆]`， `(停顿了一下)`， `主持人笑着说：`

3.  **文本分割：** 将文本分割成合理的对话片段。每个片段应包含一个完整的句子或一个逻辑上的短语。

4.  **处理不明确的情况：** 如果无法确定说话者或对话类型，请尽量做出最合理的猜测。如果完全无法确定，则将 `speaker` 设置为 "未知"，并将 `type` 设置为 "dialogue"。

5.  **JSON 格式：** 确保生成的 JSON 格式正确且易于解析。

**示例输入：**

```
主持人: 大家好，欢迎收听本期播客！
嘉宾：大家好！很高兴能来。
[场景：咖啡馆，背景音乐响起]
旁白：他们开始讨论人工智能的未来。
主持人：你觉得人工智能会如何改变我们的生活？
嘉宾：我认为它会带来很多积极的影响，但也需要注意潜在的风险。
```

**示例输出：**

```json
{
  "title": "无标题",
  "segments": [
    {
      "speaker": "主持人",
      "utterance": "大家好，欢迎收听本期播客！",
      "type": "dialogue"
    },
    {
      "speaker": "嘉宾",
      "utterance": "大家好！很高兴能来。",
      "type": "dialogue"
    },
    {
      "speaker": "旁白",
      "utterance": "[场景：咖啡馆，背景音乐响起]",
      "type": "narration"
    },
    {
      "speaker": "旁白",
      "utterance": "他们开始讨论人工智能的未来。",
      "type": "narration"
    },
    {
      "speaker": "主持人",
      "utterance": "你觉得人工智能会如何改变我们的生活？",
      "type": "dialogue"
    },
    {
      "speaker": "嘉宾",
      "utterance": "我认为它会带来很多积极的影响，但也需要注意潜在的风险。",
      "type": "dialogue"
    }
  ]
}
```

**现在，请解析以下文本：**"""

    def __init__(self, llm_service: Optional[LLMService] = None):
        """
        初始化对话服务
        
        Args:
            llm_service: LLM服务实例，如果未提供则创建新实例
        """
        self.llm_service = llm_service or LLMService()
    
    def text_to_dialogue(self, text: str, custom_prompt: Optional[str] = None, temperature: float = 0.3) -> Dict[str, Any]:
        """
        将文本转换为对话脚本
        
        Args:
            text: 输入的文本内容
            custom_prompt: 自定义提示词（可选）
            temperature: LLM温度参数，控制创造性（默认0.3，相对保守）
            
        Returns:
            包含转换结果的字典
        """
        try:
            # 使用自定义提示词或默认提示词
            system_prompt = custom_prompt or self.DEFAULT_DIALOGUE_PROMPT
            
            # 调用LLM服务进行文本处理
            result = self.llm_service.process_text(
                system_prompt=system_prompt,
                user_content=text,
                temperature=temperature
            )
            raw_response = result.get("result")
            
            if not result.get("success"):
                return {
                    "success": False,
                    "error": f"LLM处理失败: {result.get('error', '未知错误')}",
                    "raw_response": raw_response
                }
            
            # 解析LLM返回的JSON格式结果
            llm_response = raw_response
            dialogue_data = self._parse_llm_response(llm_response)
            
            if dialogue_data is None:
                return {
                    "success": False,
                    "error": "无法解析LLM返回的JSON格式数据",
                    "raw_response": llm_response
                }
            
            return {
                "success": True,
                "dialogue_data": dialogue_data,
                "raw_response": llm_response,
                "usage": result.get("usage"),
                "model": result.get("model"),
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"对话转换过程中发生错误: {str(e)}",
                "raw_response": result.get("result") if 'result' in locals() and isinstance(result, dict) else None
            }
    
    def _parse_llm_response(self, response: str) -> Optional[Dict[str, Any]]:
        """
        解析LLM返回的响应，提取JSON格式的对话数据
        
        Args:
            response: LLM的原始响应
            
        Returns:
            解析后的对话数据，如果解析失败则返回None
        """
        try:
            # 尝试直接解析JSON
            return json.loads(response)
        except json.JSONDecodeError:
            # 如果直接解析失败，尝试提取JSON部分
            try:
                # 使用正则表达式查找JSON代码块
                json_pattern = r'```json\s*(\{.*?\})\s*```'
                match = re.search(json_pattern, response, re.DOTALL)
                if match:
                    return json.loads(match.group(1))
                
                # 尝试查找普通的JSON结构
                json_pattern = r'(\{.*"segments".*?\})'
                match = re.search(json_pattern, response, re.DOTALL)
                if match:
                    return json.loads(match.group(1))
                
                # 最后尝试查找任何JSON对象
                json_pattern = r'(\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\})'
                matches = re.findall(json_pattern, response, re.DOTALL)
                for match in matches:
                    try:
                        data = json.loads(match)
                        if "segments" in data:
                            return data
                    except json.JSONDecodeError:
                        continue
                        
            except Exception:
                pass
        
        return None
    
    def validate_dialogue_data(self, dialogue_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        验证对话数据的格式和完整性
        
        Args:
            dialogue_data: 对话数据字典
            
        Returns:
            验证结果字典
        """
        errors = []
        warnings = []
        
        # 检查必要字段
        if "title" not in dialogue_data:
            errors.append("缺少 'title' 字段")
        
        if "segments" not in dialogue_data:
            errors.append("缺少 'segments' 字段")
        else:
            segments = dialogue_data["segments"]
            if not isinstance(segments, list):
                errors.append("'segments' 字段必须是数组")
            else:
                for i, segment in enumerate(segments):
                    if not isinstance(segment, dict):
                        errors.append(f"段落 {i+1} 不是有效的对象")
                        continue
                    
                    # 检查段落必要字段
                    required_fields = ["speaker", "utterance", "type"]
                    for field in required_fields:
                        if field not in segment:
                            errors.append(f"段落 {i+1} 缺少 '{field}' 字段")
                    
                    # 检查type字段的有效值
                    if "type" in segment and segment["type"] not in ["dialogue", "narration"]:
                        warnings.append(f"段落 {i+1} 的 'type' 字段值 '{segment['type']}' 不在推荐范围内")
        
        return {
            "is_valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings
        }
    
    def get_speakers_from_dialogue(self, dialogue_data: Dict[str, Any]) -> List[str]:
        """
        从对话数据中提取所有说话者
        
        Args:
            dialogue_data: 对话数据字典
            
        Returns:
            说话者列表
        """
        speakers = set()
        if "segments" in dialogue_data:
            for segment in dialogue_data["segments"]:
                if "speaker" in segment:
                    speakers.add(segment["speaker"])
        return sorted(list(speakers))
    
    def split_long_text(self, text: str, max_length: int = 3000) -> List[str]:
        """
        将长文本分割为适合LLM处理的段落
        
        Args:
            text: 输入文本
            max_length: 每段最大长度
            
        Returns:
            分割后的文本段落列表
        """
        if len(text) <= max_length:
            return [text]
        
        chunks = []
        current_chunk = ""
        
        # 按段落分割
        paragraphs = text.split('\n\n')
        
        for paragraph in paragraphs:
            if len(current_chunk) + len(paragraph) + 2 <= max_length:
                if current_chunk:
                    current_chunk += '\n\n'
                current_chunk += paragraph
            else:
                if current_chunk:
                    chunks.append(current_chunk)
                    current_chunk = paragraph
                else:
                    # 单个段落太长，强制分割
                    chunks.append(paragraph[:max_length])
                    current_chunk = paragraph[max_length:]
        
        if current_chunk:
            chunks.append(current_chunk)
        
        return chunks 
