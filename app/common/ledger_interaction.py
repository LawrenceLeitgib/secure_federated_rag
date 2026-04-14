from __future__ import annotations
import base64
from enum import Enum
from typing import Union
from dataclasses import asdict, dataclass
import json
from typing import Optional

from app.common.crypto.signing import sign_data, verify_signature



def register_user(id: str, public_key: str, private_key: bytes) -> SignedLedgerEntry:
    payload = RegisterUser(
        id=id,
        public_key=public_key,
    )
    ledger_entry = LedgerEntry(
        entry_type=LedgerEntryType.REGISTER_USER,
        payload=payload
    )
    sign_entry = sign_ledger_entry(ledger_entry,private_key)
    return sign_entry

def register_dataset(dataset_id: str, chunk_id_to_encrypted_dek_hash: dict[str, str], dataOwner_id: str, private_key: bytes) -> SignedLedgerEntry:
    payload = RegisterDatasetPayload(
        dataset_id=dataset_id,
        owner_id=dataOwner_id,
        chunk_id_to_encrypted_dek_hash=chunk_id_to_encrypted_dek_hash,
    )
    ledger_entry = LedgerEntry(
        entry_type=LedgerEntryType.REGISTER_DATASET,
        payload=payload
    )
    sign_entry = sign_ledger_entry(ledger_entry,private_key)
    return sign_entry

def add_authorization_entry(dataOwner_id: str, dataset_id: str, re_id: str, private_key: bytes) -> SignedLedgerEntry:
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
    return sign_entry



class LedgerEntryType(Enum):
    REGISTER_USER = "register_user"
    REGISTER_DATASET = "register_dataset"
    GRANT_AUTHORIZATION = "grant_authorization"

@dataclass
class RegisterUser:
    id: str
    public_key: str


@dataclass
class RegisterDatasetPayload:
    dataset_id: str
    owner_id: str
    chunk_id_to_encrypted_dek_hash: dict[str, str]  # map from chunk_id to encrypted_dek_hash


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
    
    def from_dict(data: dict) -> SignedLedgerEntry:
        entry_type = LedgerEntryType(data["entry_type"])
        payload_data = data["payload"]
        signature = data["signature"]

        if entry_type == LedgerEntryType.REGISTER_USER:
            payload = RegisterUser(**payload_data)
        elif entry_type == LedgerEntryType.REGISTER_DATASET:
            payload = RegisterDatasetPayload(**payload_data)
        elif entry_type == LedgerEntryType.GRANT_AUTHORIZATION:
            payload = GrantAuthorizationPayload(**payload_data)
        else:
            raise ValueError(f"Unknown entry type: {entry_type}")

        return SignedLedgerEntry(
            entry_type=entry_type,
            payload=payload,
            signature=signature,
        )


def sign_ledger_entry(entry: LedgerEntry, private_key: bytes,password: Optional[bytes] = None) -> SignedLedgerEntry:
    message = entry.to_canonical_bytes()
    signature = sign_data( private_key,message, password=password)
    #make the signature a string for easier transmission
    signature = base64.b64encode(signature).decode('utf-8')
    

    return SignedLedgerEntry(
        entry_type=entry.entry_type,
        payload=entry.payload,
        signature=signature
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

