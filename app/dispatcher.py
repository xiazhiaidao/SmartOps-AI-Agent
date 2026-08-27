"""Agent 调度器：根据 Router 分类结果，将请求派发到对应子 Agent。"""
from app.agents import AgentResult
from app.agents.fallback_agent import get_fallback_agent
from app.agents.lookup_agent import get_lookup_agent
from app.agents.rag_agent import get_rag_agent


def dispatch(intent: str, question: str) -> AgentResult:
    if intent == "knowledge":
        return get_rag_agent().handle(question)
    if intent == "order":
        return get_lookup_agent().handle(question)
    if intent == "data":
        from app.agents.data_agent import get_data_agent

        return get_data_agent().handle(question)
    return get_fallback_agent().handle(question)
