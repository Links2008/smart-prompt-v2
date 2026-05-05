#!/usr/bin/env python3
"""
QQ音乐→Apple Music歌单迁移工具 - 完全复刻GoMusic架构 + Apple Music API集成
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

app = FastAPI(title="QQ音乐→Apple Music歌单迁移工具", version="3.0.0")

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

class AppleMusicSearchRequest(BaseModel):
    songs: List[Dict[str, str]]
    developer_token: str

@app.get("/")
async def root():
    index_path = BASE_DIR / "frontend" / "index.html"
    if index_path.exists():
        return FileResponse(index_path)
    return {"message": "QQ音乐→Apple Music歌单迁移工具", "version": "3.0.0", "docs": "/docs"}

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
    <script src="https://js-cdn.music.apple.com/musickit/v1/musickit.js"></script>
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
        input[type="text"], input[type="password"] {
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
        button.secondary { background: #f5f5f5; color: #333; }
        button.secondary:hover { background: #e0e0e0; box-shadow: none; }
        .status { padding: 15px; border-radius: 10px; margin-bottom: 20px; }
        .status.success { background: #e8f5e9; color: #2e7d32; }
        .status.error { background: #ffebee; color: #c62828; }
        .status.info { background: #e3f2fd; color: #1565c0; }
        .song-list { max-height: 400px; overflow-y: auto; }
        .song-item {
            display: flex; align-items: center; justify-content: space-between;
            padding: 15px; border-bottom: 1px solid #f0f0f0;
        }
        .song-item:last-child { border-bottom: none; }
        .song-info { flex: 1; }
        .song-title { font-weight: 600; color: #333; }
        .song-singer { color: #666; font-size: 0.9rem; margin-top: 4px; }
        .tag { padding: 2px 8px; border-radius: 4px; font-size: 0.8rem; margin-left: 8px; }
        .tag-live { background: #fff3e0; color: #ef6c00; }
        .tag-remix { background: #e3f2fd; color: #1976d2; }
        .tag-matched { background: #e8f5e9; color: #2e7d32; }
        .tag-failed { background: #ffebee; color: #c62828; }
        .export-options { display: flex; gap: 10px; margin-top: 20px; flex-wrap: wrap; }
        .export-btn {
            flex: 1; padding: 12px; background: #f5f5f5; color: #333; border-radius: 8px;
            text-align: center; font-weight: 500; transition: background 0.2s; cursor: pointer;
            min-width: 150px;
        }
        .export-btn:hover { background: #e0e0e0; }
        .export-btn.primary { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; }
        .tips { background: #fff3e0; padding: 20px; border-radius: 10px; margin-top: 20px; }
        .tips h3 { color: #ef6c00; margin-bottom: 10px; }
        .tips p { color: #5d4037; line-height: 1.6; }
        .tips a { color: #667eea; text-decoration: none; }
        .stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 15px; margin-bottom: 20px; }
        .stat-card { background: #f8f9fa; padding: 20px; border-radius: 10px; text-align: center; }
        .stat-number { font-size: 2rem; font-weight: 700; color: #667eea; }
        .stat-label { color: #666; font-size: 0.9rem; margin-top: 5px; }
        textarea {
            width: 100%; min-height: 200px; padding: 15px; border: 1px solid #e0e0e0;
            border-radius: 10px; font-family: monospace; resize: vertical;
        }
        .progress { margin-top: 20px; }
        .progress-bar {
            height: 20px; background: #e0e0e0; border-radius: 10px; overflow: hidden;
        }
        .progress-fill {
            height: 100%; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            transition: width 0.3s;
        }
        .progress-text { text-align: center; margin-top: 10px; color: #666; }
        .section { margin-bottom: 30px; }
        .section h2 { margin-bottom: 15px; color: #333; }
        .hidden { display: none; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎵 QQ音乐→Apple Music歌单迁移</h1>
            <p>完全复刻GoMusic架构 + Apple Music API直连</p>
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
                <h3 style="margin-bottom: 15px;">歌单内容</h3>
                <div id="songList" class="song-list"></div>
            </div>

            <div id="exportContainer" class="hidden">
                <div class="section">
                    <h2>步骤2: 选择迁移方式</h2>
                    <div class="export-options">
                        <button class="export-btn primary" onclick="migrateToAppleMusic()">
                            🍎 直接迁移到Apple Music
                        </button>
                        <button class="export-btn" onclick="exportSongs('text')">
                            📝 导出TuneMyMusic格式
                        </button>
                        <button class="export-btn" onclick="exportSongs('csv')">
                            📊 导出CSV格式
                        </button>
                    </div>
                </div>
            </div>

            <div id="appleMusicConfig" class="hidden">
                <div class="section">
                    <h2>Apple Music配置</h2>
                    <p style="margin-bottom: 15px; color: #666;">
                        需要Apple Music API Developer Token。
                        <a href="https://developer.apple.com/documentation/applemusicapi/getting_keys_and_creating_tokens" target="_blank">如何获取Token?</a>
                    </p>
                    <div class="input-group">
                        <input type="password" id="developerToken" placeholder="输入Apple Music Developer Token">
                        <button onclick="connectAppleMusic()">连接Apple Music</button>
                    </div>
                </div>
            </div>

            <div id="migrationProgress" class="hidden">
                <div class="section">
                    <h2>迁移进度</h2>
                    <div class="progress">
                        <div class="progress-bar">
                            <div id="progressFill" class="progress-fill" style="width: 0%"></div>
                        </div>
                        <div id="progressText" class="progress-text">准备中...</div>
                    </div>
                </div>
            </div>

            <div id="exportResultContainer" class="hidden" style="margin-top: 20px;">
                <h4 style="margin-bottom: 10px;">导出结果</h4>
                <textarea id="exportResult" readonly></textarea>
                <button onclick="copyToClipboard()" style="margin-top: 10px; width: 100%;">复制到剪贴板</button>
            </div>

            <div class="tips">
                <h3>💡 使用说明</h3>
                <p>
                    <strong>方式1: 直接迁移（推荐）</strong><br>
                    1. 获取Apple Music Developer Token<br>
                    2. 点击"直接迁移到Apple Music"<br>
                    3. 系统会自动搜索并创建歌单<br><br>
                    
                    <strong>方式2: 手动迁移</strong><br>
                    1. 导出为TuneMyMusic或CSV格式<br>
                    2. 前往 <a href="https://www.tunemymusic.com" target="_blank">TuneMyMusic</a> 导入<br>
                    3. 选择Apple Music作为目标平台
                </p>
            </div>
        </div>
    </div>

    <script>
        let currentSongs = [];
        let appleMusicReady = false;

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
                if (song.matched === true) tags += '<span class="tag tag-matched">已匹配</span>';
                if (song.matched === false) tags += '<span class="tag tag-failed">未匹配</span>';

                return `<div class="song-item">
                    <div class="song-info">
                        <div class="song-title">${idx+1}. ${escapeHtml(song.clean_name)}${tags}</div>
                        <div class="song-singer">${escapeHtml(song.singer)}</div>
                    </div>
                </div>`;
            }).join('');
        }

        function escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }

        function migrateToAppleMusic() {
            document.getElementById('appleMusicConfig').classList.remove('hidden');
            showStatus('info', '请输入Apple Music Developer Token以继续');
        }

        async function connectAppleMusic() {
            const token = document.getElementById('developerToken').value.trim();

            if (!token) {
                showStatus('error', '请输入Developer Token');
                return;
            }

            showStatus('info', '正在连接Apple Music...');

            try {
                await MusicKit.configure({
                    developerToken: token,
                    app: {
                        name: 'QQ Music Migrator',
                        build: '1.0.0'
                    }
                });

                appleMusicReady = true;
                showStatus('success', 'Apple Music连接成功！点击下方按钮开始迁移');
                document.getElementById('migrationProgress').classList.remove('hidden');

                // 开始迁移
                startMigration();

            } catch (error) {
                console.error('连接失败:', error);
                showStatus('error', '连接失败: ' + error.message);
            }
        }

        async function startMigration() {
            const music = MusicKit.getInstance();
            const total = currentSongs.length;
            let matched = 0;
            let failed = 0;

            showStatus('info', '开始搜索并匹配歌曲...');

            for (let i = 0; i < currentSongs.length; i++) {
                const song = currentSongs[i];
                const progress = ((i + 1) / total * 100).toFixed(1);

                document.getElementById('progressFill').style.width = progress + '%';
                document.getElementById('progressText').textContent = 
                    `正在处理: ${i + 1}/${total} - ${song.clean_name}`;

                try {
                    // 搜索歌曲
                    const results = await music.api.music(
                        `/v1/catalog/${music.storefrontId}/search`,
                        {
                            term: `${song.clean_name} ${song.singer}`,
                            types: ['songs'],
                            limit: 1
                        }
                    );

                    if (results.data.results.songs && results.data.results.songs.data.length > 0) {
                        const appleSong = results.data.results.songs.data[0];
                        song.appleMusicId = appleSong.id;
                        song.matched = true;
                        matched++;
                    } else {
                        song.matched = false;
                        failed++;
                    }
                } catch (error) {
                    console.error(`搜索失败: ${song.clean_name}`, error);
                    song.matched = false;
                    failed++;
                }

                // 更新列表显示
                renderSongList(currentSongs);

                // 延迟避免API限流
                await new Promise(resolve => setTimeout(resolve, 500));
            }

            showStatus('success', `搜索完成！匹配成功: ${matched}，失败: ${failed}`);

            // 创建歌单
            const matchedSongs = currentSongs.filter(s => s.matched && s.appleMusicId);

            if (matchedSongs.length > 0) {
                showStatus('info', '正在创建Apple Music歌单...');

                try {
                    const playlist = await music.api.library.createPlaylist({
                        name: '从QQ音乐迁移的歌单',
                        description: `共${matchedSongs.length}首歌曲`
                    });

                    // 添加歌曲到歌单
                    const songIds = matchedSongs.map(s => s.appleMusicId);

                    await music.api.library.add(
                        playlist.id,
                        'playlists',
                        'tracks',
                        songIds.map(id => ({ id: id, type: 'songs' }))
                    );

                    showStatus('success', 
                        `🎉 迁移成功！已创建歌单并添加${matchedSongs.length}首歌曲`);

                } catch (error) {
                    console.error('创建歌单失败:', error);
                    showStatus('error', '创建歌单失败: ' + error.message);
                }
            }
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

            } catch (error) {
                showStatus('error', error.message || '导出失败');
            }
        }

        function copyToClipboard() {
            const textarea = document.getElementById('exportResult');
            textarea.select();
            document.execCommand('copy');
            showStatus('success', '已复制到剪贴板！');
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
    print("🎵 QQ音乐→Apple Music歌单迁移工具")
    print("=" * 60)
    print()
    print("🎉 完全复刻GoMusic架构 + Apple Music API直连")
    print("🌐 访问: http://localhost:8000")
    print("📚 文档: http://localhost:8000/docs")
    print()
    print("📋 功能特性:")
    print("  - ✅ QQ音乐官方API调用（含签名算法）")
    print("  - ✅ 数据清洗与标准化")
    print("  - ✅ 歌曲标签检测（Live/Remix等）")
    print("  - ✅ Apple Music API直连迁移")
    print("  - ✅ TuneMyMusic格式导出")
    print("  - ✅ 支持公开歌单")
    print()
    print("=" * 60)

    if not (BASE_DIR / "frontend").exists():
        (BASE_DIR / "frontend").mkdir()
        create_frontend()
    elif not (BASE_DIR / "frontend" / "index.html").exists():
        create_frontend()

    uvicorn.run(app, host="0.0.0.0", port=8000)
