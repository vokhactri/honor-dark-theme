"""Labelled icon sheet for reviewing a variant."""

from PIL import Image, ImageDraw

from .paths import APPS, BUILD
from .previews import font
from .unify import flat

COLS, CELL = 12, 150


def render(variant: str, title: str) -> None:
    pkgs = sorted(APPS, key=lambda p: APPS[p].lower())
    label = font(15)
    rows = (len(pkgs) + COLS - 1) // COLS
    s = Image.new('RGB', (COLS * CELL + 40, rows * (CELL + 26) + 80), (14, 14, 16))
    d = ImageDraw.Draw(s)
    d.text((24, 20), title, fill='white', font=font(26, bold=True))
    for i, p in enumerate(pkgs):
        x = 20 + (i % COLS) * CELL + 12
        y = 70 + (i // COLS) * (CELL + 26)
        im = flat(Image.open(BUILD / f'out/{variant}/{p}.png')).resize((126, 126), Image.LANCZOS)
        s.paste(im, (x, y), im)
        w = d.textlength(APPS[p], font=label)
        d.text((x + 63 - w / 2, y + 130), APPS[p], fill=(215, 215, 215), font=label)
    s.save(BUILD / f'mockup-{variant}.png')
