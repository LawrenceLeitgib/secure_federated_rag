import asyncio
from dataclasses import dataclass, field
import hashlib

from app.common.benchmarking import BenchmarkReport, now
from app.common.clients.blockchain_client import BlockchainClient
from app.common.clients.custodian_client import CustodianClient
from app.common.clients.storage_client import StorageClient
from app.common.crypto.asymmetric import decrypt_with_shares
from app.common.crypto.hashing import sha256_text
from app.common.crypto.signing import generate_key_pairs
from app.common.crypto.symmetric import decrypt_bytes
from app.common.ledger_interaction import register_user
from app.retrieval.embeddings import QwenEmbedder
from app.retrieval.vector_index import SimpleVectorIndex
from app.retrieval.llm import QwenLLM

import threshold_crypto as tc

@dataclass
class RetrievalEngine:
    name: str
    re_id: str
    private_key: bytes
    public_key: bytes
    embeddings: SimpleVectorIndex = field(default_factory=SimpleVectorIndex)
    custodian_clients: list[CustodianClient] = field(default_factory=list)  # Support multiple custodians
    blockchain_client: BlockchainClient = field(default=None)
    storage_client: StorageClient = field(default=None)
    llm: QwenLLM = field(default_factory=QwenLLM)
    embedder: QwenEmbedder = field(default_factory=QwenEmbedder)

    @classmethod
    async def create(cls, name: str, custodian_clients: list[CustodianClient], blockchain_client: BlockchainClient, storage_client: StorageClient) -> 'RetrievalEngine':
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
            custodian_clients=custodian_clients,
            blockchain_client=blockchain_client,
            storage_client=storage_client,
            llm=QwenLLM(),
            embedder=QwenEmbedder(),
        )

    async def query(self, query_text: str, k: int = 3) -> list[tuple[str, float, str]]:
        results, _ = await self.query_with_benchmark(query_text=query_text, k=k)
        return results

    async def query_with_benchmark(
        self,
        query_text: str,
        k: int = 3,
    ) -> tuple[list[tuple[str, float, str]], dict]:
        benchmark = BenchmarkReport()
        total_start = now()

        embed_start = now()
        query_embedding = await self.embedder.embed_text(query_text, is_query=True)
        benchmark.add_duration("embedding_generation_ms", embed_start)

        search_start = now()
        queryResults = self.embeddings.search(query_embedding, k=k)
        benchmark.add_duration("vector_search_ms", search_start)
        benchmark.set_counter("requested_top_k", k)
        benchmark.set_counter("retrieved_candidate_count", len(queryResults))

        print(f"RetrievalEngine found {len(queryResults)} results for query: {query_text}")

        # Phase 1: Fetch all chunks from storage in parallel
        storage_start = now()
        storage_responses = await asyncio.gather(
            *[self.storage_client.retrieve_chunk_async(chunk_id) for chunk_id, _ in queryResults]
        )
        benchmark.add_duration("storage_provider_ms", storage_start)

        valid_chunks: list[dict] = []
        for (chunk_id, score), resp in zip(queryResults, storage_responses):
            if resp.get("status") != "ok":
                raise RuntimeError(f"Failed to retrieve chunk {chunk_id} from storage server")
            result = resp.get("result", {})
            valid_chunks.append({
                "chunk_id": chunk_id,
                "score": score,
                "encrypted_dek": result.get("encrypted_dek"),
                "encrypted_data": result.get("encrypted_data"),
            })

        # Phase 2: Batch-request partial decryptions from both custodians concurrently
        batch_items = [{"chunk_id": c["chunk_id"], "encrypted_dek": c["encrypted_dek"]} for c in valid_chunks]
        custodian_start = now()

        #make it sequential for now to avoid overloading the custodians, can be made concurrent later if needed
        raw1_resp, raw2_resp = await asyncio.gather(
            self.custodian_clients[0].get_partial_decryptions_batch(self.re_id, batch_items),
            self.custodian_clients[1].get_partial_decryptions_batch(self.re_id, batch_items),
        )




        benchmark.add_duration("custodian_ms", custodian_start)

        if raw1_resp.get("status") != "ok":
            raise RuntimeError(f"Batch request to custodian 1 failed: {raw1_resp.get('error')}")
        if raw2_resp.get("status") != "ok":
            raise RuntimeError(f"Batch request to custodian 2 failed: {raw2_resp.get('error')}")

        raw1_results: dict = raw1_resp.get("result", {})
        raw2_results: dict = raw2_resp.get("result", {})

        # All items across both custodians ran in parallel, so wall-clock blockchain
        # time is the critical path (max), not the sum of all items.
        total_blockchain_ms = max(
            (item.get("benchmark", {}).get("timings_ms", {}).get("blockchain_ms", 0.0)
            for results in (raw1_results, raw2_results)
            for item in results.values()),
            default=0.0,
        )
        benchmark.set_duration_ms("blockchain_ms", total_blockchain_ms)
        benchmark.increment_duration_ms("custodian_ms", -total_blockchain_ms)

        # Phase 3: Decrypt each authorized chunk
        decrypted_results: list[tuple[str, float, str]] = []

        for chunk in valid_chunks:
            chunk_id = chunk["chunk_id"]
            score = chunk["score"]

            r1 = raw1_results.get(chunk_id, {})
            r2 = raw2_results.get(chunk_id, {})

            if not r1.get("authorized", False) or not r2.get("authorized", False):
                print(f"Not authorized to access chunk {chunk_id}")
                continue
            if not r1.get("found", False) or not r2.get("found", False):
                print(f"DEK for chunk {chunk_id} not found in custodian")
                continue

            encrypted_chunk = chunk["encrypted_data"]
            encrypted_dek = tc.EncryptedMessage.from_json(chunk["encrypted_dek"])
            partial_decryption1 = tc.PartialDecryption.from_json(r1.get("partial_decryption"))
            partial_decryption2 = tc.PartialDecryption.from_json(r2.get("partial_decryption"))

            decryption_start = now()
            dek = decrypt_with_shares(
                encrypted_dek=encrypted_dek,
                p1=partial_decryption1,
                p2=partial_decryption2,
                t=2,
                n=2,
            )
            text = decrypt_bytes(bytes.fromhex(encrypted_chunk), bytes.fromhex(dek)).decode("utf-8")
            benchmark.increment_duration_ms("decryption_ms", benchmark.add_duration("_tmp_decryption_ms", decryption_start))
            benchmark.timings_ms.pop("_tmp_decryption_ms", None)

            if sha256_text(text) != chunk_id:
                print(f"Decrypted text hash mismatch for chunk {chunk_id}: expected {chunk_id}, got {sha256_text(text)}")
                continue

            decrypted_results.append((chunk_id, score, text))

        benchmark.set_counter("authorized_result_count", len(decrypted_results))
        benchmark.add_duration("retrieval_total_ms", total_start)
        return decrypted_results, benchmark.to_dict()
    

    async def answer_query(self, query_text: str, k: int = 3) -> dict:
        total_start = now()
        retrieved, retrieval_benchmark = await self.query_with_benchmark(query_text=query_text, k=k)
        print(f"Time taken for retrieval k={k}: {retrieval_benchmark['timings_ms']['retrieval_total_ms'] / 1000.0:.2f} seconds")
        for chunk_id, score, text in retrieved:
            print(f"Retrieved chunk for RAG: chunk_id={chunk_id[:10]}, score={score:.2f}, text={text}...")

        contexts = [text for _, _, text in retrieved]
        benchmark = BenchmarkReport()

        llm_start = now()
        llm_response = self.llm.generate_answer(
            query=query_text,
            contexts=contexts,
        )
        benchmark.add_duration("llm_ms", llm_start)
        for name, value in retrieval_benchmark["timings_ms"].items():
            benchmark.set_duration_ms(name, value)
        for name, value in retrieval_benchmark["counters"].items():
            benchmark.set_counter(name, value)
        benchmark.add_duration("total_ms", total_start)

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
            "benchmark": benchmark.to_dict(),
        }
