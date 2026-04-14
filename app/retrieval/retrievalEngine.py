import asyncio
from dataclasses import dataclass, field
import hashlib
import time

from app.common.clients.blockchain_client import BlockchainClient
from app.common.clients.custodian_client import CustodianClient
from app.common.clients.storage_client import StorageClient
from app.common.crypto.asymmetric import decrypt_with_shares
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
        query_embedding = self.embedder.embed_text(query_text, is_query=True)

        queryResults = self.embeddings.search(query_embedding, k=k)

        print(f"RetrievalEngine found {len(queryResults)} results for query: {query_text}")

       
       
        decrypted_results: list[tuple[str, float, str]] = []

        for chunk_id, score in queryResults:
            encrypted_chunk_payload = await self.storage_client.retrieve_chunk_async(chunk_id)
            if encrypted_chunk_payload.get("status") != "ok":
                raise RuntimeError(f"Failed to retrieve chunk {chunk_id} from storage server")
           
            raw1=await self.custodian_clients[0].get_partial_decryption(re_id=self.re_id, chunk_id=chunk_id,encrypted_dek=encrypted_chunk_payload.get("result").get("encrypted_dek"))
            if raw1.get("status") != "ok":
                raise RuntimeError(f"Failed to retrieve chunk {chunk_id} from custodian 1")
            raw2=await self.custodian_clients[1].get_partial_decryption(re_id=self.re_id, chunk_id=chunk_id,encrypted_dek=encrypted_chunk_payload.get("result").get("encrypted_dek"))
            if raw2.get("status") != "ok":
                raise RuntimeError(f"Failed to retrieve chunk {chunk_id} from custodian 2")
            
            if(raw1.get("result").get("authorized") == False or raw2.get("result").get("authorized") == False):
                print(f"Not authorized to access chunk {chunk_id}")
                continue
            if(raw1.get("result").get("found") == False or raw2.get("result").get("found") == False):
                print(f"DEK for chunk {chunk_id} not found in custodian")
                continue   
 
            encrypted_chunk = encrypted_chunk_payload.get("result").get("encrypted_data")
            encrypted_dek = tc.EncryptedMessage.from_json(encrypted_chunk_payload.get("result").get("encrypted_dek"))

            partial_decryption1 = tc.PartialDecryption.from_json(raw1.get("result").get("partial_decryption"))
            partial_decryption2 = tc.PartialDecryption.from_json(raw2.get("result").get("partial_decryption"))
           
            # Combine partial decryptions to get the DEK
            dek = decrypt_with_shares(
                encrypted_dek=encrypted_dek,
                p1=partial_decryption1,
                p2=partial_decryption2,
                t=2,
                n=2,
            )
            text=decrypt_bytes(bytes.fromhex(encrypted_chunk), bytes.fromhex(dek)).decode("utf-8")
            
           
            decrypted_results.append(
                (chunk_id, score, text)
            )

        return decrypted_results
    

    async def answer_query(self, query_text: str, k: int = 3) -> dict:
        startTime=time.time()
        retrieved = await self.query(query_text=query_text, k=k)
        finishTime=time.time()
        print(f"Time taken for retrieval k={k}: {finishTime - startTime:.2f} seconds")
        for chunk_id, score, text in retrieved:
            print(f"Retrieved chunk for RAG: chunk_id={chunk_id[:10]}, score={score:.2f}, text={text}...")

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