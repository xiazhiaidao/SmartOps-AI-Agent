"""LLM 工厂：统一的 ChatOpenAI 实例，所有 Agent 共用。"""
from langchain_openai import ChatOpenAI

from app.config import settings


def create_llm(temperature: float | None = None, max_tokens: int | None = None) -> ChatOpenAI:
    """创建指向 OpenAI 兼容网关的 ChatOpenAI 实例。"""
    return ChatOpenAI(
        model=settings.llm_model,
        api_key=settings.llm_api_key,
        base_url=settings.llm_base_url,
        temperature=settings.llm_temperature if temperature is None else temperature,
        max_tokens=settings.llm_max_tokens if max_tokens is None else max_tokens,
    )
