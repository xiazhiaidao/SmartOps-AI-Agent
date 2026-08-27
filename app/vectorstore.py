"""基于 NumPy 的极简本地向量存储：文件持久化，零第三方向量库依赖。"""
import json
import threading
import uuid
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np


class NumpyVectorStore:
    """把文本块和归一化向量保存到 data/vector_index。

    文件：
      - vectors.npy  所有向量的 float32 矩阵
      - chunks.json  文本、元数据、id 的索引
    """

    def __init__(self, index_dir: Path, dim: int = 512):
        self.index_dir = Path(index_dir)
        self.dim = dim
        self._lock = threading.Lock()
        self.texts: List[str] = []
        self.ids: List[str] = []
        self.metadatas: List[Dict] = []
        self.vectors = np.zeros((0, dim), dtype=np.float32)
        self._load()

    def count(self) -> int:
        return len(self.texts)

    def add_embeddings(
        self,
        texts: List[str],
        embeddings: List[List[float]],
        metadatas: Optional[List[Dict]] = None,
        ids: Optional[List[str]] = None,
    ) -> List[str]:
        if not texts:
            return []
        emb = np.asarray(embeddings, dtype=np.float32)
        if emb.ndim != 2 or emb.shape[1] != self.dim:
            raise ValueError(f"Embedding 维度应为 ({self.dim},)，实际 {emb.ndim} 维：{emb.shape}")
        with self._lock:
            if self.vectors.shape[0] == 0:
                self.vectors = emb
            else:
                self.vectors = np.vstack([self.vectors, emb])

            new_ids: List[str] = []
            for i, text in enumerate(texts):
                doc_id = ids[i] if ids and i < len(ids) else str(uuid.uuid4())
                new_ids.append(doc_id)
                self.ids.append(doc_id)
                self.texts.append(text)
                self.metadatas.append(metadatas[i] if metadatas else {})
            self._persist()
            return new_ids

    def similarity_search_with_score(
        self,
        query_embedding: List[float],
        k: int = 4,
    ) -> List[Tuple[str, Dict, float]]:
        """返回 [(text, metadata, score)]，score 为余弦相似度（0~1）。"""
        if self.vectors.shape[0] == 0:
            return []
        q = np.asarray(query_embedding, dtype=np.float32).reshape(1, -1)
        scores = (self.vectors @ q.T).flatten()
        top_indices = np.argsort(scores)[::-1][:k]
        return [
            (self.texts[int(i)], self.metadatas[int(i)], float(scores[int(i)]))
            for i in top_indices
        ]

    def _persist(self) -> None:
        self.index_dir.mkdir(parents=True, exist_ok=True)
        np.save(self.index_dir / "vectors.npy", self.vectors)
        payload = {"ids": self.ids, "texts": self.texts, "metadatas": self.metadatas}
        with open(self.index_dir / "chunks.json", "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)

    def _load(self) -> None:
        vectors_path = self.index_dir / "vectors.npy"
        chunks_path = self.index_dir / "chunks.json"
        if not (vectors_path.exists() and chunks_path.exists()):
            return
        try:
            self.vectors = np.load(vectors_path).astype(np.float32)
            with open(chunks_path, "r", encoding="utf-8") as f:
                payload = json.load(f)
            self.ids = payload.get("ids", [])
            self.texts = payload.get("texts", [])
            self.metadatas = payload.get("metadatas", [])
        except Exception:
            # 索引损坏时从空开始，避免阻塞启动
            self.texts, self.ids, self.metadatas = [], [], []
            self.vectors = np.zeros((0, self.dim), dtype=np.float32)
