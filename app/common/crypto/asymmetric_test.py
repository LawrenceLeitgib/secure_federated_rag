# pip install threshold-crypto

import threshold_crypto as tc

# -------------------------
# 1) key generation on one machine
# -------------------------
curve_params = tc.CurveParameters()
thresh_params = tc.ThresholdParameters(t=2, n=2)

pub_key, key_shares = tc.create_public_key_and_shares_centralized(
    curve_params,
    thresh_params,
)

share1 = key_shares[0]
share2 = key_shares[1]

# Keep pub_key locally, send share1 and share2 elsewhere
pub_key_json = pub_key.to_json()
share1_json = share1.to_json()
share2_json = share2.to_json()

print("Public key JSON:", pub_key_json)
print("Share 1 JSON:", share1_json)
print("Share 2 JSON:", share2_json)

# -------------------------
# 2) encrypt with public key
# -------------------------
message = "hello threshold world"
print("Original message:", message)
encrypted_message = tc.encrypt_message(message, pub_key)
encrypted_json = encrypted_message.to_json()

print("Encrypted JSON:", encrypted_json)

# -------------------------
# 3) on custodian 1
# -------------------------
received_enc = tc.EncryptedMessage.from_json(encrypted_json)
received_share1 = tc.KeyShare.from_json(share1_json)


partial1 = tc.compute_partial_decryption(received_enc, received_share1)
partial1_json = partial1.to_json()

# -------------------------
# 4) on custodian 2
# -------------------------
received_share2 = tc.KeyShare.from_json(share2_json)
partial2 = tc.compute_partial_decryption(received_enc, received_share2)
partial2_json = partial2.to_json()

# -------------------------
# 5) combiner gets both partial decryptions
# -------------------------
p1 = tc.PartialDecryption.from_json(partial1_json)
p2 = tc.PartialDecryption.from_json(partial2_json)

decrypted = tc.decrypt_message(
    [p1, p2],
    received_enc,
    thresh_params,
)

print("Decrypted:", decrypted)