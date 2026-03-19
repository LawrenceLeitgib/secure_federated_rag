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


        
    def giveEmbeddings(self, owner_id: str, dataset_id: str,re_id: str) -> None:
        if owner_id not in self.dataOwners:
            raise KeyError(f"Data owner {owner_id} not found")
        if re_id not in self.retrieval_engines:
            raise KeyError(f"Retrieval engine {re_id} not found")
      

        embeddings = self.dataOwners[owner_id].get_embeddings(dataset_id)
        self.retrieval_engines[re_id].add_embeddings(embeddings)

        


        
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