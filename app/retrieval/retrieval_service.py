from __future__ import annotations

from typing import Any

from app.common.clients.blockchain_client import BlockchainClient
from app.common.clients.custodian_client import CustodianClient
from app.retrieval.retrievalEngine import RetrievalEngine


class RetrievalEngineService:
    """
    Service layer for retrieval.
    Acts as a client of:
      - Blockchain server (authorization)
      - Custodian servers (shares)
      - Storage server (encrypted chunks)
    """

    # remove heavy async work from __init__
    def __init__(self, engine: RetrievalEngine):
        self.engine = engine

    @classmethod
    async def create(cls, name: str) -> "RetrievalEngineService":
        custodian_client = CustodianClient()
        blockchain_client = BlockchainClient()
        engine = await RetrievalEngine.create(
            name=name,
            custodian_client=custodian_client,
            blockchain_client=blockchain_client,
        )
        return cls(engine)

    # Simple helper to load / update embeddings
    def add_embeddings(self, chunk_embeddings: list[tuple[str, list[float]]]) -> None:
        self.engine.add_embeddings(chunk_embeddings)

    async def query(
        self,
        query_text: str,
        k: int = 3,
    ) -> list[dict[str, Any]]:
      
        results= self.engine.query(query_text=query_text, k=k)

        #make it into a list of dicts with chunk_id, score and text
        decrypted_results = [
            {
                "chunk_id": chunk_id,
                "score": score,
                "text": text
            }
            for chunk_id, score, text in results
        ]

        return decrypted_results

    async def _get_share_from_custodian(
        self,
        custodian_client: CustodianClient,
        dataset_id: str,
    ) -> bytes | None:
        """
        Ask one custodian server for its share for the dataset.
        Expects a 'get_share' action response:
          { "status": "ok", "result": { "found": bool, "share": hex | None } }
        """
        resp = await custodian_client.get_share(dataset_id)
        if resp.get("status") != "ok":
            return None

        result = resp.get("result", {})
        if not result.get("found"):
            return None

        share_hex = result.get("share")
        if share_hex is None:
            return None
        return bytes.fromhex(share_hex)
