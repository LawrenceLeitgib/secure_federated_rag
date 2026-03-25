import threshold_crypto as tc


def generate_threshold_keys(t: int, n: int)->tuple[tc.PublicKey, list[tc.KeyShare]]:
    curve_params = tc.CurveParameters()
    thresh_params = tc.ThresholdParameters(t=t, n=n)

    pub_key, key_shares = tc.create_public_key_and_shares_centralized(
        curve_params,
        thresh_params,
    )

    return pub_key, key_shares

def encrypt_with_public_key(message: str, pub_key: tc.PublicKey) -> str:
    result= tc.encrypt_message(message, pub_key)

    return result.to_json()

def decrypt_with_shares(encrypted_dek: tc.EncryptedMessage, p1: tc.PartialDecryption, p2: tc.PartialDecryption, t: int, n: int) -> str:
    decrypted = tc.decrypt_message(
    [p1, p2],
    encrypted_dek,
    tc.ThresholdParameters(t=t, n=n),
)
    return decrypted