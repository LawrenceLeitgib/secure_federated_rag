from __future__ import annotations

from app.blockchain.ledger import SimpleLedger
from app.crypto.hashing import sha256_text
from app.crypto.symmetric import encrypt_bytes, decrypt_bytes, generate_key
from app.custodians.custodian import (
    Custodian,
    split_key_dummy,
    reconstruct_key_dummy,
)
from app.domain.models import Dataset, User,DataOwner,RetrievalEngine
from app.ingestion.chunking import chunk_text
from app.ingestion.merkle import build_merkle_root
from app.retrieval.embeddings import embed_text_dummy
from app.retrieval.vector_index import SimpleVectorIndex
from app.storage.provider import LocalStorageProvider


class SystemOrchestrator:
    def __init__(self) -> None:
        self.ledger = SimpleLedger()
        self.storage = LocalStorageProvider()
        self.custodian_a = Custodian("custodian_a")
        self.custodian_b = Custodian("custodian_b")
        self.dataOwners: dict[str, DataOwner] = {}
        self.users: dict[str, User] = {}
        self.retrieval_engines: dict[str, RetrievalEngine] = {}

    def register_dataOwner(self, dataOwner: DataOwner) -> None:
        self.ledger.register_DataOwner(dataOwner)

    def upload_document(
        self,
        owner_id: str,
        dataset_id: str,
        document_name: str,
        text: str,
        chunk_size: int = 300,
        overlap: int = 50,
    ) -> Dataset:
        chunks = chunk_text(text, chunk_size=chunk_size, overlap=overlap)

        dataset = Dataset(
            dataset_id=dataset_id,
            owner_id=owner_id,
            document_name=document_name,
            chunks=chunks,
        )

        kek = generate_key()
        share1, share2 = split_key_dummy(kek)
        self.custodian_a.store_share(dataset_id, share1)
        self.custodian_b.store_share(dataset_id, share2)

        leaf_hashes: list[str] = []

        for chunk in dataset.chunks:
            chunk.hash_value = sha256_text(chunk.text)
            leaf_hashes.append(chunk.hash_value)

            encrypted_chunk = encrypt_bytes(chunk.text.encode("utf-8"), kek)

            # dummy: we “encrypt” the DEK by just storing the KEK itself
            encrypted_dek = kek

            chunk.encrypted_data = encrypted_chunk
            chunk.encrypted_dek = encrypted_dek
            chunk.embedding = embed_text_dummy(chunk.text)

            self.storage.upload_chunk(
                chunk_id=chunk.chunk_id,
                encrypted_chunk=encrypted_chunk,
                encrypted_dek=encrypted_dek,
            )

            self.vector_index.add(
                chunk_id=chunk.chunk_id,
                embedding=chunk.embedding,
                text=chunk.text,
            )

        dataset.merkle_root = build_merkle_root(leaf_hashes)
        self.datasets[dataset_id] = dataset

        self.ledger.register_dataset(
            dataset_id=dataset.dataset_id,
            owner_id=dataset.owner_id,
            document_name=dataset.document_name,
            merkle_root=dataset.merkle_root,
            chunk_ids=[chunk.chunk_id for chunk in dataset.chunks],
        )

        return dataset

    def grant_access(self, user_id: str, dataset_id: str) -> None:
        self.ledger.grant_authorization(user_id, dataset_id)

    def query(self, user_id: str, dataset_id: str, query_text: str, k: int = 3) -> list[str]:
        if not self.ledger.is_authorized(user_id, dataset_id):
            raise PermissionError(f"User {user_id} is not authorized for dataset {dataset_id}")

        query_embedding = embed_text_dummy(query_text)
        results = self.vector_index.search(query_embedding, k=k)

        share1 = self.custodian_a.get_share(dataset_id)
        share2 = self.custodian_b.get_share(dataset_id)
        kek = reconstruct_key_dummy(share1, share2)

        decrypted_results: list[str] = []

        for result in results:
            encrypted_chunk, _ = self.storage.get_chunk(result.chunk_id)
            plaintext = decrypt_bytes(encrypted_chunk, kek).decode("utf-8")
            decrypted_results.append(
                f"[chunk_id={result.chunk_id} | score={result.score:.4f}] {plaintext}"
            )

        return decrypted_results