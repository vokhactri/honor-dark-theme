"""Image work: cut the glyph out of a source icon, put it on the shared plate, add glare."""

from collections.abc import Sequence
from dataclasses import dataclass
from os import PathLike
from typing import Literal

import numpy as np
import numpy.typing as npt
from PIL import Image
from scipy import ndimage as ndi

from .paths import DATA

type Arr = npt.NDArray[np.float64]  # float images: HxWx3 rgb, HxWx4 rgba, HxW alpha
type Color = Sequence[float] | npt.NDArray[np.floating]  # rgb 0..255
type StrPath = str | PathLike[str]

S = 512
MASK = (
    np.asarray(Image.open(DATA / 'system/icon_mask.png').getchannel('A').resize((S, S), Image.LANCZOS)).astype(float)
    / 255
)
BORDER = Image.open(DATA / 'system/icon_border.png').convert('RGBA').resize((S, S), Image.LANCZOS)
PROFILE = np.load(DATA / 'plate_profile.npy')  # vertical plate colour of the stock Google/Honor icons
PLATE = np.dstack([np.broadcast_to(PROFILE[:, None, :], (S, S, 3)), MASK * 255])


@dataclass(frozen=True)
class App:
    """How an app's glyph is cut out of its source image and placed on the plate."""

    key: str | None = None  # cutout method for backgrounds colour-to-alpha can't handle, see keyed_alpha
    recolor: Color | Literal['auto', 'field'] | None = 'auto'  # glyph colour; None keeps the source colours
    bg: Color | None = None  # background colour to remove; fitted from the outer ring if None
    crop: tuple[float, float, float, float] | None = None  # fractional box to crop the source to first
    holes: bool = False  # key='outside': also clear enclosed background-coloured gaps
    wlo: float = 150  # key='white': min RGB channel ramp from transparent...
    whi: float = 230  # ...to opaque
    lift: bool = False  # brighten dark glyph pixels after the cutout
    specks: bool = True  # drop tiny parts before placing; False keeps small text (i dots, thin stems)
    frac: float = 0.70  # glyph size, as a fraction of the icon
    dx: float = 0.0  # offset from centre, as a fraction of the icon
    dy: float = 0.0


_yy, _xx = np.mgrid[0:S, 0:S]
EDGE = np.minimum(np.minimum(_xx, S - 1 - _xx), np.minimum(_yy, S - 1 - _yy))  # px to the nearest canvas edge
MASK_EDGE = ndi.distance_transform_edt(MASK > 0.5)  # px to the squircle edge


def alpha_bbox(im: Image.Image, thr: int) -> tuple[int, int, int, int] | None:
    return im.getchannel('A').point(lambda v: 255 if v > thr else 0).getbbox()


def trimmed(path: StrPath) -> Arr:
    """Load a pack icon, cropped to its opaque area and scaled to S."""
    im = Image.open(path).convert('RGBA')
    return np.asarray(im.crop(alpha_bbox(im, 40)).resize((S, S), Image.LANCZOS)).astype(float)


def touching_border(mask: npt.NDArray[np.bool_]) -> npt.NDArray[np.bool_]:
    """The connected parts of `mask` that reach the canvas edge."""
    lab, _ = ndi.label(mask)
    ids = np.unique(np.concatenate([lab[0], lab[-1], lab[:, 0], lab[:, -1]]))
    return np.isin(lab, ids[ids > 0])


def lum_sat(rgb: Arr) -> tuple[Arr, Arr]:
    mx, mn = rgb.max(2), rgb.min(2)
    return mx, (mx - mn) / np.maximum(mx, 1)


def luma(x: Arr) -> Arr:
    return 0.3 * x[..., 0] + 0.59 * x[..., 1] + 0.11 * x[..., 2]


def from_orig(path: StrPath, glare: bool = False) -> Image.Image:
    """Keep a stock pack icon intact: only normalise its frame and rim."""
    a = trimmed(path)
    al = a[..., 3:4] / 255
    out = PLATE.copy()
    out[..., :3] = a[..., :3] * al + PLATE[..., :3] * (1 - al)
    # baked rim highlight -> plate colour (fades out over the outer band)
    rgb = out[..., :3]
    mx, mn = rgb.max(2), rgb.min(2)
    halo = (mx - mn < 25) & (mx > PROFILE[:, None, :].max(2) + 6)
    w = np.clip((0.05 - EDGE / S) / 0.02, 0, 1) * halo
    out[..., :3] = rgb * (1 - w[..., None]) + PLATE[..., :3] * w[..., None]
    out[..., :3] = match_plate(out[..., :3])
    out[..., 3] = MASK * 255
    img = Image.fromarray(np.clip(out, 0, 255).astype(np.uint8))
    if glare:
        img.alpha_composite(BORDER)
    return img


