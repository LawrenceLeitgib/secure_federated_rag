from __future__ import annotations

import argparse
import json
from pathlib import Path

DEFAULT_RESULTS_DIR = Path("bench_mark_result")
DEFAULT_OUTPUT_DIR = Path("bench_mark_result_graphs")
BASE_EXCLUDED_TIMINGS = {"total_ms", "client_roundtrip_ms", "retrieval_total_ms"}

BENCHMARK_TYPE_TITLES = {
    "upload": "Upload Pipeline",
    "query": "Query Pipeline",
}


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


def clean_label(name: str) -> str:
    """Convert a timing key like 'custodian_ms' to a readable label like 'Custodian'."""
    if name.endswith("_ms"):
        name = name[:-3]
    return name.replace("_", " ").title()


def compute_component_data(
    timings_ms: dict[str, float],
    excluded_timings: set[str],
) -> tuple[list[str], list[float], list[float]]:
    included = [
        (name, value)
        for name, value in timings_ms.items()
        if name not in excluded_timings and value > 0
    ]
    total = sum(value for _, value in included)
    if total <= 0:
        return [], [], []
    labels = [clean_label(name) for name, _ in included]
    values_ms = [value for _, value in included]
    percentages = [(value / total) * 100.0 for _, value in included]
    return labels, values_ms, percentages


def build_output_path(output_dir: Path, json_path: Path, suffix: str) -> Path:
    return output_dir / f"{json_path.stem}_{suffix}.png"


def generate_graph(
    json_path: Path,
    output_dir: Path,
    excluded_timings: set[str],
    filename_suffix: str,
    subtitle: str,
) -> Path | None:
    import matplotlib.pyplot as plt
    import matplotlib.ticker as mticker

    payload = json.loads(json_path.read_text(encoding="utf-8"))
    benchmark = payload.get("benchmark", {})
    timings_ms = benchmark.get("timings_ms", {})
    labels, values_ms, percentages = compute_component_data(timings_ms, excluded_timings)
    if not labels:
        return None

    benchmark_type = payload.get("benchmark_type", "benchmark")
    title_base = BENCHMARK_TYPE_TITLES.get(benchmark_type, benchmark_type.title())
    title = f"{title_base}: Component Time Distribution\n({subtitle})"

    fig, ax = plt.subplots(figsize=(12, 6))
    bars = ax.bar(labels, percentages, color="#4C72B0", edgecolor="white", linewidth=0.7)

    ax.set_ylabel("Time Share (%)", fontsize=12)
    ax.set_xlabel("Component", fontsize=12)
    ax.set_title(title, fontsize=13, fontweight="bold")
    ax.tick_params(axis="x", rotation=30, labelsize=10)
    ax.tick_params(axis="y", labelsize=10)
    plt.setp(ax.get_xticklabels(), ha="right")
    ax.yaxis.set_major_formatter(mticker.FormatStrFormatter("%.0f%%"))
    ax.set_ylim(0, max(percentages) * 1.3)
    ax.yaxis.grid(True, linestyle="--", alpha=0.6)
    ax.set_axisbelow(True)

    for bar, pct, val_ms in zip(bars, percentages, values_ms):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + max(percentages) * 0.015,
            f"{val_ms:.1f} ms\n({pct:.1f}%)",
            ha="center",
            va="bottom",
            fontsize=9,
        )

    fig.tight_layout()
    output_path = build_output_path(output_dir, json_path, filename_suffix)
    fig.savefig(output_path, dpi=160)
    plt.close(fig)
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
            subtitle="including embedding and LLM",
        )
        without_embedding_and_llm = generate_graph(
            json_path=json_path,
            output_dir=args.output_dir,
            excluded_timings=BASE_EXCLUDED_TIMINGS | {"embedding_generation_ms", "llm_ms"},
            filename_suffix="without_embedding_and_llm",
            subtitle="excluding embedding generation and LLM",
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
