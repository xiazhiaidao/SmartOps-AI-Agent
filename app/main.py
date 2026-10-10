"""FastAPI 入口：SSE 流式 /api/chat + 文档入库 /api/ingest。

启动：uvicorn app.main:app --reload --port 8000
"""
import json
import time
import uuid
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from app.agents.router import get_router
from app.config import settings
from app.dispatcher import dispatch
from app.knowledge import get_knowledge_base
from app.logging import get_logger, setup_logging

BASE_DIR = Path(__file__).resolve().parents[1]
WEB_DIR = BASE_DIR / "web"

setup_logging()
logger = get_logger(__name__)

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="电商/物联网售后多 Agent 智能客服",
)

# CORS：支持通过环境变量 CORS_ORIGINS 配置（逗号分隔），默认允许所有来源
cors_origins = settings.cors_origin_list
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=cors_origins != ["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# 图表与前端静态资源
settings.charts_dir.mkdir(parents=True, exist_ok=True)
settings.uploads_dir.mkdir(parents=True, exist_ok=True)
app.mount("/charts", StaticFiles(directory=str(settings.charts_dir)), name="charts")
app.mount("/web", StaticFiles(directory=str(WEB_DIR)), name="web")


@app.middleware("http")
async def request_context(request: Request, call_next):
    """为每个请求注入 request id，并记录访问日志。"""
    request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex[:12]
    request.state.request_id = request_id
    start = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        logger.exception("request failed: %s %s rid=%s", request.method, request.url.path, request_id)
        raise
    duration_ms = (time.perf_counter() - start) * 1000
    logger.info(
        "%s %s -> %s (%.1fms) rid=%s",
        request.method,
        request.url.path,
        response.status_code,
        duration_ms,
        request_id,
    )
    response.headers["X-Request-ID"] = request_id
    return response


def _sse(obj: dict) -> str:
    return "data: " + json.dumps(obj, ensure_ascii=False) + "\n\n"


def _chunks(text: str, size: int = 12):
    for i in range(0, len(text), size):
        yield text[i : i + size]


@app.get("/")
def index():
    return FileResponse(WEB_DIR / "index.html")


@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "service": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
    }


@app.get("/api/stats")
def stats():
    kb = get_knowledge_base()
    return kb.stats()


# ---------- SSE 流式对话 ----------
class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000, description="用户问题")
    conversation_id: str | None = Field(
        default=None,
        max_length=64,
        description="会话 ID；不传则由服务端生成并随 meta 事件返回",
    )


@app.post("/api/chat")
async def chat(payload: ChatRequest, request: Request):
    question = payload.message.strip()
    if not question:
        raise HTTPException(status_code=400, detail="message 不能为空")
    conversation_id = payload.conversation_id or uuid.uuid4().hex

    async def event_stream():
        started = time.perf_counter()
        try:
            intent = await run_in_threadpool(get_router().classify, question)
            routed = time.perf_counter()
            yield _sse(
                {
                    "type": "meta",
                    "intent": intent,
                    "conversation_id": conversation_id,
                    "request_id": request.state.request_id,
                }
            )

            result = await run_in_threadpool(dispatch, intent, question)
            finished = time.perf_counter()

            if result.sources:
                yield _sse({"type": "sources", "sources": result.sources})

            for delta in _chunks(result.text):
                yield _sse({"type": "delta", "text": delta})

            if result.chart_url:
                yield _sse({"type": "chart", "url": result.chart_url})

            yield _sse({
                "type": "done",
                "conversation_id": conversation_id,
                "request_id": request.state.request_id,
                "result_type": result.type,
                "timings_ms": {
                    "routing": round((routed - started) * 1000, 1),
                    "agent": round((finished - routed) * 1000, 1),
                    "total": round((finished - started) * 1000, 1),
                },
            })
        except Exception:
            logger.exception("chat stream error: conversation_id=%s", conversation_id)
            yield _sse({
                "type": "error",
                "text": "服务暂时不可用，请稍后重试。",
                "request_id": request.state.request_id,
            })
            yield _sse({
                "type": "done",
                "conversation_id": conversation_id,
                "request_id": request.state.request_id,
            })

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


# ---------- 知识库文档入库 ----------
_SUPPORTED_SUFFIXES = {".txt", ".md", ".markdown", ".pdf", ".docx"}


@app.post("/api/ingest")
async def ingest(file: UploadFile = File(...)):  # noqa: B008 - FastAPI 依赖注入惯用法
    suffix = Path(file.filename or "upload.txt").suffix.lower()
    if suffix not in _SUPPORTED_SUFFIXES:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件类型: {suffix}，支持 {'/'.join(sorted(_SUPPORTED_SUFFIXES))}",
        )

    max_bytes = settings.upload_max_size_mb * 1024 * 1024
    tmp_path = settings.uploads_dir / f"{uuid.uuid4().hex}{suffix}"

    size = 0
    try:
        with tmp_path.open("wb") as buffer:
            while chunk := await file.read(1024 * 1024):
                size += len(chunk)
                if size > max_bytes:
                    raise HTTPException(
                        status_code=413,
                        detail=f"文件大小超过限制（{settings.upload_max_size_mb}MB）",
                    )
                buffer.write(chunk)

        kb = get_knowledge_base()
        chunks = await run_in_threadpool(kb.ingest_document, tmp_path)
        return {"file": file.filename, "chunks": chunks, "size": size}
    finally:
        tmp_path.unlink(missing_ok=True)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
