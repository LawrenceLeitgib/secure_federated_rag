import json
from pathlib import Path

results_dir = Path("bench_mark_result")

for path in sorted(results_dir.glob("upload_*details*.json")):
    payload = json.loads(path.read_text(encoding="utf-8"))
    total = sum(
        entry["benchmark"]["counters"]["num_chunks"]
        for entry in payload.get("results", [])
    )
    print(f"{path.name}: {total} chunks across {len(payload.get('results', []))} documents")
