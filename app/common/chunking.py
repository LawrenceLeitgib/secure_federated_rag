from __future__ import annotations
from typing import List
from dataclasses import dataclass, field

from app.common.crypto.hashing import sha256_text


def chunk_text(text: str, min_size: int = 200, max_size: int = 400) -> list["Chunk"]:
    if min_size <= 0:
        raise ValueError("min_size must be > 0")
    if max_size < min_size:
        raise ValueError("max_size must be >= min_size")

    chunks: list[Chunk] = []
    n = len(text)
    start = 0

    while start < n:
        max_end = min(start + max_size, n)
        # ensure we don't cut before min_size (unless we're at the end)
        search_start = min(max(start + min_size, start), max_end)

        split_idx: int | None = None

        # 1) Prefer end-of-sentence punctuation
        for i in range(max_end - 1, search_start - 1, -1):
            if text[i] in ".!?":
                split_idx = i + 1  # include punctuation
                break

        # 2) If none, try comma
        if split_idx is None:
            for i in range(max_end - 1, search_start - 1, -1):
                if text[i] == ",":
                    split_idx = i + 1
                    break

        # 3) If none, try whitespace
        if split_idx is None:
            for i in range(max_end - 1, search_start - 1, -1):
                if text[i].isspace():
                    split_idx = i
                    break

        # 4) Fallback: just cut at max_end
        if split_idx is None or split_idx <= start:
            split_idx = max_end

        chunk_text_value = text[start:split_idx].strip()
        if chunk_text_value:
            chunks.append(
                Chunk(
                    chunk_id=sha256_text(chunk_text_value),
                    text=chunk_text_value,
                    dataset_id="",  # to be filled in later when creating the Dataset
                )
            )

        # Advance start, skipping leading whitespace for next chunk
        start = split_idx
        while start < n and text[start].isspace():
            start += 1

    return chunks


@dataclass
class Chunk:
    dataset_id: str
    chunk_id: str
    text: str
    embedding: list[float] | None = None


@dataclass
class EncryptedChunk:
    dataset_id: str
    chunk_id: str
    encrypted_data: bytes
    encrypted_dek: str


@dataclass
class Dataset:
    dataset_id: str
    owner_id: str  # the merkle tree root
    document_name: str
    chunks: List[Chunk] = field(default_factory=list)