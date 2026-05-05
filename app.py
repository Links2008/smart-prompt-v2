#!/usr/bin/env python3
"""
QQ音乐→Apple Music歌单迁移工具 - 最终修复版
"""
import sys
import asyncio
import aiohttp
import urllib.parse
from pathlib import Path
from typing import List, Dict, Any
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from fastapi import Request
from qqmusic_api import QQMusicAPI
from data_cleaner import DataCleaner

app = FastAPI(title="QQ音乐→Apple Music歌单迁移工具", version="8.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = Path(__file__).parent


class PlaylistRequest(BaseModel):
    url: str = ""

class SearchRequest(BaseModel):
    songs: list = []


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    return JSONResponse(
        status_code=400,
        content={"success": False, "error": str(exc)}
    )

@app.get("/")
async def root():
    html = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>QQ音乐→Apple Music歌单迁移</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        .container { max-width: 1000px; margin: 0 auto; }
        .header { text-align: center; color: white; margin-bottom: 30px; }
        .header h1 { font-size: 2rem; margin-bottom: 10px; }
        .card {
            background: white; border-radius: 12px; padding: 25px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.2);
        }
        .input-group { display: flex; gap: 10px; margin-bottom: 15px; }
        input {
            flex: 1; padding: 12px 15px; border: 2px solid #e0e0e0;
            border-radius: 8px; font-size: 1rem;
        }
        input:focus { outline: none; border-color: #667eea; }
        button {
            padding: 12px 25px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white; border: none; border-radius: 8px; font-size: 1rem;
            font-weight: 600; cursor: pointer;
        }
        button:hover { opacity: 0.9; }
        button:disabled { opacity: 0.5; cursor: not-allowed; }
        .status { padding: 12px; border-radius: 8px; margin-bottom: 15px; }
        .status.success { background: #e8f5e9; color: #2e7d32; }
        .status.error { background: #ffebee; color: #c62828; }
        .status.info { background: #e3f2fd; color: #1565c0; }
        .stats { display: flex; gap: 15px; margin-bottom: 15px; }
        .stat-card { flex: 1; background: #f8f9fa; padding: 15px; border-radius: 8px; text-align: center; }
        .stat-number { font-size: 1.8rem; font-weight: 700; color: #667eea; }
        .stat-label { color: #666; font-size: 0.85rem; margin-top: 5px; }
        .song-list { max-height: 300px; overflow-y: auto; border: 1px solid #e0e0e0; border-radius: 8px; }
        .song-item { padding: 10px; border-bottom: 1px solid #f0f0f0; }
        .song-item:last-child { border-bottom: none; }
        .song-title { font-weight: 600; color: #333; font-size: 0.95rem; }
        .song-singer { color: #666; font-size: 0.85rem; margin-top: 3px; }
        .tag { padding: 2px 6px; border-radius: 3px; font-size: 0.75rem; margin-left: 6px; }
        .tag-live { background: #fff3e0; color: #ef6c00; }
        .tag-remix { background: #e3f2fd; color: #1976d2; }
        .song-status { padding: 3px 10px; border-radius: 12px; font-size: 0.8rem; }
        .song-status.found { background: #e8f5e9; color: #2e7d32; }
        .song-status.not-found { background: #ffebee; color: #c62828; }
        .song-status.pending { background: #fff3e0; color: #ef6c00; }
        .progress { margin: 15px 0; }
        .progress-bar { height: 6px; background: #e0e0e0; border-radius: 3px; overflow: hidden; }
        .progress-fill { height: 100%; background: #667eea; transition: width 0.3s; }
        .progress-text { text-align: center; margin-top: 8px; color: #666; font-size: 0.85rem; }
        .batch-section { background: #f8f9fa; padding: 20px; border-radius: 8px; margin-top: 15px; }
        .batch-section h3 { margin-bottom: 10px; }
        .batch-section p { margin-bottom: 15px; color: #666; }
        .tips { background: #fff3e0; padding: 15px; border-radius: 8px; margin-top: 15px; font-size: 0.9rem; }
        .tips h3 { color: #ef6c00; margin-bottom: 8px; }
        .tips ol { margin-left: 20px; line-height: 1.6; }
        .hidden { display: none; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎵 QQ音乐→Apple Music歌单迁移</h1>
            <p>批量自动搜索并打开Apple Music</p>
        </div>

        <div class="card">
            <div class="input-group">
                <input type="text" id="urlInput" placeholder="粘贴QQ音乐歌单链接...">
                <button id="fetchBtn" onclick="fetchPlaylist()">获取歌单</button>
            </div>
            <div id="statusDiv"></div>

            <div id="statsDiv" class="hidden">
                <div class="stats">
                    <div class="stat-card">
                        <div id="totalNum" class="stat-number">0</div>
                        <div class="stat-label">总歌曲</div>
                    </div>
                    <div class="stat-card">
                        <div id="foundNum" class="stat-number">0</div>
                        <div class="stat-label">已找到</div>
                    </div>
                    <div class="stat-card">
                        <div id="notFoundNum" class="stat-number">0</div>
                        <div class="stat-label">未找到</div>
                    </div>
                </div>
            </div>

            <div id="progressDiv" class="hidden">
                <div class="progress">
                    <div class="progress-bar">
                        <div id="progressFill" class="progress-fill" style="width: 0%"></div>
                    </div>
                    <div id="progressText" class="progress-text">准备中...</div>
                </div>
            </div>

            <div id="songsDiv" class="hidden">
                <h3 style="margin-bottom: 10px;">歌单内容</h3>
                <div id="songsList" class="song-list"></div>
            </div>

            <div id="batchDiv" class="hidden">
                <div class="batch-section">
                    <h3>🚀 批量迁移</h3>
                    <p>点击按钮自动搜索所有歌曲并生成Apple Music链接</p>
                    <button id="searchBtn" onclick="startSearch()" style="width: 100%;">🔍 开始搜索</button>
                </div>
            </div>

            <div id="linksDiv" class="hidden" style="margin-top: 15px;">
                <button onclick="openAllLinks()" style="width: 100%; background: #fc3c44;">
                    🍎 一键打开所有Apple Music链接
                </button>
                <p style="color: #999; font-size: 0.85rem; margin-top: 8px; text-align: center;">
                    会打开多个标签页，请允许浏览器弹窗
                </p>
            </div>

            <div class="tips">
                <h3>💡 使用说明</h3>
                <ol>
                    <li>粘贴QQ音乐歌单链接，点击「获取歌单」</li>
                    <li>点击「开始搜索」，等待搜索完成（约3-5分钟）</li>
                    <li>点击「一键打开所有Apple Music链接」</li>
                    <li>在每个页面中添加歌曲到您的歌单</li>
                </ol>
            </div>
        </div>
    </div>

    <script>
        let songs = [];
        let results = [];

        function showStatus(type, msg) {
            document.getElementById('statusDiv').innerHTML = '<div class="status ' + type + '">' + msg + '</div>';
        }

        function clearStatus() {
            document.getElementById('statusDiv').innerHTML = '';
        }

        async function fetchPlaylist() {
            const url = document.getElementById('urlInput').value.trim();
            if (!url) {
                showStatus('error', '请输入QQ音乐歌单链接');
                return;
            }

            // 检查URL格式
            if (!url.includes('qq.com')) {
                showStatus('error', '请输入有效的QQ音乐歌单链接');
                return;
            }

            const btn = document.getElementById('fetchBtn');
            btn.disabled = true;
            showStatus('info', '正在获取歌单...');

            try {
                const res = await fetch('/api/qqmusic/playlist', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ url: url })
                });

                const data = await res.json();

                if (!data.success) {
                    throw new Error(data.error || '获取失败');
                }

                songs = data.data.songs;
                
                document.getElementById('statsDiv').classList.remove('hidden');
                document.getElementById('totalNum').textContent = data.data.total;
                document.getElementById('foundNum').textContent = '0';
                document.getElementById('notFoundNum').textContent = '0';

                document.getElementById('songsDiv').classList.remove('hidden');
                renderSongs(songs);

                document.getElementById('batchDiv').classList.remove('hidden');

                showStatus('success', '成功获取: ' + data.data.name + '，共' + data.data.total + '首');

            } catch (e) {
                console.error(e);
                showStatus('error', e.message || '获取失败');
            } finally {
                btn.disabled = false;
            }
        }

        function renderSongs(sgs) {
            let html = '';
            for (let i = 0; i < sgs.length; i++) {
                const s = sgs[i];
                let tags = '';
                if (s.is_live) tags += '<span class="tag tag-live">Live</span>';
                if (s.is_remix) tags += '<span class="tag tag-remix">Remix</span>';

                let status = '';
                if (s.status === 'found') status = '<span class="song-status found">✓</span>';
                else if (s.status === 'not-found') status = '<span class="song-status not-found">✗</span>';
                else status = '<span class="song-status pending">○</span>';

                html += '<div class="song-item">' +
                    '<div class="song-title">' + (i+1) + '. ' + s.clean_name + tags + ' ' + status + '</div>' +
                    '<div class="song-singer">' + s.singer + '</div>' +
                '</div>';
            }
            document.getElementById('songsList').innerHTML = html;
        }

        async function startSearch() {
            if (songs.length === 0) {
                showStatus('error', '请先获取歌单');
                return;
            }

            const btn = document.getElementById('searchBtn');
            btn.disabled = true;
            document.getElementById('progressDiv').classList.remove('hidden');
            showStatus('info', '正在搜索...');

            try {
                const res = await fetch('/api/search-itunes', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ songs: songs.map(function(s) { return { name: s.clean_name, singer: s.singer }; }) })
                });

                const data = await res.json();

                if (!data.success) {
                    throw new Error(data.error || '搜索失败');
                }

                results = data.results;

                let found = 0;
                let notFound = 0;
                for (let i = 0; i < results.length; i++) {
                    const r = results[i];
                    songs[i].status = r.found ? 'found' : 'not-found';
                    if (r.found) found++;
                    else notFound++;
                }

                document.getElementById('foundNum').textContent = found;
                document.getElementById('notFoundNum').textContent = notFound;
                renderSongs(songs);

                document.getElementById('linksDiv').classList.remove('hidden');

                showStatus('success', '搜索完成！找到' + found + '首，未找到' + notFound + '首');

            } catch (e) {
                console.error(e);
                showStatus('error', '搜索失败: ' + e.message);
            } finally {
                btn.disabled = false;
                document.getElementById('progressDiv').classList.add('hidden');
            }
        }

        function openAllLinks() {
            const found = results.filter(function(r) { return r.found && r.apple_music_url; });
            if (found.length === 0) {
                showStatus('error', '没有可打开的链接');
                return;
            }

            if (!confirm('即将打开' + found.length + '个页面，是否继续？')) return;

            for (let i = 0; i < found.length; i++) {
                const s = found[i];
                setTimeout(function() {
                    window.open(s.apple_music_url, '_blank');
                }, i * 500);
            }

            showStatus('success', '正在打开' + found.length + '个页面...');
        }

        document.getElementById('urlInput').addEventListener('keypress', function(e) {
            if (e.key === 'Enter') fetchPlaylist();
        });
    </script>
</body>
</html>
"""
    return HTMLResponse(content=html)

@app.post("/api/qqmusic/playlist")
async def fetch_playlist(request: PlaylistRequest):
    try:
        url = request.url
        if not url:
            raise ValueError("请提供QQ音乐歌单链接")
        
        api = QQMusicAPI()
        playlist = api.fetch_playlist(url)

        songs_data = []
        for song in playlist.songs:
            clean_name = DataCleaner.clean_song_name(song.name)
            standard_song = DataCleaner.standardize(song.name, song.singer_name)
            songs_data.append({
                "original_name": song.name,
                "clean_name": clean_name,
                "singer": song.singer_name,
                "is_live": standard_song.is_live,
                "is_remix": standard_song.is_remix
            })

        return {"success": True, "data": {"name": playlist.name, "songs": songs_data, "total": len(songs_data)}}
    except Exception as e:
        print(f"错误: {e}")
        import traceback
        traceback.print_exc()
        return {"success": False, "error": str(e)}

@app.post("/api/search-itunes")
async def search_itunes(request: SearchRequest):
    """批量搜索iTunes，返回Apple Music链接"""
    try:
        songs = request.songs
        results = []
        
        async with aiohttp.ClientSession() as session:
            for i, song in enumerate(songs):
                song_name = song.get("name", "")
                singer = song.get("singer", "")
                search_term = f"{song_name} {singer}"
                
                try:
                    url = f"https://itunes.apple.com/search?term={urllib.parse.quote(search_term)}&media=music&entity=song&limit=1"
                    async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                        if response.status == 200:
                            data = await response.json()
                            if data.get("results") and len(data["results"]) > 0:
                                track = data["results"][0]
                                results.append({
                                    "original": song,
                                    "found": True,
                                    "apple_music_url": track.get("trackViewUrl", ""),
                                    "track_name": track.get("trackName", ""),
                                    "artist_name": track.get("artistName", "")
                                })
                            else:
                                results.append({
                                    "original": song,
                                    "found": False,
                                    "apple_music_url": "",
                                    "error": "未找到"
                                })
                        else:
                            results.append({
                                "original": song,
                                "found": False,
                                "apple_music_url": "",
                                "error": f"HTTP {response.status}"
                            })
                except Exception as e:
                    results.append({
                        "original": song,
                        "found": False,
                        "apple_music_url": "",
                        "error": str(e)
                    })
                
                if i < len(songs) - 1:
                    await asyncio.sleep(0.3)
        
        return {"success": True, "results": results}
    except Exception as e:
        print(f"搜索错误: {e}")
        import traceback
        traceback.print_exc()
        return {"success": False, "error": str(e)}

if __name__ == "__main__":
    import uvicorn
    from fastapi.responses import HTMLResponse

    print("=" * 60)
    print("🎵 QQ音乐→Apple Music歌单迁移工具 - 最终修复版")
    print("=" * 60)
    print()
    print("🌐 访问: http://localhost:8000")
    print()
    uvicorn.run(app, host="0.0.0.0", port=8000)
