"""AI模块 - 智能化能力增强

本模块提供基于DeepSeek API的智能化功能，包括：
- 智能文件分类
- 文档自动摘要
- 内容智能分析
- 文本替换风险分析
"""

from .classifier import FileClassifier
from .config import AIConfig, get_ai_config
from .deepseek_client import DeepSeekClient
from .summarizer import DocumentSummarizer
from .text_analyzer import TextAnalyzer

__all__ = [
    "AIConfig",
    "get_ai_config",
    "DeepSeekClient",
    "FileClassifier",
    "DocumentSummarizer",
    "TextAnalyzer",
]
