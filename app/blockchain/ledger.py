from __future__ import annotations

from app.domain.models import LedgerEntry,DataOwner


class SimpleLedger:
    def __init__(self) -> None:
        self.entries: list[LedgerEntry] = []

    def add_entry(self, entry_type: str, payload: dict) -> None:
        self.entries.append(LedgerEntry(entry_type=entry_type, payload=payload))

    def register_dataOwner(self, dataOwner: DataOwner) -> None:
        self.add_entry(
            "register_user",
            {
                "user_id": user_id,
                "name": name,
            },
        )

    def register_dataset(
        self,
        dataset_id: str,
        owner_id: str,
        document_name: str,
        merkle_root: str,
        chunk_ids: list[str],
    ) -> None:
        self.add_entry(
            "register_dataset",
            {
                "dataset_id": dataset_id,
                "owner_id": owner_id,
                "document_name": document_name,
                "merkle_root": merkle_root,
                "chunk_ids": chunk_ids,
            },
        )

    def grant_authorization(self, user_id: str, dataset_id: str) -> None:
        self.add_entry(
            "grant_authorization",
            {
                "user_id": user_id,
                "dataset_id": dataset_id,
            },
        )

    def is_authorized(self, user_id: str, dataset_id: str) -> bool:
        for entry in self.entries:
            if (
                entry.entry_type == "grant_authorization"
                and entry.payload["user_id"] == user_id
                and entry.payload["dataset_id"] == dataset_id
            ):
                return True
        return False

    def print_entries(self) -> None:
        for i, entry in enumerate(self.entries):
            print(f"[{i}] {entry.entry_type}: {entry.payload}")