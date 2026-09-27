"""Create original, text-free daily illustrations and matching app icons."""

from __future__ import annotations

import json
import math
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "assets" / "data" / "calendar.json"
ILLUSTRATIONS = ROOT / "assets" / "illustrations"
W, H = 900, 1600

PALETTES = {
    "nature": ((228, 240, 221), (126, 166, 118), (242, 196, 116), (52, 98, 68)),
    "water": ((222, 240, 239), (102, 163, 169), (244, 198, 128), (43, 103, 119)),
    "travel": ((225, 238, 239), (94, 144, 156), (247, 193, 119), (46, 92, 112)),
    "history": ((246, 232, 207), (174, 137, 97), (241, 190, 112), (107, 77, 61)),
    "people": ((247, 230, 219), (193, 128, 111), (248, 197, 134), (116, 75, 74)),
    "peace": ((232, 240, 224), (137, 165, 132), (247, 207, 139), (62, 105, 82)),
    "sports": ((232, 241, 232), (115, 157, 123), (245, 195, 116), (55, 103, 74)),
    "science": ((227, 235, 243), (112, 143, 177), (248, 197, 121), (59, 78, 112)),
    "space": ((225, 229, 244), (106, 111, 164), (250, 205, 125), (47, 52, 103)),
    "culture": ((244, 233, 215), (177, 133, 91), (243, 192, 118), (100, 72, 67)),
    "food": ((249, 235, 210), (194, 147, 89), (243, 181, 106), (102, 81, 62)),
    "health": ((230, 241, 236), (112, 159, 143), (245, 194, 131), (54, 100, 95)),
    "technology": ((229, 237, 239), (104, 147, 157), (245, 192, 116), (48, 86, 103)),
    "work": ((239, 235, 221), (151, 139, 111), (242, 194, 121), (83, 78, 68)),
    "seasonal": ((235, 238, 227), (129, 158, 122), (245, 195, 118), (68, 92, 76)),
}
DEFAULT_THEME = "people"


def mix(a: tuple[int, int, int], b: tuple[int, int, int], t: float) -> tuple[int, int, int]:
    return tuple(round(x + (y - x) * t) for x, y in zip(a, b))


def base_scene(theme: str, seed: int):
    sky, ground, sun, dark = PALETTES.get(theme, PALETTES[DEFAULT_THEME])
    gradient = Image.new("RGB", (1, H))
    pixels = gradient.load()
    horizon = int(H * 0.67)
    lower = mix(ground, dark, 0.34)
    for y in range(H):
        t = min(1.0, y / (H * 0.74))
        color = mix(sky, mix(sky, ground, 0.48), t)
        if y > horizon:
            color = mix(ground, dark, min(0.54, (y - horizon) / H * 1.25))
        pixels[0, y] = color
    image = gradient.resize((W, H), Image.Resampling.NEAREST)
    draw = ImageDraw.Draw(image)
    offset = (seed % 7) * 0.012
    # Clock-safe space stays open; the sun and clouds sit below the clock area.
    sx, sy = int(W * (0.75 - offset)), int(H * 0.34)
    sr = 49 + (seed % 4) * 5
    draw.ellipse((sx - sr, sy - sr, sx + sr, sy + sr), fill=sun)
    cloud = mix(sky, (255, 255, 246), 0.40)
    for cx, cy, cw in [(0.18, 0.39, 78), (0.42, 0.46, 55)]:
        x, y = int(W * cx), int(H * cy)
        draw.ellipse((x - cw, y - 15, x + cw, y + 15), fill=cloud)
        draw.ellipse((x - cw * 0.45, y - 32, x + cw * 0.1, y + 15), fill=cloud)
        draw.ellipse((x, y - 27, x + cw * 0.55, y + 15), fill=cloud)
    for index in range(4):
        x = int(W * (0.12 + index * 0.19 + offset * 0.3))
        y = int(H * (0.53 + (index % 2) * 0.035))
        draw.ellipse((x, y, x + 6, y + 6), fill=mix(sky, (255, 255, 255), 0.58))
    return image, draw, sky, ground, sun, dark, lower


