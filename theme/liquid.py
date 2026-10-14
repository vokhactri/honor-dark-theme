"""Liquid Glass: Honor's apps keep the icons of the Liquid Glass theme, every other app gets its Dark Flat glyph on
that theme's see-through glass plate.

Liquid Glass uses the older flat icon format: one 218px `<package>.png` per app with the plate baked in, the plate
(icon_background.png) and rim (icon_border.png) filling the middle 196px, like the squircle of icon_mask.png in Glory.
"""

from functools import cache

from PIL import Image

from .paths import BUILD, DATA
from .unify import VIEW, flat

ICONS = DATA / 'liquid/icons'  # Liquid Glass's Honor app icons and launcher assets
SIZE = 218
M = (SIZE - VIEW) // 2  # the plate's margin in the canvas
HONOR = {f.stem for f in ICONS.glob('*.png') if f.stem.startswith(('com.', 'cn.', 'vn.'))}


@cache
def glass(p: str) -> Image.Image:
    """The full 218px icon of p: Liquid Glass's own for Honor apps, else the Dark Flat glyph on the glass plate."""
    if p in HONOR:
        return Image.open(ICONS / f'{p}.png').convert('RGBA')
    icon = Image.open(ICONS / 'icon_background.png').convert('RGBA')
    own = BUILD / f'out/glass/{p}.png'
    glyph = Image.open(own if own.exists() else BUILD / f'out/flat/{p}.png').convert('RGBA')
    glyph = glyph.resize((VIEW, VIEW), Image.LANCZOS)
    icon.alpha_composite(glyph, (M, M))
    icon.alpha_composite(Image.open(ICONS / 'icon_border.png').convert('RGBA'))
    return icon


def drawn(variant: str, p: str) -> Image.Image:
    """p's icon as the launcher shows it, without the canvas margin, for previews and mockups."""
    if variant == 'liquid':
        return glass(p).crop((M, M, M + VIEW, M + VIEW))
    return flat(Image.open(BUILD / f'out/{variant}/{p}.png'))
