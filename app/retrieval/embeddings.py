from __future__ import annotations

import numpy as np


EMBEDDING_DIM = 32


def embed_text_dummy(text: str) -> list[float]:
    vector = np.zeros(EMBEDDING_DIM, dtype=float)

    for i, char in enumerate(text.lower()):
        vector[i % EMBEDDING_DIM] += (ord(char) % 31) / 31.0

    norm = np.linalg.norm(vector)
    if norm > 0:
        vector = vector / norm

    return vector.tolist()