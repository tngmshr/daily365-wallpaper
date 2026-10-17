"""Cross-check assets/data/solar_terms.json against published and independently computed times.

Usage:
  python tools/check_solar_terms.py              # check (standard library only)
  python tools/check_solar_terms.py --recompute  # rewrite the computed column (needs astropy)

docs/solar_terms_check.csv holds, per year and term, the NAOJ almanac time (暦要項, when
published) and an independent computation (ERFA via astropy, apparent solar longitude, JST).
Exits with status 1 when a hard rule fails. Warnings are printed but do not fail.
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import sys
from contextlib import redirect_stderr
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TERMS_JSON = ROOT / "assets" / "data" / "solar_terms.json"
CHECK_CSV = ROOT / "docs" / "solar_terms_check.csv"
YEARS = range(2027, 2035)
FIELDS = ["year", "term", "longitude", "published_jst", "published_source", "computed_jst"]

# Apparent solar longitude of each term, and the dates it can fall on in this century.
LONGITUDES = {"立春": 315, "夏至": 90, "処暑": 150, "冬至": 270}
WINDOWS = {"立春": {"02-03", "02-04", "02-05"}, "夏至": {"06-20", "06-21", "06-22"},
           "処暑": {"08-22", "08-23", "08-24"}, "冬至": {"12-21", "12-22", "12-23"}}
PUBLISHED_TOLERANCE = timedelta(minutes=2)  # computation vs. almanac (rounded to the minute)
CLOSE_TO_MIDNIGHT = timedelta(minutes=30)


def parse_jst(text: str) -> datetime:
    return datetime.strptime(text, "%Y-%m-%d %H:%M")


def margin(moment: datetime) -> timedelta:
    midnight = moment.replace(hour=0, minute=0)
    return min(moment - midnight, midnight + timedelta(days=1) - moment)


def read_rows(path: Path = CHECK_CSV) -> list[dict]:
    return list(csv.DictReader(path.open(encoding="utf-8", newline="")))


def check(terms: dict, rows: list[dict], calendar: dict | None = None) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    sources = terms.get("_sources", {})
    seen = set()

    for year in YEARS:
        dates = terms.get(str(year))
        if not dates:
            errors.append(f"{year}: missing in solar_terms.json")
            continue
        if set(dates) != set(LONGITUDES):
            errors.append(f"{year}: terms {sorted(dates)}")
        for term, key in dates.items():
            if term in WINDOWS and key not in WINDOWS[term]:
                errors.append(f"{year} {term}: {key} is outside {sorted(WINDOWS[term])}")
        source = sources.get(str(year), "")
        if not (f"/yoko/{year}/" in source or source.startswith("計算値")):
            errors.append(f"{year}: _sources is neither the {year} almanac nor marked 計算値: {source!r}")

    for row in rows:
        year, term = int(row["year"]), row["term"]
        seen.add((year, term))
        label = f"{year} {term}"
        if term not in LONGITUDES or int(row["longitude"]) != LONGITUDES[term]:
            errors.append(f"{label}: unexpected term or longitude {row['longitude']}")
            continue
        expected = terms.get(str(year), {}).get(term)
        computed = parse_jst(row["computed_jst"]) if row["computed_jst"] else None
        published = parse_jst(row["published_jst"]) if row["published_jst"] else None
        if published:
            if f"/yoko/{year}/" not in row["published_source"]:
                errors.append(f"{label}: published time without the {year} almanac URL")
            if computed and abs(computed - published) > PUBLISHED_TOLERANCE:
                errors.append(f"{label}: computed {computed:%H:%M} differs from almanac {published:%H:%M}")
        if expected is None or year not in YEARS:
            continue
        # The almanac wins once published; until then the independent computation must agree.
        reference = published or computed
        if reference is None:
            errors.append(f"{label}: no published or computed time")
        elif reference.strftime("%m-%d") != expected:
            kind = "almanac" if published else "computed"
            errors.append(f"{label}: solar_terms.json {expected}, {kind} {reference:%m-%d %H:%M}")
        if published and f"/yoko/{year}/" not in sources.get(str(year), ""):
            errors.append(f"{label}: almanac is published but _sources still says {sources.get(str(year))!r}")
        if not published and computed and margin(computed) < CLOSE_TO_MIDNIGHT:
            warnings.append(f"{label}: computed {computed:%m-%d %H:%M} is within "
                            f"{int(margin(computed).total_seconds() // 60)} min of midnight")

    for year in YEARS:
        for term in LONGITUDES:
            if (year, term) not in seen:
                errors.append(f"{year} {term}: missing in {CHECK_CSV.name}")

    if calendar is not None:
        errors += check_calendar(terms, calendar)
    return errors, warnings


def check_calendar(terms: dict, calendar: dict) -> list[str]:
    from build_year import calendar_rows, resolve_year

    errors = []
    base = {row["solar_term"]: row["date"] for row in calendar_rows(calendar) if row.get("solar_term")}
    if set(base) != set(LONGITUDES):
        errors.append(f"calendar.json solar_term entries {sorted(base)}")
    for term, key in base.items():
        if term in WINDOWS and key not in WINDOWS[term]:
            errors.append(f"calendar.json {term} is placed on {key}")
    for year in YEARS:
        with redirect_stderr(io.StringIO()):
            result = resolve_year(year, calendar, {}, terms)
        rows = {row["date"]: row for row in calendar_rows(result)}
        for term, key in terms.get(str(year), {}).items():
            if rows.get(key, {}).get("solar_term") != term:
                errors.append(f"{year} {term}: build_year does not place it on {key}")
    return errors


def compute(year: int, term: str) -> datetime:
    """JST minute when the apparent solar longitude reaches the term (ERFA via astropy)."""
    import warnings

    import astropy.units as u
    from astropy.coordinates import GeocentricTrueEcliptic, get_sun
    from astropy.time import Time
    from erfa import ErfaWarning

    warnings.simplefilter("ignore", ErfaWarning)
    month, day = (int(part) for part in sorted(WINDOWS[term])[1].split("-"))
    target = LONGITUDES[term]

    def offset(t: Time) -> float:
        lon = get_sun(t).transform_to(GeocentricTrueEcliptic(equinox=t)).lon.deg
        return (lon - target + 180) % 360 - 180

    low = Time(datetime(year, month, day), scale="utc") - 3 * u.day
    high = low + 6 * u.day
    for _ in range(40):
        mid = low + (high - low) / 2
        if offset(low) * offset(mid) <= 0:
            high = mid
        else:
            low = mid
    moment = low.to_datetime() + timedelta(hours=9)
    return (moment + timedelta(seconds=30)).replace(second=0, microsecond=0)


def recompute(rows: list[dict]) -> None:
    for row in rows:
        row["computed_jst"] = compute(int(row["year"]), row["term"]).strftime("%Y-%m-%d %H:%M")
    with CHECK_CSV.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--recompute", action="store_true", help="rewrite computed_jst with astropy")
    args = parser.parse_args()
    rows = read_rows()
    if args.recompute:
        recompute(rows)
    terms = json.loads(TERMS_JSON.read_text(encoding="utf-8"))
    calendar = json.loads((ROOT / "assets" / "data" / "calendar.json").read_text(encoding="utf-8"))
    errors, warnings = check(terms, rows, calendar)
    for message in warnings:
        print("WARN ", message)
    for message in errors:
        print("ERROR", message)
    published = sum(1 for row in rows if row["published_jst"])
    closest = min((row for row in rows if not row["published_jst"] and int(row["year"]) in YEARS),
                  key=lambda row: margin(parse_jst(row["computed_jst"])), default=None)
    if closest:
        print(f"closest unpublished: {closest['year']} {closest['term']} {closest['computed_jst']}")
    print(f"{len(rows)} rows, {published} with almanac times, errors {len(errors)}, warnings {len(warnings)}")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
