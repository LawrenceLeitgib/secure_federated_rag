# app/retrieval/embeddings.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import numpy as np
import torch
import torch.nn.functional as F
from transformers import AutoModel, AutoTokenizer


EMBEDDING_DIM = 32


def embed_text_dummy(text: str) -> list[float]:
    vector = np.zeros(EMBEDDING_DIM, dtype=float)

    for i, char in enumerate(text.lower()):
        vector[i % EMBEDDING_DIM] += (ord(char) % 31) / 31.0

    norm = np.linalg.norm(vector)
    if norm > 0:
        vector = vector / norm

    return vector.tolist()


@dataclass
class EmbedderConfig:
    model_name: str = "Qwen/Qwen3-Embedding-0.6B"
    max_length: int = 2048
    output_dim: int = 1024
    query_instruction: str = (
        "Given a user question, retrieve the most relevant text chunks "
        "from the knowledge base that help answer the question"
    )
    use_fp16_on_gpu: bool = True


class QwenEmbedder:
    """
    Real semantic embedder based on Qwen/Qwen3-Embedding-0.6B.

    Minimal integration goal:
      - embed_text(text) -> list[float]
      - embed_texts(texts) -> list[list[float]]

    This keeps your current vector index unchanged.
    """

    def __init__(self, config: EmbedderConfig | None = None) -> None:
        self.config = config or EmbedderConfig()

        self.tokenizer = AutoTokenizer.from_pretrained(self.config.model_name)
        self.model = AutoModel.from_pretrained(
            self.config.model_name,
            torch_dtype=self._select_dtype(),
            device_map="auto",
        )
        self.model.eval()

    def _select_dtype(self) -> torch.dtype | str:
        if torch.cuda.is_available() and self.config.use_fp16_on_gpu:
            return torch.float16
        return "auto"

    def _last_token_pool(
        self,
        last_hidden_states: torch.Tensor,
        attention_mask: torch.Tensor,
    ) -> torch.Tensor:
        # Same pooling strategy as the official Qwen embedding example
        left_padding = (attention_mask[:, -1].sum() == attention_mask.shape[0])
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
        # Qwen3-Embedding supports taking a prefix of the vector for custom dims.
        # We keep only the requested output dimension, then L2-normalize.
        dim = min(self.config.output_dim, embeddings.shape[1])
        embeddings = embeddings[:, :dim]
        embeddings = F.normalize(embeddings, p=2, dim=1)
        return embeddings

    @torch.no_grad()
    def embed_texts(
        self,
        texts: Iterable[str],
        *,
        is_query: bool = False,
    ) -> list[list[float]]:
        input_texts = []
        for text in texts:
            text = (text or "").strip()
            if not text:
                text = " "
            if is_query:
                text = self._format_query(text)
            input_texts.append(text)

        batch = self.tokenizer(
            input_texts,
            padding=True,
            truncation=True,
            max_length=self.config.max_length,
            return_tensors="pt",
        )
        batch = {k: v.to(self.model.device) for k, v in batch.items()}

        outputs = self.model(**batch)
        embeddings = self._last_token_pool(
            outputs.last_hidden_state,
            batch["attention_mask"],
        )
        embeddings = self._normalize_dim(embeddings)

        return embeddings.cpu().tolist()

    def embed_text(self, text: str, *, is_query: bool = False) -> list[float]:
        return self.embed_texts([text], is_query=is_query)[0]