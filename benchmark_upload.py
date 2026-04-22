from __future__ import annotations

import argparse
import asyncio
from pathlib import Path

from app.data_owner.service import DataOwnerService


DEFAULT_TEXT = (
    "Retrieval-augmented generation combines retrieval and generation. "
    "In this system, data owners upload documents that are chunked, embedded, "
    "encrypted, stored by a storage provider, registered on a blockchain-like ledger, "
    "and protected through custodians holding threshold key shares. "
    "Benchmarking the upload path helps isolate chunking, embedding, encryption, storage, "
    "blockchain registration, and custodian distribution costs."
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Benchmark the data owner upload pipeline.")
    parser.add_argument("--name", default="benchmark_data_owner", help="Data owner name.")
    parser.add_argument("--document-name", default="benchmark_document", help="Base document name.")
    parser.add_argument("--text", help="Document text to upload.")
    parser.add_argument("--text-file", help="Path to a text file to upload.")
    parser.add_argument("--runs", type=int, default=1, help="Number of benchmark runs.")
    return parser.parse_args()


def load_text(args: argparse.Namespace) -> str:
    if args.text:
        return args.text
    if args.text_file:
        return Path(args.text_file).read_text(encoding="utf-8")
    return DEFAULT_TEXT


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
    text = load_text(args)
    service = DataOwnerService()
    await service.create_owner(args.name)

    all_reports: list[dict] = []
    for run_index in range(args.runs):
        result = await service.upload_text_document_with_benchmark(
            document_name=f"{args.document_name}_{run_index + 1}",
            text=text,
        )
        benchmark = result["benchmark"]
        all_reports.append(benchmark)
        print_report(f"Run {run_index + 1}: dataset_id={result['dataset_id']}", benchmark)

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
