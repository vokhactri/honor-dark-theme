"""The in-screen fingerprint icon, packed as the fingerprint_icon module (a directory, not a zip).

SystemUI (FingerprintIconUtil) loads the module's first file whose name starts with `icon` and renders an SVG at its
width x height in dp. An icon that is pure white is handled like the stock vector: SystemUI tints it and fills it with
the blurred lock screen wallpaper, so it adapts to light and dark wallpapers. Any other color is drawn as is. The
installer drops the module unless it has name.xml. The glyph is the XANA symbol from Code Lyoko
(https://codelyoko.com/XANAsymbol.svg, recolored white in data/fingerprint), as tall as the 56dp box.

fingerprint_anim is what the system server (FingerprintAnimByThemeModel, FpLayer) plays once when a finger touches the
sensor: up to 30 frames in res/light/, at <lightfps> frames per second, centered on the sensor and drawn at their pixel
size (scaled only when the screen runs below its native resolution). The installer drops the module without
res/shortcut/shortcut.png. Here the symbol turns red from the bottom up, like a tower XANA activates, with a red glow
and one pulse of the tower's aura, then fades out.
"""

import io
import xml.etree.ElementTree as ET
from functools import cache
from pathlib import Path

import numpy as np
import numpy.typing as npt
import resvg_py
from PIL import Image, ImageFilter

from .paths import BUILD, DATA

type Mask = npt.NDArray[np.float64]  # alpha 0..1

MODULES = ('fingerprint_icon', 'fingerprint_anim')
SRC = DATA / 'fingerprint/XANAsymbol.svg'
SVG = '{http://www.w3.org/2000/svg}'
BOX = 56  # dp, the size of SystemUI's ic_fingerprint
K = 10  # px per source unit when measuring the glyph
FPS, FRAMES = 30, 30  # one second; FingerprintAnimByThemeModel loads at most 30 frames
WIPE, FADE = 12, 6  # frames turning red, frames fading out at the end
ICON = 190  # px, the icon on the panel (from the sensor, so not in any resource; checked on the phone)
CANVAS = 3 * ICON  # room for the glow and the aura
WHITE, RED = np.array([255.0, 255.0, 255.0]), np.array([232.0, 16.0, 32.0])
FPTHEME = f"""<?xml version="1.0" encoding="utf-8"?>
<FPTheme>
    <resource></resource>
    <lightfps>{FPS}</lightfps>
</FPTheme>
"""
NAME = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<name>
  <values>{title}</values>
</name>
"""


def _path(e: ET.Element, transforms: tuple[str, ...] = ()) -> tuple[ET.Element, str]:
    """The source's one path, and the transforms of it and its groups, outermost first."""
    transforms += (e.get('transform', ''),)
    if e.tag == f'{SVG}path':
        return e, ' '.join(t for t in transforms if t)
    return next(_path(c, transforms) for c in e if c.tag in (f'{SVG}g', f'{SVG}path'))


@cache
def svg() -> str:
    root = ET.parse(SRC).getroot()
    path, transform = _path(root)
    # the glyph's bounds in the source's user units (it has no viewBox), rendered at K px per unit
    png = resvg_py.svg_to_bytes(svg_path=str(SRC), height=round(float(root.attrib['height']) * K))
    box = Image.open(io.BytesIO(bytes(png))).getchannel('A').getbbox()
    assert box, 'the symbol renders empty'
    x0, y0, x1, y1 = (v / K for v in box)
    side = y1 - y0
    vx, vy = (x0 + x1 - side) / 2, (y0 + y1 - side) / 2
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{BOX}" height="{BOX}" '
        f'viewBox="{vx:g} {vy:g} {side:g} {side:g}">'
        f'<path transform="{transform}" style="{path.get("style")}" d="{path.get("d")}"/></svg>\n'
    )


def ease(x: npt.ArrayLike) -> npt.NDArray[np.float64]:
    x = np.clip(x, 0, 1)
    return x * x * (3 - 2 * x)


def blur(m: Mask, r: float) -> Mask:
    im = Image.fromarray(np.round(m * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(r))
    return np.asarray(im) / 255


def frames() -> list[Image.Image]:
    png = resvg_py.svg_to_bytes(svg_string=svg(), height=ICON)
    glyph = np.zeros((CANVAS, CANVAS))
    o = (CANVAS - ICON) // 2
    glyph[o : o + ICON, o : o + ICON] = np.asarray(Image.open(io.BytesIO(bytes(png))).getchannel('A')) / 255
    near, far = blur(glyph, 0.06 * ICON), blur(glyph, 0.25 * ICON)
    y, x = np.mgrid[:CANVAS, :CANVAS] + 0.5
    r = np.hypot(x - CANVAS / 2, y - CANVAS / 2)
    soft = 0.15 * ICON  # the red front's height
    out = []
    for i in range(FRAMES):
        # the red front climbs from below the symbol to above it
        front = o + ICON + soft - ease(i / WIPE) * (ICON + 2 * soft)
        red = ease((y - front) / soft + 0.5)[..., None]
        color = WHITE * (1 - red) + RED * red
        # the glow follows the red, then breathes; the aura is one ring leaving the symbol
        glow = ease(i / WIPE) * (1 + 0.15 * np.sin(max(i - WIPE, 0) / 3))
        s = (i - WIPE) / (FRAMES - WIPE)
        ring = 0.0 if s < 0 else (1 - s) * np.exp(-(((r - (0.5 + 0.8 * s) * ICON) / (0.05 * ICON)) ** 2))
        halo = np.clip(glow * (0.9 * near + 0.5 * far) + 0.6 * ring, 0, 1)
        a = glyph + halo * (1 - glyph)
        rgb = (color * glyph[..., None] + RED * (halo * (1 - glyph))[..., None]) / np.maximum(a, 1e-6)[..., None]
        a = a * (1 - ease((i - (FRAMES - 1 - FADE)) / FADE))
        im = np.dstack([np.clip(rgb, 0, 255), a * 255])
        out.append(Image.fromarray(np.round(im).astype(np.uint8), 'RGBA'))
    return out


def files() -> dict[str, bytes]:
    """The modules' files except name.xml, the same for both themes, with each frame encoded once; also writes the
    frames to build/fingerprint for review."""
    review = BUILD / 'fingerprint'
    review.mkdir(parents=True, exist_ok=True)
    out = {'fingerprint_icon/icon.svg': svg().encode(), 'fingerprint_anim/fptheme.xml': FPTHEME.encode()}
    for i, f in enumerate(frames()):
        buf = io.BytesIO()
        f.save(buf, 'PNG')
        out[f'fingerprint_anim/res/light/{i:02d}.png'] = buf.getvalue()
        (review / f'{i:02d}.png').write_bytes(buf.getvalue())
    out['fingerprint_anim/res/shortcut/shortcut.png'] = out[f'fingerprint_anim/res/light/{WIPE + 2:02d}.png']
    return out


def build(outer: Path, title: str, files: dict[str, bytes]) -> None:
    for m in MODULES:
        (outer / m).mkdir()
        (outer / m / 'name.xml').write_text(NAME.format(title=title))
    for rel, data in files.items():
        (outer / rel).parent.mkdir(parents=True, exist_ok=True)
        (outer / rel).write_bytes(data)
