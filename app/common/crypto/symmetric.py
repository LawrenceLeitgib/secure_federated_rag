import os
from cryptography.fernet import Fernet


def generate_key() -> bytes:
    return Fernet.generate_key()


def encrypt_bytes(data: bytes, key: bytes) -> bytes:
    f = Fernet(key)
    return f.encrypt(data)


def decrypt_bytes(token: bytes, key: bytes) -> bytes:
    f = Fernet(key)
    return f.decrypt(token)


def generate_dummy_kek() -> bytes:
    return generate_key() #TODO: need to implement proper KEK management, this is just a placeholder