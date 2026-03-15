from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from app.crypto.signing import sign_data, verify_signature


@dataclass
class User:
    user_id: str
    name: str

@dataclass
class DataOwner:
    user_id: str
    name: str
    # Keys are expected to be PEM-encoded bytes. Private keys may be password
    # protected in which case pass the password to signing calls.
    private_key: bytes
    public_key: bytes

    def sign(self, data: bytes, password: Optional[bytes] = None) -> bytes:
        return sign_data(self.private_key, data, password=password)

    def verify(self, data: bytes, signature: bytes) -> bool:
    
        return verify_signature(self.public_key, data, signature)

@dataclass
class Chunk:
    chunk_id: str
    text: str
    encrypted_data: bytes | None = None
    encrypted_dek: bytes | None = None
    embedding: list[float] | None = None
    hash_value: str | None = None


@dataclass
class Dataset:
    dataset_id: str
    owner_id: str
    document_name: str
    chunks: List[Chunk] = field(default_factory=list)
    merkle_root: str | None = None


@dataclass
class LedgerEntry:
    entry_type: str
    payload: dict


@dataclass
class QueryResult:
    chunk_id: str
    score: float
    text: str

@dataclass
class RetrievalEngine:
    name: str
    re_id: str
    private_key: bytes
    public_key: bytes