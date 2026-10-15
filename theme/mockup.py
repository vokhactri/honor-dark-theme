"""Labeled icon sheet for reviewing a variant."""

from PIL import Image, ImageDraw

from .liquid import drawn
from .paths import APPS, BUILD
from .previews import font

COLS, CELL = 12, 150


def render(variant: str, title: str) -> None:
    pkgs = sorted(APPS, key=lambda p: APPS[p].lower())
    label = font(15)
    rows = (len(pkgs) + COLS - 1) // COLS
    bg = (70, 105, 150) if variant == 'liquid' else (14, 14, 16)  # glass needs a backdrop like its wallpaper
    s = Image.new('RGB', (COLS * CELL + 40, rows * (CELL + 26) + 80), bg)
    d = ImageDraw.Draw(s)
    d.text((24, 20), title, fill='white', font=font(26, bold=True))
    for i, p in enumerate(pkgs):
        x = 20 + (i % COLS) * CELL + 12
        y = 70 + (i // COLS) * (CELL + 26)
        im = drawn(variant, p).resize((126, 126), Image.LANCZOS)
        s.paste(im, (x, y), im)
        w = d.textlength(APPS[p], font=label)
        d.text((x + 63 - w / 2, y + 130), APPS[p], fill=(215, 215, 215), font=label)
    s.save(BUILD / f'mockup-{variant}.png')
