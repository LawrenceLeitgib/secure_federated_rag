from __future__ import annotations

import asyncio
import hashlib

from app.common.clients.retrieval_client import RetrievalClient



class SimpleTerminalUser:
    """A very small user that only issues retrieval queries from the terminal.

    This user doesn't upload data or interact with other services. It only:
      1. Prompts for a query on stdin.
      2. Sends it to the retrieval engine over TCP.
      3. Prints the returned results.
    """

    def __init__(self, user_id: str | None = None, client: RetrievalClient | None = None) -> None:
        # If no explicit user_id is provided, derive a deterministic dummy one.
        if user_id is None:
            user_id = hashlib.sha256(b"simple_terminal_user").hexdigest()
        self.user_id = user_id
        self.client = client or RetrievalClient()

    async def run_once(self) -> None:
        """Ask for a single query and print the retrieval results."""

        query_text = input("Enter your query (empty to exit): ").strip()
        if not query_text:
            print("Empty query, exiting.")
            return

        try:
            response = await self.client.query(self.user_id, query_text)
        except Exception as e:
            print(f"Error while querying retrieval engine: {e}")
            return

        status = response.get("status")
        if status != "ok":
            print(f"Retrieval engine returned an error: {response.get('error')}")
            return

        result = response.get("result", {})

        answer = result.get("answer")
        query=result.get("query")
        retrieved_chunks=result.get("retrieved_chunks", [])

        for chunk in retrieved_chunks:
            score=chunk.get("score")
            text=chunk.get("text")
            print(f"Retrieved chunk with score {score}: {text[:100]}...")

        print(f"Query: {query}")
        print(f"Answer: {answer}")


async def _main() -> None:
    user = SimpleTerminalUser()
    while True:
        await user.run_once()


if __name__ == "__main__":
    asyncio.run(_main())
