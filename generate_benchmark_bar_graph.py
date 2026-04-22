from __future__ import annotations

import argparse
import json
from pathlib import Path

DEFAULT_RESULTS_DIR = Path("bench_mark_result")
DEFAULT_OUTPUT_DIR = Path("bench_mark_result_graphs")
BASE_EXCLUDED_TIMINGS = {"total_ms", "client_roundtrip_ms", "retrieval_total_ms"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate bar graphs from final average benchmark JSON files.",
    )
    parser.add_argument(
        "--results-dir",
        type=Path,
        default=DEFAULT_RESULTS_DIR,
        help="Directory containing benchmark JSON files.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Directory where generated graph images will be stored.",
    )
    return parser.parse_args()


def load_final_average_json_files(results_dir: Path) -> list[Path]:
    return sorted(
        path
        for path in results_dir.glob("*.json")
        if json.loads(path.read_text(encoding="utf-8")).get("result_kind") == "final_average"
    )


def compute_component_percentages(
    timings_ms: dict[str, float],
    excluded_timings: set[str],
) -> tuple[list[str], list[float]]:
    included = [
        (name, value)
        for name, value in timings_ms.items()
        if name not in excluded_timings and value > 0
    ]
    total = sum(value for _, value in included)
    if total <= 0:
        return [], []
    labels = [name for name, _ in included]
    percentages = [(value / total) * 100.0 for _, value in included]
    return labels, percentages


def build_output_path(output_dir: Path, json_path: Path, suffix: str) -> Path:
    return output_dir / f"{json_path.stem}_{suffix}.png"


def generate_graph(
    json_path: Path,
    output_dir: Path,
    excluded_timings: set[str],
    filename_suffix: str,
    title_suffix: str,
) -> Path | None:
    import matplotlib.pyplot as plt

    payload = json.loads(json_path.read_text(encoding="utf-8"))
    benchmark = payload.get("benchmark", {})
    timings_ms = benchmark.get("timings_ms", {})
    labels, percentages = compute_component_percentages(timings_ms, excluded_timings)
    if not labels:
        return None

    plt.figure(figsize=(12, 6))
    bars = plt.bar(labels, percentages, color="#4C78A8")
    plt.ylabel("Time Share (%)")
    plt.xlabel("Component")
    plt.title(
        f"{payload.get('benchmark_type', 'benchmark').title()} Final Average Component Time Proportions {title_suffix}"
    )
    plt.xticks(rotation=35, ha="right")
    plt.ylim(0, max(percentages) * 1.2)

    for bar, percentage in zip(bars, percentages):
        plt.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height(),
            f"{percentage:.1f}%",
            ha="center",
            va="bottom",
        )

    plt.tight_layout()
    output_path = build_output_path(output_dir, json_path, filename_suffix)
    plt.savefig(output_path, dpi=160)
    plt.close()
    return output_path


def main() -> None:
    args = parse_args()
    args.results_dir.mkdir(parents=True, exist_ok=True)
    args.output_dir.mkdir(parents=True, exist_ok=True)

    json_files = load_final_average_json_files(args.results_dir)
    if not json_files:
        print(f"No final average benchmark JSON files found in {args.results_dir}")
        return

    for json_path in json_files:
        with_embedding_and_llm = generate_graph(
            json_path=json_path,
            output_dir=args.output_dir,
            excluded_timings=BASE_EXCLUDED_TIMINGS,
            filename_suffix="with_embedding_and_llm",
            title_suffix="(with embedding and llm)",
        )
        without_embedding_and_llm = generate_graph(
            json_path=json_path,
            output_dir=args.output_dir,
            excluded_timings=BASE_EXCLUDED_TIMINGS | {"embedding_generation_ms", "llm_ms"},
            filename_suffix="without_embedding_and_llm",
            title_suffix="(without embedding and llm)",
        )

        if with_embedding_and_llm is None and without_embedding_and_llm is None:
            print(f"Skipped {json_path}: no component timings available")
            continue
        if with_embedding_and_llm is not None:
            print(f"Generated {with_embedding_and_llm}")
        if without_embedding_and_llm is not None:
            print(f"Generated {without_embedding_and_llm}")


if __name__ == "__main__":
    main()
