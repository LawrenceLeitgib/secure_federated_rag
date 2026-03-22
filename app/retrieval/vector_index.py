from __future__ import annotations

import math



class SimpleVectorIndex:
    def __init__(self) -> None:
        self.vectors: dict[str, list[float]] = {}
        self.texts: dict[str, str] = {}



    async def add_embeddings(self, chunk_embeddings: list[tuple[str, list[float]]]) -> None:
        for chunk_id, embedding in chunk_embeddings:
            self.vectors[chunk_id] = embedding

    def _cosine_similarity(self, a: list[float], b: list[float]) -> float:
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(y * y for y in b))

        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)

    def search(self, query_embedding: list[float], k: int = 3) -> list[tuple[str, float]]:
        scored: list[tuple[str, float]] = []

        for chunk_id, emb in self.vectors.items():
            score = self._cosine_similarity(query_embedding, emb)
            scored.append(
                (chunk_id, score)
            )

        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:k]
    
