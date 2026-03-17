from __future__ import annotations

from typing import Optional

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa, ed25519
from cryptography.exceptions import InvalidSignature




def generate_rsa_key_pair() -> tuple[bytes, bytes]:
    """Generate a new RSA key pair and return them as PEM-encoded bytes."""
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_key = private_key.public_key()

    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    public_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    return private_pem, public_pem


def generate_ed25519_key_pair() -> tuple[bytes, bytes]:
    """Generate a new Ed25519 key pair and return them as PEM-encoded bytes."""
    private_key = ed25519.Ed25519PrivateKey.generate()
    public_key = private_key.public_key()

    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    public_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    return private_pem, public_pem

def generate_key_pairs() -> tuple[bytes, bytes]:
    """Generate a new key pair (Ed25519 by default) and return them as PEM-encoded bytes."""
    return generate_ed25519_key_pair()
def sign_data(private_pem: bytes, data: bytes, password: Optional[bytes] = None) -> bytes:
    """Sign `data` using a PEM-encoded private key (Ed25519 or RSA).

    Args:
        private_pem: private key in PEM bytes (may be password-encrypted).
        data: raw bytes to sign.
        password: optional password for encrypted PEM.

    Returns:
        signature bytes.
    """
    priv = serialization.load_pem_private_key(private_pem, password=password)

    # Ed25519 (deterministic, simple API)
    if isinstance(priv, ed25519.Ed25519PrivateKey):
        return priv.sign(data)

    # RSA (use PSS + SHA256)
    if isinstance(priv, rsa.RSAPrivateKey):
        return priv.sign(
            data,
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH,
            ),
            hashes.SHA256(),
        )

    raise ValueError("Unsupported private key type for signing")


def verify_signature(public_pem: bytes, data: bytes, signature: bytes) -> bool:
    """Verify a signature produced by `sign_data`.

    Args:
        public_pem: public key in PEM bytes.
        data: original data bytes.
        signature: signature bytes to check.

    Returns:
        True if signature is valid, False otherwise.
    """
    pub = serialization.load_pem_public_key(public_pem)

    try:
        if isinstance(pub, ed25519.Ed25519PublicKey):
            # Ed25519: verify(signature, data)
            pub.verify(signature, data)
            return True

        if isinstance(pub, rsa.RSAPublicKey):
            pub.verify(
                signature,
                data,
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH,
                ),
                hashes.SHA256(),
            )
            return True

        raise ValueError("Unsupported public key type for verification")
    except InvalidSignature:
        return False
