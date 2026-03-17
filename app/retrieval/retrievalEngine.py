from dataclasses import dataclass
import hashlib

from app.crypto.signing import generate_key_pairs


@dataclass
class RetrievalEngine:
    name: str
    re_id: str
    private_key: bytes
    public_key: bytes

    @classmethod
    def create(cls, name: str) -> 'RetrievalEngine':
        private_key, public_key = generate_key_pairs()
        re_id = hashlib.sha256(public_key).hexdigest()
        return cls(
            name=name,
            re_id=re_id,
            private_key=private_key,
            public_key=public_key,
        )