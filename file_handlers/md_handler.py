# -*- coding: utf-8 -*-
"""
处理 .md 文件，提取文本内容
"""
import logging

logger = logging.getLogger(__name__)


def extract_md_text(file_path):
    """
    提取 Markdown 文件全部文本内容。
    :param file_path: md 文件路径
    :return: 提取的文本，失败返回空字符串
    """
    logger.debug(f"提取 md 文本: {file_path}")
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            text = f.read()
        logger.debug(f"成功读取 md 文件，总字符数: {len(text)}")
        return text
    except Exception as e:
        logger.error(f"读取 md 失败 {file_path}: {e}")
        return ""
