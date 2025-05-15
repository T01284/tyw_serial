# -*- coding: utf-8 -*-
"""
@Author     : 架构修改
@Company    : 黑龙江天有为科技有限公司
@Date       : 2025-05-13
@Python     : 3.10
@Description: 日志管理模块，提供日志记录功能
"""

import os
import logging
import sys
from datetime import datetime
from logging.handlers import RotatingFileHandler


class LogManager:
    """日志管理类，用于记录日志并保存到文件"""

    # 日志级别映射
    LEVEL_MAP = {
        'DEBUG': logging.DEBUG,
        'INFO': logging.INFO,
        'WARNING': logging.WARNING,
        'ERROR': logging.ERROR,
        'CRITICAL': logging.CRITICAL
    }

    _instance = None

    def __new__(cls, *args, **kwargs):
        """单例模式实现"""
        if cls._instance is None:
            cls._instance = super(LogManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, log_dir='logs', file_name=None, console_level='DEBUG', file_level='DEBUG',
                 max_size=10 * 1024 * 1024, backup_count=10):
        """
        初始化日志管理器

        Args:
            log_dir (str): 日志文件目录
            file_name (str): 日志文件名，默认使用当前日期
            console_level (str): 控制台日志级别
            file_level (str): 文件日志级别
            max_size (int): 单个日志文件最大大小(字节)
            backup_count (int): 保留的日志文件数量
        """
        # 避免重复初始化
        if self._initialized:
            return

        self._initialized = True

        # 创建日志目录
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)

        # 如果未指定文件名，使用当前日期
        if file_name is None:
            file_name = f"log_{datetime.now().strftime('%Y%m%d')}.log"

        # 完整的日志文件路径
        log_file = os.path.join(log_dir, file_name)

        # 获取日志级别
        console_level = self.LEVEL_MAP.get(console_level.upper(), logging.INFO)
        file_level = self.LEVEL_MAP.get(file_level.upper(), logging.DEBUG)

        # 创建日志记录器
        self.logger = logging.getLogger('tyw_logger')
        self.logger.setLevel(logging.DEBUG)  # 设置为最低级别，让Handler决定输出

        # 清除已有的处理器
        for handler in self.logger.handlers[:]:
            self.logger.removeHandler(handler)

        # 创建控制台处理器
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(console_level)

        # 创建文件处理器
        file_handler = RotatingFileHandler(
            log_file, maxBytes=max_size, backupCount=backup_count, encoding='utf-8'
        )
        file_handler.setLevel(file_level)

        # 创建日志格式
        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s'
        )

        # 设置格式
        console_handler.setFormatter(formatter)
        file_handler.setFormatter(formatter)

        # 添加处理器
        self.logger.addHandler(console_handler)
        self.logger.addHandler(file_handler)

        # 记录初始化信息
        self.logger.info("日志管理器初始化完成: %s", log_file)

    def debug(self, message, *args, **kwargs):
        """记录DEBUG级别日志"""
        self.logger.debug(message, *args, **kwargs)

    def info(self, message, *args, **kwargs):
        """记录INFO级别日志"""
        self.logger.info(message, *args, **kwargs)

    def warning(self, message, *args, **kwargs):
        """记录WARNING级别日志"""
        self.logger.warning(message, *args, **kwargs)

    def error(self, message, *args, **kwargs):
        """记录ERROR级别日志"""
        self.logger.error(message, *args, **kwargs)

    def critical(self, message, *args, **kwargs):
        """记录CRITICAL级别日志"""
        self.logger.critical(message, *args, **kwargs)

    def exception(self, message, *args, exc_info=True, **kwargs):
        """记录异常信息"""
        self.logger.exception(message, *args, exc_info=exc_info, **kwargs)

    def get_logger(self):
        """获取日志记录器"""
        return self.logger


# 创建全局日志实例
logger = LogManager().get_logger()


# 提供简便的函数接口，用于替代print
def log_debug(message, *args, **kwargs):
    """记录DEBUG级别日志"""
    logger.debug(message, *args, **kwargs)


def log_info(message, *args, **kwargs):
    """记录INFO级别日志"""
    logger.info(message, *args, **kwargs)


def log_warning(message, *args, **kwargs):
    """记录WARNING级别日志"""
    logger.warning(message, *args, **kwargs)


def log_error(message, *args, **kwargs):
    """记录ERROR级别日志"""
    logger.error(message, *args, **kwargs)


def log_critical(message, *args, **kwargs):
    """记录CRITICAL级别日志"""
    logger.critical(message, *args, **kwargs)


def log_exception(message, *args, **kwargs):
    """记录异常信息"""
    logger.exception(message, *args, **kwargs)


# 直接替代print的函数
def log_print(*args, **kwargs):
    """替代print函数，将内容记录到日志"""
    message = " ".join(str(arg) for arg in args)
    logger.info(message)

    # 处理标准print的关键字参数
    file = kwargs.get('file', None)
    if file is not None and file != sys.stdout and file != sys.stderr:
        print(*args, **kwargs)  # 如果指定了特定的输出文件，执行原始print