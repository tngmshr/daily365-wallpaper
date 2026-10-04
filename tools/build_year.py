"""Resolve the four-year content rotation and published solar-term dates."""

from __future__ import annotations

import argparse
import calendar
import copy
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "assets" / "data"


def calendar_rows(payload: dict) -> list[dict]:
    return payload["entries"] + ([payload["leap_day"]] if payload.get("leap_day") else [])


def resolve_year(year: int, base: dict, overrides: dict, solar_terms: dict) -> dict:
    """Replace whole entries, then swap contents without losing any calendar day."""
    if not 1 <= year <= 9999:
        raise ValueError("year must be between 1 and 9999")
    payload = copy.deepcopy(base)
    rows = {row["date"]: row for row in calendar_rows(payload)}
    for key, replacement in overrides.items():
        if key not in rows or not isinstance(replacement, dict):
            raise ValueError(f"Invalid slot entry: {key}")
        if replacement.get("date", key) != key:
            raise ValueError(f"Slot date does not match its key: {key}")
        rows[key] = copy.deepcopy(replacement) | {"date": key}

    dates = solar_terms.get(str(year))
    if dates is None:
        print(f"WARNING: No published solar-term dates for {year}; keeping base dates.", file=sys.stderr)
    else:
        terms = [row["solar_term"] for row in rows.values() if row.get("solar_term")]
        if len(terms) != len(set(terms)):
            raise ValueError("Duplicate solar_term entries")
        targets = [dates[term] for term in terms if term in dates]
        if len(targets) != len(set(targets)):
            raise ValueError("Duplicate solar-term target dates")
        for term in terms:
            if term not in dates:
                print(f"WARNING: No date for {year} / {term}; keeping base date.", file=sys.stderr)
                continue
            source = next(key for key, row in rows.items() if row.get("solar_term") == term)
            target = dates[term]
            if target not in rows or (target == "02-29" and not calendar.isleap(year)):
                raise ValueError(f"Invalid solar-term target date: {year} / {term} / {target}")
            if source != target:
                for key in (source, target):
                    rows[key].setdefault("illustration_date", rows[key]["date"])
                rows[source], rows[target] = rows[target], rows[source]
                rows[source]["date"], rows[target]["date"] = source, target

    # Keep the base schema: ordinary days in entries, leap_day only in leap years.
    payload["entries"] = [rows[key] for key in sorted(rows) if key != "02-29"]
    if calendar.isleap(year):
        payload["leap_day"] = rows["02-29"]
    else:
        payload.pop("leap_day", None)
    return payload


def build_year(year: int, data_dir: Path = DATA) -> dict:
    slot = (year - 2027) % 4 + 1
    base = json.loads((data_dir / "calendar.json").read_text(encoding="utf-8"))
    overrides = {} if slot == 1 else json.loads(
        (data_dir / "years" / f"slot{slot}.json").read_text(encoding="utf-8")
    )
    solar_terms = json.loads((data_dir / "solar_terms.json").read_text(encoding="utf-8"))
    return resolve_year(year, base, overrides, solar_terms)


def write_calendar(payload: dict, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--year", type=int, required=True)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    output = args.out or ROOT / "build" / "calendars" / f"{args.year}.json"
    try:
        payload = build_year(args.year)
    except ValueError as error:
        parser.error(str(error))
    write_calendar(payload, output)
    print(f"{args.year}: slot {(args.year - 2027) % 4 + 1}, {len(calendar_rows(payload))} entries -> {output}")


if __name__ == "__main__":
    main()
