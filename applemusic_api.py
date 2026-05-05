#!/usr/bin/env python3
"""
Apple Music API集成模块
"""
import requests
from typing import List, Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class AppleMusicSong:
    """Apple Music歌曲"""
    id: str
    name: str
    artist: str
    album: str
    preview_url: Optional[str] = None


class AppleMusicAPI:
    """Apple Music API客户端"""

    BASE_URL = "https://api.music.apple.com/v1"

    def __init__(self, developer_token: str):
        self.developer_token = developer_token
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {developer_token}",
            "Content-Type": "application/json"
        })

    def search_song(self, song_name: str, artist: str, storefront: str = "cn") -> Optional[AppleMusicSong]:
        """搜索歌曲"""
        try:
            query = f"{song_name} {artist}"
            url = f"{self.BASE_URL}/catalog/{storefront}/search"
            params = {
                "term": query,
                "types": "songs",
                "limit": 5
            }

            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()

            data = response.json()
            songs = data.get("results", {}).get("songs", {}).get("data", [])

            if not songs:
                return None

            # 返回第一个匹配结果
            song_data = songs[0]
            attributes = song_data.get("attributes", {})

            return AppleMusicSong(
                id=song_data.get("id"),
                name=attributes.get("name", ""),
                artist=attributes.get("artistName", ""),
                album=attributes.get("albumName", ""),
                preview_url=attributes.get("previews", [{}])[0].get("url") if attributes.get("previews") else None
            )

        except Exception as e:
            print(f"搜索歌曲失败: {e}")
            return None

    def search_songs_batch(self, songs: List[Dict[str, str]], storefront: str = "cn") -> List[Dict[str, Any]]:
        """批量搜索歌曲"""
        results = []

        for i, song in enumerate(songs, 1):
            song_name = song.get("name", "")
            artist = song.get("singer", "")

            print(f"[{i}/{len(songs)}] 搜索: {song_name} - {artist}")

            apple_song = self.search_song(song_name, artist, storefront)

            if apple_song:
                results.append({
                    "original": song,
                    "apple_music": {
                        "id": apple_song.id,
                        "name": apple_song.name,
                        "artist": apple_song.artist,
                        "album": apple_song.album
                    },
                    "matched": True
                })
            else:
                results.append({
                    "original": song,
                    "apple_music": None,
                    "matched": False
                })

        return results


if __name__ == "__main__":
    print("Apple Music API模块")
    print("请在Web界面中使用此功能")
