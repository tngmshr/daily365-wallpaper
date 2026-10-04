"""Check assets/data/calendar.json against the editorial rules.

Usage: python tools/validate_calendar.py
Exits with status 1 when a hard rule fails. Warnings are printed but do not fail.
"""

from __future__ import annotations

import json
import re
import sys
from collections import Counter
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CALENDAR = ROOT / "assets" / "data" / "calendar.json"
CANDIDATES = ROOT / "work" / "candidates.json"

KINDS = {"記念日", "年中行事", "国際デー", "季節の行事", "暦のしくみ"}
VISUALS = {
    "nature", "water", "travel", "history", "people", "peace", "sports", "science",
    "space", "culture", "food", "health", "technology", "work", "seasonal",
}
SENSITIVE = re.compile(r"神事|祭祀|宮中|皇|忌|戦争|戦没|事件|事故|震災|追悼|慰霊|テロ|領土|自殺|依存症|原爆|空襲")
SCENE_BANNED = re.compile(r"\b(text|letters?|logo|flag|weapon|gun|sword|blood|god|goddess|buddha|jesus|deity)\b", re.I)


def expected_dates() -> list[str]:
    day = date(2025, 1, 1)
    out = []
    while day.year == 2025:
        out.append(day.strftime("%m-%d"))
        day += timedelta(days=1)
    return out


def copied_run(summary: str, note: str, length: int = 10) -> str | None:
    for start in range(0, max(0, len(summary) - length + 1)):
        chunk = summary[start : start + length]
        if chunk in note:
            return chunk
    return None


def main() -> int:
    data = json.loads(CALENDAR.read_text(encoding="utf-8"))
    entries = data["entries"]
    rows = entries + [data["leap_day"]]
    errors: list[str] = []
    warnings: list[str] = []

    dates = [row["date"] for row in entries]
    if dates != expected_dates():
        errors.append("entries are not exactly 01-01..12-31 in order")
    if data["leap_day"]["date"] != "02-29":
        errors.append("leap_day is not 02-29")

    candidates = json.loads(CANDIDATES.read_text(encoding="utf-8")) if CANDIDATES.exists() else {}
    for row in rows:
        key = row["date"]
        summary, tip, title = row["summary"], row["work_tip"], row["title"]
        if not 40 <= len(summary) <= 70:
            errors.append(f"{key} summary length {len(summary)}")
        if not summary.endswith("。"):
            errors.append(f"{key} summary does not end with 。")
        if not 15 <= len(tip) <= 30:
            errors.append(f"{key} work_tip length {len(tip)}")
        if len(title) > 24:
            warnings.append(f"{key} long title ({len(title)}): {title}")
        if row["kind"] not in KINDS:
            errors.append(f"{key} kind {row['kind']!r}")
        if row["visual"] not in VISUALS:
            errors.append(f"{key} visual {row['visual']!r}")
        if "solar_term" in row and row["solar_term"] not in {"立春", "夏至", "処暑", "冬至"}:
            errors.append(f"{key} unknown solar_term {row['solar_term']!r}")
        words = len(row.get("scene", "").split())
        if not 15 <= words <= 60:
            errors.append(f"{key} scene has {words} words")
        if SCENE_BANNED.search(row.get("scene", "")):
            warnings.append(f"{key} scene mentions a banned motif: {row['scene']}")
        if SENSITIVE.search(title + summary):
            warnings.append(f"{key} sensitive keyword: {title}")
        if not row["sources"] or "wikipedia.org" not in row["sources"][-1]["url"]:
            if key != "02-29":
                errors.append(f"{key} last source is not the Wikipedia date page")
        notes = " ".join(c["note"] for c in candidates.get(key, []))
        run = copied_run(summary, notes) if notes else None
        if run:
            warnings.append(f"{key} copies 10+ chars from Wikipedia: {run}")

    for label, values in (("title", [r["title"] for r in rows]), ("work_tip", [r["work_tip"] for r in rows])):
        dupes = [value for value, count in Counter(values).items() if count > 1]
        if dupes:
            errors.append(f"duplicate {label}: {dupes[:10]}")

    for message in warnings:
        print("WARN ", message)
    for message in errors:
        print("ERROR", message)
    lengths = [len(r["summary"]) for r in rows]
    print(f"{len(rows)} rows, summary length {min(lengths)}-{max(lengths)}, "
          f"kinds {dict(Counter(r['kind'] for r in rows))}, errors {len(errors)}, warnings {len(warnings)}")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
