# app/custodians/custodian_server.py
from __future__ import annotations

import asyncio
from typing import Any

from app.common.protocol import decode_message, encode_message
from app.custodians.custodian_service import CustodianService


class CustodianTCPServer:
    def __init__(self, custodian_id: str) -> None:
        # Wrap everything in a service
        self.service = CustodianService(
            custodian_id=custodian_id)

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
                response = await self.dispatch(request)

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

    async def dispatch(self, request: dict[str, Any]) -> dict[str, Any]:
        action = request.get("action")
        payload = request.get("payload", {})

        print(f"CustodianTCPServer received request: {action}")
        try:
            if action == "store_share":
                user_id: str = payload["user_id"]
                dataset_id: str = payload["dataset_id"]
                share_hex: str = payload["encrypted_private_key"]
                share = bytes.fromhex(share_hex)

                # Delegate to service
                await self.service.store_share(user_id, dataset_id, share)
                return {"status": "ok"}

            elif action == "get_share":
                dataset_id: str = payload["dataset_id"]
                share = self.service.get_share(dataset_id)

                if share is None:
                    return {"status": "ok", "result": {"found": False}}
                return {
                    "status": "ok",
                    "result": {
                        "found": True,
                        "share": share.hex(),
                    },
                }
            
            elif action == "get_plain_text_chunk":
                chunk_id: str = payload["chunk_id"]
                user_id: str = payload["user_id"]

                chunk,authorised = await self.service.get_plain_text_chunk(user_id,chunk_id)
                if not authorised:
                    return {"status": "ok", "result": {"found": False, "authorized": False}}
                if chunk is None:
                    return {"status": "ok", "result": {"found": False, "authorized": True}}
                
                chunk_dict = {
                    "dataset_id": chunk.dataset_id,
                    "chunk_id": chunk.chunk_id,
                    "text": chunk.text,  
                }

                return {
                    "status": "ok",
                    "result": {
                        "found": True,
                        "authorized": True,
                        "chunk": chunk_dict,
                    },
                }

            elif action == "ping":
                return {"status": "ok", "result": "pong"}

            else:
                return {"status": "error", "error": f"Unknown action: {action}"}

        except Exception as e:
            return {"status": "error", "error": str(e)}


async def main() -> None:
    custodian_id = "custodian_1"

    server_obj = CustodianTCPServer(custodian_id=custodian_id)
    server = await asyncio.start_server(
        server_obj.handle_client,
        "127.0.0.1",
        9001,
    )

    addrs = ", ".join(str(sock.getsockname()) for sock in server.sockets or [])
    print(f"Custodian server '{custodian_id}' listening on {addrs}")

    async with server:
        await server.serve_forever()


if __name__ == "__main__":
    asyncio.run(main())