def draw_nature(d, ground, dark, seed):
    d.polygon([(0, H*.72), (W*.18, H*.55), (W*.39, H*.72), (W*.67, H*.49), (W, H*.72), (W, H), (0, H)], fill=mix(ground, dark, .05))
    d.polygon([(0, H*.81), (W*.23, H*.67), (W*.48, H*.79), (W*.77, H*.61), (W, H*.78), (W, H), (0, H)], fill=mix(ground, dark, .34))
    d.rectangle((0, H*.84, W, H), fill=mix(ground, dark, .48))
    trees = [(62, .76, 54), (150, .72, 42), (455, .75, 68), (555, .78, 48)]
    for i, (x, y, r) in enumerate(trees):
        y0 = int(H*y)
        d.rounded_rectangle((x-7, y0+18, x+7, H*.98), radius=7, fill=(103, 82, 58))
        leaf = mix(ground, (220, 226, 155), .32 + .05*((seed+i)%3))
        for dx, dy, factor in [(-.52, -.25, .55), (0, -.55, .6), (.5, -.25, .57), (0, -.05, .48)]:
            cx, cy = x+int(dx*r), y0+int(dy*r)
            d.ellipse((cx-r*factor, cy-r*factor, cx+r*factor, cy+r*factor), fill=leaf)
    for i in range(8):
        x = 25 + ((seed*37+i*73) % (W-50))
        y = int(H*(.87 + (i%3)*.018))
        d.ellipse((x-5,y-5,x+5,y+5),fill=(241,220,150))


def draw_water(d, ground, dark, sun, seed):
    horizon = H*.67
    d.rectangle((0, horizon, W, H), fill=(77, 145, 159))
    for i in range(6):
        y = int(H*(.72+i*.047))
        x = (seed*19+i*61) % 120
        d.arc((x, y-24, W-x*.3, y+40), 5, 175, fill=mix((77,145,159),(208,232,221),.45), width=5)
    d.polygon([(0,H*.68),(W*.18,H*.59),(W*.34,H*.69),(W*.54,H*.57),(W*.77,H*.68),(W,H*.60),(W,H*.72),(0,H*.75)],fill=mix(ground,dark,.35))
    x=int(W*(.69 + (seed%5)*.025)); y=int(H*.78)
    d.polygon([(x-55,y+45),(x+61,y+45),(x+34,y+80),(x-29,y+80)], fill=(243,226,193))
    d.polygon([(x-4,y-62),(x-4,y+44),(x-46,y+44)], fill=(246,238,213))
    d.line((x,y-59,x,y+48),fill=(83,101,100),width=6)


def draw_travel(d, ground, dark, seed):
    d.polygon([(0,H*.72),(W*.19,H*.55),(W*.39,H*.71),(W*.61,H*.48),(W*.83,H*.72),(W,H*.56),(W,H),(0,H)],fill=mix(ground,dark,.04))
    d.polygon([(W*.15,H*.58),(W*.19,H*.55),(W*.31,H*.68),(W*.39,H*.71),(W*.61,H*.48),(W*.68,H*.59),(W*.61,H*.55),(W*.61,H*.48),(W*.51,H*.62),(W*.38,H*.61),(W*.27,H*.57)],fill=(239,235,215))
    d.polygon([(0,H*.78),(W*.5,H*.70),(W,H*.78),(W,H),(0,H)],fill=mix(ground,dark,.37))
    path=[(W*.58,H),(W*.49,H*.91),(W*.56,H*.83),(W*.43,H*.73),(W*.50,H*.69)]
    d.line(path,fill=(244,223,176),width=34,joint="curve")
    d.line(path,fill=(254,243,214),width=5,joint="curve")
    for x in [72, W-75]:
        d.ellipse((x-18,H*.8-18,x+18,H*.8+18),fill=(244,211,141))


