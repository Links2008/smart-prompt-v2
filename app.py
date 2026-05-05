#!/usr/bin/env python3
"""
QQ音乐→Apple Music歌单迁移工具 - 极简版
直接复制歌曲列表，手动搜索
"""
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

from qqmusic_api import QQMusicAPI
from data_cleaner import DataCleaner, Exporter

app = FastAPI(title="QQ音乐→Apple Music歌单迁移工具", version="5.0.0")

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

@app.get("/")
async def root():
    index_path = BASE_DIR / "frontend" / "index.html"
    if index_path.exists():
        return FileResponse(index_path)
    return {"message": "QQ音乐→Apple Music歌单迁移工具", "version": "5.0.0", "docs": "/docs"}

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
        .status { padding: 15px; border-radius: 10px; margin-bottom: 20px; }
        .status.success { background: #e8f5e9; color: #2e7d32; }
        .status.error { background: #ffebee; color: #c62828; }
        .status.info { background: #e3f2fd; color: #1565c0; }
        .song-list { max-height: 400px; overflow-y: auto; border: 1px solid #e0e0e0; border-radius: 10px; padding: 15px; background: #fafafa; }
        .song-item {
            padding: 10px; border-bottom: 1px solid #e0e0e0; cursor: pointer;
            transition: background 0.2s;
        }
        .song-item:last-child { border-bottom: none; }
        .song-item:hover { background: #e3f2fd; }
        .song-item.selected { background: #e8f5e9; }
        .song-title { font-weight: 600; color: #333; }
        .song-singer { color: #666; font-size: 0.9rem; margin-top: 4px; }
        .tag { padding: 2px 8px; border-radius: 4px; font-size: 0.8rem; margin-left: 8px; }
        .tag-live { background: #fff3e0; color: #ef6c00; }
        .tag-remix { background: #e3f2fd; color: #1976d2; }
        .export-section {
            background: #f8f9fa; padding: 25px; border-radius: 10px; margin-top: 20px;
        }
        .export-section h3 { margin-bottom: 15px; color: #333; }
        .export-buttons { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin-bottom: 20px; }
        .export-btn {
            padding: 15px; background: white; color: #333; border: 2px solid #e0e0e0;
            border-radius: 10px; text-align: center; font-weight: 500; cursor: pointer;
            transition: all 0.2s;
        }
        .export-btn:hover { border-color: #667eea; background: #f0f4ff; }
        .export-btn.primary { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border: none; }
        textarea {
            width: 100%; min-height: 250px; padding: 15px; border: 1px solid #e0e0e0;
            border-radius: 10px; font-family: 'Courier New', monospace; font-size: 14px;
            resize: vertical; background: white;
        }
        .copy-btn {
            width: 100%; margin-top: 10px; background: #fc3c44;
        }
        .copy-btn:hover { background: #d32f2f; }
        .tips { background: #fff3e0; padding: 20px; border-radius: 10px; margin-top: 20px; }
        .tips h3 { color: #ef6c00; margin-bottom: 10px; }
        .tips p { color: #5d4037; line-height: 1.8; }
        .tips a { color: #667eea; text-decoration: none; }
        .tips ol { margin-left: 20px; line-height: 1.8; }
        .stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 15px; margin-bottom: 20px; }
        .stat-card { background: #f8f9fa; padding: 20px; border-radius: 10px; text-align: center; }
        .stat-number { font-size: 2rem; font-weight: 700; color: #667eea; }
        .stat-label { color: #666; font-size: 0.9rem; margin-top: 5px; }
        .section { margin-bottom: 30px; }
        .section h2 { margin-bottom: 15px; color: #333; }
        .hidden { display: none; }
        .search-tip {
            background: #e3f2fd; padding: 15px; border-radius: 10px; margin-top: 15px;
            border-left: 4px solid #2196f3;
        }
        .search-tip p { color: #1565c0; margin: 5px 0; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎵 QQ音乐→Apple Music歌单迁移</h1>
            <p>极简版 - 快速导出歌曲列表</p>
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
                        <div id="liveCount" class="stat-number">0</div>
                        <div class="stat-label">Live版本</div>
                    </div>
                    <div class="stat-card">
                        <div id="remixCount" class="stat-number">0</div>
                        <div class="stat-label">Remix版本</div>
                    </div>
                </div>
            </div>

            <div id="songListContainer" class="hidden">
                <h3 style="margin-bottom: 15px;">歌单内容（点击歌曲可复制搜索词）</h3>
                <div id="songList" class="song-list"></div>
                <div class="search-tip">
                    <p><strong>💡 快速搜索技巧：</strong></p>
                    <p>• 点击任意歌曲，自动复制"歌名 歌手"到剪贴板</p>
                    <p>• 然后在Apple Music中按 Cmd/Ctrl+V 粘贴搜索</p>
                </div>
            </div>

            <div id="exportContainer" class="hidden">
                <div class="export-section">
                    <h3>步骤2: 导出歌曲列表</h3>
                    <div class="export-buttons">
                        <button class="export-btn primary" onclick="exportSongs('text')">
                            📝 导出完整列表
                        </button>
                        <button class="export-btn" onclick="exportSongs('csv')">
                            📊 导出CSV格式
                        </button>
                    </div>
                    <div id="exportResultContainer" class="hidden">
                        <textarea id="exportResult" readonly placeholder="导出结果将显示在这里..."></textarea>
                        <button class="copy-btn" onclick="copyToClipboard()">
                            📋 复制到剪贴板
                        </button>
                    </div>
                </div>
            </div>

            <div class="tips">
                <h3>💡 使用说明</h3>
                <p><strong>推荐方式：使用第三方迁移工具</strong></p>
                <ol>
                    <li>点击「导出完整列表」按钮</li>
                    <li>点击「复制到剪贴板」</li>
                    <li>前往 <a href="https://www.tunemymusic.com" target="_blank">TuneMyMusic</a> 或 <a href="https://spotlistr.com" target="_blank">Spotlistr</a></li>
                    <li>选择「任意文本」→ 粘贴 → 选择Apple Music作为目标</li>
                    <li>工具会自动匹配并创建歌单</li>
                </ol>
                <br>
                <p><strong>手动方式：逐首搜索</strong></p>
                <ol>
                    <li>点击歌单中的任意歌曲</li>
                    <li>自动复制搜索词到剪贴板</li>
                    <li>在Apple Music中粘贴搜索</li>
                    <li>添加到您的歌单</li>
                </ol>
            </div>
        </div>
    </div>

    <script>
        let currentSongs = [];

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

                const liveCount = data.songs.filter(s => s.is_live).length;
                const remixCount = data.songs.filter(s => s.is_remix).length;

                document.getElementById('liveCount').textContent = liveCount;
                document.getElementById('remixCount').textContent = remixCount;

                document.getElementById('songListContainer').classList.remove('hidden');
                renderSongList(data.songs);

                document.getElementById('exportContainer').classList.remove('hidden');

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

                return `<div class="song-item" onclick="copySongSearch('${escapeHtml(song.clean_name)}', '${escapeHtml(song.singer)}', this)">
                    <div class="song-title">${idx+1}. ${escapeHtml(song.clean_name)}${tags}</div>
                    <div class="song-singer">${escapeHtml(song.singer)}</div>
                </div>`;
            }).join('');
        }

        function escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }

        function copySongSearch(songName, singer, element) {
            const searchText = `${songName} ${singer}`;
            
            navigator.clipboard.writeText(searchText).then(() => {
                // 移除其他选中状态
                document.querySelectorAll('.song-item').forEach(item => item.classList.remove('selected'));
                // 添加选中状态
                element.classList.add('selected');
                
                showStatus('success', `已复制: ${searchText}`);
                
                // 3秒后清除提示
                setTimeout(() => {
                    clearStatus();
                }, 3000);
            }).catch(err => {
                console.error('复制失败:', err);
                showStatus('error', '复制失败，请手动复制');
            });
        }

        async function exportSongs(format) {
            try {
                const response = await fetch('/api/export', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        format,
                        songs: currentSongs.map(s => ({ name: s.clean_name, singer: s.singer }))
                    })
                });

                const result = await response.json();

                if (!result.success) {
                    throw new Error(result.detail?.error || '导出失败');
                }

                document.getElementById('exportResultContainer').classList.remove('hidden');
                document.getElementById('exportResult').value = result.content;

                showStatus('success', '导出成功！点击下方按钮复制');

            } catch (error) {
                showStatus('error', error.message || '导出失败');
            }
        }

        function copyToClipboard() {
            const textarea = document.getElementById('exportResult');
            textarea.select();
            document.execCommand('copy');
            showStatus('success', '已复制到剪贴板！现在可以去TuneMyMusic粘贴了');
        }

        document.getElementById('qqmusicUrl').addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                fetchPlaylist();
            }
        });
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
    print("🎵 QQ音乐→Apple Music歌单迁移工具 - 极简版")
    print("=" * 60)
    print()
    print("🎉 快速导出歌曲列表，一键复制")
    print("🌐 访问: http://localhost:8000")
    print("📚 文档: http://localhost:8000/docs")
    print()
    print("📋 功能特性:")
    print("  - ✅ QQ音乐官方API调用（含签名算法）")
    print("  - ✅ 数据清洗与标准化")
    print("  - ✅ 点击歌曲自动复制搜索词")
    print("  - ✅ 一键导出完整列表")
    print("  - ✅ 支持TuneMyMusic导入")
    print("  - ✅ 支持公开歌单")
    print()
    print("=" * 60)

    if not (BASE_DIR / "frontend").exists():
        (BASE_DIR / "frontend").mkdir()
        create_frontend()
    elif not (BASE_DIR / "frontend" / "index.html").exists():
        create_frontend()

    uvicorn.run(app, host="0.0.0.0", port=8000)
