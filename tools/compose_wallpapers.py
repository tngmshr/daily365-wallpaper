"""Compose dated lock-screen wallpapers from calendar text and illustrations."""

from __future__ import annotations

import argparse
import json
import math
import re
from pathlib import Path
from urllib.parse import urlparse

from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageStat

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "assets/data/calendar.json"
ILLUSTRATIONS = ROOT / "assets/illustrations"
WALLPAPERS = ROOT / "assets/wallpapers"
FONT = ROOT / "tools/fonts/NotoSansJP[wght].ttf"
PREVIEW = ROOT / "work/preview/contact.jpg"
WIDTH, HEIGHT = 1440, 3200
OUTPUT_SIZE = (1080, 2400)
CARD_LEFT, CARD_RIGHT = 110, 1330
CARD_TOP, CARD_BOTTOM = 900, 2050
PAD_X, PAD_TOP, PAD_BOTTOM = 66, 55, 52
TEXT_WIDTH = CARD_RIGHT - CARD_LEFT - 2 * PAD_X
NO_LINE_START = "、。，．・：；？！ー)）」』】〉》々ゃゅょっぁぃぅぇぉャュョッァィゥェォ］｝〕〟”’％‰℃"
NO_LINE_END = "(（「『【〈《［｛〔〝“‘"
WORD = re.compile(r"[A-Za-z0-9.,:%/+\-Ａ-Ｚａ-ｚ０-９．，：％／＋－]+|[ァ-ヴー]{2,10}")
VISUAL_COLORS = {
    "nature": (78, 120, 85), "water": (47, 119, 132),
    "travel": (50, 109, 122), "history": (120, 92, 73),
    "people": (183, 101, 86), "peace": (71, 121, 94),
    "sports": (77, 133, 93), "science": (76, 102, 132),
    "space": (81, 88, 141), "culture": (145, 105, 75),
    "food": (166, 111, 62), "health": (73, 130, 115),
    "technology": (60, 104, 115), "work": (104, 98, 79),
    "seasonal": (100, 122, 84),
}


def load_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    font = ImageFont.truetype(str(FONT), size)
    font.set_variation_by_name("Bold" if bold else "Regular")
    return font


def text_atoms(text: str) -> list[str]:
    """Keep Latin/full-width words, katakana words and Japanese prohibited breaks together."""
    atoms: list[str] = []
    index = 0
    while index < len(text):
        match = WORD.match(text, index)
        atom = match.group() if match else text[index]
        index += len(atom)
        if atom.isspace():
            if atoms and atoms[-1] != " ":
                atoms.append(" ")
        elif atom[0] in NO_LINE_START:
            if atoms and atoms[-1] == " ":
                atoms.pop()
            if not atoms:
                raise ValueError(f"Prohibited punctuation at paragraph start: {atom}")
            atoms[-1] += atom
        else:
            atoms.append(atom)
    for index in range(len(atoms) - 2, -1, -1):
        if atoms[index] and atoms[index][-1] in NO_LINE_END:
            atoms[index] += atoms.pop(index + 1)
    return atoms


def wrap_text(text: str, font: ImageFont.FreeTypeFont, width: int) -> list[str]:
    probe = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    lines: list[str] = []
    for paragraph in text.splitlines() or [""]:
        current = ""
        for atom in text_atoms(paragraph):
            if atom == " " and not current:
                continue
            candidate = current + atom
            if probe.textlength(candidate, font=font) <= width:
                current = candidate
            else:
                if current.strip():
                    lines.append(current.rstrip())
                current = "" if atom == " " else atom
                if current and probe.textlength(current, font=font) > width:
                    raise ValueError(f"Unbreakable text exceeds {width}px: {current}")
        if current.strip():
            lines.append(current.rstrip())
    return lines or [""]


