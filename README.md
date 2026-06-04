# Secure Federated RAG

A privacy-preserving, distributed Retrieval-Augmented Generation (RAG) system built as an EPFL MASTER semester project in IC. Multiple independent data owners can securely share their documents through a federated retrieval system, while maintaining cryptographic confidentiality and fine-grained access control.

---

## Overview

Traditional RAG systems require centralizing data in a single location, which creates privacy and trust problems. This system solves that by combining:

- **Threshold cryptography** — no single party can decrypt data alone
- **Blockchain-based authorization** — data owners explicitly grant access to retrieval engines
- **Federated architecture** — data owners retain control; no plaintext data ever leaves their domain

### Data Flow

```
Upload:   documents → chunk → embed → encrypt → storage + ledger + custodians
Query:    question  → embed → vector search → auth check → decrypt → LLM → answer
```

---

## Architecture

The system is composed of five independent services and two interactive clients:

| Component | Port | Role |
|-----------|------|------|
| Embedding Server | 11001 | Shared Qwen3 embedding service |
| Storage Server | 7001 | Stores encrypted document chunks |
| Blockchain Server | 8001 | In-memory authorization ledger |
| Custodian i | 900{i} | Holds threshold key shares |
| Retrieval Server | 10001 | Query processing and answer generation |

All services communicate over a simple JSON-line TCP protocol.

### Actors

- **Data Owner** — uploads documents, sets access policies, distributes key shares to custodians
- **Custodian** — holds a threshold share of decryption keys; use a t-of-n threshold parameterize to any t and n, this prototype as default set to 2-of-2
- **Retrieval Engine** — embeds queries, searches the vector index, reconstructs keys, generates answers
- **User** — submits natural language queries to the retrieval engine
- **Blockchain Ledger** — immutable record of user registrations, dataset metadata, and access grants
- **Storage Server** — Stores encrypted document chunks


---

## Cryptographic Design

| Layer | Scheme |
|-------|--------|
| Symmetric encryption | Fernet (AES-128-CBC) |
| Key encapsulation | RSA + threshold secret sharing |
| Signing | RSA-2048 |
| Hashing / chunk IDs | SHA-256 |
| Threshold scheme | 2-of-2 (both custodians required) |

Each document chunk is encrypted with an ephemeral Data Encryption Key (DEK). The DEK is split into shares and distributed to custodians. To decrypt a chunk, the retrieval engine must obtain partial decryptions from **all** custodians and receive an explicit authorization grant on the blockchain from the data owner.

---

## Models

| Model | Use | Size |
|-------|-----|------|
| `Qwen/Qwen3-Embedding-0.6B` | Semantic embeddings (1024-dim) | ~1.2 GB |
| `Qwen/Qwen3-0.6B` | Answer generation | ~1.2 GB |

Models are downloaded automatically from Hugging Face on first run.

---

## Directory Structure

```
secure_federated_rag/
├── app/
│   ├── common/               # Shared utilities (crypto, chunking, protocol, clients)
│   ├── blockchain/           # In-memory ledger + TCP server
│   ├── custodians/           # Threshold key share management
│   ├── data_owner/           # Document upload, chunking, encryption
│   ├── retrieval/            # Query engine, embeddings, LLM, vector index
│   ├── storage/              # Encrypted chunk storage
│   └── user/                 # Interactive query client
├── wiki_data_owners/         # Sample datasets (science, history, tech, geography, art)
├── bench_mark_result/        # Benchmark output (JSON)
├── bench_mark_result_graphs/ # Benchmark visualizations (PNG)
├── benchmark_upload.py       # Upload pipeline benchmark
├── benchmark_query.py        # Query pipeline benchmark
├── generate_benchmark_bar_graph.py  # Chart generation
├── generate_dataset.py       # Wikipedia dataset generation
├── main.py                   # Interactive launcher (opens terminal windows)
└── requirements.txt
```

---

## Installation

**Prerequisites:** Python 3.8+, GPU recommended (CUDA) but CPU fallback is available.

```bash
pip install -r requirements.txt
```

On first run, the Qwen models (~2.4 GB total) will be downloaded to the Hugging Face cache.

---

## Running the System

### Interactive Mode

Launches all six servers and both clients in separate terminal windows:

```bash
python main.py
```

### Manual Mode

Start each component individually in separate terminals:

```bash
# 1. Embedding server (start first — others depend on it)
python -m app.retrieval.embedding_server

# 2. Infrastructure servers
python -m app.storage.storage_server
python -m app.blockchain.blockchain_server
python -m app.custodians.custodian_server --port 9001
python -m app.custodians.custodian_server --port 9002

# 3. Retrieval server
python -m app.retrieval.retrieval_server

# 4. Clients
python -m app.data_owner.data_owner_client --name dataOwner1
python -m app.user.user_client
```

---

## Benchmarking

The benchmark suite measures per-stage latency across the full upload and query pipelines. Both scripts are self-contained: they start all required servers, run the benchmark, then stop the servers when done.

By default, both benchmarks initialize five wiki data owners (`dataOwner1` to `dataOwner5`) and upload every document found under `wiki_data_owners/`.

### Upload Benchmark

Measures chunking, embedding, encryption, storage, blockchain registration, and custodian key distribution.

```bash
python benchmark_upload.py --runs 3
```

### Query Benchmark

First loads all wiki datasets and grants retrieval access, then benchmarks the query path. Measures query embedding, vector search, storage retrieval, custodian partial decryption, blockchain authorization, LLM generation, and end-to-end latency.

```bash
python benchmark_query.py --runs 5
```

Both scripts write structured JSON files into `bench_mark_result/` — one `run_details` file and one `final_average` file per run.

### Visualization

```bash
python generate_benchmark_bar_graph.py
```

Scans `bench_mark_result/` for `final_average` JSON files and generates `.png` bar charts in `bench_mark_result_graphs/`. Each bar shows the proportion of total time spent per component.

---

## Configuration

Key parameters and where to change them:

| Parameter | Location | Default |
|-----------|----------|---------|
| Embedding model | `app/retrieval/embeddings.py` | `Qwen/Qwen3-Embedding-0.6B` |
| LLM model | `app/retrieval/llm.py` | `Qwen/Qwen3-0.6B` |
| Max answer tokens | `app/retrieval/llm.py` | 256 |
| Top-k chunks for RAG | `app/retrieval/llm.py` | 10 |
| Chunk size | `app/common/chunking.py` | 200–400 characters |
| Threshold scheme | `app/custodians/custodian.py` | 2-of-2 |

All services default to `127.0.0.1` (localhost). Network addresses are configured in `app/common/clients/`.

> **Note:** All state is in-memory. Restarting any server clears its state.

---

## Sample Datasets

Five Wikipedia-derived datasets are included under `wiki_data_owners/`:

| Data Owner | Topic |
|------------|-------|
| `data_owner_1_science` | Science |
| `data_owner_2_history` | History |
| `data_owner_3_technology` | Technology |
| `data_owner_4_geography` | Geography |
| `data_owner_5_art_culture` | Art & Culture |

New datasets can be generated with:

```bash
python generate_dataset.py
```
