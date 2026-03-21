from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
import hashlib
from typing import List, Optional

from app.common.crypto.signing import generate_key_pairs, sign_data, verify_signature
from app.common.crypto.symmetric import encrypt_bytes, generate_key,generate_dummy_kek
from app.common.ledger_interaction import register_dataset, register_user
from app.custodians.custodian import split_key_dummy
from app.common.chunking import Dataset, EncryptedChunk, chunk_text
from app.data_owner.merkle import build_merkle_root
from app.retrieval.embeddings import embed_text_dummy

from app.common.clients.storage_client import StorageClient
from app.common.clients.blockchain_client import BlockchainClient
from app.common.clients.custodian_client import CustodianClient
from app.common.clients.retrieval_client import RetrievalClient

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
    custodian_client: CustodianClient
    retrieval_client: RetrievalClient

    dataset_list: List[Dataset] = field(default_factory=list)

    #add a constructor that that a name and return a dataOwner with a generated key pair and a user_id that is the sha256 hash of the public key
    @classmethod
    async def create(
        cls,
        name: str,
        storage_client: StorageClient,
        blockchain_client: BlockchainClient,
        custodian_client: CustodianClient,
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
            custodian_client=custodian_client,
            retrieval_client=retrieval_client,
    )

    
    async def upload_document(
        self,
        document_name: str,
        text: str,
        chunk_size: int = 300,
        overlap: int = 50,
    ) -> Dataset:
        chunks = chunk_text(text, chunk_size=chunk_size, overlap=overlap)

       
        #creat a kek 
        kek = generate_dummy_kek()
      
        leaf_hashes: list[str] = []

        encrypted_chunks: list[EncryptedChunk] = []

        for chunk in chunks:
            leaf_hashes.append(chunk.chunk_id)
            chunk.embedding = embed_text_dummy(chunk.text)


            dek=generate_key()
            encrypted_chunk = encrypt_bytes(chunk.text.encode("utf-8"), dek)

            encrypted_dek = encrypt_bytes(dek,kek)

            encrypted_chunk = EncryptedChunk(
                dataset_id="", # we can fill this in later with the merkle root
                chunk_id=chunk.chunk_id,
                encrypted_data=encrypted_chunk,
                encrypted_dek=encrypted_dek

            )
            encrypted_chunks.append(encrypted_chunk)


        merkle_root = build_merkle_root(leaf_hashes)

        for chunk in chunks:
            chunk.dataset_id = merkle_root
        
        #update the dataset_id in encrypted_chunks to be the merkle root
        for enc_chunk in encrypted_chunks:
            enc_chunk.dataset_id = merkle_root
            
        
        results = await asyncio.gather(
        *(self.storage_client.upload_chunk_async(enc_chunk) for enc_chunk in encrypted_chunks),
         return_exceptions=True,
        )


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


        signedLedgerEntry= register_dataset(dataset,self.user_id ,self.private_key)
        await self.blockchain_client.add_record(signedLedgerEntry)
        share1, share2 = split_key_dummy(kek)
        await self.custodian_client.store_share(merkle_root, share1)
        #await self.custodian_client.store_share(merkle_root, share2)

        self.dataset_list.append(dataset)
        return dataset
    
    def get_embeddings(self, dataset_id: str) -> list[tuple[str, list[float]]]:
        dataset = next((d for d in self.dataset_list if d.dataset_id == dataset_id), None)
        if dataset is None:
            raise KeyError(f"Dataset {dataset_id} not found for owner {self.user_id}")
        return [(chunk.chunk_id, chunk.embedding) for chunk in dataset.chunks]



