from __future__ import annotations

import json
import math
from pathlib import Path
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "assets" / "data" / "calendar.json"
OUT = ROOT / "assets" / "wallpapers"
W, H = 900, 1600

PALETTES = {
    "travel": ((224, 242, 240), (91, 150, 151), (238, 190, 109), (53, 104, 106)),
    "nature": ((226, 240, 220), (105, 145, 98), (232, 196, 123), (49, 94, 66)),
    "history": ((243, 231, 211), (153, 124, 92), (238, 190, 109), (90, 73, 62)),
    "people": ((248, 228, 218), (195, 125, 106), (247, 202, 135), (111, 78, 73)),
    "new_year": ((225, 239, 235), (87, 127, 111), (237, 187, 104), (45, 83, 75)),
}
DEFAULT = ((231, 238, 234), (91, 132, 118), (221, 184, 117), (50, 88, 79))


def mix(a, b, t):
    return tuple(round(x + (y - x) * t) for x, y in zip(a, b))


def base_image(key):
    top, ground, sun_color, dark = PALETTES.get(key, DEFAULT)
    image = Image.new("RGB", (W, H))
    pixels = image.load()
    horizon = int(H * .62)
    for y in range(H):
        t = min(1, y / (H * .72))
        color = mix(top, mix(top, ground, .48), t)
        if y > horizon:
            color = mix(ground, dark, min(.46, (y - horizon) / H * .9))
        for x in range(W):
            pixels[x, y] = color
    d = ImageDraw.Draw(image)
    # Clock-safe upper quarter: only a soft sun and fine cloud details below it.
    d.ellipse((W*.66, H*.30, W*.88, H*.42), fill=sun_color)
    d.ellipse((W*.10, H*.34, W*.29, H*.365), fill=mix(top, (255,255,255), .34))
    d.ellipse((W*.18, H*.325, W*.39, H*.36), fill=mix(top, (255,255,255), .4))
    return image, d, top, ground, sun_color, dark


def draw_travel(image, d, top, ground, sun, dark):
    d.polygon([(0, H*.69),(W*.19,H*.52),(W*.36,H*.68),(W*.57,H*.47),(W*.78,H*.68),(W,H*.51),(W,H),(0,H)], fill=(86,132,132))
    d.polygon([(W*.19,H*.52),(W*.30,H*.63),(W*.36,H*.68),(W*.57,H*.47),(W*.68,H*.64),(W*.78,H*.68),(W,H*.51),(W,H*.73),(0,H*.77)], fill=(67,112,119))
    d.polygon([(W*.53,H*.54),(W*.57,H*.47),(W*.62,H*.56),(W*.59,H*.535),(W*.57,H*.55)], fill=(246,241,223))
    d.rectangle((0,H*.72,W,H), fill=(91,154,161))
    for y in [H*.77,H*.83,H*.9]:
        d.arc((W*.05,y-30,W*.95,y+65), 0, 180, fill=(178,217,209), width=4)
    d.line([(W*.58,H),(W*.52,H*.91),(W*.58,H*.84),(W*.46,H*.76)], fill=(243,222,174), width=42, joint="curve")
    d.line([(W*.58,H),(W*.52,H*.91),(W*.58,H*.84),(W*.46,H*.76)], fill=(250,238,205), width=7, joint="curve")


def draw_nature(image, d, top, ground, sun, dark):
    d.polygon([(0,H*.70),(W*.2,H*.53),(W*.42,H*.71),(W*.63,H*.48),(W*.86,H*.69),(W,H*.58),(W,H),(0,H)], fill=(105,151,105))
    d.polygon([(0,H*.78),(W*.25,H*.65),(W*.5,H*.78),(W*.77,H*.62),(W,H*.76),(W,H),(0,H)], fill=(67,117,78))
    d.rectangle((0,H*.82,W,H), fill=(97,151,129))
    for x, y, r in [(135,.66,68),(260,.71,54),(700,.66,81),(800,.72,60)]:
        d.rectangle((x-9,H*y,x+9,H*.88),fill=(105,82,58))
        for dx,dy in [(-.05,-.01),(0,-.07),(.05,-.01),(0,.02)]:
            d.ellipse((x+W*dx-r*.53,y*H+H*dy-r*.5,x+W*dx+r*.53,y*H+H*dy+r*.5),fill=(177,205,143))
    for i in range(7):
        x=90+i*115
        d.ellipse((x,H*.84+(i%2)*14,x+16,H*.89+(i%2)*14),fill=(235,221,164))


