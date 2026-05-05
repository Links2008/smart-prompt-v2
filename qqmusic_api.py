#!/usr/bin/env python3
"""
QQ音乐API调用模块 - 完全复刻GoMusic架构 + 完全调试修复 + 最终版
"""
import re
import time
import json
import hashlib
import requests
import urllib.parse
from typing import Optional, List, Dict, Any
from dataclasses import dataclass


@dataclass
class QQMusicSong:
    """QQ音乐歌曲"""
    name: str
    singer_names: List[str]

    @property
    def singer_name(self):
        return " / ".join(self.singer_names)


@dataclass
class QQMusicPlaylist:
    """QQ音乐歌单"""
    name: str
    songs: List[QQMusicSong]
    song_count: int


class QQMusicSigner:
    """QQ音乐签名算法 - 复刻GoMusic"""

    @staticmethod
    def encrypt(param: str) -> str:
        """复刻GoMusic的签名算法"""
        k1 = {
            "0": 0, "1": 1, "2": 2, "3": 3, "4": 4, "5": 5, "6": 6, "7": 7, "8": 8, "9": 9,
            "A": 10, "B": 11, "C": 12, "D": 13, "E": 14, "F": 15
        }
        l1 = [212, 45, 80, 68, 195, 163, 163, 203, 157, 220, 254, 91, 204, 79, 104, 6]
        t = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/="

        md5_hash = hashlib.md5(param.encode('utf-8')).hexdigest().upper()

        def select_chars(s: str, indices: List[int]) -> str:
            return "".join(s[i] for i in indices)

        t1 = select_chars(md5_hash, [21, 4, 9, 26, 16, 20, 27, 30])
        t3 = select_chars(md5_hash, [18, 11, 3, 2, 1, 7, 6, 25])

        ls2 = []
        for i in range(16):
            x1 = k1[md5_hash[i * 2]]
            x2 = k1[md5_hash[i * 2 + 1]]
            x3 = (x1 * 16 ^ x2) ^ l1[i]
            ls2.append(x3)

        ls3 = []
        for i in range(6):
            if i == 5:
                ls3.append(
                    t[ls2[-1] >> 2] +
                    t[(ls2[-1] & 3) << 4])
            else:
                x4 = ls2[i * 3] >> 2
                x5 = (ls2[i * 3 + 1] >> 4) ^ ((ls2[i * 3] & 3) << 4)
                x6 = (ls2[i * 3 + 2] >> 6) ^ ((ls2[i * 3 + 1] & 15) << 2)
                x7 = 63 & ls2[i * 3 + 2]
                ls3.append(t[x4] + t[x5] + t[x6] + t[x7])

        t2 = "".join(ls3)
        t2 = re.sub(r"[\/\+]", "", t2)
        sign = "zzb" + (t1 + t2 + t3).lower()
        return sign


