# -*- coding: utf-8 -*-
"""
数据库初始化与会话管理
"""
import logging
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker
from .models import Base
import config

logger = logging.getLogger(__name__)

def get_engine(db_path=config.DATABASE_PATH):
    """创建并返回数据库引擎"""
    return create_engine(f'sqlite:///{db_path}?check_same_thread=False')

def ensure_database(db_path=config.DATABASE_PATH):
    """
    确保数据库就绪，自动处理旧表迁移。
    """
    logger.info(f"确保数据库就绪，路径: {db_path}")
    engine = get_engine(db_path)
    inspector = inspect(engine)
    existing_tables = inspector.get_table_names()

    if not existing_tables:
        logger.info("数据库中没有表，正在创建表...")
        Base.metadata.create_all(engine)
        logger.info("表创建完成")
    else:
        logger.debug("数据库表已存在，检查是否需要迁移...")
        # 旧版 entries 表缺少 archive_id 列，安全添加
        if 'entries' in existing_tables:
            cols = [c['name'] for c in inspector.get_columns('entries')]
            if 'archive_id' not in cols:
                logger.info("迁移: 为 entries 表添加 archive_id 列")
                with engine.connect() as conn:
                    conn.execute(
                        text('ALTER TABLE entries ADD COLUMN archive_id '
                             'INTEGER REFERENCES archives(id) '
                             'ON DELETE CASCADE'))
                    conn.commit()
        if 'archives' not in existing_tables:
            logger.info("创建 archives 表")
            Base.metadata.create_all(engine)
    return engine

def init_db(db_path=config.DATABASE_PATH):
    """
    初始化数据库：删除旧表，创建新表（即重置数据库）。
    :param db_path: 数据库文件路径
    :return: SQLAlchemy engine 对象
    """
    logger.warning(f"初始化数据库（重置），路径: {db_path}")
    engine = get_engine(db_path)
    # 删除所有表
    Base.metadata.drop_all(engine)
    logger.debug("已删除所有旧表")
    # 创建新表
    Base.metadata.create_all(engine)
    logger.info("数据库表重建成功")
    return engine

def get_session(engine):
    """
    获取数据库会话。
    :param engine: SQLAlchemy engine
    :return: Session 对象
    """
    logger.debug("获取数据库会话")
    Session = sessionmaker(bind=engine)
    return Session()