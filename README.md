# secure_federated_rag

Benchmark entrypoints:

- `python benchmark_upload.py --runs 3`
- `python benchmark_query.py --runs 5`
- `python generate_benchmark_bar_graph.py`

Both scripts are self-contained: they start the embedding server, storage server, blockchain server, two custodians, and the retrieval server locally, then stop them when the benchmark finishes.

By default, both benchmarks initialize the five wiki data owners (`dataOwner1` to `dataOwner5`) and upload every document found under `wiki_data_owners`, matching the existing owner-name-based initialization flow.

`benchmark_upload.py` reports per-stage timings for each uploaded document, including chunking, embedding generation, encryption, storage upload, blockchain registration, and custodian share distribution.

`benchmark_query.py` first loads all wiki datasets and grants retrieval access, then benchmarks the query path. It reports embedding generation, vector search, storage provider access, custodian time, blockchain authorization time inside custodians, LLM generation, and end-to-end total time.

Both benchmark scripts now also write structured JSON files into `bench_mark_result/`. They save individual run outputs plus one `final_average` JSON per run.

`generate_benchmark_bar_graph.py` scans `bench_mark_result/` for those `final_average` JSON files and creates `.png` bar charts next to them. Each bar shows the proportion of total component time for the averaged result only.
