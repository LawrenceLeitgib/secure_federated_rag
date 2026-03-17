from __future__ import annotations
from ast import List
from dataclasses import dataclass, field, field

from app.crypto.hashing import sha256_text


def chunk_text(text: str, chunk_size: int = 300, overlap: int = 50) -> list[Chunk]:
    if chunk_size <= 0:
        raise ValueError("chunk_size must be > 0")
    if overlap >= chunk_size:
        raise ValueError("overlap must be smaller than chunk_size")

    chunks: list[Chunk] = []
    start = 0
    index = 0

    while start < len(text):
        end = min(len(text), start + chunk_size)
        chunk_text_value = text[start:end]

        chunks.append(
            Chunk(
                chunk_id=sha256_text(chunk_text_value),
                text=chunk_text_value,
            )
        )

        if end == len(text):
            break

        start = end - overlap
        index += 1

    return chunks


@dataclass
class Chunk:
    chunk_id: str
    text: str
    embedding: list[float] | None = None

@dataclass
class EncryptedChunk:
    chunk_id: str
    encrypted_data: bytes
    encrypted_dek: bytes

@dataclass
class Dataset:
    dataset_id: str
    owner_id: str #the merkle tree root
    document_name: str
    chunks: List[Chunk] = field(default_factory=list)
