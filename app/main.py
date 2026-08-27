"""FastAPI 入口：SSE 流式 /api/chat + 文档入库 /api/ingest。

启动：uvicorn app.main:app --reload --port 8000
"""
import json
import shutil
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from app.agents.router import get_router
from app.config import settings
from app.dispatcher import dispatch
from app.knowledge import get_knowledge_base

app = FastAPI(title="SmartOps-AI-Agent", version="1.0.0", description="电商/物联网售后多 Agent 智能客服")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# 图表与前端静态资源
settings.charts_dir.mkdir(parents=True, exist_ok=True)
app.mount("/charts", StaticFiles(directory=str(settings.charts_dir)), name="charts")
app.mount("/web", StaticFiles(directory="web"), name="web")


def _sse(obj: dict) -> str:
    return "data: " + json.dumps(obj, ensure_ascii=False) + "\n\n"


def _chunks(text: str, size: int = 12):
    for i in range(0, len(text), size):
        yield text[i : i + size]


@app.get("/")
def index():
    from fastapi.responses import FileResponse

    return FileResponse("web/index.html")


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "SmartOps-AI-Agent"}


@app.get("/api/stats")
def stats():
    kb = get_knowledge_base()
    return kb.stats()


# ---------- SSE 流式对话 ----------
class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, description="用户问题")


@app.post("/api/chat")
async def chat(payload: ChatRequest):
    question = payload.message.strip()
    if not question:
        raise HTTPException(status_code=400, detail="message 不能为空")

    async def event_stream():
        try:
            intent = await run_in_threadpool(get_router().classify, question)
            yield _sse({"type": "meta", "intent": intent})

            result = await run_in_threadpool(dispatch, intent, question)

            if result.sources:
                yield _sse({"type": "sources", "sources": result.sources})

            for delta in _chunks(result.text):
                yield _sse({"type": "delta", "text": delta})

            if result.chart_url:
                yield _sse({"type": "chart", "url": result.chart_url})

            yield _sse({"type": "done"})
        except Exception as exc:
            yield _sse({"type": "error", "text": f"服务异常：{exc}"})
            yield _sse({"type": "done"})

    return StreamingResponse(event_stream(), media_type="text/event-stream")


# ---------- 知识库文档入库 ----------
@app.post("/api/ingest")
async def ingest(file: UploadFile = File(...)):
    kb = get_knowledge_base()
    suffix = Path(file.filename or "upload.txt").suffix.lower()
    if suffix not in {".txt", ".md", ".markdown", ".pdf", ".docx"}:
        raise HTTPException(status_code=400, detail=f"不支持的文件类型: {suffix}，支持 txt/md/pdf/docx")

    tmp = settings.data_dir / f"_upload{suffix}"
    with tmp.open("wb") as f:
        shutil.copyfileobj(file.file, f)

    chunks = kb.ingest_document(tmp)
    tmp.unlink(missing_ok=True)
    return {"file": file.filename, "chunks": chunks}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
