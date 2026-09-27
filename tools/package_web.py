"""Add the iPhone Shortcut image path and offline precache list to Flutter web."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "build" / "web"
SOURCE_WALLPAPERS = ROOT / "assets" / "wallpapers"


def main() -> None:
    if not (BUILD / "index.html").is_file():
        raise SystemExit("Run flutter build web before this packaging step.")

    source_files = sorted(SOURCE_WALLPAPERS.glob("*.webp"))
    if len(source_files) != 366:
        raise SystemExit(f"Expected 366 WebP wallpapers; found {len(source_files)}. Run tools/compose_wallpapers.py first.")
    public_wallpapers = BUILD / "wallpapers"
    if public_wallpapers.exists():
        shutil.rmtree(public_wallpapers)
    public_wallpapers.mkdir(parents=True)
    for source in source_files:
        with Image.open(source) as image:
            image.convert("RGB").resize((1080, 2400), Image.Resampling.LANCZOS).save(
                public_wallpapers / f"{source.stem}.jpg", "JPEG", quality=85,
            )
    (BUILD / ".nojekyll").write_text("", encoding="utf-8")

    files = []
    for path in sorted(BUILD.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(BUILD).as_posix()
        if relative in {"service-worker.js", "precache-manifest.json"}:
            continue
        if relative.startswith("wallpapers/"):
            continue
        files.append("./" + relative)
    if "./" not in files:
        files.insert(0, "./")
    (BUILD / "precache-manifest.json").write_text(
        json.dumps({"files": files}, ensure_ascii=False, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    print(f"Prepared {len(files)} offline app files and {len(source_files)} Shortcut wallpapers.")


if __name__ == "__main__":
    main()
