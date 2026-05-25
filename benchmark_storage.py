"""
Storage overhead benchmark.

Runs the full upload pipeline in-process (no HTTP servers) and measures how many
bytes are stored across each component for a given amount of raw input text.

Components measured per document:
  - storage_provider: sum of encrypted_data + encrypted_dek for all chunks
  - ledger:           REGISTER_DATASET signed entry (JSON-serialised)
  - custodians:       both key shares (JSON-serialised) stored at the 2 custodians
  - auth_ledger:      GRANT_AUTHORIZATION signed entry (JSON-serialised)

One-time per-owner fixed cost is reported separately and NOT included in the ratio.
"""
from __future__ import annotations

import hashlib
import json

from app.common.chunking import EncryptedChunk, chunkDocument
from app.common.crypto.asymmetric import encrypt_with_public_key, generate_threshold_keys
from app.common.crypto.hashing import sha256_text
from app.common.crypto.signing import generate_key_pairs
from app.common.crypto.symmetric import encrypt_bytes, generate_key
from app.common.ledger_interaction import (
    SignedLedgerEntry,
    add_authorization_entry,
    register_dataset,
    register_user,
)
from app.data_owner.merkle import build_merkle_root
from app.common.benchmarking import BenchmarkReport, now


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _entry_bytes(entry: SignedLedgerEntry) -> int:
    return len(json.dumps(entry.to_dict(), separators=(",", ":")).encode("utf-8"))


def _share_bytes(share) -> int:
    return len(share.to_json().encode("utf-8"))


def make_text(target_bytes: int) -> str:
    """Generate synthetic text of roughly *target_bytes* UTF-8 bytes.

    Each sentence is numbered so no two chunks are textually identical,
    which prevents chunk_id collisions from distorting ledger-size measurements.
    """
    lines: list[str] = []
    total = 0
    i = 0
    template = (
        "Sentence {i}: the quick brown fox jumps over the lazy dog near the river bank. "
        "Scientists have studied animal behaviour in natural habitats for centuries. "
        "Cryptographic protocols ensure data confidentiality and integrity at rest and in transit."
    )
    while total < target_bytes:
        line = template.format(i=i) + "\n"
        lines.append(line)
        total += len(line)
        i += 1
    return "".join(lines)[:target_bytes]


# ---------------------------------------------------------------------------
# Core measurement
# ---------------------------------------------------------------------------

def measure_upload(text: str) -> dict:
    bench = BenchmarkReport()
    total_start = now()

    input_bytes = len(text.encode("utf-8"))

    # 1. Chunking
    t0 = now()
    chunks = chunkDocument(text)
    bench.add_duration("chunking_ms", t0)
    bench.set_counter("num_chunks", len(chunks))

    # 2. Threshold key pair (one per document)
    t0 = now()
    public_kek, shares = generate_threshold_keys(2, 2)
    bench.add_duration("threshold_keygen_ms", t0)

    # 3. Owner key pair (one-time; kept separate below)
    private_key, public_key = generate_key_pairs()
    user_id = hashlib.sha256(public_key).hexdigest()
    # Dummy retrieval-engine id for the auth entry
    _, re_public_key = generate_key_pairs()
    re_id = hashlib.sha256(re_public_key).hexdigest()

    # 4. Encrypt chunks
    t0 = now()
    encrypted_chunks: list[EncryptedChunk] = []
    for chunk in chunks:
        dek = generate_key()
        enc_data = encrypt_bytes(chunk.text.encode("utf-8"), dek)
        enc_dek = encrypt_with_public_key(dek.hex(), public_kek)
        encrypted_chunks.append(
            EncryptedChunk(
                dataset_id="",
                chunk_id=chunk.chunk_id,
                encrypted_data=enc_data,
                encrypted_dek=enc_dek,
            )
        )
    bench.add_duration("chunk_encryption_ms", t0)

    # 5. Merkle root → dataset_id
    leaf_hashes = [c.chunk_id for c in chunks]
    dataset_id = build_merkle_root(leaf_hashes)
    for ec in encrypted_chunks:
        ec.dataset_id = dataset_id

    # 6. Ledger entries
    chunk_id_to_dek_hash = {
        chunk.chunk_id: sha256_text(ec.encrypted_dek)
        for chunk, ec in zip(chunks, encrypted_chunks)
    }
    t0 = now()
    register_entry = register_dataset(dataset_id, chunk_id_to_dek_hash, user_id, private_key)
    auth_entry = add_authorization_entry(user_id, dataset_id, re_id, private_key)
    bench.add_duration("ledger_signing_ms", t0)

    # One-time owner-registration ledger entry (NOT counted in per-doc overhead)
    owner_reg_entry = register_user(user_id, public_key.decode("utf-8"), private_key)

    # -----------------------------------------------------------------------
    # Size accounting
    # -----------------------------------------------------------------------

    # Storage provider: encrypted_data + encrypted_dek for every chunk
    storage_enc_data_bytes = sum(len(ec.encrypted_data) for ec in encrypted_chunks)
    storage_enc_dek_bytes = sum(len(ec.encrypted_dek.encode("utf-8")) for ec in encrypted_chunks)
    storage_bytes = storage_enc_data_bytes + storage_enc_dek_bytes

    # Ledger: REGISTER_DATASET entry
    register_entry_bytes = _entry_bytes(register_entry)
    # Ledger: GRANT_AUTHORIZATION entry (per-dataset, added when granting access)
    auth_entry_bytes = _entry_bytes(auth_entry)
    ledger_bytes = register_entry_bytes + auth_entry_bytes

    # Custodians: one key share per custodian
    share_bytes_each = [_share_bytes(s) for s in shares]
    custodian_bytes = sum(share_bytes_each)

    # Total per-document stored bytes
    total_stored = storage_bytes + ledger_bytes + custodian_bytes

    # One-time per-owner fixed cost
    owner_reg_bytes = _entry_bytes(owner_reg_entry)

    bench.add_duration("total_ms", total_start)

    return {
        "input_bytes": input_bytes,
        "num_chunks": len(chunks),
        # per-document stored
        "storage_enc_data_bytes": storage_enc_data_bytes,
        "storage_enc_dek_bytes": storage_enc_dek_bytes,
        "storage_bytes": storage_bytes,
        "ledger_register_bytes": register_entry_bytes,
        "ledger_auth_bytes": auth_entry_bytes,
        "ledger_bytes": ledger_bytes,
        "custodian_share_bytes_each": share_bytes_each,
        "custodian_bytes": custodian_bytes,
        "total_stored_bytes": total_stored,
        "overhead_ratio": total_stored / input_bytes,
        # breakdown ratios
        "storage_ratio": storage_bytes / input_bytes,
        "ledger_ratio": ledger_bytes / input_bytes,
        "custodian_ratio": custodian_bytes / input_bytes,
        # one-time fixed cost (NOT in overhead_ratio)
        "owner_registration_bytes": owner_reg_bytes,
        "timings_ms": bench.to_dict()["timings_ms"],
    }


