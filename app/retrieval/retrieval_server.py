from __future__ import annotations

import asyncio
from typing import Any

from app.common.protocol import decode_message, encode_message
from app.retrieval.retrieval_service import RetrievalEngineService


class RetrievalEngineTCPServer:
    def __init__(self, service: RetrievalEngineService) -> None:
        self.service = service

    @classmethod
    async def create(cls, name: str) -> "RetrievalEngineTCPServer":
        service = await RetrievalEngineService.create(name=name)
        return cls(service)

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
            writer.write(encode_message({"status": "error", "error": str(e)}))
            await writer.drain()
        finally:
            writer.close()
            await writer.wait_closed()

    async def dispatch(self, request: dict[str, Any]) -> dict[str, Any]:
        action = request.get("action")
        payload = request.get("payload", {})
        print(f"RetrievalEngineTCPServer received request: {action}")

        try:
            if action == "query":
                user_id: str = payload["user_id"]
                query_text: str = payload["query_text"]

                rag_results = await self.service.answer_query(
                    query_text=query_text,
                    k=3,
                )
                print(f"RetrievalEngineTCPServer returning final answer for query: {query_text}")
                return {
                    "status": "ok",
                    "result":rag_results,
                }
            if action == "add_embeddings":
                user_id: str = payload["user_id"]
                embeddings = payload["embeddings"]  # list of dicts with chunk_id and embedding

                # Convert to list of tuples for the service method
                chunk_embeddings = [
                    (item["chunk_id"], item["embedding"])
                    for item in embeddings
                ]
                print(f"RetrievalEngineTCPServer received {len(chunk_embeddings)} chunk embeddings for user: {user_id}")

                await self.service.add_embeddings(chunk_embeddings)
                return {"status": "ok"}

            elif action == "ping":
                return {"status": "ok", "result": "pong"}

            else:
                return {"status": "error", "error": f"Unknown action: {action}"}

        except PermissionError as pe:
            return {"status": "error", "error": str(pe)}
        except Exception as e:
            return {"status": "error", "error": str(e)}


async def main() -> None:
    name = "retrieval_engine_1"

    server_obj = await RetrievalEngineTCPServer.create(name=name)
    server = await asyncio.start_server(
        server_obj.handle_client,
        "127.0.0.1",
        10001,
    )

    addrs = ", ".join(str(sock.getsockname()) for sock in server.sockets or [])
    print(f"Retrieval engine '{name}' listening on {addrs}")

    async with server:
        await server.serve_forever()


if __name__ == "__main__":
    asyncio.run(main())