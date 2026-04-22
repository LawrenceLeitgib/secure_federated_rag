from __future__ import annotations

import asyncio

from app.retrieval.embeddings import EmbedderConfig, QwenEmbedderServer


async def main() -> None:
    server_obj = QwenEmbedderServer.create(EmbedderConfig())
    server = await asyncio.start_server(
        server_obj.handle_client,
        "127.0.0.1",
        11001,
        limit=10 * 1024 * 1024,
    )

    addrs = ", ".join(str(sock.getsockname()) for sock in server.sockets or [])
    print(f"Embedding server listening on {addrs}")

    async with server:
        await server.serve_forever()


if __name__ == "__main__":
    asyncio.run(main())
