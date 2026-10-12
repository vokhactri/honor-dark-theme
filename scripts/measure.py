"""Glyph width, height and centroid of built icons, to balance icons that sit side by side.

uv run -m scripts.measure com.vnid com.bhxhapp
"""

import sys

import numpy as np
from PIL import Image

from theme.paths import BUILD
from theme.unify import MASK, PLATE, S, flat

for p in sys.argv[1:]:
    a = np.asarray(flat(Image.open(BUILD / f'out/flat/{p}.png'))).astype(float)
    glyph = (np.abs(a[..., :3] - PLATE[..., :3]).max(-1) > 40) & (MASK > 0.99)
    ys, xs = np.nonzero(glyph)
    w, h = (xs.max() - xs.min() + 1) / S, (ys.max() - ys.min() + 1) / S
    cx, cy = xs.mean() / S - 0.5, ys.mean() / S - 0.5
    print(f'{p:28s} w={w:.3f} h={h:.3f} area={glyph.mean():.3f} cx={cx:+.3f} cy={cy:+.3f}')
