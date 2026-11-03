"""Add the iPhone Shortcut image path and offline precache list to Flutter web."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path

from PIL import Image
from build_year import DATA, build_year, calendar_rows, write_calendar

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "build" / "web"
SOURCE_WALLPAPERS = ROOT / "assets" / "wallpapers"
JST = timezone(timedelta(hours=9))
# web/service-worker.js names its cache with this placeholder; packaging replaces it with a
# hash of the precached files so every deploy that changes the app installs a fresh cache.
CACHE_VERSION_PLACEHOLDER = "__PRECACHE_VERSION__"
# Split-per-ABI APKs add 1000/2000 to versionCode and UpdateChecker.kt compares versionCode % 1000.
MAX_BUILD_NUMBER = 999


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


def read_version(pubspec: str) -> tuple[str, int]:
    match = re.search(r"^version:\s*(\d+\.\d+\.\d+)\+(\d+)\s*$", pubspec, re.MULTILINE)
    if not match:
        raise SystemExit("pubspec.yaml needs a version like 1.3.0+6.")
    version, build_number = match.group(1), int(match.group(2))
    if not 1 <= build_number <= MAX_BUILD_NUMBER:
        # versionCode % 1000 on the device would wrap and the notice would compare the wrong numbers.
        raise SystemExit(f"pubspec.yaml build number must be 1-{MAX_BUILD_NUMBER} (got {build_number}).")
    return version, build_number


def write_version(build: Path, root: Path = ROOT) -> None:
    """Publish the app version the Android update notice compares against."""
    version, build_number = read_version((root / "pubspec.yaml").read_text(encoding="utf-8"))
    notes = json.loads((root / "tools" / "whats_new.json").read_text(encoding="utf-8"))
    (build / "version.json").write_text(
        json.dumps({"version": version, "build": build_number, "notes": notes.get(version, [])},
                   ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def write_precache(build: Path) -> list[str]:
    """List the offline app files with content revisions and stamp the service worker cache name."""
    revisions: dict[str, str] = {}
    for path in sorted(build.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(build).as_posix()
        if relative in {"service-worker.js", "precache-manifest.json", "version.json",
                        "flutter_service_worker.js"}:
            continue
        # upload-pages-artifact leaves out dotfiles (.nojekyll, .last_build_id); one 404 would
        # make cache.addAll fail and the whole offline install with it.
        if any(part.startswith(".") for part in relative.split("/")):
            continue
        if relative.startswith("wallpapers/"):
            continue
        revisions["./" + relative] = hashlib.sha256(path.read_bytes()).hexdigest()[:16]
    # "./" is the same document as index.html for navigation requests.
    if "./index.html" in revisions:
        revisions["./"] = revisions["./index.html"]
    files = sorted(revisions)
    manifest = {"files": files, "revisions": {key: revisions[key] for key in files}}
    (build / "precache-manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    worker = build / "service-worker.js"
    if worker.is_file():
        version = hashlib.sha256(json.dumps(manifest, sort_keys=True).encode("utf-8")).hexdigest()[:12]
        source = worker.read_text(encoding="utf-8")
        if CACHE_VERSION_PLACEHOLDER not in source:
            raise SystemExit(f"service-worker.js has no {CACHE_VERSION_PLACEHOLDER}; was it packaged twice?")
        worker.write_text(source.replace(CACHE_VERSION_PLACEHOLDER, version), encoding="utf-8")
    return files


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
    write_version(build)

    files = write_precache(build)
    print(f"Prepared {len(files)} offline app files, {current_count} Shortcut wallpapers, "
          f"and year directories {year} ({current_count}) / {year + 1} ({next_count}).")


if __name__ == "__main__":
    main()
