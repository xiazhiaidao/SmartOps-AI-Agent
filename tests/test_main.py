"""FastAPI 接口层测试：健康检查、SSE 流式对话、上传校验。"""
import json

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
    events = [json.loads(line[6:]) for line in body.splitlines() if line.startswith("data: ")]
    assert events[0]["request_id"] == resp.headers["X-Request-ID"]
    assert events[-1]["request_id"] == events[0]["request_id"]
    assert events[-1]["result_type"] == "text"
    assert events[-1]["timings_ms"]["total"] >= 0


def test_chat_error_does_not_expose_upstream_details(monkeypatch):
    class FailingRouter:
        def classify(self, question):
            raise RuntimeError("secret upstream configuration")

    monkeypatch.setattr("app.main.get_router", lambda: FailingRouter())
    resp = client.post("/api/chat", json={"message": "你好"})
    events = [json.loads(line[6:]) for line in resp.text.splitlines() if line.startswith("data: ")]
    assert [event["type"] for event in events] == ["error", "done"]
    assert "secret upstream" not in resp.text
    assert events[0]["request_id"] == resp.headers["X-Request-ID"]


def test_chat_blank_message_rejected():
    resp = client.post("/api/chat", json={"message": "   "})
    assert resp.status_code == 400
    assert "不能为空" in resp.json()["detail"]


def test_explicit_handoff_runs_without_llm():
    resp = client.post("/api/chat", json={"message": "订单有问题，转人工"})
    events = [json.loads(line[6:]) for line in resp.text.splitlines() if line.startswith("data: ")]
    assert events[0]["intent"] == "human"
    assert events[-1]["result_type"] == "handoff"
    answer = "".join(event["text"] for event in events if event["type"] == "delta")
    assert "尚未连接真实客服" in answer


def test_ingest_rejects_unsupported_suffix():
    resp = client.post(
        "/api/ingest",
        files={"file": ("notes.exe", b"not a document", "application/octet-stream")},
    )
    assert resp.status_code == 400
    assert "不支持的文件类型" in resp.json()["detail"]
