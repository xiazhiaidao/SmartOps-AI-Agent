"""本地 Embedding：FastEmbed + BGE 中文模型，无需外部 Embedding API。"""
import os
from pathlib import Path
from typing import List

import numpy as np

from app.config import settings

# 国内网络环境优先使用 Hugging Face 镜像下载 ONNX 权重，必须在 fastembed 发起下载前设置。
if settings.hf_endpoint:
    os.environ.setdefault("HF_ENDPOINT", settings.hf_endpoint)
# HF 新版 Xet 存储通道在镜像/受限网络下可能返回 401；禁用走普通 HTTP 下载更稳定。
os.environ.setdefault("HF_HUB_DISABLE_XET", "1" if settings.hf_hub_disable_xet else "0")

from fastembed import TextEmbedding  # noqa: E402


def _resolve_cache_dir() -> str:
    """优先复用已下载好的 BGE 模型缓存，避免重复下载。"""
    local = Path(settings.model_cache_dir)
    if local.exists():
        return str(local)
    if settings.reuse_external_model_cache:
        external = Path(settings.external_model_cache)
        if external.exists():
            return str(external)
    return str(local)


def _normalize(vector: np.ndarray) -> np.ndarray:
    norm = np.linalg.norm(vector)
    if norm == 0:
        return vector
    return vector / norm


class LocalEmbeddings:
    """FastEmbed 轻量封装，返回归一化向量，供余弦相似度直接点积。"""

    def __init__(self, model_name: str = "BAAI/bge-small-zh-v1.5", cache_dir: str | None = None):
        self.model_name = model_name
        self.cache_dir = cache_dir or _resolve_cache_dir()
        self._model = None

    @property
    def model(self) -> TextEmbedding:
        if self._model is None:
            self._model = TextEmbedding(
                model_name=self.model_name,
                cache_dir=self.cache_dir,
            )
        return self._model

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        vectors = [np.asarray(v, dtype=np.float32) for v in self.model.embed(texts)]
        return [_normalize(v).tolist() for v in vectors]

    def embed_query(self, text: str) -> List[float]:
        vector = next(self.model.embed([text]))
        return _normalize(np.asarray(vector, dtype=np.float32)).tolist()
