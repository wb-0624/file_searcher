#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
程序入口
"""
import logging
import config

def setup_logging():
    """
    配置日志：同时输出到文件和控制台
    """
    # 将字符串形式的日志级别转换为 logging 常量
    level = getattr(logging, config.LOG_LEVEL.upper(), logging.INFO)
    logging.basicConfig(
        level=level,
        format=config.LOG_FORMAT,
        handlers=[
            logging.FileHandler(config.LOG_FILE, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    # 记录启动标记
    logging.info("=" * 50)
    logging.info("程序启动")
    logging.info("=" * 50)

if __name__ == "__main__":
    setup_logging()
    from gui.app import MainWindow
    app = MainWindow()
    app.mainloop()
    logging.info("程序退出")