def fit_lines(text: str, maximum: int, sizes: range, bold: bool = False):
    for size in sizes:
        font = load_font(size, bold)
        lines = wrap_text(text, font, TEXT_WIDTH)
        if len(lines) <= maximum:
            # Avoid a last line of only a few characters (e.g. "す。") by narrowing the measure.
            for shrink in range(1, 9):
                if len(lines) < 2 or len(lines[-1]) > 3:
                    break
                narrower = wrap_text(text, font, TEXT_WIDTH - shrink * TEXT_WIDTH // 40)
                if len(narrower) == len(lines):
                    lines = narrower
            return font, lines, math.ceil(size * 1.28)
    raise ValueError(f"Text exceeds {maximum} lines: {text[:50]}")


def source_line(entry: dict) -> str:
    url = entry["sources"][-1]["url"] if entry.get("sources") else ""
    if url and "wikipedia.org" not in url:
        return f"出典: {urlparse(url).netloc.removeprefix('www.')}"
    source_month, source_day = (int(part) for part in entry.get("illustration_date", entry["date"]).split("-"))
    return f"出典: ja.wikipedia.org/wiki/{source_month}月{source_day}日 ・ CC BY-SA 4.0"


def layout_for(entry: dict) -> dict:
    month, day = (int(part) for part in entry["date"].split("-"))
    label = f"{month}月{day}日 ・ {entry['kind']}"
    source = source_line(entry)
    parts = {
        "label": (load_font(36), [label], 48),
        "title": fit_lines(entry["title"].strip(), 2, range(84, 63, -2), True),
        "summary": fit_lines(entry["summary"].strip(), 4, range(52, 43, -2)),
        "work_label": (load_font(36, True), ["今日の仕事メモ"], 48),
        "work_tip": fit_lines(entry["work_tip"].strip(), 2, range(44, 39, -2)),
        "source": (load_font(26), [source], 35),
    }
    probe = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    for key in ("label", "source"):
        font, lines, _ = parts[key]
        if probe.textlength(lines[0], font=font) > TEXT_WIDTH:
            raise ValueError(f"{key} does not fit: {entry['date']}")
    gaps = (18, 22, 29, 16, 26)
    height = PAD_TOP + PAD_BOTTOM + sum(
        len(lines) * line_height for font, lines, line_height in parts.values()
    ) + sum(gaps)
    if height > CARD_BOTTOM - CARD_TOP:
        raise ValueError(f"Card exceeds safe area: {entry['date']}")
    return parts | {"height": height, "gaps": gaps}


def lighten(color: tuple[int, int, int], amount: float) -> tuple[int, int, int]:
    return tuple(round(value + (255 - value) * amount) for value in color)


def gradient(top: tuple[int, int, int], bottom: tuple[int, int, int]) -> Image.Image:
    strip = Image.new("RGB", (1, HEIGHT))
    pixels = strip.load()
    for y in range(HEIGHT):
        blend = y / (HEIGHT - 1)
        pixels[0, y] = tuple(round(a * (1 - blend) + b * blend) for a, b in zip(top, bottom))
    return strip.resize((WIDTH, HEIGHT))


def background_for(entry: dict) -> Image.Image:
    stem = (f"themes/{entry['theme']}" if entry.get("theme")
            else entry.get("illustration_date", entry["date"]))
    artwork_path = next((path for suffix in (".webp", ".png", ".jpg")
                         if (path := ILLUSTRATIONS / f"{stem}{suffix}").is_file()), None)
    if artwork_path is None:
        color = VISUAL_COLORS.get(entry.get("visual"), (39, 96, 82))
        return gradient(lighten(color, .72), lighten(color, .34))

    with Image.open(artwork_path) as source:
        artwork = source.convert("RGB")
    scaled_height = round(artwork.height * WIDTH / artwork.width)
    artwork = artwork.resize((WIDTH, scaled_height), Image.Resampling.LANCZOS)
    top = HEIGHT - scaled_height
    sample = artwork.crop((0, round(scaled_height * .03), WIDTH, round(scaled_height * .04)))
    color = tuple(round(value) for value in ImageStat.Stat(sample).mean[:3])
    base = gradient(lighten(color, .28), color)
    visible_top = max(0, top)
    visible_height = HEIGHT - visible_top
    artwork = artwork.crop((0, max(0, -top), WIDTH, max(0, -top) + visible_height))
    mask = Image.new("L", (1, visible_height))
    mask_pixels = mask.load()
    for y in range(visible_height):
        mask_pixels[0, y] = min(255, round(y * 255 / 160)) if top > 0 else 255
    base.paste(artwork, (0, visible_top), mask.resize((WIDTH, visible_height)))
    return base


def compose(entry: dict, out_dir: Path = WALLPAPERS) -> Path:
    date = entry["date"]
    try:
        layout = layout_for(entry)
    except ValueError as error:
        raise ValueError(f"{date}: {error}") from error
    base = background_for(entry).convert("RGBA")
    bottom = CARD_TOP + layout["height"]
    shadow = Image.new("RGBA", base.size)
    ImageDraw.Draw(shadow).rounded_rectangle(
        (CARD_LEFT, CARD_TOP + 12, CARD_RIGHT, bottom + 12),
        radius=48, fill=(30, 45, 39, 55),
    )
    base = Image.alpha_composite(base, shadow.filter(ImageFilter.GaussianBlur(22)))
    card = Image.new("RGBA", base.size)
    draw = ImageDraw.Draw(card)
    draw.rounded_rectangle(
        (CARD_LEFT, CARD_TOP, CARD_RIGHT, bottom), radius=48,
        fill=(250, 248, 239, 235), outline=(255, 255, 255, 220), width=3,
    )
    base = Image.alpha_composite(base, card)
    draw = ImageDraw.Draw(base)
    x, y = CARD_LEFT + PAD_X, CARD_TOP + PAD_TOP
    order = ("label", "title", "summary", "work_label", "work_tip", "source")
    fills = ((78, 111, 93), (32, 53, 45), (43, 57, 51),
             (78, 111, 93), (43, 57, 51), (93, 107, 99))
    for index, key in enumerate(order):
        font, lines, line_height = layout[key]
        for line in lines:
            draw.text((x, y), line, font=font, fill=fills[index], anchor="lt")
            y += line_height
        if index < len(layout["gaps"]):
            gap = layout["gaps"][index]
            if key == "summary":
                draw.line((x, y + gap // 2, CARD_RIGHT - PAD_X, y + gap // 2),
                          fill=(132, 157, 139, 170), width=2)
            y += gap
    out_dir.mkdir(parents=True, exist_ok=True)
    output = out_dir / f"{date}.webp"
    base.convert("RGB").resize(OUTPUT_SIZE, Image.Resampling.LANCZOS).save(
        output, "WEBP", quality=80, method=6,
    )
    return output


def make_preview(out_dir: Path = WALLPAPERS) -> None:
    dates = [f"{month:02d}-01" for month in range(1, 13)]
    thumb_width, thumb_height = 270, 600
    sheet = Image.new("RGB", (thumb_width * 6, thumb_height * 2), "#f4f1e9")
    for index, date in enumerate(dates):
        with Image.open(out_dir / f"{date}.webp") as image:
            sheet.paste(image.resize((thumb_width, thumb_height)),
                        ((index % 6) * thumb_width, (index // 6) * thumb_height))
    PREVIEW.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(PREVIEW, "JPEG", quality=85)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--only", nargs="+", metavar="MM-DD")
    parser.add_argument("--preview", action="store_true")
    parser.add_argument("--calendar", type=Path, default=DATA)
    parser.add_argument("--out-dir", type=Path, default=WALLPAPERS)
    args = parser.parse_args()
    payload = json.loads(args.calendar.read_text(encoding="utf-8"))
    rows = payload["entries"] + ([payload["leap_day"]] if payload.get("leap_day") else [])
    entries = {entry["date"]: entry for entry in rows}
    if args.only:
        unknown = set(args.only) - entries.keys()
        if unknown:
            parser.error(f"Unknown dates: {', '.join(sorted(unknown))}")
    selected = args.only or list(entries)
    for date in selected:
        compose(entries[date], args.out_dir)
    if args.out_dir.resolve() == WALLPAPERS.resolve():
        for old in args.out_dir.glob("*.jpg"):
            old.unlink()
    if args.preview:
        for month in range(1, 13):
            date = f"{month:02d}-01"
            if not (args.out_dir / f"{date}.webp").is_file():
                compose(entries[date], args.out_dir)
        make_preview(args.out_dir)
    print(f"Composed {len(selected)} wallpapers.")


if __name__ == "__main__":
    main()
