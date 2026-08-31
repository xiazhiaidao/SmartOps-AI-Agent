"""NumPy 向量库单元测试。"""
import numpy as np
import pytest
from app.vectorstore import NumpyVectorStore


def test_add_and_search(tmp_path):
    store = NumpyVectorStore(index_dir=tmp_path, dim=2)
    store.add_embeddings(
        texts=["苹果", "香蕉", "西瓜"],
        embeddings=[[1.0, 0.0], [0.9, 0.1], [0.1, 0.9]],
        metadatas=[{"source": "a"}, {"source": "b"}, {"source": "c"}],
    )
    results = store.similarity_search_with_score([1.0, 0.0], k=2)
    assert len(results) == 2
    assert results[0][0] == "苹果"
    assert results[0][2] == pytest.approx(1.0)


def test_persist_and_reload(tmp_path):
    store = NumpyVectorStore(index_dir=tmp_path, dim=2)
    store.add_embeddings(
        texts=["hello"],
        embeddings=[[1.0, 0.0]],
        metadatas=[{"source": "x"}],
    )
    reloaded = NumpyVectorStore(index_dir=tmp_path, dim=2)
    assert reloaded.count() == 1
    assert reloaded.texts[0] == "hello"
    assert reloaded.metadatas[0]["source"] == "x"


def test_dimension_mismatch_raises(tmp_path):
    store = NumpyVectorStore(index_dir=tmp_path, dim=3)
    with pytest.raises(ValueError):
        store.add_embeddings(
            texts=["bad"],
            embeddings=[np.array([1.0, 0.0])],
        )


def test_empty_store_returns_no_results(tmp_path):
    store = NumpyVectorStore(index_dir=tmp_path, dim=2)
    assert store.similarity_search_with_score([1.0, 0.0], k=3) == []