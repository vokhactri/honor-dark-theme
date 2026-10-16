"""Cut the white Zalo bubble out of the official logo, with the "Zalo" text knocked out.

uv run scripts/zalo_knock.py Logo-Zalo-Arc.png data/web/com.zing.zalo.png
Prints the frac/dx/dy that put the bubble where it sits in the source.
"""

import sys

import numpy as np
from PIL import Image

src, out = sys.argv[1], sys.argv[2]
a = np.asarray(Image.open(src).convert('RGBA')).astype(np.float32)
alpha = a[..., :3].min(-1) * a[..., 3] / 255  # whiteness: blue frame ~0, bubble ~255, text knocked out
g = Image.fromarray(np.dstack([np.full(alpha.shape + (3,), 255.0), alpha]).clip(0, 255).astype(np.uint8))
box = g.getchannel('A').point([255 if v > 20 else 0 for v in range(256)]).getbbox()
assert box, 'the cutout is empty'
x0, y0, x1, y1 = box
W = g.width
print(f'frac={max(x1 - x0, y1 - y0) / W:.4f} dx={((x0 + x1) / 2 - W / 2) / W:.4f} dy={((y0 + y1) / 2 - W / 2) / W:.4f}')
g = g.crop(g.getbbox())
# from_store treats a cutout as already transparent only if >15% of it is, so pad it
n = int(max(g.size) * 1.4)
c = Image.new('RGBA', (n, n))
c.paste(g, ((c.width - g.width) // 2, (c.height - g.height) // 2))
c.save(out)
