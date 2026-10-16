"""Wallpapers, cover and preview images shown in the Themes app.

Sizes and layouts follow Honor's built-in Glory theme (preview_icons_0, preview_unlock_0, icon_small, icon_small_1)
and the store icon pack Colorful Transparency (preview_icons_1, the home screen).
"""

from collections.abc import Callable
from functools import cache
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from . import liquid
from .liquid import drawn
from .paths import APPS, DATA

type IconFn = Callable[[str, int], Image.Image]

W, H = 1280, 2800  # preview_*.jpg, as in Glory
WALL = 2800  # home_wallpaper_0.jpg is square, as in Glory
TIME, DATE = '09:41', 'Friday, October 10'
PHONE = 'com.android.contacts.activities.DialtactsActivity'
GALLERY, CAMERA, MESSAGES = 'com.hihonor.photos', 'com.hihonor.camera', 'com.google.android.apps.messaging'
# big icons, 3 x 5, no labels (Glory's preview_icons_0)
FEATURED = [
    PHONE,
    'com.zing.zalo',
    CAMERA,
    'com.google.android.apps.maps',
    'com.facebook.katana',
    GALLERY,
    'com.shopee.vn',
    'com.grabtaxi.passenger',
    'com.mservice.momotransfer',
    'com.openai.chatgpt',
    'com.google.android.apps.bard',
    'com.instagram.android',
    'com.hihonor.calendar',
    'com.hihonor.deskclock',
    'com.github.android',
]
# home screen, 4 x 5 with labels
HOME = [
    'com.facebook.orca',
    'com.google.android.apps.photos',
    'com.lazada.android',
    'com.ss.android.ugc.trill',
    'com.discord',
    'com.twitter.android',
    'com.reddit.frontpage',
    'com.brave.browser',
    'com.google.android.apps.docs',
    'com.readdle.spark',
    'app.revanced.android.youtube',
    'com.google.android.googlequicksearchbox',
    'com.hihonor.android.thememanager',
    'com.android.settings',
    'com.hihonor.filemanager',
    'com.linkedin.android',
    'com.android.vending',
    'com.x8bit.bitwarden',
    'com.exteragram.messenger',
    'com.hihonor.calculator',
]
DOCK = [PHONE, MESSAGES, 'org.mozilla.firefox', CAMERA]
SMALL = [
    PHONE,
    'com.zing.zalo',
    CAMERA,
    'com.google.android.apps.maps',
    'com.google.android.apps.photos',
    'com.openai.chatgpt',
]
SMALL_1 = [PHONE, 'com.zing.zalo', GALLERY, CAMERA]
# the Themes app reads these from preview/ (or builds them from the icons) for the theme thumbnail in Settings
THUMBNAIL = [PHONE, MESSAGES, GALLERY, CAMERA]


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    """Inter, with Inter Display for big bold titles and clocks (tighter spacing at large sizes)."""
    name = 'InterDisplay-Bold' if bold and size >= 100 else 'Inter-Bold' if bold else 'Inter-Regular'
    # Pillow uses Raqm only where libfribidi is installed, which moves text; pin the basic layout so every machine
    # renders the same previews
    return ImageFont.truetype(DATA / f'inter/{name}.ttf', size, layout_engine=ImageFont.Layout.BASIC)


@cache
def wallpaper() -> Image.Image:
    """The square home wallpaper: a dark gradient with two soft glows."""
    n = WALL
    y = np.linspace(0, 1, n, dtype=np.float32)[:, None, None]
    x = np.linspace(0, 1, n, dtype=np.float32)[None, :, None]
    img = np.array([22, 22, 26], np.float32) * (1 - y) + np.array([6, 6, 8], np.float32) * y
    for cx, cy, r, col in [(0.62, 0.22, 0.42, (60, 70, 110)), (0.38, 0.8, 0.38, (90, 50, 70))]:
        d = np.sqrt((x - cx) ** 2 + (y - cy) ** 2) / r
        img = img + np.clip(1 - d, 0, 1) ** 2 * np.array(col, np.float32) * 0.35
    # a little fixed noise keeps the jpeg from banding
    img = img + np.random.default_rng(0).normal(0, 0.6, (n, n, 1)).astype(np.float32)
    return Image.fromarray(np.clip(np.round(img), 0, 255).astype(np.uint8))


def view(w: int, h: int, wall: Image.Image | None = None) -> Image.Image:
    """The wallpaper (ours by default) as a w x h screen shows it: the center crop at that aspect, scaled."""
    wall = wall or wallpaper()
    cw, ch = min(wall.width, round(wall.height * w / h)), min(wall.height, round(wall.width * h / w))
    x, y = (wall.width - cw) // 2, (wall.height - ch) // 2
    return wall.crop((x, y, x + cw, y + ch)).resize((w, h), Image.Resampling.LANCZOS).convert('RGBA')


def status_bar(img: Image.Image) -> None:
    d = ImageDraw.Draw(img)
    w = img.width
    d.text((70, 48), TIME, fill='white', font=font(46, True))
    d.rounded_rectangle((w - 160, 56, w - 76, 94), 11, outline='white', width=3)
    d.rectangle((w - 153, 63, w - 97, 87), fill='white')
    d.rounded_rectangle((w - 72, 67, w - 66, 83), 2, fill='white')


def place(img: Image.Image, icon: IconFn, pkgs: list[str], xs: list[float], top: float, step: float, size: int):
    """Icons in rows of len(xs), centered on xs."""
    for i, p in enumerate(pkgs):
        r, c = divmod(i, len(xs))
        img.alpha_composite(icon(p, size), (round(xs[c] - size / 2), round(top + r * step)))