def draw_history(d, ground, dark, sun, seed):
    stone=(237,222,195)
    x0=W*(.16+(seed%3)*.025); x1=W-x0
    d.rectangle((x0,H*.59,x1,H*.84),fill=stone)
    d.polygon([(x0-30,H*.6),(W*.5,H*.47),(x1+30,H*.6)],fill=mix(stone,ground,.22))
    for x in [W*.25,W*.42,W*.58,W*.75]:
        d.rounded_rectangle((x-19,H*.62,x+19,H*.82),radius=18,fill=(184,158,128))
    d.rectangle((x0-22,H*.82,x1+22,H*.86),fill=(215,195,163))
    d.ellipse((W*.43,H*.75,W*.57,H*.89),fill=(247,207,137))
    d.rounded_rectangle((W*.48,H*.79,W*.52,H*.94),radius=8,fill=(255,247,219))
    d.ellipse((W*.483,H*.74,W*.517,H*.82),fill=(237,148,74))


def draw_people(d, ground, dark, seed):
    d.polygon([(0,H*.73),(W*.22,H*.64),(W*.44,H*.74),(W*.66,H*.59),(W,H*.72),(W,H),(0,H)],fill=mix(ground,dark,.12))
    people=[(W*.34,H*.72,(251,224,190)),(W*.51,H*.67,(244,190,132)),(W*.67,H*.73,(239,215,196))]
    if seed%2:
        people=people[1:]+people[:1]
    for x,y,c in people:
        r=31+(seed%3)*3
        d.ellipse((x-r,y-r,x+r,y+r),fill=c)
        d.rounded_rectangle((x-42,y+28,x+42,y+190),radius=30,fill=c)
    d.arc((W*.23,H*.77,W*.77,H*.97),180,360,fill=(255,241,215),width=6)


def draw_peace(d, ground, dark, seed):
    d.polygon([(0,H*.78),(W*.27,H*.69),(W*.48,H*.78),(W*.76,H*.65),(W,H*.77),(W,H),(0,H)],fill=mix(ground,dark,.22))
    d.line((W*.17,H*.94,W*.65,H*.69),fill=(77,116,79),width=13)
    for i in range(6):
        x=W*(.23+i*.064); y=H*(.91-i*.032)
        side=-1 if i%2 else 1
        leaf_x=x+side*42
        d.ellipse((min(x,leaf_x),y-24,max(x,leaf_x),y+8),fill=(156,186,137))
    for i in range(3):
        x=W*(.62+i*.09); y=H*(.59+(i%2)*.045)
        d.ellipse((x-12,y-6,x+12,y+7),fill=(250,246,226))
        d.polygon([(x,y),(x-29,y-20),(x-14,y+2)],fill=(250,246,226))
        d.polygon([(x,y),(x+25,y-17),(x+13,y+3)],fill=(250,246,226))


def draw_science(d, ground, dark, sun, seed):
    cx,cy=W*.5,H*.72
    for angle in [0,60,120]:
        box=(cx-112,cy-54,cx+112,cy+54)
        d.ellipse(box,outline=(245,244,225),width=5)
        # Rotate the orbital ellipse around the central atom.
        d.arc((cx-128,cy-72,cx+128,cy+72),angle,angle+250,fill=(246,235,201),width=4)
    d.ellipse((cx-28,cy-28,cx+28,cy+28),fill=(248,204,120))
    for i in range(3):
        x=cx+int(math.cos(seed+i*2.1)*118); y=cy+int(math.sin(seed+i*2.1)*52)
        d.ellipse((x-10,y-10,x+10,y+10),fill=(218,237,230))


def draw_space(d, ground, dark, sun, seed):
    for i in range(18):
        x=(seed*31+i*97)%W; y=int(H*(.48+((i*19+seed)%38)/100))
        r=2+(i%3)
        d.ellipse((x-r,y-r,x+r,y+r),fill=(251,242,211))
    cx,cy=W*(.53+(seed%3)*.035),H*.74; r=105+(seed%4)*8
    d.ellipse((cx-r,cy-r,cx+r,cy+r),fill=(207,154,130))
    d.arc((cx-r*1.45,cy-r*.38,cx+r*1.45,cy+r*.38),5,175,fill=(245,225,186),width=13)
    d.ellipse((cx-r*1.45,cy-r*.38,cx+r*1.45,cy+r*.38),outline=(245,225,186),width=7)