def match_plate(rgb: Arr) -> Arr:
    """Swap the icon's own plate for the shared plate, leaving the glyph untouched."""
    mx, mn = rgb.max(2), rgb.min(2)
    band = np.zeros((S, S), bool)
    band[:, int(S * 0.06) : int(S * 0.18)] = True
    band[:, int(S * 0.82) : int(S * 0.94)] = True
    cand = band & (MASK > 0.99) & (mx - mn < 6) & (mx < 80)
    own = np.array([np.median(mx[y][cand[y]]) if cand[y].sum() >= 8 else np.nan for y in range(S)])
    own = ndi.uniform_filter1d(fill_nan(own), 15)
    target = PROFILE.mean(1)
    d = np.abs(rgb - own[:, None, None]).max(2)
    w = np.clip(1 - (d - 4) / 12, 0, 1) * (mx - mn < 12)
    rgb = rgb + (w * (target - own)[:, None])[..., None]
    # baked grey rim along the mask edge -> shared plate
    r = np.clip((28 - MASK_EDGE) / 8, 0, 1) * (mx - mn < 20)
    return rgb * (1 - r[..., None]) + PROFILE[:, None, :] * r[..., None]


def fill_nan(v: Arr) -> Arr:
    """Fill NaNs by linear interpolation."""
    idx = np.arange(len(v))
    ok = ~np.isnan(v)
    return np.interp(idx, idx[ok], v[ok]) if ok.any() else v


def from_pack(path: StrPath) -> Arr:
    """Strip the dark plate (and baked-in glare) from an existing pack icon."""
    a = trimmed(path)
    rgb, al = a[..., :3], a[..., 3] / 255
    lum, sat = lum_sat(rgb)
    edge = EDGE < S * 0.07
    cand = (al < 0.5) | ((sat < 0.3) & (lum < 78)) | (edge & (sat < 0.3) & (lum < 175))
    cand |= (EDGE < S * 0.045) & (sat < 0.2)
    bgmask = touching_border(cand)
    # local plate colour per row, from the plate pixels themselves
    plate_px = bgmask & (al > 0.5) & ~edge
    pl = np.array([np.median(lum[y][plate_px[y]]) if plate_px[y].any() else np.nan for y in range(S)])
    pl = np.nan_to_num(fill_nan(pl), nan=25.0)
    platec = np.repeat(pl[:, None], S, 1)[..., None].repeat(3, 2)
    d = np.abs(rgb - platec).max(2)
    soft = np.clip((d - 6) / 34, 0, 1)
    alpha = np.where(bgmask, 0.0, 1.0)
    # anti-aliased fringe: pixels of the plate component adjacent to the glyph keep partial alpha
    near = ndi.binary_dilation(~bgmask, iterations=3) & bgmask & ~edge
    alpha[near] = soft[near]
    alpha *= al
    col = (rgb - (1 - alpha[..., None]) * platec) / np.maximum(alpha[..., None], 1e-3)
    col = np.where(alpha[..., None] > 0, np.clip(col, 0, 255), 0)
    return clean(np.dstack([col, alpha * 255]))


def boost(color: Color, min_luma: float = 105) -> Arr:
    """Lift dark brand colours so they still read on the dark plate."""
    c: Arr = np.array(color, float)
    if luma(c) >= min_luma:
        return c
    lo, hi = 0.0, 1.0
    for _ in range(20):
        m = (lo + hi) / 2
        if luma(c + (255 - c) * m) < min_luma:
            lo = m
        else:
            hi = m
    return c + (255 - c) * hi


def fit_bg(rgb: Arr, al: Arr) -> tuple[Arr, Arr]:
    """Fit a linear colour field to the outer ring so gradient backgrounds are handled."""
    ring = np.zeros((S, S), bool)
    k = int(S * 0.06)
    ring[k : k + 8, k:-k] = ring[-k - 8 : -k, k:-k] = ring[k:-k, k : k + 8] = ring[k:-k, -k - 8 : -k] = True
    ring &= al > 0.9
    yy, xx = _yy / S, _xx / S
    X = np.stack([np.ones(ring.sum()), xx[ring], yy[ring]], 1)
    coef, *_ = np.linalg.lstsq(X, rgb[ring], rcond=None)
    resid = np.abs(rgb[ring] - X @ coef).max(1)
    # outliers (glyph touching the ring) -> refit on inliers
    keep = resid < np.percentile(resid, 70) + 12
    coef, *_ = np.linalg.lstsq(X[keep], rgb[ring][keep], rcond=None)
    return np.clip(np.stack([np.ones((S, S)), xx, yy], -1) @ coef, 0, 255), np.median(rgb[ring][keep], 0)


