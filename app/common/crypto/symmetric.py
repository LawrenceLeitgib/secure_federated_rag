import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives import hashes


def generate_key() -> bytes:
    return Fernet.generate_key()


def derive_chunk_key(master_key: bytes, chunk_id: str) -> bytes:
    """Derive a Fernet-compatible DEK from a master key using HKDF, with chunk_id as context."""
    hkdf = HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=None,
        info=chunk_id.encode("utf-8"),
    )
    raw_key = hkdf.derive(master_key)
    return base64.urlsafe_b64encode(raw_key)


def encrypt_bytes(data: bytes, key: bytes) -> bytes:
    f = Fernet(key)
    return f.encrypt(data)


def decrypt_bytes(token: bytes, key: bytes) -> bytes:
    f = Fernet(key)
    return f.decrypt(token)


def generate_dummy_kek() -> bytes:
    return generate_key() #TODO: need to implement proper KEK management, this is just a placeholder