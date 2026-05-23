# -*- coding: utf-8 -*-
"""
SQLAlchemy ORM 模型定义
"""
from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey
from sqlalchemy.orm import declarative_base, relationship
import datetime

Base = declarative_base()


class Archive(Base):
    """归档表：每个扫描目录对应一个归档"""
    __tablename__ = 'archives'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(200), nullable=False)
    root_dir = Column(String(500), nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.now)

    entries = relationship('Entry', back_populates='archive',
                           cascade='all, delete-orphan')

    def __repr__(self):
        return f"<Archive(id={self.id}, name={self.name})>"


class Entry(Base):
    """数据条目表"""
    __tablename__ = 'entries'

    id = Column(Integer, primary_key=True, autoincrement=True)
    content = Column(Text, nullable=False)
    source_type = Column(String(20), nullable=False)
    source_path = Column(String(500), nullable=True)
    source_name = Column(String(200), nullable=True)
    updated_at = Column(DateTime, default=datetime.datetime.now,
                        onupdate=datetime.datetime.now)
    archive_id = Column(Integer, ForeignKey('archives.id',
                                            ondelete='CASCADE'),
                        nullable=True)

    archive = relationship('Archive', back_populates='entries')

    def __repr__(self):
        return f"<Entry(id={self.id}, source={self.source_name})>"
