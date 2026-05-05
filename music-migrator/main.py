from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from pathlib import Path

from music_migrator.qqmusic import QQMusicScraper
from music_migrator.matcher import AppleMusicMatcher
from music_migrator.exporter import Exporter
from music_migrator.errors import ErrorResult
from music_migrator.logger import get_logger

app = FastAPI(title="QQ 音乐 → Apple Music 歌单迁移工具", version="1.0.0")

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

logger = get_logger()

# 静态文件挂载
BASE_DIR = Path(__file__).parent.absolute()
if (BASE_DIR / "frontend").exists():
    app.mount("/static", StaticFiles(directory=str(BASE_DIR / "frontend")), name="static")


class PlaylistRequest(BaseModel):
    url: str


class ExportRequest(BaseModel):
    songs: List[Dict[str, Any]]
    format: str = "csv"
    filename: Optional[str] = None


@app.get("/")
async def root():
    """首页"""
    index_path = BASE_DIR / "frontend" / "index.html"
    if index_path.exists():
        return FileResponse(index_path, media_type="text/html")
    return {
        "message": "QQ 音乐 → Apple Music 歌单迁移工具",
        "version": "1.0.0",
        "docs": "/docs"
    }


@app.post("/api/qqmusic/playlist")
async def fetch_qq_playlist(request: PlaylistRequest):
    """获取 QQ 音乐歌单"""
    logger.info(f"收到获取歌单请求: {request.url}")

    scraper = QQMusicScraper()
    result = scraper.fetch_playlist(request.url)

    if not result.success:
        raise HTTPException(
            status_code=400,
            detail=result.to_dict()
        )

    return result.to_dict()


@app.post("/api/match")
async def match_songs(songs: List[Dict[str, Any]]):
    """批量匹配歌曲"""
    logger.info(f"收到匹配请求，共 {len(songs)} 首歌曲")

    matcher = AppleMusicMatcher()
    result = matcher.match_batch(songs)

    if not result.success:
        raise HTTPException(
            status_code=400,
            detail=result.to_dict()
        )

    return result.to_dict()


@app.post("/api/export")
async def export_songs(request: ExportRequest):
    """导出歌曲列表"""
    logger.info(f"收到导出请求，格式: {request.format}")

    exporter = Exporter()

    if request.format == "csv":
        result = exporter.export_csv(request.songs, request.filename)
    elif request.format == "json":
        result = exporter.export_json(
            {"songs": request.songs, "exported_at": "now"},
            request.filename
        )
    elif request.format == "m3u8":
        result = exporter.export_m3u8(request.songs, "我的歌单", request.filename)
    else:
        raise HTTPException(status_code=400, detail="不支持的格式")

    if not result.success:
        raise HTTPException(
            status_code=500,
            detail=result.to_dict()
        )

    return result.to_dict()


if __name__ == "__main__":
    import uvicorn
    print("🚀 QQ 音乐 → Apple Music 歌单迁移工具")
    print("📖 文档地址: http://localhost:8000/docs")
    print("🌐 访问页面: http://localhost:8000")
    print("-" * 50)
    uvicorn.run(app, host="0.0.0.0", port=8000)