# ---------------------------------------------------------------------------
# Report formatting
# ---------------------------------------------------------------------------

def _human(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} GB"


def print_result(r: dict) -> None:
    print(
        f"  input:      {_human(r['input_bytes']):>10}  ({r['num_chunks']} chunks)"
    )
    print(
        f"  storage:    {_human(r['storage_bytes']):>10}"
        f"  (enc_data {_human(r['storage_enc_data_bytes'])}"
        f" + enc_dek {_human(r['storage_enc_dek_bytes'])})"
    )
    print(
        f"  ledger:     {_human(r['ledger_bytes']):>10}"
        f"  (register {_human(r['ledger_register_bytes'])}"
        f" + auth {_human(r['ledger_auth_bytes'])})"
    )
    print(
        f"  custodians: {_human(r['custodian_bytes']):>10}"
        f"  ({len(r['custodian_share_bytes_each'])} shares"
        f" × {_human(r['custodian_share_bytes_each'][0])} each)"
    )
    print(f"  ─────────────────────────────────────────────")
    print(f"  TOTAL:      {_human(r['total_stored_bytes']):>10}  overhead ratio = {r['overhead_ratio']:.2f}×")
    print(
        f"    ↳ storage {r['storage_ratio']:.2f}×  "
        f"ledger {r['ledger_ratio']:.2f}×  "
        f"custodian {r['custodian_ratio']:.2f}×"
    )
    print(
        f"  (one-time owner-reg entry: {_human(r['owner_registration_bytes'])} — not counted above)"
    )


def print_summary_table(results: list[dict]) -> None:
    header = f"{'Input':>10}  {'Chunks':>6}  {'Storage':>10}  {'Ledger':>10}  {'Custodian':>10}  {'Total':>10}  {'Ratio':>7}"
    print(header)
    print("─" * len(header))
    for r in results:
        print(
            f"{_human(r['input_bytes']):>10}  "
            f"{r['num_chunks']:>6}  "
            f"{_human(r['storage_bytes']):>10}  "
            f"{_human(r['ledger_bytes']):>10}  "
            f"{_human(r['custodian_bytes']):>10}  "
            f"{_human(r['total_stored_bytes']):>10}  "
            f"{r['overhead_ratio']:>6.2f}×"
        )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

INPUT_SIZES = [
    1_000,        # 1 KB
    1_000_000,    # 1 MB
]


def main() -> None:
    results = []

    for size in INPUT_SIZES:
        text = make_text(size)
        print(f"\n{'─'*60}")
        print(f"Input size: {_human(size)}")
        r = measure_upload(text)
        print_result(r)
        results.append(r)

    print(f"\n\n{'═'*60}")
    print("SUMMARY TABLE")
    print(f"{'═'*60}")
    print_summary_table(results)

    # Save JSON
    from benchmark_results import write_result_json, utc_timestamp
    ts = utc_timestamp()
    payload = {"benchmark_type": "storage_overhead", "results": results}
    path = write_result_json(f"storage_overhead_{ts}.json", payload)
    print(f"\nResults saved to {path}")


if __name__ == "__main__":
    main()
