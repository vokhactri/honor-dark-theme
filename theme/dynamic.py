"""Dynamic clock, calendar and weather icons for Dark Flat, laid out like Liquid Glass's dynamic_icons/<package>/.

Every file is a 218px canvas with the icon in the middle 196px. The launcher draws the clock face, then the hour,
minute and second hands, each pointing at 12 and turned about the canvas center; the calendar plate with the weekday
and date set in the colors of the com.hihonor.android.launcher module; and one icon per weather condition.
"""

import zipfile
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage as ndi

from . import liquid
from .paths import DATA
from .unify import MASK, PLATE, VIEW, Arr, adaptive_layer, invert_grays, over

SIZE = liquid.SIZE
M = (SIZE - VIEW) // 2
C = 256  # center of the 512px layer
_yy, _xx = np.mgrid[0:512, 0:512]
R = np.hypot(_xx - C, _yy - C)
# the launcher draws the date in calendar_dynamic_date and the weekday in calendar_dynamic (Glory: #353535, #FA532A)
LAUNCHER = """<?xml version="1.0" encoding="utf-8"?>
<resources>
<color name="calendar_dynamic_date">#F2F2F2</color>
<color name="calendar_dynamic">#FA532A</color>
</resources>
"""


def canvas(layer: Arr) -> Image.Image:
    """A 512px layer (the part the launcher shows) on the 218px canvas."""
    out = Image.new('RGBA', (SIZE, SIZE))
    im = Image.fromarray(np.clip(np.round(layer), 0, 255).astype(np.uint8))
    out.alpha_composite(im.resize((VIEW, VIEW), Image.Resampling.LANCZOS), (M, M))
    return out


def on_plate(fg: Arr) -> Image.Image:
    """fg over the shared plate, clipped to the squircle."""
    out = PLATE.copy()
    over(out, fg)
    out[..., 3] = MASK * 255
    return canvas(out)


def masked(fg: Arr, m: np.ndarray) -> Arr:
    out = fg.copy()
    out[..., 3] *= m
    return out


def turned(fg: Arr, angle: float) -> Arr:
    """fg turned counterclockwise by angle degrees about the center."""
    return np.asarray(
        Image.fromarray(fg.astype(np.uint8)).rotate(angle, Image.Resampling.BICUBIC, center=(C, C))
    ).astype(float)


def clock() -> dict[str, Image.Image]:
    """Glory's clock split into its face and hands, with the grays made light as in the Dark Flat icon.

    Glory shows 10:09:30, so the second hand covers the 6; the 6 is redrawn as the 9 turned upside down.
    """
    fg = invert_grays(adaptive_layer(DATA / 'glory/com.hihonor.deskclock.png'))
    a = fg[..., 3]
    second = ((fg[..., 2] - fg[..., 0] > 25) & (a > 10)) | (R <= 12)  # blue hand, its ring and the dot inside
    lab, n = ndi.label((a > 30) & ~ndi.binary_dilation(second, iterations=2))
    parts = [lab == i for i in range(1, n + 1)]
    hands = sorted((m for m in parts if R[m].min() < 20 and m.sum() > 500), key=lambda m: R[m].max())
    out = {}
    face = fg.copy()
    # the ticks and numbers start 143px out; inside that only the hands and their soft shadows are drawn
    face[..., 3] *= ~ndi.binary_dilation(second | np.any(hands, 0), iterations=2) & (R > 140)
    face[396:472, 228:284, 3] = 0
    face[398:470, 232:280] = fg[221:293, 44:92][::-1, ::-1]  # the 9's box, turned 180 into the 6's place
    out['ic_deskclock_dial'] = on_plate(face)
    for name, m in zip(('hour', 'minute'), hands, strict=True):
        far = m & (R > 40)
        angle = np.degrees(np.arctan2((_xx - C)[far].mean(), (C - _yy)[far].mean()))
        out[f'ic_deskclock_{name}'] = canvas(turned(masked(fg, ndi.binary_dilation(m, iterations=2)), angle))
    out['ic_deskclock_second'] = canvas(turned(masked(fg, second), 180))
    return out


def weather() -> dict[str, Image.Image]:
    """Liquid Glass's weather icons, lifted off its glass plate onto the shared plate."""
    plate = np.asarray(Image.open(liquid.ICONS / 'icon_background.png').convert('RGBA')).astype(float) / 255
    pa, pc = plate[..., 3:4], plate[..., :3]
    out = {}
    for f in sorted((liquid.ICONS / 'dynamic_icons/com.hihonor.android.totemweather').glob('*.png')):
        im = np.asarray(Image.open(f).convert('RGBA')).astype(float) / 255
        ia, ic = im[..., 3:4], im[..., :3]
        # undo `glyph over plate`: ia = ga + pa (1 - ga), ic ia = gc ga + pc pa (1 - ga)
        ga = np.clip((ia - pa) / np.maximum(1 - pa, 1e-6), 0, 1)
        ga[ga < 0.02] = 0
        gc = np.clip((ic * ia - pc * pa * (1 - ga)) / np.maximum(ga, 1e-6), 0, 1)
        glyph = np.concatenate([gc, ga], -1)[M : M + VIEW, M : M + VIEW] * 255
        big = np.asarray(Image.fromarray(np.round(glyph).astype(np.uint8)).resize((512, 512), Image.Resampling.LANCZOS))
        out[f.stem] = on_plate(big.astype(float))
    return out


def build(icons: Path, outer: Path) -> None:
    """Write dynamic_icons/ into the icons dir and the launcher module with the calendar colors into outer."""
    sets = {
        'com.hihonor.deskclock': clock(),
        'com.android.calendar': {'calendar_background': on_plate(np.zeros((512, 512, 4)))},
        'com.hihonor.android.totemweather': weather(),
    }
    for pkg, files in sets.items():
        d = icons / 'dynamic_icons' / pkg
        d.mkdir(parents=True)
        for name, im in files.items():
            im.save(d / f'{name}.png')
    with zipfile.ZipFile(outer / 'com.hihonor.android.launcher', 'w', zipfile.ZIP_DEFLATED) as zf:
        zf.writestr('theme.xml', LAUNCHER)
