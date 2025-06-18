"""Prompt模板管理

集中管理所有AI功能的prompt模板，确保提示词的一致性和可维护性。
"""

from typing import Any


class PromptTemplate:
    """Prompt模板基类"""

    def __init__(self, template: str):
        """初始化模板实例

        Args:
            template: 模板字符串，使用花括号{}作为占位符

        """
        self.template = template

    def format(self, **kwargs: Any) -> str:
        """格式化模板"""
        return self.template.format(**kwargs)


# 文件分类Prompt
FILE_CLASSIFY_PROMPT = PromptTemplate(
    """你是一个专业的文件分类助手。请根据文件信息建议最合适的分类。

文件信息：
- 文件名：{filename}
- 文件扩展名：{extension}
- 文件大小：{file_size}
- 修改时间：{modified_time}
- 内容预览：
{content_preview}

请返回JSON格式的分类建议：
{{
    "category": "分类名称",
    "confidence": 0-100的置信度整数,
    "reason": "分类理由（不超过50字）"
}}

可选分类：
- 工作文档：包含工作相关内容，如报告、计划、会议记录等
- 个人文件：个人生活相关，如照片、日记、个人笔记等
- 项目代码：源代码、配置文件、技术文档等
- 学习资料：教程、电子书、课程资料等
- 临时文件：临时生成的文件、缓存、下载的临时内容
- 系统文件：系统配置、日志、程序生成的文件
- 归档文件：需要长期保存的历史文件
- 其他：无法明确分类的文件

注意：请严格返回JSON格式，不要包含其他说明文字。"""
)

# 文档摘要Prompt
DOCUMENT_SUMMARIZE_PROMPT = PromptTemplate(
    """请为以下文档生成一个{length}字左右的中文摘要。

文档信息：
- 标题：{title}
- 类型：{doc_type}
- 字数：{word_count}

文档内容：
{content}

要求：
1. 准确概括文档的核心内容
2. 使用简洁清晰的中文表达
3. 保持客观中立的语气
4. 突出关键信息和要点
5. 摘要长度控制在{length}字左右

请直接返回摘要内容，不需要其他说明。"""
)

# 文本替换风险分析Prompt
TEXT_REPLACE_ANALYSIS_PROMPT = PromptTemplate(
    """你是一个文本处理专家。请分析以下文本替换操作的潜在风险。

替换操作：
- 查找文本："{old_text}"
- 替换为："{new_text}"
- 文件类型：{file_types}
- 示例内容：
{content_samples}

请返回JSON格式的分析结果：
{{
    "risk_level": "low/medium/high",
    "potential_issues": [
        "潜在问题描述1",
        "潜在问题描述2"
    ],
    "suggestions": [
        "改进建议1",
        "改进建议2"
    ],
    "safe_pattern": "更安全的匹配模式（如果需要）"
}}

注意事项：
1. 考虑可能的误匹配情况
2. 评估对代码、配置文件的影响
3. 检查是否会破坏文件格式
4. 考虑大小写敏感性问题"""
)

# 文件版本识别Prompt
FILE_VERSION_ANALYSIS_PROMPT = PromptTemplate(
    """分析以下相似文件，识别它们的版本关系并推荐保留哪个。

文件组信息：
{file_group_info}

请返回JSON格式的分析结果：
{{
    "version_chain": [
        {{"filename": "文件名", "version": "版本标识", "is_latest": true/false}}
    ],
    "recommended_keep": "建议保留的文件名",
    "reason": "推荐理由",
    "relationship": "版本关系描述"
}}

分析要点：
1. 识别文件名中的版本标识（如v1, v2, final, 最新等）
2. 根据修改时间判断先后顺序
3. 考虑文件大小变化
4. 识别常见的版本命名模式"""
)

# 增强版文件版本分析Prompt（用于version_analyzer）
VERSION_ANALYSIS_PROMPT = PromptTemplate(
    """你是一个文件版本关系分析专家。请分析以下重复文件的版本关系。

文件列表：
{files}

基础分析结果：
{basic_analysis}

请综合考虑以下因素：
1. 文件名中的版本标识（v1, v2, final, 最新, new, old等）
2. 文件修改时间的先后顺序
3. 文件大小的变化（通常新版本会更大）
4. 文件名模式（副本、copy、backup等通常不是主版本）
5. 如果有内容预览，分析内容的完整性

请返回JSON格式的分析结果：
{{
    "recommended_file": "建议保留的文件名",
    "confidence": 0.0-1.0的置信度,
    "reason": "详细的推荐理由（100字以内）",
    "version_relationship": {{
        "type": "version/backup/copy",
        "description": "版本关系的具体描述"
    }}
}}

注意：
- 优先保留最新、最完整的版本
- 如果有"final"、"最终"等标识，通常应该保留
- 备份和副本通常可以删除
- 请用中文回答，但返回的JSON字段名保持英文"""
)


# Prompt管理器
class PromptManager:
    """Prompt模板管理器"""

    templates: dict[str, PromptTemplate] = {
        "file_classify": FILE_CLASSIFY_PROMPT,
        "document_summarize": DOCUMENT_SUMMARIZE_PROMPT,
        "text_replace_analysis": TEXT_REPLACE_ANALYSIS_PROMPT,
        "file_version_analysis": FILE_VERSION_ANALYSIS_PROMPT,
        "version_analysis": VERSION_ANALYSIS_PROMPT,
    }

    @classmethod
    def get(cls, name: str) -> PromptTemplate:
        """获取指定的prompt模板"""
        if name not in cls.templates:
            raise ValueError(f"未知的prompt模板: {name}")
        return cls.templates[name]

    @classmethod
    def format(cls, name: str, **kwargs: Any) -> str:
        """格式化指定的prompt模板"""
        template = cls.get(name)
        return template.format(**kwargs)


# 创建全局实例
prompt_manager = PromptManager()