def square(im: Image.Image) -> Image.Image:
    """Pad to a square without stretching; pad with transparency or the edge colour."""
    w, h = im.size
    if w != h:
        a = np.asarray(im)
        edge = np.concatenate([a[0], a[-1], a[:, 0], a[:, -1]])
        fill = (0, 0, 0, 0) if np.median(edge[:, 3]) < 128 else tuple(int(v) for v in np.median(edge, 0))
        n = max(w, h)
        c = Image.new('RGBA', (n, n), fill)
        c.paste(im, ((n - w) // 2, (n - h) // 2))
        im = c
    return im.resize((S, S), Image.LANCZOS)


def keyed_alpha(app: App, rgb: Arr, al: Arr) -> Arr:
    """Glyph alpha for icons whose background a plain colour-to-alpha can't remove."""
    lum, sat = lum_sat(rgb)
    match app.key:
        case 'white':  # keep only the white glyph
            return np.clip((rgb.min(2) - app.wlo) / (app.whi - app.wlo), 0, 1) * al
        case 'whitefill':  # white shape plus everything it encloses
            a0 = np.clip((rgb.min(2) - 150) / 80, 0, 1) * al
            return np.maximum(a0, ndi.binary_fill_holes(a0 > 0.5).astype(float))
        case 'warm':  # keep orange/red/yellow glyph parts
            return np.clip((rgb[..., 0] - rgb[..., 2] - 50) / 50, 0, 1) * al
        case 'sat':  # keep only the saturated glyph
            return np.clip((sat - 0.25) / 0.3, 0, 1) * np.clip((lum - 40) / 40, 0, 1) * al
        case 'checker':  # fake 'transparent' checkerboard baked into the image
            outside = touching_border((sat < 0.08) & (lum > 170))
            fringe = ndi.binary_dilation(outside, iterations=3) & ~outside
            alpha = np.where(outside, 0.0, 1.0)
            alpha[fringe] = np.clip(sat[fringe] / 0.6, 0, 1)
            return ndi.gaussian_filter(alpha, 0.7) * al
        case 'outside':  # drop only the background connected to the border, keep same-colour parts inside
            bgc = fit_bg(rgb, al)[1] if app.bg is None else np.array(app.bg, float)
            d = np.abs(rgb - bgc).max(2)
            soft = np.clip(d / 40, 0, 1) * (d > 8)
            alpha = np.where(touching_border((d < 40) | (al < 0.1)), soft, 1.0) * al
            if app.holes:  # also clear enclosed bg-coloured gaps
                lab, idx, sizes = components(d < 40)
                gaps = np.isin(lab, idx[sizes > 0.003 * S * S])
                alpha = np.where(gaps, np.minimum(alpha, soft), alpha)
            return alpha
    raise ValueError(f'unknown key {app.key!r}')


def from_store(path: StrPath, app: App) -> Arr:
    """Lift the glyph off a store icon's background (colour-to-alpha against a fitted bg)."""
    bg, crop, recolor = app.bg, app.crop, app.recolor
    thr = 0.10  # colour distance below which a pixel counts as background
    im = Image.open(path).convert('RGBA')
    if crop:
        w, h = im.size
        im = im.crop((int(crop[0] * w), int(crop[1] * h), int(crop[2] * w), int(crop[3] * h)))
    a = np.asarray(square(im)).astype(float)
    rgb, al = a[..., :3], a[..., 3] / 255
    lum, sat = lum_sat(rgb)
    col, bgc = rgb, None
    if app.key:
        alpha = keyed_alpha(app, rgb, al)
    elif np.mean(al < 0.1) > 0.15 and bg is None:
        alpha = al  # already cut out
    else:
        if bg is None:
            field, bgc = fit_bg(rgb, al)
        else:
            bgc = np.array(bg, float)
            field = np.broadcast_to(bgc, rgb.shape)
        up = np.where(rgb >= field, (rgb - field) / np.maximum(255 - field, 1), (field - rgb) / np.maximum(field, 1))
        alpha = np.clip((up.max(2) - thr) / (1 - thr), 0, 1) ** 0.85 * al
        alpha[alpha < 0.04] = 0
        col = np.clip(field + (rgb - field) / np.maximum(alpha[..., None], 1e-3), 0, 255)
    g = alpha > 0.5
    if recolor == 'auto':
        recolor = None
        if bgc is not None and g.any():
            bl, bs = (v[0, 0] for v in lum_sat(bgc[None, None]))
            achrom = np.mean(sat[g] < 0.18) > 0.6
            if achrom and bs > 0.3 and bl > 60:
                recolor = tuple(boost(bgc))  # white/black glyph on brand colour
            elif achrom and np.median(lum[g]) < 90:
                recolor = (235, 235, 235)  # dark glyph on light/neutral bg -> white
    if recolor == 'field':  # fill the glyph with the blurred background around it
        w = 1 - alpha
        num = np.stack([ndi.gaussian_filter(rgb[..., c] * w, 25) for c in range(3)], -1)
        den = ndi.gaussian_filter(w, 25)[..., None]
        col = np.where(alpha[..., None] > 0, np.clip(num / np.maximum(den, 1e-3) * 1.1, 0, 255), col)
    elif recolor is not None:
        rc = boost(recolor)
        shade = np.clip(lum / 255, 0, 1)[..., None]
        bright = np.median(lum[g]) > 128 if g.any() else True
        col = np.where(alpha[..., None] > 0, rc * ((0.6 + 0.4 * shade) if bright else 1.0), col)
    col = np.where(alpha[..., None] > 0, col, 0)
    fg = clean(np.dstack([col, alpha * 255]))
    return lift(fg) if app.lift else fg


def components(m: npt.NDArray[np.bool_]) -> tuple[npt.NDArray[np.int32], npt.NDArray[np.int_], npt.NDArray]:
    """Label connected parts; return labels, label ids and pixel counts."""
    lab, n = ndi.label(m)
    idx = np.arange(1, n + 1)
    return lab, idx, ndi.sum(m, lab, idx)


def clean(fg: Arr, min_frac: float = 0.002, band: float = 0.12) -> Arr:
    """Drop tiny specks near the rim (leftover glare dots, corner noise)."""
    lab, idx, sizes = components(fg[..., 3] > 30)
    if len(idx):
        cy, cx = np.array(ndi.center_of_mass(fg[..., 3] > 30, lab, idx)).T
        rim = np.minimum.reduce([cx, cy, S - 1 - cx, S - 1 - cy]) < band * S
        fg[..., 3][np.isin(lab, idx[(sizes < min_frac * S * S) & rim])] = 0
    return fg


def drop_specks(fg: Arr) -> Arr:
    """Remove junk that would skew centring: dark specks, rim leftovers, crumbs."""
    lab, idx, sizes = components(fg[..., 3] > 20)
    if len(idx) > 1:
        big = sizes.max()
        mlum = ndi.mean(fg[..., :3].max(2), lab, idx)
        at_rim = np.array([min(y.start, x.start, S - y.stop, S - x.stop) < 0.05 * S for y, x in ndi.find_objects(lab)])
        junk = (
            ((sizes < 0.004 * S * S) & (mlum < 80))
            | (sizes < 0.0005 * S * S)
            | (at_rim & (sizes < 0.1 * big))
            | (sizes < 0.002 * big)
        )
        fg[..., 3][np.isin(lab, idx[junk])] = 0
    return fg


def lift(fg: Arr, min_luma: float = 95, amount: float = 0.6) -> Arr:
    """Brighten dark-coloured glyph pixels so they read on the dark plate."""
    rgb = fg[..., :3]
    t = np.clip((min_luma - luma(rgb)) / min_luma, 0, 1)[..., None] * amount
    fg[..., :3] = rgb + (255 - rgb) * t * (fg[..., 3:4] > 0)
    return fg


def compose(fg: Arr, app: App, glare: bool) -> Image.Image:
    """Centre the glyph on the shared plate at `app.frac` of the icon size, clip to the squircle."""
    frac, dx, dy = app.frac, app.dx, app.dy
    fgim = Image.fromarray((drop_specks(fg.copy()) if app.specks else fg).astype(np.uint8))
    out = Image.fromarray(PLATE.astype(np.uint8))
    if bb := alpha_bbox(fgim, 20):
        g = fgim.crop(bb)
        k = frac * S / max(g.size)
        g = g.resize((max(1, round(g.width * k)), max(1, round(g.height * k))), Image.LANCZOS)
        layer = Image.new('RGBA', (S, S))
        layer.alpha_composite(g, ((S - g.width) // 2 + int(dx * S), (S - g.height) // 2 + int(dy * S)))
        out.alpha_composite(layer)
    o = np.asarray(out).astype(float)
    o[..., 3] = np.minimum(o[..., 3], MASK * 255)
    out = Image.fromarray(o.astype(np.uint8))
    if glare:
        out.alpha_composite(BORDER)
    return out
