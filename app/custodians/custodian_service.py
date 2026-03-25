# app/custodians/service.py
from __future__ import annotations

from typing import Any, Optional

from numpy import byte

from app.common.chunking import Chunk, EncryptedChunk
from app.custodians.custodian import Custodian
from app.common.clients.blockchain_client import BlockchainClient

import threshold_crypto as tc


class CustodianService:
    def __init__(
        self,
        custodian_id: str,
    ) -> None:
        self.custodian = Custodian(custodian_id=custodian_id)
        self.blockchain_client = BlockchainClient() # ledger server

    async def store_share(self, user_id: str, dataset_id: str, share: tc.KeyShare) -> None:
        #TODO: in the future, check the blockain to verify that the user_id own the dataset.

        print(f"Storing share for dataset: {dataset_id}, user: {user_id}, share: {share}")
        # 1. Store locally in the custodian domain object
        self.custodian.store_share(dataset_id, share)

   
    async def get_partial_decryption(self,re_id: str,chunk_id: str) -> tuple[str | None, bool]:
        print(f"Retrieving partial decryption for chunk: {chunk_id}")
        if self.blockchain_client is  None:
            raise RuntimeError("Blockchain client not available for authorization check")
        
        chunkMetadata = await self.blockchain_client.get_chunk_metadata(chunk_id)
        if chunkMetadata.get("status") != "ok":
            raise RuntimeError(f"Failed to retrieve chunk metadata: {chunkMetadata.get('error')}")
        metadata_result = chunkMetadata.get("result")
        dataset_id = metadata_result.get("dataset_id")
        authorized = await self.blockchain_client.is_authorized(re_id, dataset_id)
       
        if not authorized:
            print(f"User {re_id} is not authorized to access dataset {dataset_id}")
            return None, False
        encrypted_dek= metadata_result.get("encrypted_dek")
        partial_decryption = self.custodian.get_partial_decryption(encrypted_dek, dataset_id)
        return partial_decryption, True