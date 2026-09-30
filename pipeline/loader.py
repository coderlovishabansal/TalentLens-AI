import gzip
import json
from pathlib import Path
from tqdm import tqdm


def load_candidates(path: str) -> list[dict]:
    """Load candidates from .jsonl or .jsonl.gz file."""
    p = Path(path)
    candidates = []

    opener = gzip.open if p.suffix == ".gz" else open
    mode = "rt"

    with opener(p, mode, encoding="utf-8") as f:
        for line in tqdm(f, desc="Loading candidates"):
            line = line.strip()
            if line:
                candidates.append(json.loads(line))

    print(f"Loaded {len(candidates):,} candidates")
    return candidates


def load_sample(path: str) -> list[dict]:
    """Load from sample_candidates.json (pretty-printed array)."""
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data if isinstance(data, list) else [data]


def candidate_summary(c: dict) -> str:
    """One-line summary of a candidate for quick inspection."""
    p = c["profile"]
    return (
        f"{p['anonymized_name']} | {p['current_title']} | "
        f"{p['years_of_experience']}yrs | {p['location']}"
    )
