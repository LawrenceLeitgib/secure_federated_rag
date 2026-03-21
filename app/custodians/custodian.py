from __future__ import annotations

from app.common.chunking import Chunk, EncryptedChunk
from app.common.crypto.symmetric import decrypt_bytes


class Custodian:
    def __init__(self, custodian_id: str) -> None:
        self.custodian_id = custodian_id
        self.key_shares: dict[str, bytes] = {}

    def store_share(self, dataset_id: str, share: bytes) -> None:
        self.key_shares[dataset_id] = share

    def get_share(self, dataset_id: str) -> bytes:
        if dataset_id not in self.key_shares:
            raise KeyError(f"No share stored for dataset {dataset_id}")
        return self.key_shares[dataset_id]
    
    def decrypt_chunk(self, encrypted_chunk: EncryptedChunk) -> Chunk:
        share = self.get_share(encrypted_chunk.dataset_id)
        kek=share
        dek=decrypt_bytes(encrypted_chunk.encrypted_dek, kek)
        plain_text=decrypt_bytes(encrypted_chunk.encrypted_data, dek)
        chunK=Chunk(
            dataset_id=encrypted_chunk.dataset_id,
            chunk_id=encrypted_chunk.chunk_id,
            text=plain_text.decode('utf-8')
        )

        return chunK 
def split_key_dummy(key: bytes) -> tuple[bytes, bytes]:
    return key,key


def reconstruct_key_dummy(share1: bytes, share2: bytes) -> bytes:
    return share1