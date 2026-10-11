"""Cover and preview images shown in the Themes app."""

from collections.abc import Callable
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from .paths import APPS, BUILD, DATA

type IconFn = Callable[[str, int], Image.Image]

W, H = 1256, 2808
DATE = 'Friday, October 10'
SHOWCASE = [
    'com.zing.zalo',
    'com.facebook.katana',
    'com.facebook.orca',
    'com.instagram.android',
    'com.google.android.apps.maps',
    'com.google.android.apps.photos',
    'com.shopee.vn',
    'com.lazada.android',
    'com.grabtaxi.passenger',
    'com.mservice.momotransfer',
    'com.ss.android.ugc.trill',
    'com.openai.chatgpt',
    'com.google.android.apps.bard',
    'com.discord',
    'com.twitter.android',
    'com.reddit.frontpage',
    'com.hihonor.camera',
    'com.hihonor.calendar',
    'com.hihonor.deskclock',
    'com.hihonor.photos',
    'com.github.android',
    'com.brave.browser',
    'org.mozilla.firefox',
    'com.google.android.apps.docs',
]
DOCK = ['com.hihonor.contacts', 'com.google.android.apps.messaging', 'org.mozilla.firefox', 'com.hihonor.camera']
HERO = [
    'com.google.android.apps.maps',
    'com.zing.zalo',
    'com.instagram.android',
    'com.hihonor.camera',
    'com.shopee.vn',
    'com.google.android.apps.photos',
    'com.openai.chatgpt',
]
HERO_SIZES = [150, 170, 195, 230, 195, 170, 150]


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    """Inter, with Inter Display for big bold titles and clocks (tighter spacing at large sizes)."""
    name = 'InterDisplay-Bold' if bold and size >= 100 else 'Inter-Bold' if bold else 'Inter-Regular'
    # Pillow uses Raqm only where libfribidi is installed, which moves text; pin the basic layout so every machine
    # renders the same previews
    return ImageFont.truetype(DATA / f'inter/{name}.ttf', size, layout_engine=ImageFont.Layout.BASIC)


def bg(w: int, h: int, glow: tuple[int, int, int] = (60, 70, 110)) -> Image.Image:
    y = np.linspace(0, 1, h)[:, None]
    base = np.array([22, 22, 26.0]) * (1 - y) + np.array([6, 6, 8.0]) * y
    img = np.broadcast_to(base[:, None, :], (h, w, 3)).copy()
    yy, xx = np.mgrid[0:h, 0:w]
    for cx, cy, r, col in [(0.85, 0.12, 0.55, glow), (0.1, 0.8, 0.5, (90, 50, 70))]:
        d = np.sqrt(((xx / w - cx) * w / h) ** 2 + (yy / h - cy) ** 2) / r
        img += np.clip(1 - d, 0, 1)[..., None] ** 2 * np.array(col) * 0.35
    return Image.fromarray(np.clip(img, 0, 255).astype(np.uint8)).convert('RGBA')


def screen(glow: tuple[int, int, int] = (60, 70, 110)) -> tuple[Image.Image, ImageDraw.ImageDraw]:
    """A phone-sized background with the status bar drawn on it."""
    img = bg(W, H, glow)
    d = ImageDraw.Draw(img)
    d.text((60, 40), '09:41', fill='white', font=font(44, True))
    d.rounded_rectangle((W - 150, 48, W - 70, 84), 10, outline='white', width=3)
    d.rectangle((W - 144, 54, W - 92, 78), fill='white')
    return img, d


def grid(img: Image.Image, icon: IconFn, pkgs: list[str], top: int, size=200, gapy=330, label=True) -> None:
    d = ImageDraw.Draw(img)
    cw = W / 4
    f = font(36)
    for i, p in enumerate(pkgs):
        r, c = divmod(i, 4)
        x = int(c * cw + (cw - size) / 2)
        y = top + r * gapy
        img.alpha_composite(icon(p, size), (x, y))
        if label:
            t = APPS[p]
            tw = d.textlength(t, font=f)
            while tw > cw - 16:
                t = t[:-1]
                tw = d.textlength(t + '…', font=f)
            t = t if t == APPS[p] else t + '…'
            d.text((x + size / 2 - tw / 2, y + size + 18), t, fill=(230, 230, 232), font=f)


