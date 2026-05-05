#!/usr/bin/env python3
"""
数据清洗与标准化模块 - 完全复刻GoMusic架构
"""
import re
from typing import List, Dict, Any
from dataclasses import dataclass


@dataclass
class StandardSong:
    """标准化歌曲"""
    original_name: str
    clean_name: str
    singer: str
    is_live: bool = False
    is_remix: bool = False
    has_version_tag: bool = False

    @property
    def search_text(self):
        return f"{self.clean_name} - {self.singer}"


class DataCleaner:
    """数据清洗器"""

    LIVE_PATTERNS = [
        r"Live", r"live", r"现场", r"演唱会", r"LIVE",
    ]

    REMIX_PATTERNS = [
        r"Remix", r"remix", r"RMX", r"Remixed",
    ]

    VERSION_PATTERNS = [
        r"版本", r"Ver\.", r"Version", r"Acoustic",
    ]

    BRACKETS_PATTERNS = [
        r"（.*?）",  # 中文括号
        r"\(.*?\)",  # 英文括号
        r"【.*?】",  # 全角方括号
        r"\[.*?\]",  # 半角方括号
        r"\{.*?\}",  # 花括号
    ]

    @classmethod
    def clean_song_name(cls, song_name: str) -> str:
        """清洗歌曲名称"""
        cleaned = song_name

        # 移除各类括号及其内容
        for pattern in cls.BRACKETS_PATTERNS:
            cleaned = re.sub(pattern, "", cleaned)

        # 移除多余空格
        cleaned = re.sub(r"\s+", " ", cleaned).strip()

        return cleaned

    @classmethod
    def detect_song_tags(cls, song_name: str) -> tuple[bool, bool, bool]:
        """检测歌曲标签"""
        song_name_lower = song_name.lower()

        is_live = any(pat.lower() in song_name_lower for pat in cls.LIVE_PATTERNS)
        is_remix = any(pat.lower() in song_name_lower for pat in cls.REMIX_PATTERNS)
        has_version = any(pat.lower() in song_name_lower for pat in cls.VERSION_PATTERNS)

        return is_live, is_remix, has_version

    @classmethod
    def standardize(cls, song_name: str, singer: str) -> StandardSong:
        """标准化歌曲信息"""
        is_live, is_remix, has_version = cls.detect_song_tags(song_name)
        cleaned_name = cls.clean_song_name(song_name)

        return StandardSong(
            original_name=song_name,
            clean_name=cleaned_name,
            singer=singer,
            is_live=is_live,
            is_remix=is_remix,
            has_version_tag=has_version
        )


class SongMatcher:
    """歌曲匹配器（三级匹配）"""

    @staticmethod
    def calculate_similarity(text1: str, text2: str) -> float:
        """计算字符串相似度"""
        t1 = text1.lower().strip()
        t2 = text2.lower().strip()

        if not t1 or not t2:
            return 0.0

        # 简单版本的相似度
        return 0.8 if t1 == t2 else 0.6 if t1 in t2 or t2 in t1 else 0.3

    @staticmethod
    def match_exact(
        song_name: str, singer: str, candidates: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """第一级：精确匹配"""
        best_match = None
        best_score = 0.0

        for candidate in candidates:
            name_score = SongMatcher.calculate_similarity(
                song_name, candidate.get("name", "")
            )
            singer_score = SongMatcher.calculate_similarity(
                singer, candidate.get("singer", "")
            )
            total_score = name_score * 0.7 + singer_score * 0.3

            if total_score > best_score and total_score > 0.8:
                best_score = total_score
                best_match = candidate

        return best_match

    @staticmethod
    def match_fuzzy(
        song_name: str, singer: str, candidates: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """第二级：模糊匹配"""
        best_match = None
        best_score = 0.0

        for candidate in candidates:
            name_score = SongMatcher.calculate_similarity(
                song_name, candidate.get("name", "")
            )
            singer_score = SongMatcher.calculate_similarity(
                singer, candidate.get("singer", "")
            )
            total_score = name_score * 0.7 + singer_score * 0.3

            if total_score > best_score and total_score > 0.5:
                best_score = total_score
                best_match = candidate

        return best_match

    @staticmethod
    def match_keyword(
        song_name: str, singer: str, candidates: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """第三级：关键词匹配"""
        best_match = None
        best_score = 0.0

        for candidate in candidates:
            name_score = SongMatcher.calculate_similarity(
                song_name, candidate.get("name", "")
            )
            singer_score = SongMatcher.calculate_similarity(
                singer, candidate.get("singer", "")
            )
            total_score = name_score * 0.7 + singer_score * 0.3

            if total_score > best_score and total_score > 0.3:
                best_score = total_score
                best_match = candidate

        return best_match


class Exporter:
    """导出器"""

    @staticmethod
    def export_text(songs: List[Dict[str, Any]]) -> str:
        """导出为文本格式（TuneMyMusic兼容）"""
        lines = []
        for song in songs:
            name = song.get("name", song.get("title", "未知"))
            singer = song.get("singer", song.get("artist", "未知"))
            lines.append(f"{name} - {singer}")

        return "\n".join(lines)

    @staticmethod
    def export_csv(songs: List[Dict[str, Any]]) -> str:
        """导出为CSV格式"""
        import csv
        import io

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["Title", "Artist", "Album"])
        for song in songs:
            name = song.get("name", song.get("title", ""))
            singer = song.get("singer", song.get("artist", ""))
            album = song.get("album", "")
            writer.writerow([name, singer, album])

        return output.getvalue()
