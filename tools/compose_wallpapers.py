"""Place each day's date, headline, summary, and attribution on its wallpaper."""

from __future__ import annotations

import json
import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "assets" / "data" / "calendar.json"
ILLUSTRATIONS = ROOT / "assets" / "illustrations"
WALLPAPERS = ROOT / "assets" / "wallpapers"
WIDTH, HEIGHT = 900, 1600
CARD_MAX_HEIGHT = 900
CARD_CENTER_Y = 920
CARD_SAFE_TOP = 485
CARD_SAFE_BOTTOM = 150
CARD_MARGIN_X = 42
CARD_PADDING_X = 36
CARD_PADDING_TOP = 30
CARD_PADDING_BOTTOM = 26
NO_LINE_START = "、。，．・？！…：；）」』】〉》］｝〕〟”’％‰℃"
NO_LINE_END = "（「『【〈《［｛〔〝“‘"


def font_path(bold: bool) -> Path:
    names = (
        ["meiryob.ttc", "YuGothB.ttc", "NotoSansCJK-Bold.ttc"]
        if bold
        else ["meiryo.ttc", "YuGothR.ttc", "NotoSansCJK-Regular.ttc"]
    )
    roots = [
        Path("C:/Windows/Fonts"),
        Path("/usr/share/fonts/opentype/noto"),
        Path("/usr/share/fonts/truetype/noto"),
    ]
    for root in roots:
        for name in names:
            candidate = root / name
            if candidate.is_file():
                return candidate
    raise SystemExit("A Japanese font is required (for example, Meiryo on Windows).")


def load_font(path: Path, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(path), size)


def wrap_text(text: str, font: ImageFont.FreeTypeFont, width: int) -> list[str]:
    probe = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    lines: list[str] = []
    for paragraph in text.splitlines() or [text]:
        current = ""
        for character in paragraph:
            if character.isspace() and not current:
                continue
            candidate = current + character
            if not current or probe.textlength(candidate, font=font) <= width:
                current = candidate
                continue
            if character in NO_LINE_START:
                current += character
                continue
            if current[-1] in NO_LINE_END and len(current) > 1:
                opening = current[-1]
                lines.append(current[:-1].rstrip())
                current = opening + character
            else:
                lines.append(current.rstrip())
                current = "" if character.isspace() else character
        if current.strip():
            lines.append(current.rstrip())
    return lines or [""]


def layout_for(
    entry: dict[str, object], bold_path: Path, regular_path: Path, width: int
) -> dict[str, object]:
    date = str(entry["date"])
    month, day = (int(part) for part in date.split("-"))
    label = f"{month}月{day}日　｜　{entry['kind']}"
    title = str(entry["title"]).strip()
    summary = str(entry["summary"]).strip()
    source = (
        f"出典: ja.wikipedia.org/wiki/{month}月{day}日　・　CC BY-SA 4.0"
    )

    for summary_size in range(30, 22, -1):
        for title_size in range(52, 35, -2):
            label_font = load_font(regular_path, 24)
            title_font = load_font(bold_path, title_size)
            summary_font = load_font(regular_path, summary_size)
            source_font = load_font(regular_path, 15)
            title_lines = wrap_text(title, title_font, width)
            summary_lines = wrap_text(summary, summary_font, width)
            label_lines = wrap_text(label, label_font, width)
            source_lines = wrap_text(source, source_font, width)

            label_height = 31 * len(label_lines)
            title_line_height = math.ceil(title_size * 1.23)
            summary_line_height = math.ceil(summary_size * 1.48)
            source_height = 20 * len(source_lines)
            gaps = 14 * 3
            height = (
                CARD_PADDING_TOP
                + label_height
                + gaps
                + title_line_height * len(title_lines)
                + summary_line_height * len(summary_lines)
                + source_height
                + CARD_PADDING_BOTTOM
            )
            if height <= CARD_MAX_HEIGHT:
                return {
                    "date": label,
                    "title": title,
                    "summary": summary,
                    "source": source,
                    "label_font": label_font,
                    "title_font": title_font,
                    "summary_font": summary_font,
                    "source_font": source_font,
                    "title_lines": title_lines,
                    "summary_lines": summary_lines,
                    "label_lines": label_lines,
                    "source_lines": source_lines,
                    "label_height": label_height,
                    "title_line_height": title_line_height,
                    "summary_line_height": summary_line_height,
                    "source_height": source_height,
                    "height": height,
                }
    raise ValueError(f"Text does not fit on a wallpaper: {date}")


