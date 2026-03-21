from __future__ import annotations

import math

from app.common.ledger_interaction import QueryResult


class SimpleVectorIndex:
    def __init__(self) -> None:
        self.vectors: dict[str, list[float]] = {}
        self.texts: dict[str, str] = {}

    def add(self, chunk_id: str, embedding: list[float], text: str) -> None:
        self.vectors[chunk_id] = embedding
        self.texts[chunk_id] = text

    def add_embeddings(self, chunk_embeddings: list[tuple[str, list[float]]]) -> None:
        for chunk_id, embedding in chunk_embeddings:
            self.vectors[chunk_id] = embedding

    def _cosine_similarity(self, a: list[float], b: list[float]) -> float:
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(y * y for y in b))

        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)

    def search(self, query_embedding: list[float], k: int = 3) -> list[QueryResult]:
        scored: list[QueryResult] = []

        for chunk_id, emb in self.vectors.items():
            score = self._cosine_similarity(query_embedding, emb)
            scored.append(
                QueryResult(
                    chunk_id=chunk_id,
                    score=score,
                    text=self.texts[chunk_id],
                )
            )

        scored.sort(key=lambda x: x.score, reverse=True)
        return scored[:k]
    
