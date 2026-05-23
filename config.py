# -*- coding: utf-8 -*-
"""
配置文件：数据库路径、日志设置
"""
import os

# SQLite 数据库文件路径
DATABASE_PATH = os.path.join(os.path.dirname(__file__), "data.db")

# 日志配置
LOG_FILE = os.path.join(os.path.dirname(__file__), "app.log")
LOG_LEVEL = "INFO"
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
