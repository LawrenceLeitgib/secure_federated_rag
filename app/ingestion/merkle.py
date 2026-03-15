from __future__ import annotations

from app.crypto.hashing import sha256_text


def _pairwise_hash(left: str, right: str) -> str:
    return sha256_text(left + right)


def build_merkle_root(values: list[str]) -> str:
    if not values:
        return sha256_text("")

    level = values[:]

    while len(level) > 1:
        next_level: list[str] = []

        for i in range(0, len(level), 2):
            left = level[i]
            right = level[i + 1] if i + 1 < len(level) else level[i]
            next_level.append(_pairwise_hash(left, right))

        level = next_level

    return level[0]