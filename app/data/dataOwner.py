from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from typing import List, Optional

from app.blockchain.ledger import  SimpleLedger
from app.crypto.signing import generate_key_pairs, sign_data, verify_signature
from app.crypto.symmetric import encrypt_bytes, generate_key,generate_dummy_kek
from app.custodians.custodian import Custodian, split_key_dummy
from app.data.chunking import Dataset, EncryptedChunk, chunk_text
from app.data.merkle import build_merkle_root
from app.retrieval.embeddings import embed_text_dummy
from app.storage.provider import LocalStorageProvider

@dataclass
class DataOwner:
    user_id: str
    name: str
    # Keys are expected to be PEM-encoded bytes. Private keys may be password
    # protected in which case pass the password to signing calls.
    private_key: bytes
    public_key: bytes

    dataset_list: List[Dataset] = field(default_factory=list)

    #add a constructor that that a name and return a dataOwner with a generated key pair and a user_id that is the sha256 hash of the public key
    @classmethod
    def create(cls, name: str, password: Optional[bytes] = None) -> DataOwner:
        private_key, public_key = generate_key_pairs()
        user_id = hashlib.sha256(public_key).hexdigest()
        return cls(
            user_id=user_id,
            name=name,
            private_key=private_key,
            public_key=public_key,
        )

    def sign(self, data: bytes, password: Optional[bytes] = None) -> bytes:
        return sign_data(self.private_key, data, password=password)

    def verify(self, data: bytes, signature: bytes) -> bool:
    
        return verify_signature(self.public_key, data, signature)
    
    def upload_document(
        self,
        owner_id: str,
        document_name: str,
        text: str,
        custodians: List[Custodian],
        storage: LocalStorageProvider,
        ledger: SimpleLedger,
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
                chunk_id=chunk.chunk_id,
                encrypted_data=encrypted_chunk,
                encrypted_dek=encrypted_dek
            )
            encrypted_chunks.append(encrypted_chunk)

            storage.upload_chunk(encrypted_chunk )

            

          

            

        merkle_root = build_merkle_root(leaf_hashes)
        dataset = Dataset(
            dataset_id=merkle_root,
            owner_id=owner_id,
            document_name=document_name,
            chunks=chunks,
        )

        share1, share2 = split_key_dummy(kek)
        custodians[0].store_share(merkle_root, share1)
        custodians[1].store_share(merkle_root, share2)


       
       
        self.dataset_list.append(dataset)

        return dataset
    
    def get_embeddings(self, dataset_id: str) -> list[tuple[str, list[float]]]:
        dataset = next((d for d in self.dataset_list if d.dataset_id == dataset_id), None)
        if dataset is None:
            raise KeyError(f"Dataset {dataset_id} not found for owner {self.user_id}")
        return [(chunk.chunk_id, chunk.embedding) for chunk in dataset.chunks]



