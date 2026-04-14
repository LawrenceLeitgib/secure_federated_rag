# app/data_owner/service.py
from __future__ import annotations

from app.common.clients.blockchain_client import BlockchainClient
from app.common.clients.custodian_client import CustodianClient
from app.common.clients.retrieval_client import RetrievalClient
from app.common.clients.storage_client import StorageClient
from app.common.ledger_interaction import add_authorization_entry, register_user
from app.data_owner.data_owner import DataOwner
# plus imports for storage, blockchain, custodian, retrieval if you move them out


class DataOwnerService:
    def __init__(self) -> None:
        self.owner: DataOwner | None = None
        self.storage_client = StorageClient()
        self.custodian_clients = [CustodianClient(), CustodianClient(port=9002)]  
        self.blockchain_client = BlockchainClient()
        self.retrieval_client = RetrievalClient()
        
    async def create_owner(self, name: str) -> dict:
        self.owner = await DataOwner.create(name, self.storage_client, self.blockchain_client, self.custodian_clients, self.retrieval_client)
        return {
            "user_id": self.owner.user_id,
            "name": self.owner.name,
            "public_key": self.owner.public_key.decode("utf-8"),
        }
    
    def _require_owner(self) -> DataOwner:
        if self.owner is None:
            raise ValueError("No data owner created yet")
        return self.owner

    def get_owner_info(self) -> dict:
        owner = self._require_owner()
        return {
            "user_id": owner.user_id,
            "name": owner.name,
            "public_key": owner.public_key.decode("utf-8"),
        }

    async def upload_text_document(
        self,
        document_name: str,
        text: str,
    ) -> dict:
        owner = self._require_owner()

        # For now, `DataOwner.upload_document` owns the whole pipeline:
        # - chunking
        # - encryption
        # - calling LocalStorageProvider
        # - calling custodians
        # - computing Merkle root
        dataset = await owner.upload_document(
            document_name=document_name,
            text=text
        )

        return {
            "dataset_id": dataset.dataset_id,
            "owner_id": dataset.owner_id,
            "document_name": dataset.document_name,
            "num_chunks": len(dataset.chunks),
        }
    
    async def give_embeddings(self, dataset_id: str, re_id: str) -> None:
        owner = self._require_owner()
        await self.retrieval_client.add_embeddings(re_id, owner.get_embeddings(dataset_id))

    async def grant_authorization(self, dataset_id: str, re_id: str) -> None:
        owner = self._require_owner()
        await self.blockchain_client.add_record(add_authorization_entry(
            dataOwner_id=owner.user_id,
            dataset_id=dataset_id,
            re_id=re_id,
            private_key=owner.private_key,) )
        
    async def give_access(self, dataset_id: str, re_id: str) -> None:
        await self.grant_authorization(dataset_id, re_id)
        await self.give_embeddings(dataset_id, re_id)

    async def get_retrieval_engine_id(self) -> str:
        # For simplicity, we assume there's only one retrieval engine and we can get its id from the retrieval client
        re_id = await self.retrieval_client.get_re_id()
        return re_id


    def list_datasets(self) -> list[dict]:
        owner = self._require_owner()
        return [
            {
                "dataset_id": d.dataset_id,
                "owner_id": d.owner_id,
                "document_name": d.document_name,
                "num_chunks": len(d.chunks),
            }
            for d in owner.dataset_list
        ]