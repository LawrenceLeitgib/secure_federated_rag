# secure_federated_rag

Benchmark entrypoints:

- `python benchmark_upload.py --text-file path/to/document.txt --runs 3`
- `python benchmark_query.py --query "your question" --runs 5`

`benchmark_upload.py` reports per-stage timings for the data owner upload flow, including chunking, embedding generation, encryption, storage upload, blockchain registration, and custodian share distribution.

`benchmark_query.py` reports per-stage timings for the user query flow, including embedding generation, vector search, storage provider access, custodian time, blockchain authorization time inside custodians, LLM generation, and end-to-end total time.
