#!/usr/bin/env python3
"""
QQ音乐API调用模块 - 完全复刻GoMusic架构
"""
import re
import time
import json
import hashlib
import base64
import requests
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, asdict


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
    """QQ音乐签名算法"""

    @staticmethod
    def encrypt(param: str) -> str:
        """GoMusic的签名算法复刻"""
        # MD5哈希
        md5_hash = hashlib.md5(param.encode('utf-8')).hexdigest().upper()

        k1 = {
            "0": 0, "1": 1, "2": 2, "3": 3, "4": 4, "5": 5, "6": 6, "7": 7, "8": 8, "9": 9,
            "A": 10, "B": 11, "C": 12, "D": 13, "E": 14, "F": 15
        }
        l1 = [212, 45, 80, 68, 195, 163, 163, 203, 157, 220, 254, 91, 204, 79, 104, 6]
        t = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/="

        # 选择字符
        def select_chars(s: str, indices: List[int]) -> str:
            return "".join(s[i] for i in indices)

        t1 = select_chars(md5_hash, [21, 4, 9, 26, 16, 20, 27, 30])
        t3 = select_chars(md5_hash, [18, 11, 3, 2, 1, 7, 6, 25])

        ls2 = []
        for i in range(16):
            x1 = k1.get(md5_hash[i * 2])
            x2 = k1.get(md5_hash[i * 2 + 1])
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
    """QQ音乐API"""
    API_URL = "https://u6.y.qq.com/cgi-bin/musics.fcg?sign={}&_={}"

    @staticmethod
    def build_playlist_request(
        disstid: int,
        platform: str = "-1",
        song_begin: int = 0,
        song_num: int = 30
    ) -> str:
        """构建QQ音乐歌单请求"""
        request = {
            "req_0": {
                "module": "music.srfDissInfo.aiDissInfo",
                "method": "uniform_get_Dissinfo",
                "param": {
                    "disstid": disstid,
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
        return json.dumps(request, ensure_ascii=False)

    @staticmethod
    def extract_playlist_id(url: str) -> Optional[int]:
        """从URL中提取歌单ID"""
        # 检测短链接或分享链接
        if any(keyword in url for keyword in ["fcgi-bin", "c6.y.qq.com", "__="]):
            raise ValueError("检测到短链接/分享链接，请提供标准QQ音乐歌单链接")
        
        # 检测是否需要登录
        if any(keyword in url for keyword in ["login", "privacy", "private"]):
            raise ValueError("链接需要登录或为私密歌单，请提供公开可访问的歌单链接")
        
        # 匹配 playlist/数字
        playlist_match = re.search(r"playlist/(\d+)", url)
        if playlist_match:
            return int(playlist_match.group(1))

        # 匹配 id=数字
        id_match = re.search(r"id=(\d+)", url)
        if id_match:
            return int(id_match.group(1))

        # 最后检查是否为标准QQ音乐域名
        if "y.qq.com" not in url:
            raise ValueError("请提供有效的QQ音乐歌单链接")

        return None

    def fetch_playlist(
        self, url: str, max_songs: int = 3000
    ) -> Optional[QQMusicPlaylist]:
        """获取QQ音乐歌单"""
        disstid = self.extract_playlist_id(url)
        
        platforms = ["-1", "android", "iphone", "h5", "wxfshare"]

        for platform in platforms:
            try:
                result = self._try_fetch_playlist(
                    disstid, platform,
                    song_begin=0,
                    song_num=30
                )
                if result:
                    return result
            except Exception as e:
                print(f"平台 {platform} 失败: {e}")
                continue

        raise Exception("所有平台尝试均失败")

    def _try_fetch_playlist(
        self,
        disstid: int,
        platform: str,
        song_begin: int,
        song_num: int
    ) -> Optional[QQMusicPlaylist]:
        """尝试获取歌单"""
        # 构建请求
        param_str = self.build_playlist_request(
            disstid, platform,
            song_begin, song_num
        )
        sign = QQMusicSigner.encrypt(param_str)
        url = self.API_URL.format(sign, int(time.time() * 1000))

        # 发送请求
        response = requests.post(url, data=param_str.encode('utf-8'))
        response.raise_for_status()
        response_json = response.json()

        # 检查响应
        if response_json.get("code") != 0:
            return None

        # 解析歌单
        req0 = response_json.get("req_0", {})
        if req0.get("code") != 0:
            return None

        data = req0.get("data", {})
        dirinfo = data.get("dirinfo", {})
        songlist = data.get("songlist", [])

        songs = []
        for song in songlist:
            song_name = song.get("name", "未知")
            singers = song.get("singer", [])
            singer_names = [s.get("name", "未知") for s in singers]
            songs.append(QQMusicSong(song_name, singer_names))

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
        print(f"歌单: {playlist.name}")
        print(f"歌曲数量: {playlist.song_count}")
        print()
        for song in playlist.songs[:10]:
            print(f"{song.name} - {song.singer_name}")
    else:
        print("请提供QQ音乐歌单URL")
