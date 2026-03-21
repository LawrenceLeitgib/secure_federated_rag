
# app/common/clients/storage_client.py
from __future__ import annotations

import asyncio
from typing import Any

from app.common.protocol import encode_message, decode_message


class RetrievalClient:
    def __init__(self, host: str = "127.0.0.1", port: int = 10001) -> None:
        self.host = host
        self.port = port

    async def add_embeddings(self, user_id: str, embeddings: list[tuple[str, list[float]]]) -> dict[str, Any]:
        reader, writer = await asyncio.open_connection(self.host, self.port)
        try:
            payload = {
                "user_id": user_id,
                "embeddings": [
                    {"chunk_id": chunk_id, "embedding": embedding}
                    for chunk_id, embedding in embeddings
                ],
            }
            request = {"action": "add_embeddings", "payload": payload}
            writer.write(encode_message(request))
            await writer.drain()

            line = await reader.readline()
            if not line:
                raise RuntimeError("Retrieval server closed connection")

            response = decode_message(line)
            return response
        finally:
            writer.close()
            await writer.wait_closed()