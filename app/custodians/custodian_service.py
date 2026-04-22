# app/custodians/service.py
from __future__ import annotations

from typing import Any, Optional

from numpy import byte

from app.common.benchmarking import BenchmarkReport, now
from app.common.chunking import Chunk, EncryptedChunk
from app.common.crypto.hashing import sha256_text
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
        #check the blockain to verify that the user_id own the dataset.
        owner_id = await self.blockchain_client.get_dataset_owner(dataset_id)
        if owner_id != user_id:
            raise RuntimeError(f"User {user_id} is not the owner of dataset {dataset_id}")

        print(f"Storing share for dataset: {dataset_id}, user: {user_id}, share: {share}")
        # 1. Store locally in the custodian domain object
        self.custodian.store_share(dataset_id, share)

   
    async def get_partial_decryption(self, re_id: str,chunk_id: str, encrypted_dek: str) -> tuple[str | None, bool, dict]:
        print(f"Retrieving partial decryption for chunk: {chunk_id}")
        if self.blockchain_client is  None:
            raise RuntimeError("Blockchain client not available for authorization check")

        benchmark = BenchmarkReport()
        total_start = now()

        metadata_start = now()
        chunkMetadata = await self.blockchain_client.get_chunk_metadata(chunk_id)
        benchmark.add_duration("blockchain_get_chunk_metadata_ms", metadata_start)
        if chunkMetadata.get("status") != "ok":
            raise RuntimeError(f"Failed to retrieve chunk metadata: {chunkMetadata.get('error')}")
        metadata_result = chunkMetadata.get("result")
        dataset_id = metadata_result.get("dataset_id")

        auth_start = now()
        authorized = await self.blockchain_client.is_authorized(re_id, dataset_id)
        benchmark.add_duration("blockchain_is_authorized_ms", auth_start)
       
        if not authorized:
            print(f"User {re_id} is not authorized to access dataset {dataset_id}")
            benchmark.set_duration_ms(
                "blockchain_ms",
                benchmark.timings_ms["blockchain_get_chunk_metadata_ms"]
                + benchmark.timings_ms["blockchain_is_authorized_ms"],
            )
            benchmark.add_duration("total_ms", total_start)
            return None, False, benchmark.to_dict()
        encrypted_dek_hash= metadata_result.get("encrypted_dek_hash")
        if encrypted_dek_hash != sha256_text(encrypted_dek):
            print(f"Encrypted DEK hash mismatch for chunk {chunk_id}: expected {encrypted_dek_hash}, got {sha256_text(encrypted_dek.encode()).hexdigest()}")
            benchmark.set_duration_ms(
                "blockchain_ms",
                benchmark.timings_ms["blockchain_get_chunk_metadata_ms"]
                + benchmark.timings_ms["blockchain_is_authorized_ms"],
            )
            benchmark.add_duration("total_ms", total_start)
            return None, False, benchmark.to_dict()
        partial_start = now()
        partial_decryption = self.custodian.get_partial_decryption(encrypted_dek, dataset_id)
        benchmark.add_duration("partial_decryption_ms", partial_start)
        benchmark.set_duration_ms(
            "blockchain_ms",
            benchmark.timings_ms["blockchain_get_chunk_metadata_ms"]
            + benchmark.timings_ms["blockchain_is_authorized_ms"],
        )
        benchmark.add_duration("total_ms", total_start)
        return partial_decryption, True, benchmark.to_dict()
