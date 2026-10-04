"""Add the iPhone Shortcut image path and offline precache list to Flutter web."""

from __future__ import annotations

import argparse
import json
import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path

from PIL import Image
from build_year import DATA, build_year, calendar_rows, write_calendar

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "build" / "web"
SOURCE_WALLPAPERS = ROOT / "assets" / "wallpapers"
JST = timezone(timedelta(hours=9))


def publishing_year(now: datetime, rollover: bool = False) -> int:
    today = now.astimezone(JST)
    # The scheduled publish starts at 23:30 JST, just before the new year.
    return today.year + int(rollover and (today.month, today.day) == (12, 31))


def package_wallpapers(year: int, build: Path, only: list[str] | None = None) -> tuple[int, int]:
    base = json.loads((DATA / "calendar.json").read_text(encoding="utf-8"))
    base_rows = {row["date"]: row for row in calendar_rows(base)}
    calendars = {value: build_year(value) for value in (year, year + 1)}
    if only:
        unknown = set(only) - base_rows.keys()
        if unknown:
            raise ValueError(f"Unknown dates: {', '.join(sorted(unknown))}")
    public = build / "wallpapers"
    if public.exists():
        shutil.rmtree(public)
    public.mkdir(parents=True)
    # Intermediate calendars/images stay outside the deployed web app.
    generated = build.parent / "yearly"
    reused: dict[str, Path] = {}
    counts = [0, 0]
    for value, payload in calendars.items():
        write_calendar(payload, generated / f"{value}.json")
        target_dir = public / str(value)
        target_dir.mkdir()
        for entry in calendar_rows(payload):
            key = entry["date"]
            if only and key not in only:
                continue
            fingerprint = json.dumps(entry, ensure_ascii=False, sort_keys=True)
            target = target_dir / f"{key}.jpg"
            if fingerprint in reused:
                shutil.copyfile(reused[fingerprint], target)
            else:
                source = SOURCE_WALLPAPERS / f"{key}.webp"
                if entry != base_rows.get(key) or not source.is_file():
                    from compose_wallpapers import compose
                    source = compose(entry, generated / str(value))
                with Image.open(source) as image:
                    image.convert("RGB").resize((1080, 2400), Image.Resampling.LANCZOS).save(
                        target, "JPEG", quality=85,
                    )
                reused[fingerprint] = target
            counts[int(value != year)] += 1
            if value == year:
                shutil.copyfile(target, public / target.name)
    return counts[0], counts[1]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--year", type=int, help="Override the JST year for a reproducible build")
    parser.add_argument("--rollover", action="store_true", help="Publish next year on December 31 JST")
    parser.add_argument("--only", nargs="+", metavar="MM-DD", help="Package a few dates for local verification")
    parser.add_argument("--build-dir", type=Path, default=BUILD)
    args = parser.parse_args()
    build = args.build_dir.resolve()
    if not (build / "index.html").is_file():
        raise SystemExit("Run flutter build web before this packaging step.")
    year = args.year if args.year is not None else publishing_year(datetime.now(JST), args.rollover)
    try:
        current_count, next_count = package_wallpapers(year, build, args.only)
    except ValueError as error:
        parser.error(str(error))
    (build / ".nojekyll").write_text("", encoding="utf-8")

    files = []
    for path in sorted(build.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(build).as_posix()
        if relative in {"service-worker.js", "precache-manifest.json"}:
            continue
        if relative.startswith("wallpapers/"):
            continue
        files.append("./" + relative)
    if "./" not in files:
        files.insert(0, "./")
    (build / "precache-manifest.json").write_text(
        json.dumps({"files": files}, ensure_ascii=False, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    print(f"Prepared {len(files)} offline app files, {current_count} Shortcut wallpapers, "
          f"and year directories {year} ({current_count}) / {year + 1} ({next_count}).")


if __name__ == "__main__":
    main()
