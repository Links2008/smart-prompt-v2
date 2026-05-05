#!/usr/bin/env python3
"""
QQ音乐→Apple Music歌单迁移工具 - 批量版
后端批量搜索iTunes，生成Apple Music链接
"""
import sys
import asyncio
import aiohttp
from pathlib import Path
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

from qqmusic_api import QQMusicAPI
from data_cleaner import DataCleaner, Exporter

app = FastAPI(title="QQ音乐→Apple Music歌单迁移工具", version="6.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = Path(__file__).parent

class PlaylistRequest(BaseModel):
    url: str
    detailed: bool = False

class BatchSearchRequest(BaseModel):
    songs: List[Dict[str, str]]

@app.get("/")
async def root():
    index_path = BASE_DIR / "frontend" / "index.html"
    if index_path.exists():
        return FileResponse(index_path)
    return {"message": "QQ音乐→Apple Music歌单迁移工具", "version": "6.0.0", "docs": "/docs"}

@app.post("/api/qqmusic/playlist")
async def fetch_playlist(request: PlaylistRequest):
    try:
        api = QQMusicAPI()
        playlist = api.fetch_playlist(request.url)

        songs_data = []
        for song in playlist.songs:
            clean_name = DataCleaner.clean_song_name(song.name) if not request.detailed else song.name
            standard_song = DataCleaner.standardize(song.name, song.singer_name)
            songs_data.append({
                "original_name": song.name,
                "clean_name": clean_name,
                "singer": song.singer_name,
                "is_live": standard_song.is_live,
                "is_remix": standard_song.is_remix,
                "has_version_tag": standard_song.has_version_tag
            })

        return {"success": True, "data": {"name": playlist.name, "songs": songs_data, "total": len(songs_data)}}
    except Exception as e:
        print(f"错误: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=400, detail={"success": False, "error": str(e)})

@app.post("/api/search-itunes")
async def search_itunes(request: BatchSearchRequest):
    """批量搜索iTunes，返回Apple Music链接"""
    results = []
    
    async with aiohttp.ClientSession() as session:
        for i, song in enumerate(request.songs):
            song_name = song.get("name", "")
            singer = song.get("singer", "")
            search_term = f"{song_name} {singer}"
            
            try:
                url = f"https://itunes.apple.com/search?term={search_term}&media=music&entity=song&limit=1"
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
                                "artist_name": track.get("artistName", ""),
                                "preview_url": track.get("previewUrl", "")
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
            
            # 避免请求过快
            if i < len(request.songs) - 1:
                await asyncio.sleep(0.3)
    
    return {"success": True, "results": results}

@app.post("/api/export")
async def export_songs(request_data: Dict[str, Any]):
    try:
        format_type = request_data.get("format", "text")
        songs = request_data.get("songs", [])

        if format_type == "text":
            content = Exporter.export_text(songs)
        elif format_type == "csv":
            content = Exporter.export_csv(songs)
        else:
            raise ValueError("不支持的格式")

        return {"success": True, "format": format_type, "content": content}
    except Exception as e:
        raise HTTPException(status_code=400, detail={"success": False, "error": str(e)})

def create_frontend():
    html_content = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>QQ音乐→Apple Music歌单迁移</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        .container { max-width: 1200px; margin: 0 auto; }
        .header { text-align: center; color: white; margin-bottom: 40px; }
        .header h1 { font-size: 2.5rem; margin-bottom: 10px; text-shadow: 0 2px 10px rgba(0,0,0,0.2); }
        .card {
            background: white; border-radius: 16px; padding: 30px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.2); margin-bottom: 20px;
        }
        .input-group { display: flex; gap: 15px; margin-bottom: 20px; }
        input[type="text"] {
            flex: 1; padding: 15px 20px; border: 2px solid #e0e0e0; border-radius: 10px;
            font-size: 1rem; transition: border-color 0.3s;
        }
        input:focus { outline: none; border-color: #667eea; }
        button {
            padding: 15px 30px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white; border: none; border-radius: 10px; font-size: 1rem;
            font-weight: 600; cursor: pointer; transition: transform 0.2s, box-shadow 0.2s;
        }
        button:hover { transform: translateY(-2px); box-shadow: 0 5px 20px rgba(102,126,234,0.4); }
        button:disabled { opacity: 0.6; cursor: not-allowed; transform: none; }
        button.apple { background: linear-gradient(135deg, #fc3c44 0%, #fc3c44 100%); }
        button.apple:hover { background: linear-gradient(135deg, #d32f2f 0%, #d32f2f 100%); }
        .status { padding: 15px; border-radius: 10px; margin-bottom: 20px; }
        .status.success { background: #e8f5e9; color: #2e7d32; }
        .status.error { background: #ffebee; color: #c62828; }
        .status.info { background: #e3f2fd; color: #1565c0; }
        .song-list { max-height: 400px; overflow-y: auto; border: 1px solid #e0e0e0; border-radius: 10px; }
        .song-item {
            padding: 15px; border-bottom: 1px solid #f0f0f0; display: flex; justify-content: space-between; align-items: center;
        }
        .song-item:last-child { border-bottom: none; }
        .song-item:hover { background: #f8f9fa; }
        .song-info { flex: 1; }
        .song-title { font-weight: 600; color: #333; }
        .song-singer { color: #666; font-size: 0.9rem; margin-top: 4px; }
        .song-status { padding: 4px 12px; border-radius: 20px; font-size: 0.85rem; }
        .song-status.found { background: #e8f5e9; color: #2e7d32; }
        .song-status.not-found { background: #ffebee; color: #c62828; }
        .song-status.pending { background: #fff3e0; color: #ef6c00; }
        .tag { padding: 2px 8px; border-radius: 4px; font-size: 0.8rem; margin-left: 8px; }
        .tag-live { background: #fff3e0; color: #ef6c00; }
        .tag-remix { background: #e3f2fd; color: #1976d2; }
        .progress { margin: 20px 0; }
        .progress-bar { height: 8px; background: #e0e0e0; border-radius: 4px; overflow: hidden; }
        .progress-fill { height: 100%; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); transition: width 0.3s; }
        .progress-text { text-align: center; margin-top: 10px; color: #666; font-size: 0.9rem; }
        .stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 15px; margin-bottom: 20px; }
        .stat-card { background: #f8f9fa; padding: 20px; border-radius: 10px; text-align: center; }
        .stat-number { font-size: 2rem; font-weight: 700; color: #667eea; }
        .stat-label { color: #666; font-size: 0.9rem; margin-top: 5px; }
        .section { margin-bottom: 30px; }
        .section h2 { margin-bottom: 15px; color: #333; }
        .hidden { display: none; }
        .batch-section {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 30px; border-radius: 15px; margin-top: 20px; color: white;
        }
        .batch-section h3 { margin-bottom: 15px; }
        .batch-section p { margin-bottom: 20px; opacity: 0.9; }
        .batch-section button { background: white; color: #667eea; }
        .batch-section button:hover { background: #f0f4ff; }
        .tips { background: #fff3e0; padding: 20px; border-radius: 10px; margin-top: 20px; }
        .tips h3 { color: #ef6c00; margin-bottom: 10px; }
        .tips p { color: #5d4037; line-height: 1.8; }
        .tips a { color: #667eea; text-decoration: none; }
        .tips ol { margin-left: 20px; line-height: 1.8; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎵 QQ音乐→Apple Music歌单迁移</h1>
            <p>批量版 - 自动搜索并打开Apple Music</p>
        </div>

        <div class="card">
            <div class="section">
                <h2>步骤1: 获取QQ音乐歌单</h2>
                <div class="input-group">
                    <input type="text" id="qqmusicUrl" placeholder="粘贴QQ音乐歌单链接...">
                    <button id="fetchBtn" onclick="fetchPlaylist()">获取歌单</button>
                </div>
                <div id="statusContainer"></div>
            </div>

            <div id="statsContainer" class="hidden">
                <div class="stats">
                    <div class="stat-card">
                        <div id="totalSongs" class="stat-number">0</div>
                        <div class="stat-label">总歌曲</div>
                    </div>
                    <div class="stat-card">
                        <div id="foundSongs" class="stat-number">0</div>
                        <div class="stat-label">已找到</div>
                    </div>
                    <div class="stat-card">
                        <div id="notFoundSongs" class="stat-number">0</div>
                        <div class="stat-label">未找到</div>
                    </div>
                </div>
            </div>

            <div id="progressContainer" class="hidden">
                <div class="progress">
                    <div class="progress-bar">
                        <div id="progressFill" class="progress-fill" style="width: 0%"></div>
                    </div>
                    <div id="progressText" class="progress-text">准备中...</div>
                </div>
            </div>

            <div id="songListContainer" class="hidden">
                <h3 style="margin-bottom: 15px;">歌单内容</h3>
                <div id="songList" class="song-list"></div>
            </div>

            <div id="batchContainer" class="hidden">
                <div class="batch-section">
                    <h3>🚀 批量迁移到Apple Music</h3>
                    <p>点击下方按钮，系统会自动搜索所有歌曲并打开Apple Music页面</p>
                    <button onclick="batchSearchAndOpen()">
                        🔍 搜索所有歌曲并生成链接
                    </button>
                </div>

                <div id="openLinksContainer" class="hidden" style="margin-top: 20px;">
                    <h3 style="margin-bottom: 15px;">已找到的歌曲</h3>
                    <button class="apple" onclick="openAllLinks()" style="width: 100%; margin-bottom: 15px;">
                        🍎 一键打开所有Apple Music链接
                    </button>
                    <p style="color: #666; font-size: 0.9rem; margin-bottom: 15px;">
                        注意：此操作会打开多个标签页，请确保浏览器允许弹窗
                    </p>
                    <div id="linksList" style="max-height: 300px; overflow-y: auto; border: 1px solid #e0e0e0; border-radius: 10px; padding: 15px; background: #fafafa;"></div>
                </div>
            </div>

            <div class="tips">
                <h3>💡 使用说明</h3>
                <p><strong>推荐方式：批量自动迁移</strong></p>
                <ol>
                    <li>获取QQ音乐歌单</li>
                    <li>点击「搜索所有歌曲并生成链接」</li>
                    <li>等待搜索完成（约需1-2分钟）</li>
                    <li>点击「一键打开所有Apple Music链接」</li>
                    <li>在打开的页面中添加歌曲到您的歌单</li>
                </ol>
            </div>
        </div>
    </div>

    <script>
        let currentSongs = [];
        let searchResults = [];

        function showStatus(type, message) {
            const container = document.getElementById('statusContainer');
            container.innerHTML = `<div class="status ${type}">${message}</div>`;
        }

        function clearStatus() {
            document.getElementById('statusContainer').innerHTML = '';
        }

        async function fetchPlaylist() {
            const url = document.getElementById('qqmusicUrl').value.trim();
            const btn = document.getElementById('fetchBtn');

            if (!url) {
                showStatus('error', '请输入QQ音乐歌单链接');
                return;
            }

            btn.disabled = true;
            clearStatus();
            showStatus('info', '正在获取歌单...');

            try {
                const response = await fetch('/api/qqmusic/playlist', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ url, detailed: false })
                });

                const result = await response.json();

                if (!result.success) {
                    throw new Error(result.detail?.error || '获取歌单失败');
                }

                const data = result.data;
                currentSongs = data.songs;

                document.getElementById('statsContainer').classList.remove('hidden');
                document.getElementById('totalSongs').textContent = data.total;
                document.getElementById('foundSongs').textContent = '0';
                document.getElementById('notFoundSongs').textContent = '0';

                document.getElementById('songListContainer').classList.remove('hidden');
                renderSongList(data.songs);

                document.getElementById('batchContainer').classList.remove('hidden');

                clearStatus();
                showStatus('success', `成功获取歌单: ${data.name}，共${data.total}首歌曲`);

            } catch (error) {
                console.error('错误:', error);
                showStatus('error', error.message || '获取失败，请检查链接是否正确');
            } finally {
                btn.disabled = false;
            }
        }

        function renderSongList(songs) {
            const container = document.getElementById('songList');
            container.innerHTML = songs.map((song, idx) => {
                let tags = '';
                if (song.is_live) tags += '<span class="tag tag-live">Live</span>';
                if (song.is_remix) tags += '<span class="tag tag-remix">Remix</span>';

                const status = song.status || 'pending';
                let statusText = '';
                if (status === 'found') statusText = '<span class="song-status found">✓ 已找到</span>';
                else if (status === 'not-found') statusText = '<span class="song-status not-found">✗ 未找到</span>';
                else statusText = '<span class="song-status pending">等待搜索</span>';

                return `<div class="song-item">
                    <div class="song-info">
                        <div class="song-title">${idx+1}. ${escapeHtml(song.clean_name)}${tags}</div>
                        <div class="song-singer">${escapeHtml(song.singer)}</div>
                    </div>
                    ${statusText}
                </div>`;
            }).join('');
        }

        function escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }

        async function batchSearchAndOpen() {
            if (currentSongs.length === 0) {
                showStatus('error', '请先获取歌单');
                return;
            }

            document.getElementById('progressContainer').classList.remove('hidden');
            showStatus('info', '正在搜索歌曲...');

            try {
                const response = await fetch('/api/search-itunes', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ songs: currentSongs.map(s => ({ name: s.clean_name, singer: s.singer })) })
                });

                const result = await response.json();

                if (!result.success) {
                    throw new Error('搜索失败');
                }

                searchResults = result.results;

                // 更新歌曲状态
                let found = 0;
                let notFound = 0;
                searchResults.forEach((res, idx) => {
                    currentSongs[idx].status = res.found ? 'found' : 'not-found';
                    if (res.found) found++;
                    else notFound++;
                });

                document.getElementById('foundSongs').textContent = found;
                document.getElementById('notFoundSongs').textContent = notFound;
                renderSongList(currentSongs);

                // 显示链接列表
                renderLinksList(searchResults);
                document.getElementById('openLinksContainer').classList.remove('hidden');

                showStatus('success', `搜索完成！找到 ${found} 首，未找到 ${notFound} 首`);

            } catch (error) {
                console.error('搜索失败:', error);
                showStatus('error', '搜索失败: ' + error.message);
            } finally {
                document.getElementById('progressContainer').classList.add('hidden');
            }
        }

        function renderLinksList(results) {
            const container = document.getElementById('linksList');
            const foundSongs = results.filter(r => r.found);
            
            container.innerHTML = foundSongs.map((res, idx) => {
                return `<div class="song-item">
                    <div class="song-info">
                        <div class="song-title">${idx+1}. ${escapeHtml(res.track_name)}</div>
                        <div class="song-singer">${escapeHtml(res.artist_name)}</div>
                    </div>
                    <a href="${res.apple_music_url}" target="_blank" style="color: #667eea; text-decoration: none; font-size: 0.9rem;">
                        打开 →
                    </a>
                </div>`;
            }).join('');
        }

        function openAllLinks() {
            const foundSongs = searchResults.filter(r => r.found && r.apple_music_url);
            
            if (foundSongs.length === 0) {
                showStatus('error', '没有找到可打开的链接');
                return;
            }

            const confirmed = confirm(`即将打开 ${foundSongs.length} 个Apple Music页面\\n请确保浏览器允许弹窗\\n\\n是否继续？`);
            
            if (!confirmed) return;

            foundSongs.forEach((song, idx) => {
                setTimeout(() => {
                    window.open(song.apple_music_url, '_blank');
                }, idx * 500); // 每个链接间隔500ms
            });

            showStatus('success', `正在打开 ${foundSongs.length} 个Apple Music页面...`);
        }
    </script>
</body>
</html>
"""
    frontend_dir = BASE_DIR / "frontend"
    frontend_dir.mkdir(exist_ok=True)
    (frontend_dir / "index.html").write_text(html_content, encoding="utf-8")

if __name__ == "__main__":
    import uvicorn

    print("=" * 60)
    print("🎵 QQ音乐→Apple Music歌单迁移工具 - 批量版")
    print("=" * 60)
    print()
    print("🎉 后端批量搜索iTunes，一键打开所有链接")
    print("🌐 访问: http://localhost:8000")
    print("📚 文档: http://localhost:8000/docs")
    print()
    print("📋 功能特性:")
    print("  - ✅ QQ音乐官方API调用（含签名算法）")
    print("  - ✅ 后端批量搜索iTunes")
    print("  - ✅ 自动生成Apple Music链接")
    print("  - ✅ 一键打开所有链接")
    print("  - ✅ 支持公开歌单")
    print()
    print("=" * 60)

    if not (BASE_DIR / "frontend").exists():
        (BASE_DIR / "frontend").mkdir()
        create_frontend()
    elif not (BASE_DIR / "frontend" / "index.html").exists():
        create_frontend()

    uvicorn.run(app, host="0.0.0.0", port=8000)
