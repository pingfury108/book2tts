"""
AI音色推荐服务
基于角色特征分析自动推荐合适的TTS音色
"""
import json
import logging
from typing import Dict, List, Optional
from django.conf import settings

logger = logging.getLogger(__name__)

# 配置日志
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        '[%(asctime)s] %(levelname)s %(name)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
logger.setLevel(logging.INFO)

class VoiceRecommendationService:
    """AI音色推荐服务"""

    def __init__(self):
        self.available_voices = self._get_available_voices()

    def _get_available_voices(self) -> List[Dict]:
        """获取可用音色列表"""
        try:
            from book2tts.tts import edge_tts_volices
            voices = edge_tts_volices() or []
            return [
                {
                    'value': voice,
                    'name': voice,
                    'features': self._analyze_voice_features(voice)
                }
                for voice in voices
            ]
        except Exception as e:
            logger.error(f"获取音色列表失败: {e}")
            return []

    def _analyze_voice_features(self, voice_name: str) -> Dict:
        """分析音色特征"""
        features = {
            'gender': 'unknown',
            'language': 'unknown',
            'accent': 'unknown',
            'age_group': 'adult',
            'personality': 'unknown'
        }

        voice_lower = voice_name.lower()

        # 性别识别
        if any(gender in voice_lower for gender in ['female', 'woman', 'lady']):
            features['gender'] = 'female'
        elif any(gender in voice_lower for gender in ['male', 'man', 'gentleman']):
            features['gender'] = 'male'

        # 语言识别
        if 'zh-' in voice_lower or 'chinese' in voice_lower:
            features['language'] = 'chinese'
        elif 'en-' in voice_lower or 'english' in voice_lower:
            features['language'] = 'english'
        elif 'ja-' in voice_lower or 'japanese' in voice_lower:
            features['language'] = 'japanese'
        elif 'ko-' in voice_lower or 'korean' in voice_lower:
            features['language'] = 'korean'

        # 年龄组识别
        if any(age in voice_lower for age in ['child', 'kid', 'young']):
            features['age_group'] = 'young'
        elif any(age in voice_lower for age in ['senior', 'old', 'elder']):
            features['age_group'] = 'senior'

        return features

    def analyze_character_features(self, speaker_name: str, dialogue_content: str) -> Dict:
        """
        分析角色特征

        Args:
            speaker_name: 说话者名称
            dialogue_content: 对话内容

        Returns:
            角色特征字典
        """
        try:
            from book2tts.llm_service import LLMService

            llm_service = LLMService()

            system_prompt = """你是一个专业的角色分析助手。请根据角色名称和对话内容分析角色特征，并以严格的JSON格式返回结果。"""

            user_prompt = f"""
请分析以下角色特征：

角色名称：{speaker_name}
对话内容：{dialogue_content}

请根据角色名称和对话内容，分析以下特征：
1. 性别（male/female/unknown）
2. 年龄组（child/young/adult/senior/unknown）
3. 性格特征（gentle/energetic/calm/authoritative/friendly/formal/casual/unknown）
4. 语言偏好（chinese/english/japanese/korean/unknown）

请以JSON格式返回分析结果，格式如下：
{{
    "gender": "male/female/unknown",
    "age_group": "child/young/adult/senior/unknown",
    "personality": "gentle/energetic/calm/authoritative/friendly/formal/casual/unknown",
    "language_preference": "chinese/english/japanese/korean/unknown"
}}
"""

            result = llm_service.process_text(system_prompt, user_prompt)

            if result.get('success') and result.get('result'):
                response_text = result['result']

                # 解析LLM响应
                try:
                    character_features = json.loads(response_text)
                    return character_features
                except json.JSONDecodeError:
                    # 如果JSON解析失败，使用启发式规则
                    return self._fallback_character_analysis(speaker_name, dialogue_content)
            else:
                # LLM调用失败，使用备用方法
                logger.warning(f"LLM调用失败: {result.get('error', 'Unknown error')}")
                return self._fallback_character_analysis(speaker_name, dialogue_content)

        except Exception as e:
            logger.error(f"角色特征分析失败: {e}")
            return self._fallback_character_analysis(speaker_name, dialogue_content)

    def _fallback_character_analysis(self, speaker_name: str, dialogue_content: str) -> Dict:
        """备用角色分析方法"""
        features = {
            'gender': 'unknown',
            'age_group': 'adult',
            'personality': 'unknown',
            'language_preference': 'chinese'
        }

        # 基于角色名称的简单推断
        name_lower = speaker_name.lower()

        # 性别推断
        if any(female_indicator in name_lower for female_indicator in ['女', 'female', 'woman', 'lady', 'miss', 'ms', 'girl', 'daughter', 'mother', 'wife']):
            features['gender'] = 'female'
        elif any(male_indicator in name_lower for male_indicator in ['男', 'male', 'man', 'gentleman', 'mr', 'boy', 'son', 'father', 'husband']):
            features['gender'] = 'male'

        # 年龄推断
        if any(young_indicator in name_lower for young_indicator in ['小', '少年', '青年', 'young', 'child', 'kid', 'teen', 'student']):
            features['age_group'] = 'young'
        elif any(senior_indicator in name_lower for senior_indicator in ['老', '爷爷', '奶奶', 'senior', 'old', 'grand', 'elder']):
            features['age_group'] = 'senior'

        # 基于对话内容的简单性格推断
        dialogue_lower = dialogue_content.lower()
        if any(calm_word in dialogue_lower for calm_word in ['安静', '平静', '温柔', '轻声', '慢慢']):
            features['personality'] = 'gentle'
        elif any(energetic_word in dialogue_lower for energetic_word in ['快', '兴奋', '激动', '大声', '活力']):
            features['personality'] = 'energetic'
        elif any(authoritative_word in dialogue_lower for authoritative_word in ['命令', '必须', '应该', '要求', '领导']):
            features['personality'] = 'authoritative'

        logger.info(f"备用分析结果 - 角色: {speaker_name}, 特征: {features}")
        return features

    def recommend_voice_for_character(self, speaker_name: str, dialogue_content: str) -> Optional[str]:
        """
        为角色推荐音色

        Args:
            speaker_name: 说话者名称
            dialogue_content: 对话内容

        Returns:
            推荐的音色名称，如果没有合适推荐则返回None
        """
        try:
            # 分析角色特征
            character_features = self.analyze_character_features(speaker_name, dialogue_content)
            logger.info(f"角色分析完成 - 角色: {speaker_name}, 特征: {character_features}")

            # 计算音色匹配分数
            voice_scores = []
            for voice in self.available_voices:
                score = self._calculate_voice_match_score(voice, character_features)
                voice_scores.append((voice['value'], score))

            # 按分数排序，选择最高分的音色
            voice_scores.sort(key=lambda x: x[1], reverse=True)

            if voice_scores and voice_scores[0][1] > 0:
                recommended_voice = voice_scores[0][0]
                logger.info(f"音色推荐结果 - 角色: {speaker_name}, 推荐音色: {recommended_voice}, 最高分: {voice_scores[0][1]}")
                return recommended_voice
            else:
                logger.warning(f"未找到合适音色 - 角色: {speaker_name}, 最高分: {voice_scores[0][1] if voice_scores else 0}")
                return None

        except Exception as e:
            logger.error(f"音色推荐失败: {e}")
            return None

    def _calculate_voice_match_score(self, voice: Dict, character_features: Dict) -> float:
        """计算音色与角色特征的匹配分数"""
        score = 0.0
        voice_features = voice['features']

        # 性别匹配（权重最高）
        if character_features['gender'] != 'unknown':
            if voice_features['gender'] == character_features['gender']:
                score += 3.0

        # 年龄组匹配
        if character_features['age_group'] != 'unknown':
            if voice_features['age_group'] == character_features['age_group']:
                score += 2.0

        # 语言匹配
        if character_features['language_preference'] != 'unknown':
            if voice_features['language'] == character_features['language_preference']:
                score += 2.0

        # 性格匹配
        if character_features['personality'] != 'unknown':
            # 温柔性格匹配温柔音色
            if character_features['personality'] == 'gentle':
                if any(gentle_indicator in voice['value'].lower() for gentle_indicator in ['gentle', 'soft', 'calm', 'warm']):
                    score += 1.5
            # 活力性格匹配活力音色
            elif character_features['personality'] == 'energetic':
                if any(energetic_indicator in voice['value'].lower() for energetic_indicator in ['energetic', 'lively', 'bright', 'cheerful']):
                    score += 1.5
            # 权威性格匹配成熟音色
            elif character_features['personality'] == 'authoritative':
                if any(authoritative_indicator in voice['value'].lower() for authoritative_indicator in ['deep', 'authoritative', 'mature', 'professional']):
                    score += 1.5

        # 默认中文音色加分（针对中文内容）
        if voice_features['language'] == 'chinese':
            score += 1.0

        # 友好音色通用加分
        if any(friendly_indicator in voice['value'].lower() for friendly_indicator in ['friendly', 'kind', 'pleasant']):
            score += 0.5

        logger.debug(f"音色匹配评分 - 音色: {voice['value']}, 角色特征: {character_features}, 分数: {score}")
        return score

    def recommend_voices_for_script(self, script_data: Dict) -> Dict[str, str]:
        """
        为整个对话脚本推荐音色

        Args:
            script_data: 对话脚本数据

        Returns:
            说话者到音色的映射字典
        """
        recommendations = {}

        if not script_data or 'segments' not in script_data:
            return recommendations

        # 按说话者分组对话内容
        speaker_dialogues = {}
        for segment in script_data['segments']:
            speaker = segment.get('speaker', '')
            utterance = segment.get('utterance', '')

            if speaker:
                if speaker not in speaker_dialogues:
                    speaker_dialogues[speaker] = []
                speaker_dialogues[speaker].append(utterance)

        # 为每个说话者推荐音色
        for speaker, dialogues in speaker_dialogues.items():
            # 合并对话内容进行分析
            combined_content = ' '.join(dialogues[:3])  # 取前3句进行分析

            recommended_voice = self.recommend_voice_for_character(speaker, combined_content)
            if recommended_voice:
                recommendations[speaker] = recommended_voice

        return recommendations

    def get_voices_by_category(self, category: str, value: str) -> List[Dict]:
        """
        根据分类获取音色列表

        Args:
            category: 分类类型 ('gender', 'language', 'age_group', 'personality')
            value: 分类值

        Returns:
            符合条件的音色列表
        """
        return [
            voice for voice in self.available_voices
            if voice['features'].get(category) == value
        ]

    def get_voice_statistics(self) -> Dict[str, Dict]:
        """
        获取音色统计信息

        Returns:
            音色统计字典
        """
        stats = {
            'gender': {},
            'language': {},
            'age_group': {},
            'personality': {}
        }

        for voice in self.available_voices:
            features = voice['features']

            # 统计性别
            gender = features.get('gender', 'unknown')
            stats['gender'][gender] = stats['gender'].get(gender, 0) + 1

            # 统计语言
            language = features.get('language', 'unknown')
            stats['language'][language] = stats['language'].get(language, 0) + 1

            # 统计年龄组
            age_group = features.get('age_group', 'adult')
            stats['age_group'][age_group] = stats['age_group'].get(age_group, 0) + 1

            # 统计性格
            personality = features.get('personality', 'unknown')
            stats['personality'][personality] = stats['personality'].get(personality, 0) + 1

        return stats

    def get_voices_by_category(self, category: str, value: str) -> List[Dict]:
        """
        根据分类获取音色列表

        Args:
            category: 分类类型 ('gender', 'language', 'age_group', 'personality')
            value: 分类值

        Returns:
            符合条件的音色列表
        """
        return [
            voice for voice in self.available_voices
            if voice['features'].get(category) == value
        ]

    def get_voice_statistics(self) -> Dict[str, Dict]:
        """
        获取音色统计信息

        Returns:
            音色统计字典
        """
        stats = {
            'gender': {},
            'language': {},
            'age_group': {},
            'personality': {}
        }

        for voice in self.available_voices:
            features = voice['features']

            # 统计性别
            gender = features.get('gender', 'unknown')
            stats['gender'][gender] = stats['gender'].get(gender, 0) + 1

            # 统计语言
            language = features.get('language', 'unknown')
            stats['language'][language] = stats['language'].get(language, 0) + 1

            # 统计年龄组
            age_group = features.get('age_group', 'adult')
            stats['age_group'][age_group] = stats['age_group'].get(age_group, 0) + 1

            # 统计性格
            personality = features.get('personality', 'unknown')
            stats['personality'][personality] = stats['personality'].get(personality, 0) + 1

        return stats