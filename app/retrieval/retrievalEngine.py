import asyncio
from dataclasses import dataclass, field
import hashlib

from app.common.clients.blockchain_client import BlockchainClient
from app.common.clients.custodian_client import CustodianClient
from app.common.crypto.signing import generate_key_pairs
from app.common.ledger_interaction import register_user
from app.retrieval.embeddings import QwenEmbedder
from app.retrieval.vector_index import SimpleVectorIndex
from app.retrieval.llm import QwenLLM

@dataclass
class RetrievalEngine:
    name: str
    re_id: str
    private_key: bytes
    public_key: bytes
    embeddings: SimpleVectorIndex = field(default_factory=SimpleVectorIndex)
    custodian_client: CustodianClient = field(default=None)
    blockchain_client: BlockchainClient = field(default=None)
    llm: QwenLLM = field(default_factory=QwenLLM)
    embedder: QwenEmbedder = field(default_factory=QwenEmbedder)

    @classmethod
    async def create(cls, name: str, custodian_client: CustodianClient, blockchain_client: BlockchainClient) -> 'RetrievalEngine':
        private_key, public_key = generate_key_pairs()
        re_id = hashlib.sha256(public_key).hexdigest()
        sign_entry = register_user(re_id, public_key.decode("utf-8"), private_key)
        await blockchain_client.add_record(sign_entry)  
        print(f"Registered retrieval engine on blockchain with id: {re_id}")



        return cls(
            name=name,
            re_id=re_id,
            private_key=private_key,
            public_key=public_key,
            embeddings=SimpleVectorIndex(),
            custodian_client=custodian_client,
            blockchain_client=blockchain_client,
            llm=QwenLLM(),
            embedder=QwenEmbedder(),
        )
    
    
    
    """
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
    """

    async def query(self, query_text: str, k: int = 3) -> list[tuple[str, float, str]]:
        query_embedding = self.embedder.embed_text(query_text, is_query=True)

        queryResults = self.embeddings.search(query_embedding, k=k)

        print(f"RetrievalEngine found {len(queryResults)} results for query: {query_text}")

       
       
        decrypted_results: list[tuple[str, float, str]] = []

        for chunk_id, score in queryResults:
            raw=await self.custodian_client.get_plain_text_chunk(self.re_id, chunk_id) #TODO make it more async and handle errors properly
            if(raw.get("status") != "ok"):
                raise RuntimeError(f"Failed to retrieve chunk {chunk_id} from custodian")
            
            chunk = raw.get("result").get("chunk")
            text=chunk.get("text")
            dataset_id=chunk.get("dataset_id")

            
           
            decrypted_results.append(
                (chunk_id, score, text)
            )

        return decrypted_results
    

    async def answer_query(self, query_text: str, k: int = 3) -> dict:
        retrieved = await self.query(query_text=query_text, k=k)
        for chunk_id, score, text in retrieved:
            print(f"Retrieved chunk for RAG: chunk_id={chunk_id}, score={score}, text={text[:50]}...")

        contexts = [text for _, _, text in retrieved]
        llm_response = self.llm.generate_answer(
            query=query_text,
            contexts=contexts,
        )

        return {
            "query": query_text,
            "answer": llm_response.answer,
            "retrieved_chunks": [
                {
                    "chunk_id": chunk_id,
                    "score": score,
                    "text": text,
                }
                for chunk_id, score, text in retrieved
            ],
            "usage": {
                "prompt_tokens": llm_response.prompt_tokens,
                "generated_tokens": llm_response.generated_tokens,
            },
        }