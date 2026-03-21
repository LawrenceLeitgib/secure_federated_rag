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
        self.entries.append(SignedLedgerEntry)

    def is_authorized(self, user_id: str, dataset_id: str) -> bool:
        for entry in self.entries:
            if entry.entry_type == LedgerEntryType.GRANT_AUTHORIZATION:
                payload: GrantAuthorizationPayload = entry.payload
                if payload.re_id == user_id and payload.dataset_id == dataset_id:   
                    return True
        return False

    def print_entries(self) -> None:
        for i, entry in enumerate(self.entries):
            print(f"[{i}] {entry.entry_type}: {entry.payload}")

