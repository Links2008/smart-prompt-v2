import re
import time
import random
from typing import Optional, List, Dict, Any
from urllib.parse import urlparse, parse_qs

import requests
from bs4 import BeautifulSoup

from .errors import ErrorCode, ErrorResult
from .logger import get_logger


class QQMusicScraper:
    """QQ 音乐歌单抓取器"""

    def __init__(self):
        self.logger = get_logger()
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        })

    def _get_playlist_id(self, url: str) -> Optional[str]:
        """从 QQ 音乐链接提取歌单 ID"""
        try:
            parsed = urlparse(url)
            if "y.qq.com" not in parsed.netloc:
                return None

            query_params = parse_qs(parsed.query)
            if "id" in query_params:
                return query_params["id"][0]

            path_match = re.search(r"/playlist/(\d+)", parsed.path)
            if path_match:
                return path_match.group(1)

            return None
        except Exception as e:
            self.logger.error(f"提取歌单 ID 失败: {e}", exc_info=True)
            return None

    def _request_with_retry(
        self,
        url: str,
        method: str = "GET",
        max_retries: int = 3,
        **kwargs
    ) -> ErrorResult:
        """
        带重试机制的网络请求

        Args:
            url: 请求 URL
            method: HTTP 方法
            max_retries: 最大重试次数
            **kwargs: 其他 requests 参数

        Returns:
            ErrorResult: 统一错误结果
        """
        retry_delays = [1, 2, 5]  # 重试间隔
        last_error = None

        for attempt in range(max_retries):
            try:
                if attempt > 0:
                    delay = retry_delays[min(attempt - 1, len(retry_delays) - 1)]
                    self.logger.info(f"重试第 {attempt} 次，等待 {delay}s...")
                    time.sleep(delay)

                response = self.session.request(method, url, timeout=30, **kwargs)

                # 处理限流
                if response.status_code == 429:
                    retry_after = response.headers.get("Retry-After")
                    if retry_after:
                        try:
                            wait_time = int(retry_after)
                            self.logger.warning(f"限流触发，等待 {wait_time}s...")
                            time.sleep(wait_time)
                        except ValueError:
                            pass
                    raise Exception("触发限流 (429)")

                if response.status_code in [503, 500]:
                    raise Exception(f"服务端错误 ({response.status_code})")

                if not response.ok:
                    raise Exception(f"HTTP 错误 ({response.status_code})")

                return ErrorResult.success({"response": response})

            except requests.Timeout:
                self.logger.warning(f"请求超时 (尝试 {attempt + 1}/{max_retries})")
                last_error = ErrorCode.NETWORK_TIMEOUT
            except requests.ConnectionError:
                self.logger.warning(f"连接失败 (尝试 {attempt + 1}/{max_retries})")
                last_error = ErrorCode.NETWORK_CONNECTION_FAILED
            except Exception as e:
                self.logger.warning(f"请求失败 (尝试 {attempt + 1}/{max_retries}): {e}")
                if "限流" in str(e):
                    last_error = ErrorCode.NETWORK_RATE_LIMITED
                elif "私密" in str(e) or "403" in str(e):
                    last_error = ErrorCode.NETWORK_PAGE_PRIVATE
                else:
                    last_error = ErrorCode.NETWORK_CONNECTION_FAILED

        # 所有重试都失败
        error_msg = self._get_error_message(last_error)
        return ErrorResult.failure(last_error, error_msg, {"url": url})

    def _get_error_message(self, error_code: ErrorCode) -> str:
        """获取人类可读的错误信息"""
        messages = {
            ErrorCode.NETWORK_TIMEOUT: "网络超时，请检查网络连接",
            ErrorCode.NETWORK_CONNECTION_FAILED: "无法连接到 QQ 音乐",
            ErrorCode.NETWORK_RATE_LIMITED: "请求过于频繁，请稍后再试",
            ErrorCode.NETWORK_PAGE_PRIVATE: "该歌单为私密歌单，无法读取",
            ErrorCode.NETWORK_PAGE_STRUCTURE_CHANGED: "QQ 音乐页面结构发生变化，请联系开发者更新"
        }
        return messages.get(error_code, "未知网络错误")

    def _parse_playlist_data(self, html: str, playlist_url: str) -> ErrorResult:
        """
        解析歌单 HTML 数据

        Args:
            html: 页面 HTML
            playlist_url: 原始歌单链接（用于错误记录）

        Returns:
            ErrorResult: 解析结果
        """
        try:
            soup = BeautifulSoup(html, "lxml")
            songs = []

            # 尝试多种选择器解析歌曲
            song_elements = (
                soup.select(".songlist__item") or
                soup.select(".song-item") or
                soup.select("li[data-mid]")
            )

            if not song_elements:
                # 尝试从 script 标签提取 JSON 数据
                script_tags = soup.find_all("script")
                for script in script_tags:
                    if script.string and "window.__INITIAL_STATE__" in script.string:
                        # 尝试解析 JSON 数据（简化处理）
                        return self._parse_from_json(script.string, playlist_url)

                return ErrorResult.failure(
                    ErrorCode.NETWORK_PAGE_STRUCTURE_CHANGED,
                    "无法解析歌单页面，可能是页面结构已变化或歌单转为私密",
                    {"url": playlist_url, "snapshot": html[:500]}
                )

            for idx, element in enumerate(song_elements):
                try:
                    song = self._parse_single_song(element, idx)
                    if song:
                        songs.append(song)
                except Exception as e:
                    self.logger.warning(f"解析第 {idx} 首歌曲失败: {e}")
                    songs.append({
                        "title": "未知",
                        "artist": "未知",
                        "album": "未知",
                        "parse_failed": True
                    })

            return ErrorResult.success({
                "songs": songs,
                "total": len(songs)
            })

        except Exception as e:
            self.logger.error(f"解析歌单失败: {e}", exc_info=True)
            return ErrorResult.failure(
                ErrorCode.PARSE_STRUCTURE_CHANGED,
                "页面结构异常，解析失败",
                {"url": playlist_url, "error": str(e)}
            )

    def _parse_single_song(self, element, index: int) -> Optional[Dict[str, Any]]:
        """解析单个歌曲元素"""
        title = "未知"
        artist = "未知"
        album = "未知"

        # 尝试获取歌曲名
        title_elem = (
            element.select_one(".songlist__songname_txt") or
            element.select_one(".song-name") or
            element.select_one(".songtitle")
        )
        if title_elem:
            title = title_elem.get_text(strip=True)

        # 尝试获取歌手
        artist_elem = (
            element.select_one(".songlist__artist") or
            element.select_one(".singer-name") or
            element.select_one(".artist")
        )
        if artist_elem:
            artist = artist_elem.get_text(strip=True)

        # 尝试获取专辑
        album_elem = (
            element.select_one(".songlist__album") or
            element.select_one(".album-name")
        )
        if album_elem:
            album = album_elem.get_text(strip=True)

        # 特殊字符清理
        title = self._clean_text(title)
        artist = self._clean_text(artist)
        album = self._clean_text(album)

        # 关键字段为空的处理
        if not title or title == "未知":
            return None

        return {
            "id": index,
            "title": title,
            "artist": artist,
            "album": album
        }

    def _parse_from_json(self, script_content: str, playlist_url: str) -> ErrorResult:
        """从 JavaScript 中解析歌单数据（备用方案）"""
        try:
            # 简单提取示例（实际实现需要根据 QQ 音乐页面结构调整）
            songs = []

            # 简化处理，直接返回错误，因为主要方案已失败
            return ErrorResult.failure(
                ErrorCode.PARSE_STRUCTURE_CHANGED,
                "JSON 解析方案未实现，请使用主要解析方案",
                {"url": playlist_url}
            )

        except Exception as e:
            return ErrorResult.failure(
                ErrorCode.PARSE_INVALID_JSON,
                "JSON 解析失败",
                {"error": str(e)}
            )

    def _clean_text(self, text: str) -> str:
        """清理文本中的特殊字符"""
        if not text:
            return "未知"

        # 移除多余空白
        text = re.sub(r"\s+", " ", text).strip()

        # 移除不可见字符
        text = re.sub(r"[\x00-\x1f\x7f]", "", text)

        return text if text else "未知"

    def fetch_playlist(self, url: str) -> ErrorResult:
        """
        获取 QQ 音乐歌单

        Args:
            url: QQ 音乐歌单链接

        Returns:
            ErrorResult: 统一结果对象
        """
        self.logger.info(f"开始获取 QQ 音乐歌单: {url}")

        # 第一步：提取并验证歌单 ID
        playlist_id = self._get_playlist_id(url)
        if not playlist_id:
            return ErrorResult.failure(
                ErrorCode.NETWORK_PAGE_PRIVATE,
                "无法识别歌单链接，请确保是有效的 QQ 音乐歌单分享链接",
                {"url": url}
            )

        self.logger.info(f"歌单 ID: {playlist_id}")

        # 第二步：请求歌单页面
        request_result = self._request_with_retry(url)
        if not request_result.success:
            return request_result

        # 第三步：解析歌单数据
        html = request_result.error_data["response"].text
        parse_result = self._parse_playlist_data(html, url)

        if not parse_result.success:
            return parse_result

        # 返回成功结果
        data = parse_result.error_data
        self.logger.info(f"成功获取 {data['total']} 首歌曲")
        return parse_result
