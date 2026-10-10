"""隔离 Embedding / LLM，验证知识库拒答和引用链路。"""
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from app.config import settings
from app.knowledge import KnowledgeBase


@pytest.mark.parametrize("scores", [[], [0.1, 0.34], [0.35, 0.9, 0.1]])
def test_retrieval_threshold_and_abstention(monkeypatch, scores):
    monkeypatch.setattr(settings, "score_threshold", 0.35)
    kb = KnowledgeBase.__new__(KnowledgeBase)
    kb.embeddings = Mock()
    kb.vectorstore = Mock()
    kb.vectorstore.similarity_search_with_score.return_value = [
        ("保修期一年。", {"source": f"policy-{i}.md"}, score)
        for i, score in enumerate(scores)
    ]
    kb.llm = Mock()
    kb.llm.invoke.return_value = SimpleNamespace(content="保修期一年。")

    result = kb.ask("保修期多久？")

    expected = [score for score in scores if score >= 0.35]
    assert [source["score"] for source in result["sources"]] == expected
    assert result["top_k"] == len(expected)
    if expected:
        kb.llm.invoke.assert_called_once()
        prompt = kb.llm.invoke.call_args.args[0][1]["content"]
        assert "policy-2.md" not in prompt
        assert "保修期一年。" in prompt
    else:
        kb.llm.invoke.assert_not_called()
        assert "无法回答" in result["answer"]
