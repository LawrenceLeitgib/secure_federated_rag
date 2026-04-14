from __future__ import annotations

from ..common.ledger_interaction import (
    GrantAuthorizationPayload,
    LedgerEntryType,
    SignedLedgerEntry,
)


class SimpleLedger:
    def __init__(self) -> None:
        self.entries: list[SignedLedgerEntry] = []

    def add_entry(self, SignedLedgerEntry: SignedLedgerEntry) -> None:
        print(f"Adding ledger entry: {SignedLedgerEntry.entry_type} with payload: {SignedLedgerEntry.payload}")
        self.entries.append(SignedLedgerEntry)

    def is_authorized(self, user_id: str, dataset_id: str) -> bool:
        print(f"Checking authorization for user: {user_id}, dataset: {dataset_id}")
        for entry in self.entries:
            if entry.entry_type == LedgerEntryType.GRANT_AUTHORIZATION:
                payload: GrantAuthorizationPayload = entry.payload
                if payload.re_id == user_id and payload.dataset_id == dataset_id:   
                    return True
        return False
    
    def get_chunk_metadata(self, chunk_id: str) -> dict[str, str | dict]:
        print(f"Retrieving metadata for chunk: {chunk_id}")
        for entry in self.entries:
            if entry.entry_type == LedgerEntryType.REGISTER_DATASET:
                payload = entry.payload
                chunk_id_to_encrypted_dek_hash = payload.chunk_id_to_encrypted_dek_hash

                if chunk_id in chunk_id_to_encrypted_dek_hash:
                    return {
                        "status": "ok",
                        "result": {
                            "dataset_id": payload.dataset_id,
                            "encrypted_dek_hash": chunk_id_to_encrypted_dek_hash[chunk_id],
                        },
                    }
        return {"status": "error", "error": "Chunk not found"}

    def print_entries(self) -> None:
        for i, entry in enumerate(self.entries):
            print(f"[{i}] {entry.entry_type}: {entry.payload}")

