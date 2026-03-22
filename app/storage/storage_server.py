# app/storage/storage_server.py
from __future__ import annotations

import asyncio
from typing import Any

from app.common.protocol import decode_message, encode_message
from app.common.chunking import EncryptedChunk
from app.storage.provider import LocalStorageProvider


class StorageTCPServer:
    def __init__(self) -> None:
        self.storage = LocalStorageProvider()

    async def handle_client(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
    ) -> None:
        try:
            while True:
                line = await reader.readline()
                if not line:
                    break

                request = decode_message(line)
                response = self.dispatch(request)

                writer.write(encode_message(response))
                await writer.drain()
        except Exception as e:
            writer.write(
                encode_message({"status": "error", "error": str(e)})
            )
            await writer.drain()
        finally:
            writer.close()
            await writer.wait_closed()

    def dispatch(self, request: dict[str, Any]) -> dict[str, Any]:
        action = request.get("action")
        payload = request.get("payload", {})
        print(f"StorageTCPServer received request: {action}")

        try:
            if action == "upload_chunk":
                # Expect payload with the fields to build EncryptedChunk
                chunk_id: str = payload["chunk_id"]
                encrypted_data_hex: str = payload["encrypted_data"]
                encrypted_dek_hex: str = payload["encrypted_dek"]
                dataset_id: str = payload.get("dataset_id")

                encrypted_chunk = EncryptedChunk(
                    dataset_id=dataset_id,
                    chunk_id=chunk_id,
                    encrypted_data=bytes.fromhex(encrypted_data_hex),
                    encrypted_dek=bytes.fromhex(encrypted_dek_hex),
                )

                self.storage.upload_chunk(encrypted_chunk)
                return {"status": "ok"}

         
            elif action == "get_chunk":
                chunk_id: str = payload["chunk_id"]
                print(f"Requesting chunk from storage for chunk_id: {chunk_id}")
                encrypted_chunk = self.storage.get_chunk(chunk_id)
                print(f"Retrieved chunk from storage: {encrypted_chunk}")

                return {
                    "status": "ok",
                    "result": {
                        "dataset_id": encrypted_chunk.dataset_id,
                        "chunk_id": encrypted_chunk.chunk_id,
                        "encrypted_data": encrypted_chunk.encrypted_data.hex(),
                        "encrypted_dek": encrypted_chunk.encrypted_dek.hex(),
                    },
                }

            else:
                return {"status": "error", "error": f"Unknown action: {action}"}

        except Exception as e:
            return {"status": "error", "error": str(e)}


async def main() -> None:
    server_obj = StorageTCPServer()
    server = await asyncio.start_server(
        server_obj.handle_client,
        "127.0.0.1",
        7001,  
    )

    addrs = ", ".join(str(sock.getsockname()) for sock in server.sockets or [])
    print(f"Storage server listening on {addrs}")

    async with server:
        await server.serve_forever()


if __name__ == "__main__":
    asyncio.run(main())