from __future__ import annotations

from app.common.chunking import EncryptedChunk


class LocalStorageProvider:
    def __init__(self) -> None:
        self.storage: dict[str, dict[str, bytes]] = {}

    def upload_chunk(self, encrypted_chunk: EncryptedChunk) -> None:
        print(f"LocalStorageProvider: Storing chunk {encrypted_chunk.chunk_id}")
        self.storage[encrypted_chunk.chunk_id] = {
            "encrypted_chunk": encrypted_chunk.encrypted_data,
            "encrypted_dek": encrypted_chunk.encrypted_dek,
            "dataset_id": encrypted_chunk.dataset_id,
        }

    def get_chunk(self, chunk_id: str) -> EncryptedChunk:
        if chunk_id not in self.storage:
            raise KeyError(f"Chunk {chunk_id} not found in storage")

        entry = self.storage[chunk_id]
        return EncryptedChunk(
            dataset_id=entry["dataset_id"],
            chunk_id=chunk_id,
            encrypted_data=entry["encrypted_chunk"],
            encrypted_dek=entry["encrypted_dek"],
        )
    