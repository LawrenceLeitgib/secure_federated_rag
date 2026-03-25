from __future__ import annotations

from app.common.chunking import Chunk, EncryptedChunk
from app.common.crypto.symmetric import decrypt_bytes

import threshold_crypto as tc

class Custodian:
    def __init__(self, custodian_id: str) -> None:
        self.custodian_id = custodian_id
        self.key_shares: dict[str, tc.KeyShare] = {}

    def store_share(self, dataset_id: str, share: tc.KeyShare) -> None:
        self.key_shares[dataset_id] = share

    def get_share(self, dataset_id: str) -> tc.KeyShare | None:
        if dataset_id not in self.key_shares:
            print(f"No share stored for dataset {dataset_id}")
            print(f"Available shares: {self.key_shares}")
            return None
        return self.key_shares[dataset_id]
    
    def get_partial_decryption(self, encrypted_dek: str, dataset_id: str) -> str | None:
        share = self.get_share(dataset_id)
        if(share is None):
            return None
        partial_decryption = tc.compute_partial_decryption(tc.EncryptedMessage.from_json(encrypted_dek), share)
        return partial_decryption.to_json()