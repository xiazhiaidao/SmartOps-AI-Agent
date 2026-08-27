"""知识库 Agent：走 RAG 管线，回答产品/售后类问题，并附引用来源。"""
from app.agents import AgentResult
from app.knowledge import get_knowledge_base


class RagAgent:
    def handle(self, question: str) -> AgentResult:
        kb = get_knowledge_base()
        result = kb.ask(question)
        return AgentResult(
            text=result["answer"],
            type="text",
            sources=result["sources"],
        )


_rag_agent: RagAgent | None = None


def get_rag_agent() -> RagAgent:
    global _rag_agent
    if _rag_agent is None:
        _rag_agent = RagAgent()
    return _rag_agent
