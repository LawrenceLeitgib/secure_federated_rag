# app/blockchain/ledger_server.py
from __future__ import annotations

import asyncio
from typing import Any

from app.common.protocol import decode_message, encode_message
from app.blockchain.ledger import SimpleLedger
from app.common.ledger_interaction import (
    SignedLedgerEntry,
)


class LedgerTCPServer:
    def __init__(self) -> None:
        self.ledger = SimpleLedger()

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

        print(f"LedgerTCPServer received request: {action}")
        #print(f"Payload: {payload}")

        #print(action=="add_entry")

        try:
            if action == "add_entry":
                # Expect the client to send a SignedLedgerEntry serialized as dict
                entry = SignedLedgerEntry.from_dict(payload)
                self.ledger.add_entry(entry)
                return {"status": "ok"}

            elif action == "is_authorized":
                user_id = payload["user_id"]
                dataset_id = payload["dataset_id"]
                authorized = self.ledger.is_authorized(user_id, dataset_id)
                return {"status": "ok", "result": {"authorized": authorized}}

            elif action == "print_entries":
                # For debugging; prints on server side
                self.ledger.print_entries()
                return {"status": "ok"}

            else:
                return {"status": "error", "error": f"Unknown action: {action}"}

        except Exception as e:
            return {"status": "error", "error": str(e)}


async def main() -> None:
    server_obj = LedgerTCPServer()
    server = await asyncio.start_server(
        server_obj.handle_client,
        "127.0.0.1",
        8001,  # choose a port for the ledger
    )

    addrs = ", ".join(str(sock.getsockname()) for sock in server.sockets or [])
    print(f"Ledger server listening on {addrs}")

    async with server:
        await server.serve_forever()


if __name__ == "__main__":
    asyncio.run(main())