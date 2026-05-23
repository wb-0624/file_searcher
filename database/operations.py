# -*- coding: utf-8 -*-
"""
业务操作：归档管理、同步文件、搜索
"""
import os
import datetime
import logging
from sqlalchemy import or_
from .models import Archive, Entry
from file_handlers.docx_handler import extract_docx_text
from file_handlers.xlsx_handler import extract_xlsx_text
from file_handlers.md_handler import extract_md_text
from utils.helpers import extract_context

logger = logging.getLogger(__name__)

SUPPORTED_EXT = ('.docx', '.xlsx', '.md')


# ==========================================
#  文件文本提取
# ==========================================
def extract_file_text(file_path):
    ext = os.path.splitext(file_path)[1].lower()
    logger.debug(f"提取文件文本: {file_path}, 扩展名: {ext}")
    try:
        if ext == '.docx':
            return extract_docx_text(file_path)
        elif ext == '.xlsx':
            return extract_xlsx_text(file_path)
        elif ext == '.md':
            return extract_md_text(file_path)
        else:
            logger.warning(f"不支持的文件类型: {file_path}")
            return ''
    except Exception as e:
        logger.error(f"提取文件文本失败 {file_path}: {e}")
        return ''


# ==========================================
#  归档管理
# ==========================================
def create_archive(session, name, root_dir):
    """创建新归档"""
    logger.info(f"创建归档: {name}, 目录: {root_dir}")
    archive = Archive(name=name, root_dir=root_dir)
    session.add(archive)
    session.commit()
    logger.info(f"归档创建成功，ID: {archive.id}")
    return archive.id


def delete_archive(session, archive_id):
    """删除归档及其中所有条目"""
    logger.info(f"删除归档 ID: {archive_id}")
    archive = session.query(Archive).get(archive_id)
    if archive:
        session.delete(archive)
        session.commit()
        logger.info("归档已删除")
        return True
    return False


def list_archives(session):
    """列出所有归档，含条目数"""
    archives = session.query(Archive).order_by(Archive.created_at).all()
    result = []
    for a in archives:
        count = session.query(Entry).filter_by(archive_id=a.id).count()
        result.append({
            'id': a.id,
            'name': a.name,
            'root_dir': a.root_dir,
            'created_at': a.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            'entry_count': count,
        })
    # 全部归档的条目总数
    total = session.query(Entry).filter(Entry.archive_id.isnot(None)).count()
    return result, total


def update_archive_name(session, archive_id, new_name):
    """重命名归档"""
    archive = session.query(Archive).get(archive_id)
    if archive:
        archive.name = new_name
        session.commit()


# ==========================================
#  文件同步
# ==========================================
def rebuild_archive(session, archive_id):
    """扫描指定归档的目录，增量同步文件"""
    archive = session.query(Archive).get(archive_id)
    if not archive:
        logger.error(f"归档不存在: {archive_id}")
        return

    root_dir = os.path.expanduser(archive.root_dir)
    logger.info(f"整理归档 [{archive.name}]，目录: {root_dir}")

    current_files = {}
    if os.path.isdir(root_dir):
        for dirpath, _, filenames in os.walk(root_dir):
            for f in filenames:
                if f.lower().endswith(SUPPORTED_EXT):
                    full_path = os.path.join(dirpath, f)
                    try:
                        mtime = os.path.getmtime(full_path)
                        current_files[full_path] = mtime
                    except OSError as e:
                        logger.warning(f"无法访问文件 {full_path}: {e}")
                        continue

    logger.info(f"发现 {len(current_files)} 个文件")

    # 该归档下所有文件记录
    db_files = session.query(Entry).filter_by(
        source_type='file', archive_id=archive_id).all()
    db_file_map = {e.source_path: e for e in db_files}

    # 删除不存在的
    for path, entry in db_file_map.items():
        if path not in current_files:
            logger.info(f"删除不存在的文件记录: {path}")
            session.delete(entry)

    # 新增或更新
    for path, mtime in current_files.items():
        db_entry = db_file_map.get(path)
        if db_entry is None:
            logger.info(f"新增文件: {path}")
            content = extract_file_text(path)
            if content:
                entry = Entry(
                    content=content,
                    source_type='file',
                    source_path=path,
                    source_name=os.path.basename(path),
                    updated_at=datetime.datetime.fromtimestamp(mtime),
                    archive_id=archive_id,
                )
                session.add(entry)
        else:
            db_mtime = db_entry.updated_at.timestamp()
            if mtime > db_mtime:
                logger.info(f"文件已更新，重新提取: {path}")
                content = extract_file_text(path)
                if content:
                    db_entry.content = content
                    db_entry.updated_at = datetime.datetime.fromtimestamp(
                        mtime)

    session.commit()
    logger.info("归档整理完成")


# ==========================================
#  搜索
# ==========================================
def search(session, keyword, archive_id=None):
    """
    搜索关键词。
    :param archive_id: None=搜索全部，int=搜索指定归档
    """
    scope = f"归档 {archive_id}" if archive_id else "全部归档"
    logger.info(f"执行搜索 [{scope}]，关键词: {keyword}")

    q = session.query(Entry).filter(
        or_(
            Entry.content.contains(keyword),
            Entry.source_name.contains(keyword)
        )
    )
    if archive_id is not None:
        q = q.filter_by(archive_id=archive_id)

    entries = q.all()
    kw_lower = keyword.lower()
    logger.debug(f"搜索到 {len(entries)} 条记录")

    results = []
    for entry in entries:
        if entry.content:
            context = extract_context(entry.content, keyword, window=50)
            match_count = entry.content.lower().count(kw_lower)
        else:
            context = f'[文件名匹配: {entry.source_name}]'
            match_count = 0
        results.append({
            'id': entry.id,
            'highlight': context,
            'source_type': entry.source_type,
            'source_path': entry.source_path,
            'source_name': entry.source_name,
            'updated_at': entry.updated_at.strftime('%Y-%m-%d %H:%M:%S'),
            'match_count': match_count,
            'archive_id': entry.archive_id,
        })
    return results