def draw_culture(d, ground, dark, seed):
    cx=W*.5; y=H*.72
    d.polygon([(cx,y-76),(cx-145,y-116),(cx-136,y+109),(cx-8,y+144),(cx,y+130)],fill=(248,233,201))
    d.polygon([(cx,y-76),(cx+145,y-116),(cx+136,y+109),(cx+8,y+144),(cx,y+130)],fill=(242,220,179))
    d.line((cx,y-73,cx,y+131),fill=(160,123,84),width=7)
    for side in [-1,1]:
        for i in range(3):
            yy=y-27+i*43
            d.line((cx+side*35,yy,cx+side*(96-i*5),yy+4),fill=(199,170,128),width=5)
    if seed%2:
        d.ellipse((W*.73,H*.57,W*.81,H*.65),outline=(124,95,70),width=5)
        d.line((W*.8,H*.63,W*.84,H*.75),fill=(124,95,70),width=5)


def draw_food(d, ground, dark, sun, seed):
    cx=W*.5; cy=H*.78
    d.ellipse((cx-166,cy-83,cx+166,cy+86),fill=(249,239,215))
    d.ellipse((cx-130,cy-58,cx+130,cy+56),fill=(217,228,193))
    for i in range(6):
        x=cx-84+(i%3)*79; y=cy-28+(i//3)*55
        color=[(218,138,100),(232,185,94),(122,159,107),(216,170,115),(201,115,98),(123,155,132)][i]
        d.ellipse((x-26,y-23,x+26,y+23),fill=color)
    d.arc((cx-168,cy-73,cx+168,cy+107),0,180,fill=(166,132,96),width=5)


def draw_health(d, ground, dark, seed):
    cx,cy=W*.5,H*.73
    pts=[(cx,cy+117),(cx-126,cy+4),(cx-147,cy-47),(cx-124,cy-101),(cx-69,cy-106),(cx,cy-48),(cx+70,cy-107),(cx+127,cy-93),(cx+151,cy-35),(cx+122,cy+16),(cx,cy+117)]
    d.polygon(pts,fill=(226,135,121))
    d.line([(W*.23,cy+14),(W*.38,cy+14),(W*.44,cy-20),(W*.51,cy+55),(W*.59,cy-8),(W*.66,cy+14),(W*.78,cy+14)],fill=(255,241,220),width=8,joint="curve")


def draw_technology(d, ground, dark, sun, seed):
    cx,cy=W*.5,H*.73
    d.ellipse((cx-96,cy-96,cx+96,cy+96),fill=(211,226,218),outline=(71,115,123),width=11)
    for i in range(12):
        angle=math.pi*2*i/12
        x1=cx+math.cos(angle)*93; y1=cy+math.sin(angle)*93
        x2=cx+math.cos(angle)*126; y2=cy+math.sin(angle)*126
        d.line((x1,y1,x2,y2),fill=(71,115,123),width=20)
    d.ellipse((cx-38,cy-38,cx+38,cy+38),fill=(245,196,120))
    for x,y in [(W*.25,H*.59),(W*.75,H*.9),(W*.77,H*.58)]:
        d.ellipse((x-12,y-12,x+12,y+12),fill=(249,241,215))


def draw_work(d, ground, dark, sun, seed):
    desk_y=H*.84
    d.polygon([(W*.1,desk_y),(W*.9,desk_y),(W*.78,H*.95),(W*.22,H*.95)],fill=(104,84,69))
    d.rounded_rectangle((W*.3,H*.62,W*.7,H*.82),radius=14,fill=(249,238,210))
    d.line((W*.37,H*.68,W*.63,H*.68),fill=(178,149,109),width=5)
    d.line((W*.37,H*.73,W*.59,H*.73),fill=(178,149,109),width=5)
    d.line((W*.37,H*.78,W*.55,H*.78),fill=(178,149,109),width=5)
    d.line((W*.74,H*.63,W*.62,H*.88),fill=(218,170,103),width=12)
    d.ellipse((W*.71,H*.59,W*.77,H*.66),fill=(248,208,128))


def draw_sports(d, ground, dark, sun, seed):
    d.rectangle((0,H*.71,W,H),fill=(81,139,102))
    d.ellipse((W*.12,H*.63,W*.88,H*.96),outline=(242,230,196),width=8)
    d.ellipse((W*.24,H*.69,W*.76,H*.90),outline=(242,230,196),width=5)
    cx=W*(.49+(seed%3)*.01); cy=H*.79; r=66
    d.ellipse((cx-r,cy-r,cx+r,cy+r),fill=(244,236,215),outline=(88,107,83),width=5)
    d.polygon([(cx,cy-r*.48),(cx+r*.46,cy-r*.16),(cx+r*.28,cy+r*.38),(cx-r*.28,cy+r*.38),(cx-r*.46,cy-r*.16)],fill=(83,112,91))
    for angle in [0,72,144,216,288]:
        ex=cx+math.cos(math.radians(angle))*r*.84; ey=cy+math.sin(math.radians(angle))*r*.84
        d.line((cx,cy,ex,ey),fill=(107,130,101),width=3)


def draw_sports(d, ground, dark, sun, seed):
    d.rectangle((0,H*.71,W,H),fill=(81,139,102))
    d.ellipse((W*.12,H*.63,W*.88,H*.96),outline=(242,230,196),width=8)
    d.ellipse((W*.24,H*.69,W*.76,H*.90),outline=(242,230,196),width=5)
    cx=W*(.49+(seed%3)*.01); cy=H*.79; r=66
    d.ellipse((cx-r,cy-r,cx+r,cy+r),fill=(244,236,215),outline=(88,107,83),width=5)
    d.polygon([(cx,cy-r*.48),(cx+r*.46,cy-r*.16),(cx+r*.28,cy+r*.38),(cx-r*.28,cy+r*.38),(cx-r*.46,cy-r*.16)],fill=(83,112,91))
    for angle in [0,72,144,216,288]:
        ex=cx+math.cos(math.radians(angle))*r*.84; ey=cy+math.sin(math.radians(angle))*r*.84
        d.line((cx,cy,ex,ey),fill=(107,130,101),width=3)


def draw_seasonal(d, date: str, ground, dark, sun, seed):
    month=int(date.split("-")[0])
    if month in (12,1,2):
        draw_nature(d, ground, dark, seed)
        snow=(247,246,235)
        for i in range(18):
            x=(i*71+seed*17)%W; y=int(H*(.61+((i*17)%36)/100))
            r=3+(i%3)
            d.ellipse((x-r,y-r,x+r,y+r),fill=snow)
    elif month in (3,4,5):
        draw_nature(d, ground, dark, seed)
        petals=(239,177,177)
        for i in range(13):
            x=(i*53+seed*19)%W; y=int(H*(.65+((i*23)%32)/100)); r=7+(i%4)
            d.ellipse((x-r,y-r,x+r,y+r),fill=petals)
    elif month in (6,7,8):
        draw_water(d, ground, dark, sun, seed)
        d.arc((W*.14,H*.77,W*.85,H*.97),180,355,fill=(255,230,171),width=4)
    else:
        draw_nature(d, ground, dark, seed)
        leaf=(211,145,94)
        for i in range(11):
            x=(i*59+seed*13)%W; y=int(H*(.65+((i*17)%33)/100))
            d.ellipse((x-11,y-6,x+11,y+6),fill=leaf)


DRAWERS = {
    "nature": lambda d, date, g, k, s, seed: draw_nature(d,g,k,seed),
    "water": lambda d, date, g, k, s, seed: draw_water(d,g,k,s,seed),
    "travel": lambda d, date, g, k, s, seed: draw_travel(d,g,k,seed),
    "history": lambda d, date, g, k, s, seed: draw_history(d,g,k,s,seed),
    "people": lambda d, date, g, k, s, seed: draw_people(d,g,k,seed),
    "peace": lambda d, date, g, k, s, seed: draw_peace(d,g,k,seed),
    "sports": lambda d, date, g, k, s, seed: draw_sports(d,g,k,s,seed),
    "sports": lambda d, date, g, k, s, seed: draw_sports(d,g,k,s,seed),
    "science": lambda d, date, g, k, s, seed: draw_science(d,g,k,s,seed),
    "space": lambda d, date, g, k, s, seed: draw_space(d,g,k,s,seed),
    "culture": lambda d, date, g, k, s, seed: draw_culture(d,g,k,seed),
    "food": lambda d, date, g, k, s, seed: draw_food(d,g,k,s,seed),
    "health": lambda d, date, g, k, s, seed: draw_health(d,g,k,seed),
    "technology": lambda d, date, g, k, s, seed: draw_technology(d,g,k,s,seed),
    "work": lambda d, date, g, k, s, seed: draw_work(d,g,k,s,seed),
    "seasonal": lambda d, date, g, k, s, seed: draw_seasonal(d,date,g,k,s,seed),
}


def render_wallpaper(date: str, theme: str, output: Path) -> None:
    seed=sum((index+1)*ord(character) for index,character in enumerate(date))
    theme=theme if theme in PALETTES else DEFAULT_THEME
    image, draw, sky, ground, sun, dark, _lower=base_scene(theme,seed)
    DRAWERS[theme](draw,date,ground,dark,sun,seed)
    image.save(output,"JPEG",quality=84,optimize=True,progressive=True,subsampling=1)


def render_icon(size: int, output: Path, maskable: bool=False) -> None:
    scale=size/512
    image=Image.new("RGBA",(size,size),(43,91,77,255))
    d=ImageDraw.Draw(image)
    pad=int((58 if maskable else 44)*scale)
    x0,y0=size*0.24,size*0.19
    x1,y1=size*0.76,size*0.81
    d.rounded_rectangle((x0,y0,x1,y1),radius=int(34*scale),fill=(249,242,221,255))
    d.rounded_rectangle((x0,y0,x1,y0+size*.19),radius=int(34*scale),fill=(80,132,111,255))
    d.rectangle((x0,y0+size*.12,x1,y0+size*.19),fill=(80,132,111,255))
    for x in [size*.39,size*.61]:
        d.rounded_rectangle((x-size*.025,y0-size*.025,x+size*.025,y0+size*.10),radius=int(9*scale),fill=(250,218,151,255))
    d.ellipse((size*.39,size*.43,size*.61,size*.65),fill=(239,183,105,255))
    d.polygon([(size*.28,size*.68),(size*.45,size*.55),(size*.57,size*.69),(size*.69,size*.59),(size*.73,size*.74),(size*.28,size*.74)],fill=(109,157,124,255))
    d.line((size*.5,size*.68,size*.5,size*.76),fill=(75,119,91,255),width=max(2,int(6*scale)))
    output.parent.mkdir(parents=True,exist_ok=True)
    image.resize((size,size),Image.Resampling.LANCZOS).save(output,"PNG",optimize=True)


def main() -> None:
    data=json.loads(DATA.read_text(encoding="utf-8"))
    entries=data["entries"]+[data["leap_day"]]
    ILLUSTRATIONS.mkdir(parents=True,exist_ok=True)
    for item in entries:
        render_wallpaper(item["date"],item["visual"],ILLUSTRATIONS/(item["date"]+".jpg"))
    mipmap_sizes={"mipmap-mdpi":48,"mipmap-hdpi":72,"mipmap-xhdpi":96,"mipmap-xxhdpi":144,"mipmap-xxxhdpi":192}
    for folder,size in mipmap_sizes.items():
        render_icon(size,ROOT/"android"/"app"/"src"/"main"/"res"/folder/"ic_launcher.png")
    render_icon(192,ROOT/"web"/"icons"/"Icon-192.png")
    render_icon(512,ROOT/"web"/"icons"/"Icon-512.png")
    render_icon(192,ROOT/"web"/"icons"/"Icon-maskable-192.png",True)
    render_icon(512,ROOT/"web"/"icons"/"Icon-maskable-512.png",True)
    render_icon(32,ROOT/"web"/"favicon.png")
    print(f"Generated {len(entries)} topic-matched illustrations and the app icons.")


if __name__ == "__main__":
    main()