def dock(img: Image.Image, icon: IconFn) -> None:
    layer = Image.new('RGBA', img.size)
    ImageDraw.Draw(layer).rounded_rectangle((40, H - 330, W - 40, H - 90), 70, fill=(255, 255, 255, 28))
    img.alpha_composite(layer)
    cw = (W - 80) / 4
    for i, p in enumerate(DOCK):
        img.alpha_composite(icon(p, 190), (int(40 + i * cw + (cw - 190) / 2), H - 305))


def render(variant: str, title: str, outdir: Path) -> None:
    """Write cover, banner and preview images for one variant into `outdir`."""

    def icon(p: str, s: int) -> Image.Image:
        return Image.open(BUILD / f'out/{variant}/{p}.png').resize((s, s), Image.LANCZOS)

    def save(img: Image.Image, name: str) -> None:
        img.convert('RGB').save(outdir / name, quality=90)

    rest = [p for p in sorted(APPS, key=lambda p: APPS[p].lower()) if p not in SHOWCASE]
    allp = SHOWCASE + rest

    # cover: the theme list shows a centre crop (~0.56 aspect, ~285px lost top and bottom), so keep everything inside it
    img, d = screen()
    d.text((W / 2, 480), title, fill='white', font=font(130, True), anchor='mm')
    d.text((W / 2, 590), 'Icon pack  ·  by trivk', fill=(170, 170, 178), font=font(48), anchor='mm')
    d.line((W / 2 - 160, 660, W / 2 + 160, 660), fill=(90, 90, 100), width=3)
    grid(img, icon, SHOWCASE, 750, size=205, gapy=290, label=False)
    save(img, 'cover.jpg')

    # banner: title + a row of icons with reflections
    bw, bh = 1448, 1086
    img = bg(bw, bh)
    d = ImageDraw.Draw(img)
    d.text((bw / 2, 250), title, fill='white', font=font(150, True), anchor='mm')
    d.text((bw / 2, 380), 'Icon pack  ·  by trivk', fill=(170, 170, 178), font=font(52), anchor='mm')
    x = (bw - sum(HERO_SIZES) - 30 * 6) / 2
    for p, s in zip(HERO, HERO_SIZES, strict=True):
        y = 700 - s // 2
        ic = icon(p, s)
        img.alpha_composite(ic, (int(x), y))
        a = np.asarray(ic.transpose(Image.FLIP_TOP_BOTTOM)).astype(float)
        a[..., 3] *= np.linspace(0.35, 0, s)[:, None]
        img.alpha_composite(Image.fromarray(a.astype(np.uint8)), (int(x), y + s + 10))
        x += s + 30
    save(img, 'icon_small.jpg')

    # home screen
    img, d = screen()
    d.text((80, 260), '09:41', fill='white', font=font(220, True))
    d.text((90, 520), DATE, fill=(210, 210, 215), font=font(54))
    grid(img, icon, allp[:16], 820)
    dock(img, icon)
    save(img, 'preview_home_0.jpg')

    # icon grid pages
    names = ['preview_icons_0.jpg', 'preview_icons_1.jpg', 'preview_settings_0.jpg', 'preview_settings_1.jpg']
    for i, name in enumerate(names):
        img, _ = screen()
        grid(img, icon, allp[16 + 28 * i : 16 + 28 * (i + 1)], 260, gapy=345)
        save(img, name)

    # lock screen
    img, d = screen(glow=(80, 60, 120))
    d.text((W / 2, 330), DATE, fill=(220, 220, 225), font=font(56), anchor='mm')
    d.text((W / 2, 620), '09:41', fill='white', font=font(330, True), anchor='mm')
    for i, p in enumerate(['com.hihonor.deskclock', 'com.hihonor.calendar']):
        img.alpha_composite(icon(p, 120), (W // 2 - 150 + i * 180, 900))
    d.text((W / 2, H - 200), title + '  ·  trivk', fill=(150, 150, 158), font=font(40), anchor='mm')
    save(img, 'preview_unlock_0.jpg')
