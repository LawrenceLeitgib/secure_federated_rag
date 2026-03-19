from dataclasses import dataclass, field
import hashlib

from app.crypto.signing import generate_key_pairs
from app.retrieval.embeddings import embed_text_dummy


@dataclass
class RetrievalEngine:
    name: str
    re_id: str
    private_key: bytes
    public_key: bytes
    embeddings: dict[str, list[float]] = field(default_factory=dict)

  
    @classmethod
    def create(cls, name: str) -> 'RetrievalEngine':
        private_key, public_key = generate_key_pairs()
        re_id = hashlib.sha256(public_key).hexdigest()
        return cls(
            name=name,
            re_id=re_id,
            private_key=private_key,
            public_key=public_key,
        )
    
    def add_embeddings(self, chunk_embeddings: list[tuple[str, list[float]]]) -> None:
        for chunk_id, embedding in chunk_embeddings:
            self.embeddings[chunk_id] = embedding
        

    def add_embedding(self, chunk_id: str, embedding: list[float]) -> None:
        self.embeddings[chunk_id] = embedding


    def query(self, query_text: str, k: int = 3) -> list[tuple[str, float]]:
        query_embedding = embed_text_dummy(query_text)
        scored: list[tuple[str, float]] = []
        for chunk_id, embedding in self.embeddings.items():
            score = self._cosine_similarity(query_embedding, embedding)
            scored.append((chunk_id, score))
        scored.sort(key=lambda x: x[1], reverse=True)
        return [chunk for chunk in scored[:k]]
    
    def _cosine_similarity(self, a: list[float], b: list[float]) -> float:
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = sum(x * x for x in a) ** 0.5
        norm_b = sum(y * y for y in b) ** 0.5
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)