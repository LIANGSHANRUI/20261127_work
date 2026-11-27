"""聊天助手 FastAPI 网页端。

启动：
    python -m pip install -r requirements.txt
    python app.py

然后打开 http://127.0.0.1:8000
API Key 只从服务端 .env 读取，不会发送到浏览器。
"""
from __future__ import annotations

import json
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
from openai import AsyncOpenAI
from pydantic import BaseModel, Field

BASE = Path(__file__).resolve().parent
load_dotenv(BASE / ".env")


def _env_bool(name: str, default: bool = False) -> bool:
    return os.getenv(name, str(default)).strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default


API_KEY = os.getenv("CHAT_API_KEY", "").strip()
BASE_URL = os.getenv(
    "CHAT_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1"
).strip()
MODEL = os.getenv("CHAT_MODEL", "qwen4-max").strip()
ENABLE_THINKING = _env_bool("CHAT_ENABLE_THINKING", False)
MAX_HISTORY = max(0, _env_int("CHAT_MAX_HISTORY", 12))
HOST = os.getenv("HOST", "127.0.0.1")
PORT = _env_int("PORT", 8010)

# 与 chat.py 中的人设保持一致
DEFAULT_SYSTEM = (
    "你是一个聊天助手，你的语言风格很幽默，可以参考郭德纲的语言风格，"
    "可以适当使用网络流行语"
)

_client: AsyncOpenAI | None = None


@asynccontextmanager
async def lifespan(_: FastAPI):
    yield
    global _client
    if _client is not None:
        await _client.close()
        _client = None


app = FastAPI(
    title="聊天助手 Web",
    description="浏览器端聊天页面，后端代理调用 OpenAI 兼容接口。",
    version="1.0.0",
    lifespan=lifespan,
)


def get_client() -> AsyncOpenAI:
    global _client
    if not API_KEY:
        raise HTTPException(
            status_code=503,
            detail="未配置 CHAT_API_KEY：请在 work/.env 中填写 API Key 后重启服务。",
        )
    if _client is None:
        _client = AsyncOpenAI(api_key=API_KEY, base_url=BASE_URL, timeout=120)
    return _client


class HistoryMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=20_000)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=8_000)
    system: str = Field(default="", max_length=4_000)
    history: list[HistoryMessage] = Field(default_factory=list, max_length=40)
    temperature: float = Field(default=1.2, ge=0.0, le=2.0)
    top_p: float = Field(default=0.9, ge=0.0, le=1.0)


def build_messages(payload: ChatRequest) -> list[dict[str, str]]:
    system = payload.system.strip() or DEFAULT_SYSTEM
    messages: list[dict[str, str]] = [{"role": "system", "content": system}]
    for item in payload.history[-MAX_HISTORY:]:
        messages.append({"role": item.role, "content": item.content})
    messages.append({"role": "user", "content": payload.message})
    return messages


def request_kwargs(payload: ChatRequest) -> dict:
    return {
        "model": MODEL,
        "messages": build_messages(payload),
        "temperature": payload.temperature,
        "top_p": payload.top_p,
        "extra_body": {"enable_thinking": ENABLE_THINKING},
    }


def error_text(exc: Exception) -> str:
    text = str(exc).strip() or exc.__class__.__name__
    return f"{exc.__class__.__name__}: {text[:600]}"


def sse(payload: dict) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "no-referrer"
    return response


@app.get("/", include_in_schema=False)
def index() -> FileResponse:
    return FileResponse(
        BASE / "static" / "index.html",
        media_type="text/html",
        headers={"Cache-Control": "no-cache"},
    )


@app.get("/favicon.ico", include_in_schema=False)
def favicon() -> Response:
    return Response(status_code=204)


@app.get("/api/health")
def health() -> dict:
    """给前端显示连接状态；不返回任何密钥内容。"""
    return {
        "ok": bool(API_KEY),
        "model": MODEL,
        "key_configured": bool(API_KEY),
        "enable_thinking": ENABLE_THINKING,
        "max_history": MAX_HISTORY,
    }


@app.post("/api/chat")
async def chat(payload: ChatRequest) -> dict:
    """一次性返回完整回答，方便用 curl 或接口文档调试。"""
    try:
        result = await get_client().chat.completions.create(**request_kwargs(payload))
        content = (result.choices[0].message.content or "").strip()
        return {"content": content, "model": MODEL}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=502, detail=error_text(exc)) from exc


@app.post("/api/chat/stream")
async def chat_stream(payload: ChatRequest, request: Request) -> StreamingResponse:
    """SSE 流式回答，前端逐字显示。

    每个事件都是 JSON：
        {"type": "delta", "text": "..."}
        {"type": "error", "message": "..."}
        {"type": "done"}
    """
    if not API_KEY:
        raise HTTPException(
            status_code=503,
            detail="未配置 CHAT_API_KEY：请在 work/.env 中填写 API Key 后重启服务。",
        )

    async def event_stream():
        stream = None
        try:
            stream = await get_client().chat.completions.create(
                **request_kwargs(payload), stream=True
            )
            async for chunk in stream:
                if await request.is_disconnected():
                    break
                if not chunk.choices:
                    continue
                text = getattr(chunk.choices[0].delta, "content", None)
                if text:
                    yield sse({"type": "delta", "text": text})
            else:
                yield sse({"type": "done"})
        except Exception as exc:
            yield sse({"type": "error", "message": error_text(exc)})
        finally:
            if stream is not None:
                await stream.close()

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream; charset=utf-8",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


app.mount("/static", StaticFiles(directory=BASE / "static"), name="static")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=HOST, port=PORT)