def draw_history(image, d, top, ground, sun, dark):
    # Quiet memorial architecture and a small light; no graphic depiction.
    stone=(236,222,196)
    d.rectangle((W*.17,H*.58,W*.83,H*.84),fill=stone)
    d.polygon([(W*.12,H*.59),(W*.5,H*.47),(W*.88,H*.59)],fill=(214,194,164))
    for x in [W*.24,W*.42,W*.58,W*.76]:
        d.rounded_rectangle((x-24,H*.61,x+24,H*.82),radius=22,fill=(190,165,132))
    d.rectangle((W*.14,H*.82,W*.86,H*.85),fill=(218,199,168))
    # Candle and warm glow in the lower center.
    d.ellipse((W*.42,H*.75,W*.58,H*.91),fill=(247,210,139))
    d.rounded_rectangle((W*.47,H*.80,W*.53,H*.93),radius=10,fill=(255,247,220))
    d.ellipse((W*.48,H*.75,W*.52,H*.83),fill=(238,151,77))


def draw_people(image, d, top, ground, sun, dark):
    d.polygon([(0,H*.72),(W*.18,H*.63),(W*.38,H*.72),(W*.58,H*.58),(W*.83,H*.71),(W,H*.62),(W,H),(0,H)],fill=(177,126,110))
    for x, y, col in [(W*.35,H*.70,(252,227,196)),(W*.5,H*.65,(246,198,133)),(W*.65,H*.70,(246,225,208))]:
        r=43
        d.ellipse((x-r,y-r,x+r,y+r),fill=col)
        d.rounded_rectangle((x-54,y+36,x+54,y+210),radius=38,fill=col)
    d.arc((W*.25,H*.72,W*.75,H*.93),180,360,fill=(255,241,215),width=7)


def draw_new_year(image, d, top, ground, sun, dark):
    d.polygon([(0,H*.74),(W*.22,H*.57),(W*.41,H*.74),(W*.67,H*.52),(W*.9,H*.74),(W,H*.68),(W,H),(0,H)],fill=(110,151,134))
    d.ellipse((W*.34,H*.54,W*.66,H*.86),fill=(239,184,105))
    d.rectangle((0,H*.80,W,H),fill=(94,137,122))
    # Pine sprigs at the bottom corners frame the scene without obscuring the center.
    for x, direction in [(45,1),(855,-1)]:
        d.line((x,H*.98,x+direction*62,H*.78),fill=(46,89,77),width=12)
        for i in range(5):
            yy=H*(.82+i*.028)
            xx=x+direction*(52-i*5)
            d.line((x+direction*25,yy,xx,yy-30),fill=(55,104,87),width=7)


def make_wallpaper(key, path):
    image, d, top, ground, sun, dark = base_image(key)
    drawer = {"travel":draw_travel,"nature":draw_nature,"history":draw_history,"people":draw_people,"new_year":draw_new_year}.get(key,draw_travel)
    drawer(image,d,top,ground,sun,dark)
    # Soft film grain keeps the flat illustration from looking sterile.
    image.save(path, "JPEG", quality=88, optimize=True, progressive=True)


def main():
    payload=json.loads(DATA.read_text(encoding="utf-8"))
    OUT.mkdir(parents=True,exist_ok=True)
    for entry in payload["entries"]:
        name=entry["date"]+".jpg"
        make_wallpaper(entry.get("visual","default"), OUT/name)
    print("Generated", len(payload["entries"]), "topic-matched wallpaper previews in", OUT)

if __name__ == "__main__":
    main()
