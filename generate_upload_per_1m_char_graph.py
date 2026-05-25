from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

DEFAULT_RESULTS_DIR = Path("bench_mark_result")
DEFAULT_WIKI_DIR = Path("wiki_data_owners")
DEFAULT_OUTPUT_DIR = Path("bench_mark_result_graphs")

BASE_EXCLUDED_TIMINGS = {"total_ms", "client_roundtrip_ms"}

OWNER_DIR_MAP = {
    "dataOwner1": "data_owner_1_science",
    "dataOwner2": "data_owner_2_history",
    "dataOwner3": "data_owner_3_technology",
    "dataOwner4": "data_owner_4_geography",
    "dataOwner5": "data_owner_5_art_culture",
}


def normalize_name(name: str) -> str:
    name = name.lower()
    name = re.sub(r"[^a-z0-9\s]", " ", name)
    return re.sub(r"\s+", " ", name).strip()


def find_wiki_file(owner_name: str, document_name: str, wiki_dir: Path) -> Path | None:
    owner_subdir = OWNER_DIR_MAP.get(owner_name)
    if owner_subdir is None:
        return None
    owner_dir = wiki_dir / owner_subdir
    target = normalize_name(document_name)
    for path in owner_dir.glob("*.txt"):
        stem = re.sub(r"^\d+_", "", path.stem)
        if normalize_name(stem) == target:
            return path
    return None


def count_chars(path: Path) -> int:
    return len(path.read_text(encoding="utf-8"))


def clean_label(name: str) -> str:
    if name.endswith("_ms"):
        name = name[:-3]
    return name.replace("_", " ").title()


def load_upload_details_files(results_dir: Path) -> list[Path]:
    return sorted(
        path
        for path in results_dir.glob("upload_*.json")
        if json.loads(path.read_text(encoding="utf-8")).get("result_kind") == "run_details"
    )


def compute_weighted_average(
    results: list[dict],
    wiki_dir: Path,
    excluded_timings: set[str],
) -> tuple[list[str], list[float], list[float]] | None:
    """
    Compute the char-count-weighted average ms per 1M characters for each component.

    Returns (labels, values_per_1m_chars, percentages) or None if no data.
    """
    total_ms_per_comp: dict[str, float] = {}
    total_chars = 0

    for entry in results:
        owner = entry.get("owner_name", "")
        doc_name = entry.get("document_name", "")
        timings = entry.get("benchmark", {}).get("timings_ms", {})

        wiki_file = find_wiki_file(owner, doc_name, wiki_dir)
        if wiki_file is None:
            print(f"  Warning: no wiki file found for {owner}/{doc_name}")
            continue

        char_count = count_chars(wiki_file)
        if char_count == 0:
            continue

        total_chars += char_count
        for k, v in timings.items():
            if k not in excluded_timings and v > 0:
                total_ms_per_comp[k] = total_ms_per_comp.get(k, 0.0) + v

    if total_chars == 0 or not total_ms_per_comp:
        return None
    print(f"Total characters across all documents: {total_chars}")

    included = [(k, v) for k, v in total_ms_per_comp.items() if v > 0]
    grand_total = sum(v for _, v in included)

    labels = [clean_label(k) for k, _ in included]
    values_per_1m_chars = [(v / total_chars) * 1_000_000 for _, v in included]
    percentages = [(v / grand_total) * 100 for _, v in included]
    return labels, values_per_1m_chars, percentages


def generate_graph(
    json_path: Path,
    wiki_dir: Path,
    output_dir: Path,
    excluded_timings: set[str],
    filename_suffix: str,
    subtitle: str,
) -> Path | None:
    import matplotlib.pyplot as plt

    payload = json.loads(json_path.read_text(encoding="utf-8"))
    results = payload.get("results", [])
    if not results:
        return None

    result = compute_weighted_average(results, wiki_dir, excluded_timings)
    if result is None:
        return None
    labels, values_per_1m_chars, percentages = result

    print(f"\n{json_path.name} — {subtitle}:")
    for label, val, pct in zip(labels, values_per_1m_chars, percentages):
        print(f"  {label}: {val:.1f} ms/Mc ({pct:.1f}%)")
    print(f"  Total: {sum(values_per_1m_chars):.1f} ms/Mc")

    title = f"Upload Pipeline: Component Time per 1 M Characters\n({subtitle})"

    fig, ax = plt.subplots(figsize=(12, 6))
    bars = ax.bar(labels, values_per_1m_chars, color="#4C72B0", edgecolor="white", linewidth=0.7)

    ax.set_ylabel("ms per 1 M characters", fontsize=12)
    ax.set_xlabel("Component", fontsize=12)
    ax.set_title(title, fontsize=13, fontweight="bold")
    ax.tick_params(axis="x", rotation=30, labelsize=10)
    ax.tick_params(axis="y", labelsize=10)
    plt.setp(ax.get_xticklabels(), ha="right")
    ax.set_ylim(0, max(values_per_1m_chars) * 1.3)
    ax.yaxis.grid(True, linestyle="--", alpha=0.6)
    ax.set_axisbelow(True)

    for bar, val, pct in zip(bars, values_per_1m_chars, percentages):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + max(values_per_1m_chars) * 0.015,
            f"{val:.1f} ms/Mc\n({pct:.1f}%)",
            ha="center",
            va="bottom",
            fontsize=9,
        )

    fig.tight_layout()
    output_path = output_dir / f"{json_path.stem}_{filename_suffix}.png"
    fig.savefig(output_path, dpi=160)
    plt.close(fig)
    return output_path


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate per-1000-words upload benchmark graphs from run_details JSON files.",
    )
    parser.add_argument("--results-dir", type=Path, default=DEFAULT_RESULTS_DIR)
    parser.add_argument("--wiki-dir", type=Path, default=DEFAULT_WIKI_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)

    json_files = load_upload_details_files(args.results_dir)
    if not json_files:
        print(f"No upload run_details JSON files found in {args.results_dir}")
        return

    for json_path in json_files:
        with_embedding = generate_graph(
            json_path=json_path,
            wiki_dir=args.wiki_dir,
            output_dir=args.output_dir,
            excluded_timings=BASE_EXCLUDED_TIMINGS,
            filename_suffix="per_1m_chars_with_embedding",
            subtitle="including embedding generation",
        )
        without_embedding = generate_graph(
            json_path=json_path,
            wiki_dir=args.wiki_dir,
            output_dir=args.output_dir,
            excluded_timings=BASE_EXCLUDED_TIMINGS | {"embedding_generation_ms"},
            filename_suffix="per_1m_chars_without_embedding",
            subtitle="excluding embedding generation",
        )

        if with_embedding is None and without_embedding is None:
            print(f"Skipped {json_path}: no usable data")
            continue
        if with_embedding is not None:
            print(f"Generated {with_embedding}")
        if without_embedding is not None:
            print(f"Generated {without_embedding}")


if __name__ == "__main__":
    main()
