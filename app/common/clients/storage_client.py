# app/common/clients/storage_client.py
from __future__ import annotations

import asyncio
from typing import Any

from app.common.protocol import encode_message, decode_message
from app.common.chunking import EncryptedChunk


class StorageClient:
    def __init__(self, host: str = "127.0.0.1", port: int = 7001) -> None:
        self.host = host
        self.port = port

    async def upload_chunk_async(self, chunk: EncryptedChunk) -> dict[str, Any]:
        reader, writer = await asyncio.open_connection(self.host, self.port)
        try:
            payload = {
                "chunk_id": chunk.chunk_id,
                "encrypted_data": chunk.encrypted_data.hex(),
                "encrypted_dek": chunk.encrypted_dek.hex(),
            }
            request = {"action": "upload_chunk", "payload": payload}
            writer.write(encode_message(request))
            await writer.drain()

            line = await reader.readline()
            if not line:
                raise RuntimeError("Storage server closed connection")

            response = decode_message(line)
            return response
        finally:
            writer.close()
            await writer.wait_closed()

    async def retrieve_chunk_async(self, chunk_id: str) -> dict[str, Any]:
        reader, writer = await asyncio.open_connection(self.host, self.port)
        try:
            payload = {"chunk_id": chunk_id}
            request = {"action": "get_chunk", "payload": payload}
            writer.write(encode_message(request))
            await writer.drain()

            line = await reader.readline()
            if not line:
                raise RuntimeError("Storage server closed connection")

            response = decode_message(line)
            return response
        finally:
            writer.close()
            await writer.wait_closed()