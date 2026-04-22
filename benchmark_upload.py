from __future__ import annotations

import argparse
import asyncio

from benchmark_runtime import BenchmarkEnvironment, bootstrap_wiki_data_owners
from benchmark_results import utc_timestamp, write_result_json


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Benchmark wiki document uploads across the five default data owners.",
    )
    parser.add_argument("--runs", type=int, default=1, help="Number of full benchmark runs.")
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

    avg_counters["documents"] = num_reports
    return {"timings_ms": avg_timings, "counters": avg_counters}


def save_document_result(run_index: int, result: dict, timestamp: str):
    payload = {
        "benchmark_type": "upload",
        "result_kind": "document",
        "run_index": run_index,
        "owner_name": result["owner_name"],
        "document_name": result["document_name"],
        "dataset_id": result["dataset_id"],
        "benchmark": result["benchmark"],
    }
    filename = (
        f"upload_run_{run_index:03d}_{result['owner_name']}_{result['document_name']}_{timestamp}.json"
        .replace(" ", "_")
        .replace("/", "_")
    )
    return write_result_json(filename, payload)


def save_average_result(run_index: int, average_report: dict, timestamp: str):
    payload = {
        "benchmark_type": "upload",
        "result_kind": "final_average",
        "run_index": run_index,
        "benchmark": average_report,
    }
    filename = f"upload_run_{run_index:03d}_final_average_{timestamp}.json"
    return write_result_json(filename, payload)


async def run_once(run_index: int, timestamp: str) -> None:
    print(f"Starting upload benchmark run {run_index}")
    async with BenchmarkEnvironment():
        _, upload_results = await bootstrap_wiki_data_owners(benchmark_uploads=True)

    reports = [result["benchmark"] for result in upload_results if "benchmark" in result]
    for result in upload_results:
        print_report(
            f"Owner={result['owner_name']} document={result['document_name']} dataset_id={result['dataset_id']}",
            result["benchmark"],
        )
        saved_path = save_document_result(run_index, result, timestamp)
        print(f"  saved_json: {saved_path}")

    if reports:
        average_report = average_reports(reports)
        print_report(f"Run {run_index} average", average_report)
        saved_path = save_average_result(run_index, average_report, timestamp)
        print(f"Saved final average JSON to {saved_path}")


async def main() -> None:
    args = parse_args()
    timestamp = utc_timestamp()
    for run_index in range(1, args.runs + 1):
        await run_once(run_index, timestamp)


if __name__ == "__main__":
    asyncio.run(main())
