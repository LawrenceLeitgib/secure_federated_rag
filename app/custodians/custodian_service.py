# app/custodians/service.py
from __future__ import annotations

from typing import Any, Optional

from app.custodians.custodian import Custodian
from app.common.clients.storage_client import StorageClient
from app.common.clients.blockchain_client import BlockchainClient
from app.common.ledger_interaction import register_custodian_share  # if you add this kind of helper


class CustodianService:
    def __init__(
        self,
        custodian_id: str,
    ) -> None:
        self.custodian = Custodian(custodian_id=custodian_id)
        self.storage_client =   StorageClient()       # storage server
        self.blockchain_client = BlockchainClient() # ledger server

    def store_share(self, dataset_id: str, share: bytes) -> None:
        # 1. Store locally in the custodian domain object
        self.custodian.store_share(dataset_id, share)

        # 2. Optionally, register something on blockchain
        if self.blockchain_client is not None:
            # e.g., write a record that this custodian holds a share
            # The exact API depends on your ledger_interaction module
            entry = register_custodian_share(
                custodian_id=self.custodian.custodian_id,
                dataset_id=dataset_id,
            )
            self.blockchain_client.add_record(entry)

    def get_share(self, dataset_id: str) -> bytes | None:
        return self.custodian.get_share(dataset_id)
    
    def get_plain_text_chunk(self, dataset_id: str) -> tuple[dict[str, Any] | None, bool]:
        if self.blockchain_client is not None:
            # Check if the custodian is authorized to access this dataset
            if not self.blockchain_client.is_custodian_authorized(self.custodian.custodian_id, dataset_id):
                return None, False  # Not authorized
        else :
            raise RuntimeError("Blockchain client not available for authorization check")


        if self.storage_client is not None:
            return self.storage_client.retrieve_plaintext_chunk(dataset_id), True
        return None, True