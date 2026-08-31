"""FastAPI 接口层测试：健康检查、SSE 流式对话、上传校验。"""
from app.agents import AgentResult
from app.main import app
from fastapi.testclient import TestClient

client = TestClient(app)


def test_health():
    resp = client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["service"] == "SmartOps-AI-Agent"
    assert data["version"]


def test_chat_sse_stream(monkeypatch):
    class FakeRouter:
        def classify(self, question: str) -> str:
            return "knowledge"

    monkeypatch.setattr(
        "app.main.get_router",
        lambda: FakeRouter(),
    )
    monkeypatch.setattr(
        "app.main.dispatch",
        lambda intent, question: AgentResult(
            text="你好，这是测试回答。",
            type="text",
        ),
    )

    resp = client.post("/api/chat", json={"message": "我的榨汁机坏了怎么办"})
    assert resp.status_code == 200
    assert "text/event-stream" in resp.headers["content-type"]

    body = resp.text
    assert '"type": "meta"' in body
    assert '"intent": "knowledge"' in body
    assert '"type": "delta"' in body
    assert '"type": "done"' in body
    assert "conversation_id" in body


def test_chat_blank_message_rejected():
    resp = client.post("/api/chat", json={"message": "   "})
    assert resp.status_code == 400
    assert "不能为空" in resp.json()["detail"]


def test_ingest_rejects_unsupported_suffix():
    resp = client.post(
        "/api/ingest",
        files={"file": ("notes.exe", b"not a document", "application/octet-stream")},
    )
    assert resp.status_code == 400
    assert "不支持的文件类型" in resp.json()["detail"]
