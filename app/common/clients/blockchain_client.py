# app/common/clients/storage_client.py
from __future__ import annotations

import asyncio
from typing import Any

from app.common.ledger_interaction import SignedLedgerEntry
from app.common.protocol import encode_message, decode_message
from app.common.chunking import EncryptedChunk


class BlockchainClient:
    def __init__(self, host: str = "127.0.0.1", port: int = 8001) -> None:
        self.host = host
        self.port = port

    async def add_record(self, signed_ledger_entry: SignedLedgerEntry) -> dict[str, Any]:
        reader, writer = await asyncio.open_connection(self.host, self.port)
        try:
            payload= signed_ledger_entry.to_dict()
            request = {"action": "add_entry", "payload": payload}
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

    async def is_authorized(self, user_id: str, dataset_id: str) -> bool:
        reader, writer = await asyncio.open_connection(self.host, self.port)
        try:
            payload = {"user_id": user_id, "dataset_id": dataset_id}
            request = {"action": "is_authorized", "payload": payload}
            writer.write(encode_message(request))
            await writer.drain()

            line = await reader.readline()
            if not line:
                raise RuntimeError("Storage server closed connection")

            response = decode_message(line)
            return response.get("result", {}).get("authorized", False)
        finally:
            writer.close()
            await writer.wait_closed()


    async def get_chunk_metadata(self, chunk_id: str) -> dict[str, Any]:
        reader, writer = await asyncio.open_connection(self.host, self.port)
        try:
            payload = {"chunk_id": chunk_id}
            request = {"action": "get_chunk_metadata", "payload": payload}
            writer.write(encode_message(request))
            await writer.drain()

            line = await reader.readline()
            if not line:
                raise RuntimeError("Storage server closed connection")

            response = decode_message(line)
            return response.get("result", {}).get("chunk_metadata", {})
        finally:
            writer.close()
            await writer.wait_closed()

    async def get_dataset_owner(self, dataset_id: str) -> str:
        reader, writer = await asyncio.open_connection(self.host, self.port)
        try:
            payload = {"dataset_id": dataset_id}
            request = {"action": "get_dataset_owner", "payload": payload}
            writer.write(encode_message(request))
            await writer.drain()

            line = await reader.readline()
            if not line:
                raise RuntimeError("Storage server closed connection")

            response = decode_message(line)
            print(f"Response from get_dataset_owner: {response}")
            return response.get("result", {}).get("owner_id", "")
        finally:
            writer.close()
            await writer.wait_closed()