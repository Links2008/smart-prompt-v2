#!/usr/bin/env python3
"""
Prompt 优化器后端服务
使用 FastAPI 提供 API 接口，避免跨域问题
"""

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import requests
import os
import logging
from pathlib import Path

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(title="Prompt Optimizer API", version="1.0.0")

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 静态文件挂载
current_dir = Path(__file__).parent
if (current_dir / "prompt_optimizer_v2.html").exists():
    app.mount("/static", StaticFiles(directory=str(current_dir)), name="static")

# API 请求模型
class ChatRequest(BaseModel):
    provider: str
    model: str
    api_key: str
    messages: List[Dict[str, str]]
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = 2048
    stream: Optional[bool] = False
    custom_url: Optional[str] = None

# 服务提供商配置
PROVIDER_CONFIG = {
    "doubao": {
        "url": "https://ark.cn-beijing.volces.com/api/v3/chat/completions",
        "models": ["doubao-pro-4k", "doubao-lite-4k", "doubao-lite-32k", "doubao-pro-32k"],
        "docs_url": "https://console.volcengine.com/ark"
    },
    "kimi": {
        "url": "https://api.moonshot.cn/v1/chat/completions",
        "models": ["moonshot-v1-8k", "moonshot-v1-32k", "moonshot-v1-128k"],
        "docs_url": "https://platform.moonshot.cn/"
    },
    "openai": {
        "url": "https://api.openai.com/v1/chat/completions",
        "models": ["gpt-4o", "gpt-4-turbo", "gpt-3.5-turbo"],
        "docs_url": "https://platform.openai.com/"
    },
    "deepseek": {
        "url": "https://api.deepseek.com/v1/chat/completions",
        "models": ["deepseek-chat"],
        "docs_url": "https://platform.deepseek.com/"
    },
    "local": {
        "url": "http://localhost:11434/v1/chat/completions",
        "models": ["gemma:2b", "llama3:8b", "mistral:7b"],
        "docs_url": "https://ollama.com/"
    }
}

@app.get("/")
async def root():
    """根路径，返回主页面"""
    index_path = current_dir / "prompt_optimizer_v2.html"
    if index_path.exists():
        return FileResponse(index_path, media_type="text/html")
    return {"message": "Prompt Optimizer API is running", "docs": "/docs"}

@app.post("/api/chat/completions")
async def chat_completions(request: ChatRequest):
    """处理聊天完成请求，转发到对应AI服务商"""
    logger.info(f"收到请求: provider={request.provider}, model={request.model}")

    # 检查API Key是否提供
    if not request.api_key or request.api_key.strip() == "":
        provider_info = PROVIDER_CONFIG.get(request.provider, {})
        docs_url = provider_info.get("docs_url", "")
        raise HTTPException(
            status_code=400,
            detail=f"请填写API Key！\n\n获取API Key地址：\n• 豆包: https://console.volcengine.com/ark\n• Kimi: https://platform.moonshot.cn/\n• OpenAI: https://platform.openai.com/\n• DeepSeek: https://platform.deepseek.com/"
        )

    try:
        # 获取API URL
        if request.provider == "local" and request.custom_url:
            api_url = request.custom_url
        else:
            api_url = PROVIDER_CONFIG[request.provider]["url"]

        logger.info(f"请求地址: {api_url}")

        # 构建请求头
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {request.api_key}"
        }

        # 构建请求体
        body = {
            "model": request.model,
            "messages": request.messages,
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
            "stream": request.stream
        }

        logger.info(f"请求体: {body}")

        # 发送请求到AI服务商
        response = requests.post(
            api_url,
            headers=headers,
            json=body,
            timeout=60
        )

        logger.info(f"响应状态: {response.status_code}")
        logger.info(f"响应内容: {response.text}")

        # 检查响应
        if not response.ok:
            # 解析错误信息
            try:
                error_data = response.json()
                error_code = error_data.get("error", {}).get("code", "UnknownError")
                error_message = error_data.get("error", {}).get("message", "未知错误")

                # 针对401认证错误提供更友好的提示
                if response.status_code == 401 or error_code == "AuthenticationError":
                    raise HTTPException(
                        status_code=401,
                        detail=f"API Key无效！请检查：\n1. 是否正确粘贴了API Key\n2. API Key是否过期或被撤销\n3. 模型名称是否正确\n\n获取豆包API Key：https://console.volcengine.com/ark"
                    )
                elif response.status_code == 400:
                    raise HTTPException(
                        status_code=400,
                        detail=f"请求参数错误 [{error_code}]: {error_message}\n\n请检查模型名称是否正确"
                    )
                elif response.status_code == 429:
                    raise HTTPException(
                        status_code=429,
                        detail=f"请求过于频繁，请稍后再试"
                    )
                else:
                    raise HTTPException(
                        status_code=response.status_code,
                        detail=f"API错误 [{error_code}]: {error_message}"
                    )
            except HTTPException:
                raise
            except:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"API请求失败: {response.text}"
                )

        # 返回结果
        return response.json()

    except HTTPException:
        raise
    except requests.Timeout:
        logger.error("API请求超时")
        raise HTTPException(status_code=408, detail="API请求超时，请检查网络连接")
    except requests.RequestException as e:
        logger.error(f"请求错误: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"网络请求错误: {str(e)}")
    except Exception as e:
        logger.error(f"服务器错误: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"服务器错误: {str(e)}")

@app.get("/api/models/{provider}")
async def get_models(provider: str):
    """获取指定提供商的模型列表"""
    if provider not in PROVIDER_CONFIG:
        raise HTTPException(status_code=400, detail="不支持的提供商")

    return {
        "provider": provider,
        "models": PROVIDER_CONFIG[provider]["models"],
        "url": PROVIDER_CONFIG[provider]["url"]
    }

@app.get("/api/providers")
async def get_providers():
    """获取所有支持的服务商列表"""
    return {
        "providers": [
            {"id": provider, "name": config["name"], "models": config["models"]}
            for provider, config in PROVIDER_CONFIG.items()
        ]
    }

if __name__ == "__main__":
    import uvicorn
    print("🚀 启动 Prompt 优化器后端服务...")
    print("📖 文档地址: http://localhost:8000/docs")
    print("🌐 访问页面: http://localhost:8000")
    print("-" * 50)

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )
