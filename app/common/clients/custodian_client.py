
# app/common/clients/storage_client.py
from __future__ import annotations

import asyncio
from typing import Any

from app.common.protocol import encode_message, decode_message

import threshold_crypto as tc



class CustodianClient:
    def __init__(self, host: str = "127.0.0.1", port: int = 9001) -> None:
        self.host = host
        self.port = port

    async def store_share(self, user_id: str, dataset_id: str, encrypted_private_key: tc.KeyShare) -> dict[str, Any]:
        reader, writer = await asyncio.open_connection(self.host, self.port)
        try:
            payload = {
                "user_id": user_id,
                "dataset_id": dataset_id,
                "private_share_key": encrypted_private_key.to_json(),
            }
            request = {"action": "store_share", "payload": payload}
            writer.write(encode_message(request))
            await writer.drain()

            line = await reader.readline()
            if not line:
                raise RuntimeError("Custodian server closed connection")

            response = decode_message(line)
            return response
        finally:
            writer.close()
            await writer.wait_closed()

    async def get_partial_decryption(self, re_id: str, chunk_id: str) -> dict[str, Any]:
        reader, writer = await asyncio.open_connection(self.host, self.port)
        try:
            payload = {"re_id": re_id, "chunk_id": chunk_id}
            request = {"action": "get_partial_decryption", "payload": payload}
            writer.write(encode_message(request))
            await writer.drain()

            line = await reader.readline()
            if not line:
                raise RuntimeError("Custodian server closed connection")

            response = decode_message(line)
            return response
        finally:
            writer.close()
            await writer.wait_closed()