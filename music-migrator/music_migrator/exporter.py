import csv
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

from .errors import ErrorCode, ErrorResult
from .logger import get_logger
from . import config


class Exporter:
    """数据导出器"""

    def __init__(self):
        self.logger = get_logger()

    def export_csv(
        self,
        songs: List[Dict[str, Any]],
        filename: Optional[str] = None,
        include_matched: bool = True
    ) -> ErrorResult:
        """导出为 CSV 格式"""
        try:
            if not filename:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"playlist_{timestamp}.csv"

            filepath = config.EXPORT_DIR / filename

            with open(filepath, "w", encoding="utf-8-sig", newline="") as f:
                writer = csv.writer(f)
                # 表头
                writer.writerow(["序号", "歌曲名", "歌手", "专辑", "状态", "Apple Music ID"])
                for idx, song in enumerate(songs, 1):
                    row = [
                        idx,
                        song.get("title", "未知"),
                        song.get("artist", "未知"),
                        song.get("album", "未知"),
                        song.get("status", "待匹配"),
                        song.get("apple_music_id", "")
                    ]
                    writer.writerow(row)

            self.logger.info(f"成功导出 CSV 文件: {filepath}")
            return ErrorResult.success({"path": str(filepath), "format": "csv"})
        except Exception as e:
            self.logger.error(f"导出 CSV 失败: {e}", exc_info=True)
            return ErrorResult.failure(
                ErrorCode.SYSTEM_INTERNAL_ERROR,
                f"导出失败: {str(e)}"
            )

    def export_json(
        self,
        data: Dict[str, Any],
        filename: Optional[str] = None
    ) -> ErrorResult:
        """导出为 JSON 格式"""
        try:
            if not filename:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"playlist_{timestamp}.json"

            filepath = config.EXPORT_DIR / filename
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            self.logger.info(f"成功导出 JSON 文件: {filepath}")
            return ErrorResult.success({"path": str(filepath), "format": "json"})
        except Exception as e:
            self.logger.error(f"导出 JSON 失败: {e}", exc_info=True)
            return ErrorResult.failure(
                ErrorCode.SYSTEM_INTERNAL_ERROR,
                f"导出失败: {str(e)}"
            )

    def export_m3u8(
        self,
        songs: List[Dict[str, Any]],
        playlist_name: str = "我的歌单",
        filename: Optional[str] = None
    ) -> ErrorResult:
        """导出为 M3U8 格式"""
        try:
            if not filename:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"playlist_{timestamp}.m3u8"

            filepath = config.EXPORT_DIR / filename

            with open(filepath, "w", encoding="utf-8") as f:
                f.write("#EXTM3U\n")
                f.write(f"#PLAYLIST:{playlist_name}\n")
                for song in songs:
                    title = song.get("title", "未知")
                    artist = song.get("artist", "未知")
                    f.write(f"#EXTINF:-1,{artist} - {title}\n")
                    f.write(f"{title} - {artist}\n")

            self.logger.info(f"成功导出 M3U8 文件: {filepath}")
            return ErrorResult.success({"path": str(filepath), "format": "m3u8"})
        except Exception as e:
            self.logger.error(f"导出 M3U8 失败: {e}", exc_info=True)
            return ErrorResult.failure(
                ErrorCode.SYSTEM_INTERNAL_ERROR,
                f"导出失败: {str(e)}"
            )