class QQMusicAPI:
    """QQ音乐API - 完全复刻GoMusic + 调试优化 + 最终修复版"""

    API_URL = "https://u6.y.qq.com/cgi-bin/musics.fcg?sign={}&_={}"
    QQ_MUSIC_ERROR_RESPONSE_LENGTH = 108
    MAX_SONGS_PER_PAGE = 30
    MAX_TOTAL_SONGS = 10000

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 QQMusic/12.3.5"
        })

    @staticmethod
    def _try_extract_from_single_url(link: str) -> Optional[int]:
        """从单个URL中尝试所有提取方式（不访问网络）"""
        # 方式A：URL查询参数 id=
        try:
            parsed = urllib.parse.urlparse(link)
            params = urllib.parse.parse_qs(parsed.query)
            if "id" in params:
                tid = int(params["id"][0])
                return tid
        except:
            pass

        # 方式B：playlist/数字
        if re.search(r"playlist/\d+", link):
            tid = QQMusicAPI.extract_number_after_keyword(link, "playlist/")
            if tid:
                return tid

        # 方式C：id=数字（正则）
        id_match = re.search(r"id=(\d+)", link)
        if id_match:
            try:
                tid = int(id_match.group(1))
                return tid
            except:
                pass

        return None

    @staticmethod
    def extract_playlist_id(link: str) -> Optional[int]:
        """从QQ音乐链接中提取歌单ID - 最终修复版"""
        print(f"正在分析链接: {link}")

        # 1. 先尝试从当前URL直接提取
        tid = QQMusicAPI._try_extract_from_single_url(link)
        if tid:
            print(f"✅ 从当前URL提取到ID: {tid}")
            return tid

        # 2. 如果当前URL提取不到，尝试访问并获取重定向
        if "fcgi-bin" in link or "c6.y.qq.com" in link or "y.qq.com" in link:
            print(f"检测到QQ音乐链接，尝试完整访问...")
            try:
                response = requests.get(link, timeout=10, allow_redirects=True)
                print(f"   最终URL: {response.url}")
                print(f"   访问状态: {response.status_code}")

                # A. 从重定向后的URL再提取一次！（关键！）
                tid = QQMusicAPI._try_extract_from_single_url(response.url)
                if tid:
                    print(f"✅ 从重定向URL中提取到ID: {tid}")
                    return tid
            except Exception as e:
                print(f"   访问链接失败: {e}")

        return None

    @staticmethod
    def extract_number_after_keyword(s: str, keyword: str) -> Optional[int]:
        """从字符串中提取关键词后面的数字 - 复刻GoMusic"""
        index = s.find(keyword)
        if index < 0:
            return None

        start_index = index + len(keyword)
        end_index = len(s)

        for i in range(start_index, len(s)):
            if not s[i].isdigit():
                end_index = i
                break

        num_str = s[start_index:end_index]
        if not num_str:
            return None

        try:
            return int(num_str)
        except:
            return None

    @staticmethod
    def build_request(tid: int, platform: str = "-1", song_begin: int = 0, song_num: int = 30) -> str:
        """构建QQ音乐请求 - 复刻GoMusic"""
        req = {
            "req_0": {
                "module": "music.srfDissInfo.aiDissInfo",
                "method": "uniform_get_Dissinfo",
                "param": {
                    "disstid": tid,
                    "enc_host_uin": "",
                    "tag": 1,
                    "userinfo": 1,
                    "song_begin": song_begin,
                    "song_num": song_num
                }
            },
            "comm": {
                "g_tk": 5381,
                "uin": 0,
                "format": "json",
                "platform": platform
            }
        }
        return json.dumps(req, ensure_ascii=False)

    def fetch_playlist_page(self, tid: int, song_begin: int = 0, song_num: int = 30) -> Optional[bytes]:
        """获取歌单指定页数据 - 复刻GoMusic"""
        platforms = ["-1", "android", "iphone", "h5", "wxfshare", "iphone_wx", "windows"]

        for platform in platforms:
            param_string = QQMusicAPI.build_request(tid, platform, song_begin, song_num)
            sign = QQMusicSigner.encrypt(param_string)
            request_url = QQMusicAPI.API_URL.format(sign, int(time.time() * 1000))

            try:
                response = self.session.post(request_url, data=param_string.encode('utf-8'), timeout=30)
                response.raise_for_status()

                data = response.content

                if len(data) != QQMusicAPI.QQ_MUSIC_ERROR_RESPONSE_LENGTH:
                    print(f"✅ 平台 {platform} 请求成功")
                    return data

            except Exception as e:
                print(f"   平台 {platform} 请求失败: {e}")
                continue

        return None

    def fetch_playlist_data(self, tid: int) -> Optional[Dict[str, Any]]:
        """获取完整歌单数据（支持分页） - 复刻GoMusic"""
        basic_data = self.fetch_playlist_page(tid, 0, QQMusicAPI.MAX_SONGS_PER_PAGE)
        if not basic_data:
            return None

        try:
            basic_resp = json.loads(basic_data)
            total_songs = basic_resp.get("req_0", {}).get("data", {}).get("dirinfo", {}).get("songnum", 0)

            if total_songs <= QQMusicAPI.MAX_SONGS_PER_PAGE:
                return basic_resp

            if total_songs > QQMusicAPI.MAX_TOTAL_SONGS:
                total_songs = QQMusicAPI.MAX_TOTAL_SONGS

            page_count = (total_songs + QQMusicAPI.MAX_SONGS_PER_PAGE - 1) // QQMusicAPI.MAX_SONGS_PER_PAGE
            merged_resp = basic_resp.copy()
            merged_resp["req_0"]["data"]["dirinfo"]["songnum"] = total_songs

            for page in range(1, page_count):
                song_begin = page * QQMusicAPI.MAX_SONGS_PER_PAGE
                page_data = self.fetch_playlist_page(tid, song_begin, QQMusicAPI.MAX_SONGS_PER_PAGE)
                if page_data:
                    try:
                        page_resp = json.loads(page_data)
                        page_songs = page_resp.get("req_0", {}).get("data", {}).get("songlist", [])
                        merged_resp["req_0"]["data"]["songlist"].extend(page_songs)
                    except Exception as e:
                        print(f"解析第{page+1}页数据失败: {e}")

            merged_resp["req_0"]["data"]["dirinfo"]["songnum"] = len(
                merged_resp["req_0"]["data"]["songlist"]
            )
            return merged_resp

        except Exception as e:
            print(f"解析歌单数据失败: {e}")
            return None

    def fetch_playlist(self, link: str, detailed: bool = False) -> Optional[QQMusicPlaylist]:
        """获取QQ音乐歌单 - 完全复刻GoMusic"""
        tid = QQMusicAPI.extract_playlist_id(link)
        if not tid:
            raise ValueError(
                "无法从链接中提取歌单ID，请尝试以下方法：\n"
                "1. 使用QQ音乐网页版打开歌单，复制地址栏链接\n"
                "2. 链接格式类似：https://y.qq.com/n/ryqq/playlist/[歌单ID]"
            )

        print(f"开始获取歌单，ID: {tid}")
        response_data = self.fetch_playlist_data(tid)
        if not response_data:
            raise ValueError("获取QQ音乐歌单数据失败")

        req0 = response_data.get("req_0", {})
        if req0.get("code") != 0:
            raise ValueError("QQ音乐API返回错误")

        data = req0.get("data", {})
        dirinfo = data.get("dirinfo", {})
        songlist = data.get("songlist", [])

        songs = []
        for song in songlist:
            name = song.get("name", "未知")
            singers = song.get("singer", [])
            singer_names = [s.get("name", "未知") for s in singers]
            songs.append(QQMusicSong(name, singer_names))

        return QQMusicPlaylist(
            name=dirinfo.get("title", "未知歌单"),
            songs=songs,
            song_count=len(songs)
        )


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        url = sys.argv[1]
        api = QQMusicAPI()
        playlist = api.fetch_playlist(url)
        print(f"\n✅ 获取成功！")
        print(f"歌单: {playlist.name}")
        print(f"歌曲数量: {playlist.song_count}")
        print()
        for song in playlist.songs[:15]:
            print(f"  {song.name} - {song.singer_name}")
    else:
        print("请提供QQ音乐歌单链接")
