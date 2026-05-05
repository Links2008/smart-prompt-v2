import re
import difflib
import time
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass

from .errors import ErrorCode, ErrorResult
from .logger import get_logger


@dataclass
class MatchResult:
    """歌曲匹配结果"""
    original_song: Dict[str, Any]
    matched: bool
    match_score: float
    matched_song: Optional[Dict[str, Any]] = None
    error_code: Optional[ErrorCode] = None
    error_msg: Optional[str] = None
    match_type: Optional[str] = None  # "exact", "version", "translation", "fallback"


class SongMatcher:
    """歌曲匹配器"""

    # 版本关键词
    VERSION_KEYWORDS = [
        "Remix", "Live", "Acoustic", "Instrumental", "Live版", "Remix版",
        "演唱会", "演奏版", "版本", "Version", "VIP", "现场版", "伴奏"
    ]

    # 别名映射（中英文互译字典）
    ARTIST_ALIASES = {
        "the weeknd": ["盆栽", "威肯"],
        "justin bieber": ["比伯", "丁日"],
        "taylor swift": ["霉霉", "泰勒"],
        "周杰伦": ["jay chou"],
        "陈奕迅": ["eason chan"],
        "林俊杰": ["jj lin"],
        "邓紫棋": ["gem"],
        "薛之谦": ["joker xue"]
    }

    def __init__(self):
        self.logger = get_logger()

    def normalize_text(self, text: str) -> str:
        """标准化文本，用于匹配"""
        if not text:
            return ""
        text = text.lower().strip()
        # 移除特殊字符
        text = re.sub(r"[^\w\s]", "", text)
        return text

    def calculate_score(self, original: str, candidate: str) -> float:
        """计算相似度分数（0-1）"""
        original = self.normalize_text(original)
        candidate = self.normalize_text(candidate)

        if not original or not candidate:
            return 0.0

        ratio = difflib.SequenceMatcher(None, original, candidate).ratio()
        return ratio

    def check_version_match(self, song: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """检查歌曲版本检测"""
        title = song["title"].lower()
        version_type = None

        for keyword in self.VERSION_KEYWORDS:
            if keyword.lower() in title:
                version_type = keyword
                break

        return (version_type is not None, version_type)

    def fallback_match(self, song: Dict[str, Any]) -> Dict[str, Any]:
        """降级匹配：移除版本信息后的匹配"""
        original_title = song["title"]

        # 移除版本关键词
        cleaned_title = original_title
        for keyword in self.VERSION_KEYWORDS:
            cleaned_title = cleaned_title.replace(keyword, "")
        cleaned_title = cleaned_title.strip()

        return {
            **song,
            "title": cleaned_title,
            "is_version_cleaned": True
        }

    def match_song(
        self,
        song: Dict[str, Any],
        candidates: List[Dict[str, Any]],
        threshold: float = 0.7
    ) -> MatchResult:
        """
        匹配单个歌曲

        Args:
            song: 原始歌曲，包含 song['title'], song['artist']
            candidates: 候选歌曲列表
            threshold: 匹配阈值
        """
        self.logger.info(f"开始匹配: {song['title']} - {song['artist']}")

        best_score = 0.0
        best_match = None
        match_type = None

        # 1. 多轮搜索策略
        search_strategies = ["exact", "artist_only", "title_only", "translation"]

        for strategy in search_strategies:
            matches = self._search_by_strategy(song, candidates, strategy)

            if matches:
                # 按分数排序
                sorted_matches = sorted(matches, key=lambda x: x["score"], reverse=True)
                best_candidate = sorted_matches[0]

                if best_candidate["score"] >= threshold:
                    return MatchResult(
                        original_song=song,
                        matched=True,
                        match_score=best_candidate["score"],
                        matched_song=best_candidate["song"],
                        match_type=strategy
                    )

                # 记录最佳候选
                if best_candidate["score"] > best_score:
                    best_score = best_candidate["score"]
                    best_match = best_candidate

        # 2. 如果策略失败，检查是否是版权问题
        if not candidates:
            return MatchResult(
                original_song=song,
                matched=False,
                match_score=0.0,
                error_code=ErrorCode.MATCH_NO_COPYRIGHT,
                error_msg="Apple Music 可能无此歌曲版权"
            )

        # 3. 所有策略匹配分数都低于阈值
        return MatchResult(
            original_song=song,
            matched=False,
            match_score=best_score,
            error_code=ErrorCode.MATCH_INSUFFICIENT_SCORE,
            error_msg="匹配分数过低，无法确定正确匹配"
        )

    def _search_by_strategy(
        self,
        song: Dict[str, Any],
        candidates: List[Dict[str, Any]],
        strategy: str
    ) -> List[Dict[str, Any]]:
        """根据策略搜索候选"""
        results = []

        title = song["title"]
        artist = song["artist"]

        for candidate in candidates:
            score = 0.0
            title_score = self.calculate_score(title, candidate.get("title", ""))
            artist_score = self.calculate_score(artist, candidate.get("artist", ""))

            if strategy == "exact":
                score = title_score * 0.7 + artist_score * 0.3
            elif strategy == "artist_only":
                score = artist_score
            elif strategy == "title_only":
                score = title_score
            elif strategy == "translation":
                # 别名匹配
                score = max(title_score, artist_score)
                # 检查艺术家别名
                artist_normalized = self.normalize_text(artist)
                for alias, translations in self.ARTIST_ALIASES.items():
                    if artist_normalized == alias or artist_normalized in translations:
                        candidate_artist = self.normalize_text(candidate.get("artist", ""))
                        if candidate_artist == alias or candidate_artist in translations:
                            score = max(score, 0.9)

            if score > 0:
                results.append({
                    "song": candidate,
                    "score": score
                })

        return results


class AppleMusicMatcher:
    """Apple Music 匹配器"""

    def __init__(self):
        self.logger = get_logger()
        self.matcher = SongMatcher()

    def match_batch(
        self,
        songs: List[Dict[str, Any]],
        progress_callback=None
    ) -> ErrorResult:
        """
        批量匹配歌曲

        Args:
            songs: 歌曲列表
            progress_callback: 进度回调函数
        """
        results = []
        matched_count = 0
        failed_count = 0

        self.logger.info(f"开始匹配 {len(songs)} 首歌曲")

        for idx, song in enumerate(songs):
            if progress_callback:
                progress_callback(idx, len(songs))

            # 模拟搜索候选（在真实环境调用 Apple Music API）
            candidates = self._search_apple_music(song)

            if not candidates:
                results.append(MatchResult(
                    original_song=song,
                    matched=False,
                    match_score=0.0,
                    error_code=ErrorCode.MATCH_NO_COPYRIGHT,
                    error_msg="Apple Music 无此歌曲版权"
                ))
                failed_count += 1
                continue

            match_result = self.matcher.match_song(song, candidates)

            results.append(match_result)
            if match_result.matched:
                matched_count += 1
            else:
                failed_count += 1

            # 避免限流控制
            if (idx + 1) % 10 == 0:
                time.sleep(0.5)

        return ErrorResult.success({
            "results": results,
            "matched_count": matched_count,
            "failed_count": failed_count,
            "total_count": len(songs)
        })

    def _search_apple_music(self, song: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        搜索 Apple Music（模拟实现）

        在真实环境中，这里应该调用 Apple Music Search API
        """
        # 模拟实现 - 真实环境下调用 Apple Music Search API
        # 这里返回一些示例数据
        return [
            {
                "title": song["title"],
                "artist": song["artist"],
                "album": "模拟专辑",
                "id": "123456"
            }
        ]
