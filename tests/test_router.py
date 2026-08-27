"""Router 意图路由测试：验证关键词快速通道与 LLM 故障兜底。"""
from app.agents.router import RouterAgent


class _FailingLLM:
    def invoke(self, *args, **kwargs):
        raise RuntimeError("simulated LLM failure")


def _force_keyword_router(monkeypatch):
    """让 RouterAgent.llm 返回一个必然失败的 LLM，强制走关键词兜底。"""
    monkeypatch.setattr(RouterAgent, "llm", property(lambda self: _FailingLLM()))
    return RouterAgent()


def test_data_keyword_fast_path_does_not_require_llm():
    router = RouterAgent()
    assert router.classify("帮我分析一下各品类的销售额") == "data"


def test_keyword_fallback_for_order(monkeypatch):
    router = _force_keyword_router(monkeypatch)
    assert router.classify("查询订单 ORD-2026-00123 到哪了") == "order"


def test_keyword_fallback_for_knowledge(monkeypatch):
    router = _force_keyword_router(monkeypatch)
    assert router.classify("我的榨汁机坏了怎么办") == "knowledge"


def test_keyword_fallback_for_human(monkeypatch):
    router = _force_keyword_router(monkeypatch)
    assert router.classify("你好呀") == "human"