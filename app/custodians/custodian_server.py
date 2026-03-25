# app/custodians/custodian_server.py
from __future__ import annotations

import argparse
import asyncio
from typing import Any

import threshold_crypto as tc

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
                share: str = payload["private_share_key"]
                share = tc.KeyShare.from_json(share)  # Convert back to KeyShare object

                # Delegate to service
                await self.service.store_share(user_id, dataset_id, share)
                return {"status": "ok"}

         
            elif action == "get_partial_decryption":
                chunk_id: str = payload["chunk_id"]
                re_id: str = payload["re_id"]

                partial_decryption, authorised = await self.service.get_partial_decryption(re_id,chunk_id)
                if not authorised:
                    return {"status": "ok", "result": {"found": False, "authorized": False}}
                if partial_decryption is None:
                    return {"status": "ok", "result": {"found": False, "authorized": True}}
                
               

                return {
                    "status": "ok",
                    "result": {
                        "found": True,
                        "authorized": True,
                        "partial_decryption": partial_decryption,
                    },
                }

            elif action == "ping":
                return {"status": "ok", "result": "pong"}

            else:
                return {"status": "error", "error": f"Unknown action: {action}"}

        except Exception as e:
            return {"status": "error", "error": str(e)}


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--port",
        type=int,
        required=True,
        help="TCP port for this custodian server",
    )
   
    args = parser.parse_args()
    server_obj = CustodianTCPServer(custodian_id=f"custodian_{args.port}")
    server = await asyncio.start_server(
        server_obj.handle_client,
        "127.0.0.1",
        args.port,
    )

    addrs = ", ".join(str(sock.getsockname()) for sock in server.sockets or [])
    print(f"Custodian server 'custodian_{args.port}' listening on {addrs}")

    async with server:
        await server.serve_forever()


if __name__ == "__main__":
    asyncio.run(main())