def labels(img: Image.Image, pkgs: list[str], xs: list[float], top: float, step: float, f: ImageFont.FreeTypeFont):
    """App names under icons laid out by place(); `top` is the first label line."""
    d = ImageDraw.Draw(img)
    room = (xs[1] - xs[0]) - 16
    for i, p in enumerate(pkgs):
        r, c = divmod(i, len(xs))
        t = APPS[p]
        if d.textlength(t, font=f) > room:
            while d.textlength(t + '…', font=f) > room:
                t = t[:-1]
            t = t.rstrip() + '…'
        d.text((xs[c], top + r * step), t, fill=(235, 235, 238), font=f, anchor='ma')


COLS4 = [W * f for f in (0.155, 0.386, 0.614, 0.845)]  # home screen columns, as in Colorful Transparency


def home(img: Image.Image, icon: IconFn, pkgs: list[str], top: float = 300, step: float = 350) -> None:
    """A 4-column home screen page with labels."""
    place(img, icon, pkgs, COLS4, top, step, 196)
    labels(img, pkgs, COLS4, top + 196 + 18, step, font(40))


def render(variant: str, outdir: Path) -> None:
    """Write the cover, preview and thumbnail images for one variant into `outdir`."""

    wall = Image.open(DATA / 'liquid/base/wallpaper/home_wallpaper_0.jpg') if variant == 'liquid' else wallpaper()
    mask = liquid.ICONS / 'icon_mask.png' if variant == 'liquid' else DATA / 'system/icon_mask.png'

    @cache
    def big(p: str) -> Image.Image:
        return drawn(variant, p)

    def icon(p: str, s: int) -> Image.Image:
        return big(p).resize((s, s), Image.Resampling.LANCZOS)

    def screen(w: int, h: int) -> Image.Image:
        return view(w, h, wall)

    def save(img: Image.Image, name: str) -> None:
        img.convert('RGB').save(outdir / name, quality=92)

    # cover: the theme card in the list; a home screen with the clock on top
    cw, ch = 1080, 1920
    img = screen(cw, ch)
    d = ImageDraw.Draw(img)
    d.text((cw / 2, 300), TIME, fill='white', font=font(190, True), anchor='mm')
    d.text((cw / 2, 430), DATE, fill=(225, 225, 230), font=font(46), anchor='mm')
    place(img, icon, FEATURED + [MESSAGES], [cw * f for f in (0.155, 0.386, 0.614, 0.845)], 620, 300, 172)
    save(img, 'cover.jpg')

    # big icons, no labels
    img = screen(W, H)
    place(img, icon, FEATURED, [310, 640, 970], 417, 437, 219)
    save(img, 'preview_icons_0.jpg')

    # home screen with search pill and dock
    img = screen(W, H)
    status_bar(img)
    home(img, icon, HOME)
    layer = Image.new('RGBA', img.size)
    ld = ImageDraw.Draw(layer)
    ld.rounded_rectangle((W / 2 - 130, 2290, W / 2 + 130, 2370), 40, fill=(255, 255, 255, 40))
    ld.rounded_rectangle((58, 2430, W - 58, 2720), 80, fill=(255, 255, 255, 34))
    img.alpha_composite(layer)
    ImageDraw.Draw(img).text((W / 2, 2330), 'Search', fill='white', font=font(40), anchor='mm')
    place(img, icon, DOCK, COLS4, 2477, 0, 196)
    save(img, 'preview_icons_1.jpg')

    # every app, alphabetically
    allp = sorted(APPS, key=lambda p: APPS[p].lower())
    per = 28
    for i in range(0, len(allp), per):
        img = screen(W, H)
        status_bar(img)
        home(img, icon, allp[i : i + per], top=230, step=360)
        save(img, f'preview_icons_{2 + i // per}.jpg')

    # lock screen
    img = screen(W, H)
    status_bar(img)
    d = ImageDraw.Draw(img)
    d.text((W / 2, 256), DATE, fill=(230, 230, 235), font=font(54), anchor='mm')
    d.text((W / 2, 420), TIME, fill='white', font=font(240, True), anchor='mm')
    save(img, 'preview_unlock_0.jpg')

    # cards in the Themes app's icon list: 3 x 2 on black, 2 x 2 on light gray
    img = Image.new('RGBA', (510, 345), 'black')
    place(img, icon, SMALL, [101.5, 254.5, 408.5], 52, 138, 103)
    save(img, 'icon_small.jpg')
    img = Image.new('RGBA', (612, 612), (213, 217, 220))
    place(img, icon, SMALL_1, [174, 439], 81, 264, 186)
    save(img, 'icon_small_1.jpg')

    # what the Themes app would otherwise build from the icons: each icon on the 218px mask canvas, and a 2 x 2 sheet
    def masked(p: str) -> Image.Image:
        c = Image.new('RGBA', (218, 218))
        c.alpha_composite(icon(p, 196), (11, 11))
        return c

    sheet = Image.new('RGBA', (654, 654))
    for i, p in enumerate(THUMBNAIL):
        r, c = divmod(i, 2)
        sheet.alpha_composite(masked(p), (72 + c * 290, 72 + r * 290))
    sheet.save(outdir / 'icon_thumbnail.png')
    for p in (PHONE, GALLERY, CAMERA):
        masked(p).save(outdir / f'{p}.png')
    Image.open(mask).save(outdir / 'icon_mask.png')


def wallpapers(outdir: Path) -> None:
    """home_wallpaper_0.jpg (square) and unlock_wallpaper_0.jpg (screen-sized), as in Glory."""
    outdir.mkdir(parents=True, exist_ok=True)
    wallpaper().save(outdir / 'home_wallpaper_0.jpg', quality=92)
    view(W, H).convert('RGB').save(outdir / 'unlock_wallpaper_0.jpg', quality=92)
