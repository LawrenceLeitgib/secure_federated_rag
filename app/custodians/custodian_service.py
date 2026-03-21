# app/custodians/service.py
from __future__ import annotations

from typing import Any, Optional

from app.common.chunking import Chunk, EncryptedChunk
from app.custodians.custodian import Custodian
from app.common.clients.storage_client import StorageClient
from app.common.clients.blockchain_client import BlockchainClient


class CustodianService:
    def __init__(
        self,
        custodian_id: str,
    ) -> None:
        self.custodian = Custodian(custodian_id=custodian_id)
        self.storage_client =   StorageClient()       # storage server
        self.blockchain_client = BlockchainClient() # ledger server

    async def store_share(self, dataset_id: str, share: bytes) -> None:
        print(f"Storing share for dataset: {dataset_id}")
        # 1. Store locally in the custodian domain object
        self.custodian.store_share(dataset_id, share)

    async def get_share(self, dataset_id: str) -> bytes | None:
        print(f"Retrieving share for dataset: {dataset_id}")
        return self.custodian.get_share(dataset_id)
    
    async def get_plain_text_chunk(self,user_id: str,chunk_id: str) -> tuple[Chunk | None, bool]:
        print(f"Retrieving plain text chunk: {chunk_id}")
        if self.blockchain_client is not None:
            # Check if the custodian is authorized to access this dataset
            #if not await self.blockchain_client.is_authorized(user_id, dataset_id):
            #    return None, False  # Not authorized
            pass  #TODO: implement a true authorization check here, for now we skip it to test the flow
        else :
            raise RuntimeError("Blockchain client not available for authorization check")


        if self.storage_client is not None:
            encrypted_chunk_payload = await self.storage_client.retrieve_chunk_async(chunk_id)
            if encrypted_chunk_payload.get("status") == "ok":
                result=encrypted_chunk_payload.get("result")
                chunk_id = result.get("chunk_id")
                encrypted_chunk = result.get("encrypted_chunk")
                encrypted_dek= result.get("encrypted_dek")
                # Decrypt the chunk using the custodian's share (DEK)
                chunk = self.custodian.decrypt_chunk(
                    encrypted_chunk=EncryptedChunk(
                        chunk_id=chunk_id,
                        encrypted_data=encrypted_chunk,
                        encrypted_dek=encrypted_dek
                    )
                )

                return chunk, True
              
            else:
                raise RuntimeError(f"Failed to retrieve chunk: {encrypted_chunk_payload.get('error')}")
        return None, True