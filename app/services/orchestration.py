from __future__ import annotations

from app.blockchain.ledger import SimpleLedger
from app.common.crypto.symmetric import  decrypt_bytes
from app.custodians.custodian import (
    Custodian,
    reconstruct_key_dummy,
)
from app.common.chunking import Dataset
from app.data_owner.dataOwner import DataOwner
from app.retrieval.retrievalEngine import RetrievalEngine
from app.storage.provider import LocalStorageProvider


class SystemOrchestrator:
    def __init__(self) -> None:
        self.ledger = SimpleLedger()
        self.storage = LocalStorageProvider()
        self.custodian_a = Custodian("custodian_a")
        self.custodian_b = Custodian("custodian_b")
        self.dataOwners: dict[str, DataOwner] = {}
        self.retrieval_engines: dict[str, RetrievalEngine] = {}



        


        
