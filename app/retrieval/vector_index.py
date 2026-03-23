from __future__ import annotations

import numpy as np


class SimpleVectorIndex:
    def __init__(self) -> None:
        # store as a 2D matrix + parallel list of ids for fast batch ops
        self.ids: list[str] = []
        self.emb_matrix: np.ndarray | None = None  # shape: (n, d)

    async def add_embeddings(self, chunk_embeddings: list[tuple[str, list[float]]]) -> None:
        # ...existing code...
        if not chunk_embeddings:
            return

        new_ids = [cid for cid, _ in chunk_embeddings]
        new_vecs = np.array([emb for _, emb in chunk_embeddings], dtype=np.float32)

        if self.emb_matrix is None:
            self.ids = new_ids
            self.emb_matrix = new_vecs
        else:
            self.ids.extend(new_ids)
            self.emb_matrix = np.vstack([self.emb_matrix, new_vecs])

    def _cosine_similarity_batch(
        self, query: np.ndarray, matrix: np.ndarray
    ) -> np.ndarray:
        # query: (d,), matrix: (n, d)
        # normalize
        q_norm = np.linalg.norm(query)
        if q_norm == 0:
            return np.zeros(matrix.shape[0], dtype=np.float32)

        m_norms = np.linalg.norm(matrix, axis=1)
        # avoid division by zero
        mask = m_norms == 0
        m_norms[mask] = 1.0

        dots = matrix @ query  # (n,)
        sims = dots / (m_norms * q_norm)
        sims[mask] = 0.0
        return sims

    def search(self, query_embedding: list[float], k: int = 3) -> list[tuple[str, float]]:
        if self.emb_matrix is None or len(self.ids) == 0:
            return []

        query = np.array(query_embedding, dtype=np.float32)

        sims = self._cosine_similarity_batch(query, self.emb_matrix)
        # get top-k indices
        if k >= len(sims):
            top_idx = np.argsort(-sims)
        else:
            # partial sort for speed on large n
            top_idx_part = np.argpartition(-sims, k - 1)[:k]
            top_idx = top_idx_part[np.argsort(-sims[top_idx_part])]

        return [(self.ids[i], float(sims[i])) for i in top_idx[:k]]