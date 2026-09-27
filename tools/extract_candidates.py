"""Extract per-date anniversary candidates from the cached Wikipedia date pages.

Writes work/candidates.json: {"MM-DD": [{"title", "note", "refs"}...]} so that the
calendar text can be re-selected and rewritten by hand (or by an assistant).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_calendar import clean_title, clean_wikitext, parse_items, references  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "work" / "date_articles_raw.json"
OUT = ROOT / "work" / "candidates.json"
MAX_CANDIDATES = 15
MAX_NOTE = 360


def main() -> None:
    pages = json.loads(RAW.read_text(encoding="utf-8"))
    result: dict[str, list[dict[str, object]]] = {}
    for page_title, raw in pages.items():
        month, day = map(int, page_title.removesuffix("日").split("月"))
        key = f"{month:02d}-{day:02d}"
        rows = []
        for item in parse_items(raw):
            name = clean_title(item["raw_title"])
            if not name:
                continue
            note = clean_wikitext(item["raw_note"])
            rows.append({
                "title": name,
                "note": note[:MAX_NOTE],
                "refs": references(item["raw_note"])[:2],
            })
        result[key] = rows[:MAX_CANDIDATES]
    ordered = dict(sorted(result.items()))
    OUT.write_text(json.dumps(ordered, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    counts = [len(v) for v in ordered.values()]
    print(f"{len(ordered)} dates; candidates min/avg/max = {min(counts)}/{sum(counts) // len(counts)}/{max(counts)}")


if __name__ == "__main__":
    main()
