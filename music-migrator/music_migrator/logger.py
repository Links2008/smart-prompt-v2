import logging
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional
from . import config


class Logger:
    """统一日志系统"""

    _instance: Optional["Logger"] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if hasattr(self, "logger"):
            return

        self.logger = logging.getLogger("MusicMigrator")
        self.logger.setLevel(logging.DEBUG)

        # 格式化器
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )

        # 控制台输出
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)

        # 文件输出
        log_file = config.LOGS_DIR / f"migration_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)

        self.log_file = log_file

    def info(self, message: str):
        self.logger.info(message)

    def debug(self, message: str):
        self.logger.debug(message)

    def warning(self, message: str):
        self.logger.warning(message)

    def error(self, message: str, exc_info: bool = False):
        self.logger.error(message, exc_info=exc_info)


def get_logger() -> Logger:
    """获取全局日志实例"""
    return Logger()
