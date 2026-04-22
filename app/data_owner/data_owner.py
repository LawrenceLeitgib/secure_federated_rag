from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
import hashlib
from typing import List, Optional

from app.common.benchmarking import BenchmarkReport, now
from app.common.crypto.hashing import sha256_text
from app.common.crypto.signing import generate_key_pairs
from app.common.crypto.symmetric import encrypt_bytes, generate_key
from app.common.crypto.asymmetric import encrypt_with_public_key, generate_threshold_keys
from app.common.ledger_interaction import register_dataset, register_user
from app.common.chunking import Dataset, EncryptedChunk, chunk_text
from app.data_owner.merkle import build_merkle_root

from app.common.clients.storage_client import StorageClient
from app.common.clients.blockchain_client import BlockchainClient
from app.common.clients.custodian_client import CustodianClient
from app.common.clients.retrieval_client import RetrievalClient
from app.retrieval.embeddings import QwenEmbedder

@dataclass
class DataOwner:
    user_id: str
    name: str
    # Keys are expected to be PEM-encoded bytes. Private keys may be password
    # protected in which case pass the password to signing calls.
    private_key: bytes
    public_key: bytes

    storage_client: StorageClient
    blockchain_client: BlockchainClient
    custodian_clients: List[CustodianClient] = field(default_factory=list)
    retrieval_client: RetrievalClient = field(default=None)

    dataset_list: List[Dataset] = field(default_factory=list)
    embedder: QwenEmbedder = field(default_factory=QwenEmbedder)

    

    #add a constructor that that a name and return a dataOwner with a generated key pair and a user_id that is the sha256 hash of the public key
    @classmethod
    async def create(
        cls,
        name: str,
        storage_client: StorageClient,
        blockchain_client: BlockchainClient,
        custodian_clients: List[CustodianClient],
        retrieval_client: RetrievalClient,
        password: Optional[bytes] = None,
    ) -> DataOwner:
        private_key, public_key = generate_key_pairs()
        user_id = hashlib.sha256(public_key).hexdigest()
        sign_entry = register_user(user_id, public_key.decode("utf-8"), private_key)
        await blockchain_client.add_record(sign_entry)
        return cls(
            user_id=user_id,
            name=name,
            private_key=private_key,
            public_key=public_key,
            storage_client=storage_client,
            blockchain_client=blockchain_client,
            custodian_clients=custodian_clients,
            retrieval_client=retrieval_client,
            embedder=QwenEmbedder(),
        )

    
    async def upload_document(
        self,
        document_name: str,
        text: str,
    ) -> Dataset:
        dataset, _ = await self.upload_document_with_benchmark(
            document_name=document_name,
            text=text,
        )
        return dataset

    async def upload_document_with_benchmark(
        self,
        document_name: str,
        text: str,
    ) -> tuple[Dataset, dict]:
        benchmark = BenchmarkReport()
        total_start = now()

        chunking_start = now()
        chunks = chunk_text(text)
        benchmark.add_duration("chunking_ms", chunking_start)
        benchmark.set_counter("num_chunks", len(chunks))

        embedding_start = now()
        chunk_embeddings = await self.embedder.embed_texts(
            [chunk.text for chunk in chunks],
            is_query=False,
        )
        benchmark.add_duration("embedding_generation_ms", embedding_start)

        for chunk, embedding in zip(chunks, chunk_embeddings):
            chunk.embedding = embedding

        keygen_start = now()
        public_kek, shares=  generate_threshold_keys(2, 2)
        benchmark.add_duration("threshold_key_generation_ms", keygen_start)
      
        leaf_hashes: list[str] = []

        encrypted_chunks: list[EncryptedChunk] = []

        encryption_start = now()
        for chunk in chunks:
            leaf_hashes.append(chunk.chunk_id)

            dek=generate_key()
            encrypted_chunk = encrypt_bytes(chunk.text.encode("utf-8"), dek)

            encrypted_dek = encrypt_with_public_key(dek.hex(), public_kek)

            encrypted_chunk = EncryptedChunk(
                dataset_id="", # we can fill this in later with the merkle root
                chunk_id=chunk.chunk_id,
                encrypted_data=encrypted_chunk,
                encrypted_dek=encrypted_dek

            )
            encrypted_chunks.append(encrypted_chunk)
        benchmark.add_duration("chunk_encryption_ms", encryption_start)

        print(f"Leaf hashes: {leaf_hashes}")
        merkle_start = now()
        merkle_root = build_merkle_root(leaf_hashes)
        benchmark.add_duration("merkle_root_ms", merkle_start)

        for chunk in chunks:
            chunk.dataset_id = merkle_root
        
        #update the dataset_id in encrypted_chunks to be the merkle root
        for enc_chunk in encrypted_chunks:
            enc_chunk.dataset_id = merkle_root
            
        storage_start = now()
        results = await asyncio.gather(
        *(self.storage_client.upload_chunk_async(enc_chunk) for enc_chunk in encrypted_chunks),
         return_exceptions=True,
        )
        benchmark.add_duration("storage_upload_ms", storage_start)
        print(f"Finished uploading chunks to storage. Results: {results}")


        dataset = Dataset(
            dataset_id=merkle_root,
            owner_id=self.user_id,
            document_name=document_name,
            chunks=chunks,
        )
        print(f"Dataset {dataset.dataset_id} created with Merkle root {merkle_root} and {len(chunks)} chunks")
        print(f"the chunk IDs are: {'\n '.join(chunk.chunk_id for chunk in chunks)}")
        print()
        print()
        #we want to define a datastructure instead of leaf which is List[str,str] where the first string is the chunk_id and the second string is the encrypted_dek.
        chunk_id_to_encrypted_dek_hash = {chunk.chunk_id: sha256_text(enc_chunk.encrypted_dek) for chunk, enc_chunk in zip(chunks, encrypted_chunks)}
        
        signedLedgerEntry= register_dataset(dataset.dataset_id,chunk_id_to_encrypted_dek_hash,self.user_id ,self.private_key)
        blockchain_start = now()
        r=await self.blockchain_client.add_record(signedLedgerEntry)
        benchmark.add_duration("blockchain_registration_ms", blockchain_start)
        print(f"Registered dataset on blockchain with result: {r}")

        custodian_start = now()
        await self.custodian_clients[0].store_share(self.user_id, merkle_root, shares[0])
        await self.custodian_clients[1].store_share(self.user_id, merkle_root, shares[1])
        benchmark.add_duration("custodian_share_distribution_ms", custodian_start)

        self.dataset_list.append(dataset)
        benchmark.add_duration("total_ms", total_start)
        return dataset, benchmark.to_dict()
    
    def get_embeddings(self, dataset_id: str) -> list[tuple[str, list[float]]]:
        dataset = next((d for d in self.dataset_list if d.dataset_id == dataset_id), None)
        if dataset is None:
            raise KeyError(f"Dataset {dataset_id} not found for owner {self.user_id}")
        return [(chunk.chunk_id, chunk.embedding) for chunk in dataset.chunks]
