from pathlib import Path

# 项目根目录
BASE_DIR = Path(__file__).parent.parent.absolute()

# 数据目录
DATA_DIR = BASE_DIR / "data"
LOGS_DIR = DATA_DIR / "logs"
CACHE_DIR = DATA_DIR / "cache"
EXPORT_DIR = DATA_DIR / "exports"

# 确保目录存在
for directory in [DATA_DIR, LOGS_DIR, CACHE_DIR, EXPORT_DIR]:
    directory.mkdir(parents=True, exist_ok=True)
