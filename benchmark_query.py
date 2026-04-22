from __future__ import annotations

import argparse
import asyncio
import hashlib

from app.common.benchmarking import elapsed_ms, now
from app.common.clients.retrieval_client import RetrievalClient


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Benchmark the user query pipeline.")
    parser.add_argument(
        "--query",
        default="How does the secure federated RAG system protect stored documents?",
        help="Query to send to the retrieval engine.",
    )
    parser.add_argument("--runs", type=int, default=1, help="Number of benchmark runs.")
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


async def main() -> None:
    args = parse_args()
    user_id = args.user_id or hashlib.sha256(b"benchmark_query_user").hexdigest()
    client = RetrievalClient()

    all_reports: list[dict] = []
    for run_index in range(args.runs):
        request_start = now()
        response = await client.query(user_id=user_id, query_text=args.query)
        roundtrip_ms = elapsed_ms(request_start)

        if response.get("status") != "ok":
            raise RuntimeError(response.get("error", "Query benchmark failed"))

        result = response.get("result", {})
        benchmark = result.get("benchmark", {"timings_ms": {}, "counters": {}})
        benchmark["timings_ms"]["client_roundtrip_ms"] = roundtrip_ms
        benchmark["counters"]["retrieved_chunks"] = len(result.get("retrieved_chunks", []))
        all_reports.append(benchmark)

        print_report(f"Run {run_index + 1}: answer={result.get('answer', '')[:80]}", benchmark)

    if len(all_reports) > 1:
        avg_timings: dict[str, float] = {}
        for report in all_reports:
            for name, value in report.get("timings_ms", {}).items():
                avg_timings[name] = avg_timings.get(name, 0.0) + value
        for name in avg_timings:
            avg_timings[name] /= len(all_reports)
        print_report("Average", {"timings_ms": avg_timings, "counters": {"runs": len(all_reports)}})


if __name__ == "__main__":
    asyncio.run(main())
