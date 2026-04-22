from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Iterable

import numpy as np
import torch
import torch.nn.functional as F
from transformers import AutoModel, AutoTokenizer

from app.common.protocol import decode_message, encode_message


EMBEDDING_DIM = 32


def embed_text_dummy(text: str) -> list[float]:
    vector = np.zeros(EMBEDDING_DIM, dtype=float)

    for i, char in enumerate(text.lower()):
        vector[i % EMBEDDING_DIM] += (ord(char) % 31) / 31.0

    norm = np.linalg.norm(vector)
    if norm > 0:
        vector = vector / norm

    return vector.tolist()


@dataclass(frozen=True)
class EmbedderConfig:
    model_name: str = "Qwen/Qwen3-Embedding-0.6B"
    max_length: int = 2048
    output_dim: int = 1024
    batch_size: int = 8
    device: str | None = None
    query_instruction: str = (
        "Given a user question, retrieve the most relevant text chunks "
        "from the knowledge base that help answer the question"
    )
    use_fp16_on_gpu: bool = True


class LocalQwenEmbedder:
    def __init__(self, config: EmbedderConfig | None = None) -> None:
        self.config = config or EmbedderConfig()
        self.device = self._select_device()

        self.tokenizer = AutoTokenizer.from_pretrained(self.config.model_name)
        model_kwargs = {"torch_dtype": self._select_dtype()}
        if self.device == "cuda":
            model_kwargs["device_map"] = "auto"

        self.model = AutoModel.from_pretrained(self.config.model_name, **model_kwargs)
        if self.device != "cuda":
            self.model.to(self.device)
        self.model.eval()

    def _select_device(self) -> str:
        if self.config.device is not None:
            return self.config.device
        if torch.cuda.is_available():
            return "cuda"
        return "cpu"

    def _select_dtype(self) -> torch.dtype:
        if self.device == "cuda" and self.config.use_fp16_on_gpu:
            return torch.float16
        return torch.float32

    def _last_token_pool(
        self,
        last_hidden_states: torch.Tensor,
        attention_mask: torch.Tensor,
    ) -> torch.Tensor:
        left_padding = attention_mask[:, -1].sum() == attention_mask.shape[0]
        if left_padding:
            return last_hidden_states[:, -1]
        sequence_lengths = attention_mask.sum(dim=1) - 1
        batch_size = last_hidden_states.shape[0]
        return last_hidden_states[
            torch.arange(batch_size, device=last_hidden_states.device),
            sequence_lengths,
        ]

    def _format_query(self, query: str) -> str:
        query = query.strip()
        return f"Instruct: {self.config.query_instruction}\nQuery: {query}"

    def _normalize_dim(self, embeddings: torch.Tensor) -> torch.Tensor:
        dim = min(self.config.output_dim, embeddings.shape[1])
        embeddings = embeddings[:, :dim]
        embeddings = F.normalize(embeddings, p=2, dim=1)
        return embeddings

    def _prepare_texts(
        self,
        texts: Iterable[str],
        *,
        is_query: bool = False,
    ) -> list[str]:
        input_texts: list[str] = []
        for text in texts:
            text = (text or "").strip()
            if not text:
                text = " "
            if is_query:
                text = self._format_query(text)
            input_texts.append(text)
        return input_texts

    @torch.no_grad()
    def _embed_prepared_batch(self, input_texts: list[str]) -> list[list[float]]:
        batch = self.tokenizer(
            input_texts,
            padding=True,
            truncation=True,
            max_length=self.config.max_length,
            return_tensors="pt",
        )
        batch = {k: v.to(self.device) for k, v in batch.items()}

        outputs = self.model(**batch)
        embeddings = self._last_token_pool(
            outputs.last_hidden_state,
            batch["attention_mask"],
        )
        embeddings = self._normalize_dim(embeddings)
        result = embeddings.cpu().tolist()

        del outputs
        del embeddings
        del batch
        if self.device == "cuda":
            torch.cuda.empty_cache()
        return result

    def _embed_with_backoff(self, input_texts: list[str]) -> list[list[float]]:
        if not input_texts:
            return []

        batch_size = min(self.config.batch_size, len(input_texts))
        while True:
            try:
                return self._embed_prepared_batch(input_texts[:batch_size])
            except RuntimeError as exc:
                if self.device != "cuda" or "CUDA out of memory" not in str(exc):
                    raise
                if batch_size == 1:
                    raise
                if self.device == "cuda":
                    torch.cuda.empty_cache()
                batch_size = max(1, batch_size // 2)

    @torch.no_grad()
    def embed_texts(
        self,
        texts: Iterable[str],
        *,
        is_query: bool = False,
    ) -> list[list[float]]:
        input_texts = self._prepare_texts(texts, is_query=is_query)
        all_embeddings: list[list[float]] = []

        start = 0
        while start < len(input_texts):
            stop = min(start + self.config.batch_size, len(input_texts))
            all_embeddings.extend(self._embed_with_backoff(input_texts[start:stop]))
            start = stop

        return all_embeddings

    def embed_text(self, text: str, *, is_query: bool = False) -> list[float]:
        return self.embed_texts([text], is_query=is_query)[0]


class QwenEmbedder:
    def __init__(self, host: str = "127.0.0.1", port: int = 11001) -> None:
        self.host = host
        self.port = port
        self.stream_limit = 10 * 1024 * 1024

    async def embed_texts(
        self,
        texts: Iterable[str],
        *,
        is_query: bool = False,
    ) -> list[list[float]]:
        reader, writer = await asyncio.open_connection(
            self.host,
            self.port,
            limit=self.stream_limit,
        )
        try:
            payload = {
                "texts": list(texts),
                "is_query": is_query,
            }
            writer.write(encode_message({"action": "embed_texts", "payload": payload}))
            await writer.drain()

            line = await reader.readline()
            if not line:
                raise RuntimeError("Embedding server closed connection")

            response = decode_message(line)
            if response.get("status") != "ok":
                raise RuntimeError(response.get("error", "Embedding request failed"))
            return response["result"]["embeddings"]
        finally:
            writer.close()
            await writer.wait_closed()

    async def embed_text(self, text: str, *, is_query: bool = False) -> list[float]:
        return (await self.embed_texts([text], is_query=is_query))[0]


class QwenEmbedderServer:
    def __init__(self, embedder: LocalQwenEmbedder) -> None:
        self.embedder = embedder
        self._request_lock = asyncio.Lock()

    @classmethod
    def create(
        cls,
        config: EmbedderConfig | None = None,
    ) -> "QwenEmbedderServer":
        return cls(LocalQwenEmbedder(config=config))

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
        except Exception as exc:
            writer.write(encode_message({"status": "error", "error": str(exc)}))
            await writer.drain()
        finally:
            writer.close()
            await writer.wait_closed()

    async def dispatch(self, request: dict[str, object]) -> dict[str, object]:
        action = request.get("action")
        payload = request.get("payload", {})

        if action == "ping":
            return {"status": "ok", "result": "pong"}

        if action == "embed_texts":
            if not isinstance(payload, dict):
                return {"status": "error", "error": "Invalid payload"}
            texts = payload.get("texts", [])
            is_query = bool(payload.get("is_query", False))
            if not isinstance(texts, list):
                return {"status": "error", "error": "texts must be a list"}
            async with self._request_lock:
                embeddings = self.embedder.embed_texts(texts, is_query=is_query)
            return {"status": "ok", "result": {"embeddings": embeddings}}

        return {"status": "error", "error": f"Unknown action: {action}"}
