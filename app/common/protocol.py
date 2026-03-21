import json
from typing import Any


def encode_message(message: dict[str, Any]) -> bytes:
    return (json.dumps(message) + "\n").encode("utf-8")


def decode_message(line: bytes) -> dict[str, Any]:
    return json.loads(line.decode("utf-8"))