from __future__ import annotations


class LocalStorageProvider:
    def __init__(self) -> None:
        self.storage: dict[str, dict[str, bytes]] = {}

    def upload_chunk(self, chunk_id: str, encrypted_chunk: bytes, encrypted_dek: bytes) -> None:
        self.storage[chunk_id] = {
            "encrypted_chunk": encrypted_chunk,
            "encrypted_dek": encrypted_dek,
        }

    def get_chunk(self, chunk_id: str) -> tuple[bytes, bytes]:
        if chunk_id not in self.storage:
            raise KeyError(f"Chunk {chunk_id} not found in storage")

        entry = self.storage[chunk_id]
        return entry["encrypted_chunk"], entry["encrypted_dek"]