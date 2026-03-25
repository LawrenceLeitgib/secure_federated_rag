from __future__ import annotations

from app.common.chunking import EncryptedChunk


class LocalStorageProvider:
    def __init__(self) -> None:
        self.storage: dict[str, EncryptedChunk] = {}

    def upload_chunk(self, encrypted_chunk: EncryptedChunk) -> None:
        print(f"LocalStorageProvider: Storing chunk {encrypted_chunk.chunk_id}")
        self.storage[encrypted_chunk.chunk_id] = encrypted_chunk

    def get_chunk(self, chunk_id: str) -> EncryptedChunk:
        if chunk_id not in self.storage:
            raise KeyError(f"Chunk {chunk_id} not found in storage")

        return self.storage[chunk_id]