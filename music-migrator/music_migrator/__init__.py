#!/usr/bin/env python3
"""
QQ 音乐 → Apple Music 歌单迁移工具
"""

import os
from pathlib import Path

__version__ = "1.0.0"
__author__ = "Music Migrator"

# 项目根目录
BASE_DIR = Path(__file__).parent.absolute()

# 数据目录
DATA_DIR = BASE_DIR / "data"
LOGS_DIR = DATA_DIR / "logs"
CACHE_DIR = DATA_DIR / "cache"
EXPORT_DIR = DATA_DIR / "exports"

# 确保目录存在
for directory in [DATA_DIR, LOGS_DIR, CACHE_DIR, EXPORT_DIR]:
    directory.mkdir(parents=True, exist_ok=True)
