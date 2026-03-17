from __future__ import annotations
from typing import Union
from dataclasses import asdict, dataclass
import json
from typing import Optional

from app.crypto.signing import sign_data, verify_signature
from app.domain.models import LedgerEntryType


class SimpleLedger:
    def __init__(self) -> None:
        self.entries: list[SignedLedgerEntry] = []

    def add_entry(self, SignedLedgerEntry: SignedLedgerEntry) -> None:
        self.entries.append(SignedLedgerEntry)

    def register_user(self, id: str, public_key: str,private_key: bytes) -> None:
        payload = RegisterUser(
            id=id,
            public_key=public_key,
        )
        ledger_entry = LedgerEntry(
            entry_type=LedgerEntryType.REGISTER_USER,
            payload=payload
        )
        sign_entry = sign_ledger_entry(ledger_entry,private_key)
        self.add_entry(sign_entry)

    def register_dataset(self, dataset_id: str, dataOwner_id: str, private_key: bytes) -> None:
        payload = RegisterDatasetPayload(
            dataset_id=dataset_id,
            owner_id=dataOwner_id,
        )
        ledger_entry = LedgerEntry(
            entry_type=LedgerEntryType.REGISTER_DATASET,
            payload=payload
        )
        sign_entry = sign_ledger_entry(ledger_entry,private_key)
        self.add_entry(sign_entry)

    def add_authorization_entry(self, dataOwner_id: str, dataset_id: str, re_id: str, private_key: bytes) -> None:
        payload = GrantAuthorizationPayload(
            dataOwner_id=dataOwner_id,
            dataset_id=dataset_id,
            re_id=re_id,
        )
        ledger_entry = LedgerEntry(
            entry_type=LedgerEntryType.GRANT_AUTHORIZATION,
            payload=payload
        )
        sign_entry = sign_ledger_entry(ledger_entry,private_key)
        self.add_entry(sign_entry)  

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



@dataclass
class RegisterUser:
    id: str
    public_key: str


@dataclass
class RegisterDatasetPayload:
    dataset_id: str
    owner_id: str


@dataclass
class GrantAuthorizationPayload:
    dataOwner_id: str
    re_id: str
    dataset_id: str

LedgerPayload = Union[
    RegisterUser,
    RegisterDatasetPayload,
    GrantAuthorizationPayload,
]


@dataclass
class LedgerEntry:
    entry_type: LedgerEntryType
    payload: LedgerPayload

    def to_dict(self) -> dict:
        return {
            "entry_type": self.entry_type.value,
            "payload": asdict(self.payload),
        }

    def to_canonical_bytes(self) -> bytes:
        """
        Convert to a stable JSON byte representation.
        This is what should be signed.
        """
        return json.dumps(
            self.to_dict(),
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    
@dataclass
class SignedLedgerEntry:
    entry_type: LedgerEntryType
    payload: LedgerPayload
    signature: str  # base64 string

    def to_dict(self) -> dict:
        return {
            "entry_type": self.entry_type.value,
            "payload": asdict(self.payload),
            "signature": self.signature,
        }


def sign_ledger_entry(entry: LedgerEntry, private_key: bytes,password: Optional[bytes] = None) -> SignedLedgerEntry:
    message = entry.to_canonical_bytes()
    signature = sign_data( private_key,message, password=password)
    

    return SignedLedgerEntry(
        entry_type=entry.entry_type,
        payload=entry.payload,
        signature=signature,
    )


def verify_signed_ledger_entry(
    signed_entry: SignedLedgerEntry,
    public_key: bytes,
) -> bool:
    unsigned_entry = LedgerEntry(
        entry_type=signed_entry.entry_type,
        payload=signed_entry.payload,
    )
    message = unsigned_entry.to_canonical_bytes()
    return  verify_signature(public_key, message, signed_entry.signature)