def draw_lines(
    draw: ImageDraw.ImageDraw,
    lines: list[str],
    x: int,
    y: int,
    font: ImageFont.FreeTypeFont,
    line_height: int,
    fill: tuple[int, int, int, int],
) -> int:
    for line in lines:
        draw.text((x, y), line, font=font, fill=fill, anchor="lt")
        y += line_height
    return y


def compose(entry: dict[str, object], regular_path: Path, bold_path: Path) -> None:
    date = str(entry["date"])
    artwork_path = ILLUSTRATIONS / f"{date}.jpg"
    if not artwork_path.is_file():
        raise FileNotFoundError(artwork_path)

    left = CARD_MARGIN_X
    right = WIDTH - CARD_MARGIN_X
    inner_width = right - left - CARD_PADDING_X * 2
    layout = layout_for(entry, bold_path, regular_path, inner_width)
    card_height = int(layout["height"])
    top = round(CARD_CENTER_Y - card_height / 2)
    top = max(CARD_SAFE_TOP, min(top, HEIGHT - CARD_SAFE_BOTTOM - card_height))
    bottom = top + card_height

    base = Image.open(artwork_path).convert("RGBA")
    if base.size != (WIDTH, HEIGHT):
        raise ValueError(f"Expected {WIDTH}x{HEIGHT}: {artwork_path} is {base.size}")

    shadow = Image.new("RGBA", base.size, (0, 0, 0, 0))
    shadow_draw = ImageDraw.Draw(shadow)
    shadow_draw.rounded_rectangle(
        (left, top + 9, right, bottom + 9),
        radius=34,
        fill=(30, 45, 39, 54),
    )
    base = Image.alpha_composite(base, shadow.filter(ImageFilter.GaussianBlur(16)))

    draw = ImageDraw.Draw(base, "RGBA")
    draw.rounded_rectangle(
        (left, top, right, bottom),
        radius=34,
        fill=(250, 248, 239, 238),
        outline=(255, 255, 255, 242),
        width=3,
    )

    x = left + CARD_PADDING_X
    y = top + CARD_PADDING_TOP
    y = draw_lines(
        draw,
        layout["label_lines"],
        x,
        y,
        layout["label_font"],
        31,
        (78, 111, 93, 255),
    )
    y += 14
    y = draw_lines(
        draw,
        layout["title_lines"],
        x,
        y,
        layout["title_font"],
        int(layout["title_line_height"]),
        (32, 53, 45, 255),
    )
    y += 14
    y = draw_lines(
        draw,
        layout["summary_lines"],
        x,
        y,
        layout["summary_font"],
        int(layout["summary_line_height"]),
        (43, 57, 51, 255),
    )
    y += 14
    draw_lines(
        draw,
        layout["source_lines"],
        x,
        y,
        layout["source_font"],
        20,
        (93, 107, 99, 255),
    )

    output = WALLPAPERS / f"{date}.jpg"
    output.parent.mkdir(parents=True, exist_ok=True)
    base.convert("RGB").save(
        output,
        "JPEG",
        quality=88,
        optimize=True,
        progressive=True,
        subsampling=0,
    )


def main() -> None:
    payload = json.loads(DATA.read_text(encoding="utf-8"))
    entries = payload["entries"] + [payload["leap_day"]]
    regular_path = font_path(bold=False)
    bold_path = font_path(bold=True)
    for entry in entries:
        compose(entry, regular_path, bold_path)
    print(f"Composed {len(entries)} dated wallpapers with readable summaries.")


if __name__ == "__main__":
    main()
