# -*- coding: utf-8 -*-
"""
处理 .docx 文件，提取文本内容
"""
import logging
from docx import Document

logger = logging.getLogger(__name__)

def extract_docx_text(file_path):
    """
    提取docx文件所有段落文本。
    :param file_path: docx文件路径
    :return: 提取的文本，失败返回空字符串
    """
    logger.debug(f"提取docx文本: {file_path}")
    try:
        doc = Document(file_path)
        paragraphs = [para.text for para in doc.paragraphs if para.text]
        text = '\n'.join(paragraphs)
        logger.debug(f"成功提取 {len(paragraphs)} 个段落，总字符数: {len(text)}")
        return text
    except Exception as e:
        logger.error(f"读取docx失败 {file_path}: {e}")
        return ""