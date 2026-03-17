from __future__ import annotations

from app.blockchain.ledger import SimpleLedger
from app.crypto.symmetric import  decrypt_bytes
from app.custodians.custodian import (
    Custodian,
    reconstruct_key_dummy,
)
from app.data.chunking import Dataset
from app.data.dataOwner import DataOwner
from app.domain.models import User
from app.retrieval.embeddings import embed_text_dummy
from app.retrieval.retrievalEngine import RetrievalEngine
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
        self.dataOwners[dataOwner.user_id]=dataOwner
        self.ledger.register_user(dataOwner.user_id, dataOwner.public_key.decode("utf-8"), dataOwner.private_key)

    def register_retrievalEngine(self, retrieval_engine: RetrievalEngine) -> None:
        self.retrieval_engines[retrieval_engine.re_id]=retrieval_engine
        self.ledger.register_user(retrieval_engine.re_id, retrieval_engine.public_key.decode("utf-8"), retrieval_engine.private_key)
    
    
    def upload_document(self, owner_id: str, document_name: str, text: str) -> Dataset:
        if(owner_id not in self.dataOwners):
            raise KeyError("unknown owner")
        owner=self.dataOwners[owner_id]
        dataset=owner.upload_document(
            owner_id=owner.user_id,
            document_name=document_name,
            text=text,
            custodians=[self.custodian_a, self.custodian_b],
            storage=self.storage,
            ledger=self.ledger,
        )
         #sign the dataset registration with the data owner's private key
        self.ledger.register_dataset(dataset_id=dataset.dataset_id, dataOwner_id=dataset.owner_id, private_key=owner.private_key)
        return dataset
        
            

    def grant_authorization(self,data_owner_id:str,re_id : str, dataset_id: str) -> None:
        if data_owner_id not in self.dataOwners:
            raise KeyError(f"Data owner {data_owner_id} not found")
        if re_id not in self.retrieval_engines:
            raise KeyError(f"Retrieval engine {re_id} not found")

        self.ledger.add_authorization_entry(
            dataOwner_id=data_owner_id,
            dataset_id=dataset_id,
            re_id=re_id,
            private_key=self.dataOwners[data_owner_id].private_key,
        )


        
    def giveEmbeddings(self, owner_id: str, dataset_id: str,re_id: str) -> list[tuple[str, list[float]]]:
        if not self.ledger.is_authorized(re_id, dataset_id):
            raise PermissionError(f"Retrieval engine {re_id} is not authorized for dataset {dataset_id}") ##TODO should we check here?
        dataset = None
        for dataOwner in self.dataOwners.values():
            if dataset_id in [d.dataset_id for d in dataOwner.datasets]:
                dataset = next(d for d in dataOwner.datasets if d.dataset_id == dataset_id)
                break

        if dataset is None:
            raise KeyError(f"Dataset {dataset_id} not found")

        return [(chunk.chunk_id, chunk.embedding) for chunk in dataset.chunks]

        
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