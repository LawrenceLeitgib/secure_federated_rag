from __future__ import annotations

from dataclasses import dataclass
from enum import Enum



@dataclass
class User:
    user_id: str
    name: str


@dataclass
class LedgerEntry:
    entry_type: str
    payload: dict


class LedgerEntryType(Enum):
    REGISTER_USER = "register_user"
    REGISTER_DATASET = "register_dataset"
    GRANT_AUTHORIZATION = "grant_authorization"


@dataclass
class QueryResult:
    chunk_id: str
    score: float
    text: str

