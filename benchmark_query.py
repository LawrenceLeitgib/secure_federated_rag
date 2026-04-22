from __future__ import annotations

import argparse
import asyncio
import hashlib

from app.common.benchmarking import elapsed_ms, now
from app.common.clients.retrieval_client import RetrievalClient
from benchmark_runtime import BenchmarkEnvironment, bootstrap_wiki_data_owners
from benchmark_results import utc_timestamp, write_result_json


DEFAULT_QUERIES = [
    "What is quantum mechanics?",
    "What caused the French Revolution?",
    "What is artificial intelligence?",
    "What is a continent?",
    "What defines classical music?",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Benchmark user queries after loading wiki datasets from the five default data owners.",
    )
    parser.add_argument(
        "--query",
        action="append",
        dest="queries",
        help="Query to benchmark. Repeat to provide multiple queries.",
    )
    parser.add_argument("--runs", type=int, default=1, help="Number of full benchmark runs.")
    parser.add_argument("--user-id", help="Optional user identifier sent to the retrieval service.")
    return parser.parse_args()


def print_report(title: str, report: dict) -> None:
    print(title)
    print("  timings_ms:")
    for name, value in report.get("timings_ms", {}).items():
        print(f"    {name}: {value:.3f}")
    print("  counters:")
    for name, value in report.get("counters", {}).items():
        print(f"    {name}: {value}")


def average_reports(reports: list[dict]) -> dict:
    avg_timings: dict[str, float] = {}
    avg_counters: dict[str, float] = {}

    for report in reports:
        for name, value in report.get("timings_ms", {}).items():
            avg_timings[name] = avg_timings.get(name, 0.0) + value
        for name, value in report.get("counters", {}).items():
            if isinstance(value, (int, float)):
                avg_counters[name] = avg_counters.get(name, 0.0) + float(value)

    num_reports = len(reports)
    for name in avg_timings:
        avg_timings[name] /= num_reports
    for name in avg_counters:
        avg_counters[name] /= num_reports

    avg_counters["queries"] = num_reports
    return {"timings_ms": avg_timings, "counters": avg_counters}


def save_query_result(run_index: int, query: str, benchmark: dict, timestamp: str):
    payload = {
        "benchmark_type": "query",
        "result_kind": "query",
        "run_index": run_index,
        "query": query,
        "benchmark": benchmark,
    }
    safe_query = "".join(ch if ch.isalnum() else "_" for ch in query).strip("_")[:80] or "query"
    filename = f"query_run_{run_index:03d}_{safe_query}_{timestamp}.json"
    return write_result_json(filename, payload)


def save_average_result(run_index: int, average_report: dict, timestamp: str):
    payload = {
        "benchmark_type": "query",
        "result_kind": "final_average",
        "run_index": run_index,
        "benchmark": average_report,
    }
    filename = f"query_run_{run_index:03d}_final_average_{timestamp}.json"
    return write_result_json(filename, payload)


async def run_once(run_index: int, queries: list[str], user_id: str, timestamp: str) -> None:
    print(f"Starting query benchmark run {run_index}")
    async with BenchmarkEnvironment():
        await bootstrap_wiki_data_owners(benchmark_uploads=False)
        client = RetrievalClient()

        reports: list[dict] = []
        for query in queries:
            request_start = now()
            response = await client.query(user_id=user_id, query_text=query)
            roundtrip_ms = elapsed_ms(request_start)

            if response.get("status") != "ok":
                raise RuntimeError(response.get("error", "Query benchmark failed"))

            result = response.get("result", {})
            benchmark = result.get("benchmark", {"timings_ms": {}, "counters": {}})
            benchmark["timings_ms"]["client_roundtrip_ms"] = roundtrip_ms
            benchmark["counters"]["retrieved_chunks"] = len(result.get("retrieved_chunks", []))
            reports.append(benchmark)

            print_report(f"Run {run_index} query={query}", benchmark)
            saved_path = save_query_result(run_index, query, benchmark, timestamp)
            print(f"  saved_json: {saved_path}")

        if reports:
            average_report = average_reports(reports)
            print_report(f"Run {run_index} average", average_report)
            saved_path = save_average_result(run_index, average_report, timestamp)
            print(f"Saved final average JSON to {saved_path}")


async def main() -> None:
    args = parse_args()
    queries = args.queries or DEFAULT_QUERIES
    user_id = args.user_id or hashlib.sha256(b"benchmark_query_user").hexdigest()
    timestamp = utc_timestamp()

    for run_index in range(1, args.runs + 1):
        await run_once(run_index, queries, user_id, timestamp)


if __name__ == "__main__":
    asyncio.run(main())
