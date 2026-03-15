from __future__ import annotations

from app.domain.models import Chunk


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
                chunk_id=f"chunk_{index}",
                text=chunk_text_value,
            )
        )

        if end == len(text):
            break

        start = end - overlap
        index += 1

    return chunks