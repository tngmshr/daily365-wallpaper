"""Check assets/data/calendar.json and the 2nd-4th year slots against the editorial rules.

Usage: python tools/validate_calendar.py [--skip-layout]
Exits with status 1 when a hard rule fails. Warnings are printed but do not fail.

Checked files:
- assets/data/calendar.json        base year (01-01..12-31 in order, plus leap_day 02-29)
- assets/data/years/slot{2,3,4}.json  per-date replacements used by tools/build_year.py
- assets/data/solar_terms.json     dates for entries that carry "solar_term"
- docs/themes.json                 shared illustration ids ("theme")
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "assets" / "data"
CALENDAR = DATA / "calendar.json"
CANDIDATES = ROOT / "work" / "candidates.json"
THEMES_FILE = ROOT / "docs" / "themes.json"
ILLUSTRATIONS = ROOT / "assets" / "illustrations"
SLOTS = (2, 3, 4)

KINDS = {"記念日", "年中行事", "国際デー", "季節の行事", "暦のしくみ", "できごと"}
VISUALS = {
    "nature", "water", "travel", "history", "people", "peace", "sports", "science",
    "space", "culture", "food", "health", "technology", "work", "seasonal",
}
REQUIRED = ("date", "title", "kind", "summary", "work_tip", "visual", "scene", "sources")
OPTIONAL = {"theme", "solar_term", "illustration_date"}
SUMMARY_LENGTH = (40, 70)
WORK_TIP_LENGTH = (15, 30)
TITLE_SOFT_LIMIT = 24
SCENE_WORDS = (15, 60)
# 年によって日付が動く暦の節目。見出しにこれを含む項目は solar_term で日付を解決しないと、
# 固定日のままでは年によって1日ずれる（例: 節分は立春の前日。2025年は2月2日）。
MOVABLE = ("小寒", "大寒", "立春", "雨水", "啓蟄", "春分", "清明", "穀雨", "立夏", "小満", "芒種", "夏至",
           "小暑", "大暑", "立秋", "処暑", "白露", "秋分", "寒露", "霜降", "立冬", "小雪", "大雪", "冬至",
           "節分", "彼岸", "土用", "八十八夜", "入梅", "半夏生", "二百十日", "二百二十日")
SENSITIVE = re.compile(r"神事|祭祀|宮中|皇|忌|戦争|戦没|事件|事故|震災|追悼|慰霊|テロ|領土|自殺|依存症|原爆|空襲")
SCENE_BANNED = re.compile(r"\b(text|letters?|logo|flag|weapon|gun|sword|blood|god|goddess|buddha|jesus|deity)\b", re.I)
DATE_KEY = re.compile(r"^\d{2}-\d{2}$")
IMAGE_SUFFIXES = (".webp", ".png", ".jpg")


def expected_dates(year: int = 2025) -> list[str]:
    day = date(year, 1, 1)
    out = []
    while day.year == year:
        out.append(day.strftime("%m-%d"))
        day += timedelta(days=1)
    return out


ALL_DATES = set(expected_dates(2028))  # includes 02-29


def copied_run(summary: str, note: str, length: int = 10) -> str | None:
    for start in range(0, max(0, len(summary) - length + 1)):
        chunk = summary[start : start + length]
        if chunk in note:
            return chunk
    return None


def illustration_exists(stem: str, directory: Path = ILLUSTRATIONS) -> bool:
    return any((directory / f"{stem}{suffix}").is_file() for suffix in IMAGE_SUFFIXES)


def check_dates(entries: list, leap_day, errors: list[str]) -> None:
    """Report duplicate, missing, unexpected and out-of-order dates separately."""
    dates = [row.get("date") if isinstance(row, dict) else None for row in entries]
    expected = expected_dates()
    counts = Counter(dates)
    dupes = sorted(str(key) for key, count in counts.items() if count > 1)
    if dupes:
        errors.append(f"entries: duplicate dates {dupes}")
    missing = [key for key in expected if key not in counts]
    if missing:
        errors.append(f"entries: missing dates {missing}")
    unexpected = sorted(str(key) for key in counts if key not in expected)
    if "02-29" in unexpected:
        errors.append("entries: 02-29 must be stored in leap_day, not entries")
        unexpected.remove("02-29")
    if unexpected:
        errors.append(f"entries: invalid dates {unexpected}")
    if not dupes and not missing and not unexpected and dates != expected:
        errors.append("entries: dates are not in calendar order")
    if not isinstance(leap_day, dict):
        errors.append("leap_day: missing (needed for 02-29 in leap years)")
    elif leap_day.get("date") != "02-29":
        errors.append(f"leap_day: date is {leap_day.get('date')!r}, expected '02-29'")


def check_row(label: str, row, themes: set[str], terms: set[str],
              errors: list[str], warnings: list[str], illustrations: Path | None) -> bool:
    """Check one entry. Returns False when the row is too broken for later checks."""
    if not isinstance(row, dict):
        errors.append(f"{label} is not an object")
        return False
    missing = [key for key in REQUIRED if key not in row]
    if missing:
        errors.append(f"{label} missing fields {missing}")
        return False
    unknown = sorted(set(row) - set(REQUIRED) - OPTIONAL)
    if unknown:
        warnings.append(f"{label} unknown fields {unknown}")
    for key in ("title", "kind", "summary", "work_tip", "visual", "scene"):
        value = row[key]
        if not isinstance(value, str) or not value.strip():
            errors.append(f"{label} {key} is empty or not text")
            return False
        if value != value.strip() or "\n" in value:
            errors.append(f"{label} {key} has surrounding spaces or a line break")

    summary, tip, title = row["summary"], row["work_tip"], row["title"]
    if not SUMMARY_LENGTH[0] <= len(summary) <= SUMMARY_LENGTH[1]:
        errors.append(f"{label} summary length {len(summary)} (allowed {SUMMARY_LENGTH[0]}-{SUMMARY_LENGTH[1]})")
    if not summary.endswith("。"):
        errors.append(f"{label} summary does not end with 。")
    if not WORK_TIP_LENGTH[0] <= len(tip) <= WORK_TIP_LENGTH[1]:
        errors.append(f"{label} work_tip length {len(tip)} (allowed {WORK_TIP_LENGTH[0]}-{WORK_TIP_LENGTH[1]})")
    if len(title) > TITLE_SOFT_LIMIT:
        warnings.append(f"{label} long title ({len(title)}): {title}")
    if row["kind"] not in KINDS:
        errors.append(f"{label} kind {row['kind']!r}")
    if row["visual"] not in VISUALS:
        errors.append(f"{label} visual {row['visual']!r}")

    if "theme" in row:
        if row["theme"] not in themes:
            errors.append(f"{label} unknown theme {row['theme']!r} (not in docs/themes.json)")
        elif illustrations is not None and not illustration_exists(f"themes/{row['theme']}", illustrations):
            errors.append(f"{label} theme {row['theme']!r} has no image in assets/illustrations/themes/")
    elif illustrations is not None and not illustration_exists(row.get("illustration_date", row["date"]), illustrations):
        warnings.append(f"{label} has no illustration; the wallpaper falls back to a plain gradient")

    if "solar_term" in row:
        if row["solar_term"] not in terms:
            errors.append(f"{label} unknown solar_term {row['solar_term']!r} (not in solar_terms.json)")
        elif row["solar_term"] not in title:
            warnings.append(f"{label} solar_term {row['solar_term']} does not appear in the title {title!r}")
    else:
        moved = [word for word in MOVABLE if word in title]
        if moved:
            errors.append(f"{label} title mentions {moved[0]}, whose date changes by year; "
                          f"add solar_term and dates in solar_terms.json, or retitle")

    words = len(row["scene"].split())
    if not SCENE_WORDS[0] <= words <= SCENE_WORDS[1]:
        errors.append(f"{label} scene has {words} words")
    if SCENE_BANNED.search(row["scene"]):
        warnings.append(f"{label} scene mentions a banned motif: {row['scene']}")
    if SENSITIVE.search(title + summary):
        warnings.append(f"{label} sensitive keyword: {title}")

    sources = row["sources"]
    if not isinstance(sources, list) or not sources:
        errors.append(f"{label} has no source")
        return True
    for index, source in enumerate(sources):
        if not isinstance(source, dict) or not str(source.get("label", "")).strip():
            errors.append(f"{label} source {index + 1} has no label")
            continue
        url = source.get("url")
        if not isinstance(url, str) or not re.match(r"https?://[^\s/]+\.[^\s/]+/?\S*$", url):
            errors.append(f"{label} source {index + 1} url is not a web URL: {url!r}")
        elif url.startswith("http://"):
            warnings.append(f"{label} source {index + 1} uses http (no TLS): {url}")
    if any("wikipedia.org" in str(s.get("url", "")) for s in sources[:-1] if isinstance(s, dict)):
        # Entries adapted from Wikipedia credit the date page last; primary-source entries cite no Wikipedia.
        errors.append(f"{label} last source is not the Wikipedia date page")
    return True


def check_duplicates(scope: str, rows: list[dict], errors: list[str]) -> None:
    for key in ("title", "work_tip", "summary"):
        values = Counter(row[key] for row in rows if isinstance(row.get(key), str))
        dupes = [value for value, count in values.items() if count > 1]
        if dupes:
            errors.append(f"{scope}: duplicate {key}: {dupes[:10]}")


def check_layout(label: str, row: dict, errors: list[str]) -> None:
    from compose_wallpapers import layout_for
    try:
        layout_for(row)
    except (ValueError, KeyError) as error:
        errors.append(f"{label} does not fit the wallpaper card: {error}")


def validate(data: dict, slots: dict[int, dict], themes: set[str], solar_terms: dict,
             candidates: dict | None = None, illustrations: Path | None = ILLUSTRATIONS,
             layout: bool = False) -> tuple[list[str], list[str], list[dict]]:
    """Return (errors, warnings, base rows). Pure enough to unit-test with in-memory data."""
    errors: list[str] = []
    warnings: list[str] = []
    entries = data.get("entries")
    if not isinstance(entries, list):
        return ["calendar.json has no entries list"], warnings, []
    leap_day = data.get("leap_day")
    check_dates(entries, leap_day, errors)
    rows = entries + ([leap_day] if isinstance(leap_day, dict) else [])

    years = {key: value for key, value in solar_terms.items() if not key.startswith("_")}
    terms = {term for dates in years.values() if isinstance(dates, dict) for term in dates}

    valid_rows = []
    for row in rows:
        label = row.get("date", "?") if isinstance(row, dict) else "?"
        if check_row(str(label), row, themes, terms, errors, warnings, illustrations):
            valid_rows.append(row)
            if layout:
                check_layout(str(label), row, errors)
        notes = " ".join(c["note"] for c in (candidates or {}).get(label, []))
        run = copied_run(row.get("summary", ""), notes) if notes and isinstance(row, dict) else None
        if run:
            warnings.append(f"{label} copies 10+ chars from Wikipedia: {run}")
    check_duplicates("base year", valid_rows, errors)

    # Every movable entry needs a date in every published year, and only one entry per term.
    base_terms = Counter(row["solar_term"] for row in valid_rows if "solar_term" in row)
    for term, count in base_terms.items():
        if count > 1:
            errors.append(f"solar_term {term} is used by {count} entries")
    for year, dates in sorted(years.items()):
        if not isinstance(dates, dict):
            errors.append(f"solar_terms.json {year} is not an object")
            continue
        absent = sorted(set(base_terms) - set(dates))
        if absent:
            errors.append(f"solar_terms.json {year} has no date for {absent}")
        for term, target in dates.items():
            leap = int(year) % 4 == 0 and (int(year) % 100 != 0 or int(year) % 400 == 0)
            if not isinstance(target, str) or target not in ALL_DATES or (target == "02-29" and not leap):
                errors.append(f"solar_terms.json {year} {term} has invalid date {target!r}")
        targets = Counter(dates.values())
        if any(count > 1 for count in targets.values()):
            errors.append(f"solar_terms.json {year} puts two terms on one date")

    base = {row["date"]: row for row in valid_rows}
    term_dates = {row["date"] for row in valid_rows if "solar_term" in row}
    for slot, overrides in sorted(slots.items()):
        scope = f"slot{slot}"
        if not isinstance(overrides, dict):
            errors.append(f"{scope}.json is not an object of MM-DD keys")
            continue
        merged = dict(base)
        for key, row in overrides.items():
            label = f"{scope}/{key}"
            if not DATE_KEY.match(key) or key not in ALL_DATES:
                errors.append(f"{label}: invalid date key")
                continue
            if isinstance(row, dict) and row.get("date", key) != key:
                errors.append(f"{label}: date {row.get('date')!r} does not match its key")
            if key in term_dates:
                errors.append(f"{label}: replaces the {base[key]['solar_term']} entry, which would vanish that year")
            if isinstance(row, dict) and "solar_term" in row:
                errors.append(f"{label}: slot entries cannot carry solar_term (only the base year moves)")
            if isinstance(row, dict) and "illustration_date" in row:
                errors.append(f"{label}: illustration_date is set by build_year, not by hand")
            if check_row(label, row, themes, terms, errors, warnings, illustrations):
                merged[key] = row
                if layout:
                    check_layout(label, row | {"date": key}, errors)
            if isinstance(row, dict) and key in base and row.get("title") == base[key].get("title"):
                warnings.append(f"{label} has the same title as the base year: {row.get('title')}")
        check_duplicates(f"{scope} year", list(merged.values()), errors)
    return errors, warnings, valid_rows


def load_slots(data_dir: Path = DATA) -> dict[int, dict]:
    slots = {}
    for slot in SLOTS:
        path = data_dir / "years" / f"slot{slot}.json"
        if path.is_file():
            slots[slot] = json.loads(path.read_text(encoding="utf-8"))
    return slots


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--skip-layout", action="store_true",
                        help="Skip the wallpaper text-fit check (needs Pillow and tools/fonts)")
    args = parser.parse_args()

    data = json.loads(CALENDAR.read_text(encoding="utf-8"))
    themes = {t["id"] for t in json.loads(THEMES_FILE.read_text(encoding="utf-8"))["themes"]}
    solar_terms = json.loads((DATA / "solar_terms.json").read_text(encoding="utf-8"))
    candidates = json.loads(CANDIDATES.read_text(encoding="utf-8")) if CANDIDATES.exists() else {}
    layout = not args.skip_layout
    if layout:
        try:
            import compose_wallpapers  # noqa: F401  (needs Pillow)
        except ImportError as error:
            print(f"WARN  layout check skipped: {error}")
            layout = False
    errors, warnings, rows = validate(data, load_slots(), themes, solar_terms, candidates, ILLUSTRATIONS, layout)

    for message in warnings:
        print("WARN ", message)
    for message in errors:
        print("ERROR", message)
    lengths = [len(r["summary"]) for r in rows] or [0]
    print(f"{len(rows)} rows, summary length {min(lengths)}-{max(lengths)}, "
          f"kinds {dict(Counter(r['kind'] for r in rows))}, errors {len(errors)}, warnings {len(warnings)}")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
