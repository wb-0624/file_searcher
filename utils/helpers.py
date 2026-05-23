# -*- coding: utf-8 -*-
"""
辅助函数
"""
import logging

logger = logging.getLogger(__name__)

def extract_context(text, keyword, window=50):
    """
    返回包含关键词的一段文本，前后各取window字符。
    :param text: 原始文本
    :param keyword: 关键词
    :param window: 上下文窗口大小
    :return: 包含关键词的片段（如果关键词不存在，返回开头200字符）
    """
    if not text:
        logger.debug("extract_context: 文本为空")
        return ""
    pos = text.lower().find(keyword.lower())
    if pos == -1:
        logger.debug(f"extract_context: 未找到关键词 '{keyword}'，返回开头200字符")
        return text[:200]
    start = max(0, pos - window)
    end = min(len(text), pos + len(keyword) + window)
    snippet = text[start:end]
    if start > 0:
        snippet = '...' + snippet
    if end < len(text):
        snippet = snippet + '...'
    logger.debug(f"extract_context: 提取片段长度 {len(snippet)}")
    return snippet