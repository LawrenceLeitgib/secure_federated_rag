from dataclasses import dataclass, field
import hashlib

from app.common.crypto.signing import generate_key_pairs
from app.common.crypto.symmetric import decrypt_bytes
from app.custodians.custodian import reconstruct_key_dummy
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
        ledger.register_user(retrieval_engine.re_id, retrieval_engine.public_key.decode("utf-8"), retrieval_engine.private_key)

        return cls(
            name=name,
            re_id=re_id,
            private_key=private_key,
            public_key=public_key,
        )
    
    def add_embeddings(self, chunk_embeddings: list[tuple[str, list[float]]]) -> None:
        for chunk_id, embedding in chunk_embeddings:
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
    
    def query(self, re_id: str, dataset_id: str, query_text: str, k: int = 3) -> list[tuple[str, float, str]]:
        if not self.ledger.is_authorized(re_id, dataset_id):
            raise PermissionError(f"User {re_id} is not authorized for dataset {dataset_id}")

      
        results = self.retrieval_engines[re_id].query(query_text, k=k)

        share1 = self.custodian_a.get_share(dataset_id)
        share2 = self.custodian_b.get_share(dataset_id)
        kek = reconstruct_key_dummy(share1, share2)

        decrypted_results: list[tuple[str, float, str]] = []

        for result in results:
            encrypted_chunk = self.storage.get_chunk(result[0])
            dek = decrypt_bytes(encrypted_chunk.encrypted_dek, kek).decode("utf-8")
            plaintext = decrypt_bytes(encrypted_chunk.encrypted_data, dek).decode("utf-8")
            decrypted_results.append(
                (result[0], result[1], plaintext)
            )

        return decrypted_results