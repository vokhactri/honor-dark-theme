"""Status bar icons, packed as the com.android.systemui module.

The module is a zip of res/drawable-xxhdpi/<name>.png; each PNG replaces the SystemUI drawable of that name. The
names follow Honor's official theme 荣耀机器人. Every canvas has the size of the stock drawable's viewport
(data/statusbar/sizes.tsv): SystemUI stretches a theme PNG to the stock drawable's bounds. The layout inside each canvas
follows the stock SystemUI vectors, since several drawables are stacked in one view (signal bars + network type + in/out
arrows, battery frame + level + charge bolt). SystemUI tints the glyphs, so they are black on transparent; only the low
battery levels keep their own colour. Glyphs are Material Symbols Rounded (Apache 2.0, data/statusbar), text is Inter
Display Bold (OFL, data/inter).

The module is com.android.systemui rather than com.android.systemui.status: the Themes app merges a .status module
into a com.android.systemui zip without a night/ entry, and SystemUI then takes the theme as light-only
(FullScreenAodNotificationControllerImpl.checkTheme) and draws notifications, dialogs and the screenshot UI light in
dark mode. The night/ entry here is what checkTheme looks for.
"""

import io
import zipfile
from collections.abc import Callable
from functools import cache
from pathlib import Path

import numpy as np
import numpy.typing as npt
import resvg_py
from PIL import Image, ImageDraw, ImageFont

from .paths import BUILD, DATA

type Mask = npt.NDArray[np.float64]  # alpha 0..1 at S x the PNG size

S = 4  # supersampling
H = 60  # every icon is 60px tall (20dp at xxhdpi)
DIM = 0.3  # the unlit part of a meter, as in the stock vectors (fillAlpha 0.3)
LOW, CRITICAL = (0xFF, 0x9B, 0x1A), (0xF5, 0x48, 0x42)  # SystemUI's low battery colours (<= 20%, <= 10%)
MODULE = 'com.android.systemui'
# name -> (w, h) of the stock drawable
SIZES = {
    n: (float(w), float(h))
    for n, w, h in (line.split('\t') for line in (DATA / 'statusbar/sizes.tsv').read_text().splitlines())
}


def blank(w: float, h: float = H) -> Mask:
    return np.zeros((round(h * S), round(w * S)))


def draw(m: Mask, fn: Callable[[ImageDraw.ImageDraw], None]) -> Mask:
    """Run fn on an S-scaled drawing surface and return what it drew as a mask."""
    im = Image.new('L', (m.shape[1], m.shape[0]))
    fn(ImageDraw.Draw(im))
    return np.asarray(im) / 255


def rrect(m: Mask, box: tuple[float, float, float, float], r: float) -> Mask:
    x0, y0, x1, y1 = (v * S for v in box)
    return draw(m, lambda d: d.rounded_rectangle((x0, y0, x1, y1), r * S, fill=255))


def poly(m: Mask, pts: list[tuple[float, float]]) -> Mask:
    return draw(m, lambda d: d.polygon([(x * S, y * S) for x, y in pts], fill=255))


def over(*layers: tuple[Mask, float]) -> Mask:
    """Stack (mask, alpha) layers; a later layer replaces what is under it."""
    out = np.zeros_like(layers[0][0])
    for m, a in layers:
        out = out * (1 - m) + m * a
    return out


@cache
def _symbol(name: str, em: float) -> Mask:
    """A Material symbol rendered with its 24-unit box em px tall, cropped to the glyph."""
    png = resvg_py.svg_to_bytes(svg_path=str(DATA / f'statusbar/{name}.svg'), height=round(em * S))
    a = Image.open(io.BytesIO(bytes(png))).getchannel('A')
    return np.asarray(a.crop(a.getbbox())) / 255


def symbol(name: str, h: float | None = None, w: float | None = None) -> Mask:
    """A Material symbol scaled so the glyph is h px tall, or w px wide."""
    g = _symbol(name, 96)
    k = h / (g.shape[0] / S) if h else w / (g.shape[1] / S)
    return _symbol(name, 96 * k)


def paste(m: Mask, g: Mask, cx: float, cy: float) -> Mask:
    """Put glyph g centred on (cx, cy) in a canvas the size of m."""
    out = np.zeros_like(m)
    y, x = round(cy * S - g.shape[0] / 2), round(cx * S - g.shape[1] / 2)
    if y < 0 or x < 0 or y + g.shape[0] > m.shape[0] or x + g.shape[1] > m.shape[1]:
        raise ValueError(f'glyph {g.shape} at ({cx}, {cy}) does not fit {m.shape}')
    out[y : y + g.shape[0], x : x + g.shape[1]] = g
    return out


def png(m: Mask, rgb: tuple[int, int, int] = (0, 0, 0)) -> Image.Image:
    h, w = m.shape[0] // S, m.shape[1] // S
    a = m.reshape(h, S, w, S).mean((1, 3))
    im = Image.new('RGBA', (w, h), (*rgb, 0))
    im.putalpha(Image.fromarray(np.round(a * 255).astype(np.uint8)))
    return im


# --- pictograms: one Material symbol centred on the stock canvas


PICTOGRAMS = {
    'stat_sys_alarm': 'alarm',
    'stat_sys_alarm_dim': 'alarm',
    'stat_sys_cast': 'cast',
    'stat_sys_data_bluetooth': 'bluetooth',
    'stat_sys_data_bluetooth_connected': 'bluetooth_connected',
    'stat_sys_data_saver': 'data_saver_on',
    'stat_sys_hotspot': 'wifi_tethering',
    'stat_sys_location': 'location_on',
    'stat_sys_nfc': 'nfc',
    'stat_sys_no_sim': 'no_sim',
    'stat_sys_ringer_silent': 'notifications_off',
    'stat_sys_ringer_vibrate': 'mobile_vibrate',
    'stat_sys_vpn_ic': 'vpn_key',
    'stat_sys_signal_flightmode': 'airplanemode_active',
    'ic_statusbar_nodistub': 'bedtime',
    'ic_statusbar_eyecare': 'visibility',
    'ic_performance_turbo': 'speed',
    'ic_stat_statellite': 'satellite_alt',
    'ic_stat_statellite_beidou': 'satellite_alt',
    'ic_statusbar_battery_reverse_charge': 'battery_android_share',
    'ic_statusbar_dial_wifi': 'wifi_calling',
    'stat_sys_incall_vowifi': 'wifi_calling',
    'ic_statusbar_hd_warning': 'phone_disabled',
    'ic_statusbar_phone': 'call',
    'ic_statusbar_synergy': 'devices',
    'stat_sys_airplane_mode': 'airplanemode_active',
    'stat_sys_ethernet_fully': 'settings_ethernet',
    'stat_sys_managed_profile_status': 'work',
    'stat_sys_network_sharing_ic': 'share',
    'stat_sys_rtt': 'rtt',
    'stat_sys_tty_mode': 'tty',
    'stat_sys_zen_important': 'bedtime',
    'stat_sys_zen_none': 'bedtime',
    # MagicOS 11 scene modes (HnIconVectorDrawable, 16.25dp)
    'stat_sys_zen_mode_date': 'calendar_month',
    'stat_sys_zen_mode_default': 'sentiment_satisfied',
    'stat_sys_zen_mode_draw': 'palette',
    'stat_sys_zen_mode_drive': 'directions_car',
    'stat_sys_zen_mode_exam': 'edit_document',
    'stat_sys_zen_mode_family': 'home',
    'stat_sys_zen_mode_flow': 'ecg_heart',
    'stat_sys_zen_mode_game': 'sports_esports',
    'stat_sys_zen_mode_lecture': 'co_present',
    'stat_sys_zen_mode_movie': 'movie',
    'stat_sys_zen_mode_music': 'music_note',
    'stat_sys_zen_mode_personal': 'person',
    'stat_sys_zen_mode_pet': 'pets',
    'stat_sys_zen_mode_read': 'menu_book',
    'stat_sys_zen_mode_sleep': 'bed',
    'stat_sys_zen_mode_social': 'forum',
    'stat_sys_zen_mode_speed_rail': 'train',
    'stat_sys_zen_mode_sport': 'directions_run',
    'stat_sys_zen_mode_theater': 'curtains',
    'stat_sys_zen_mode_work': 'work',
}
EM = 50  # Material's 24-unit box, so a full-height glyph is about 42px


def fit(name: str, w: float, h: float = H) -> Mask:
    """A symbol centred on a w x h canvas, at the pictograms' size relative to the height."""
    return paste(blank(w, h), _symbol(name, EM * h / H), w / 2, h / 2)


# --- mobile signal: bars on the right of an 80px canvas, network type top left, in/out arrows bottom left


BAR_BOTTOM, BAR_TOP = 52, 10


def bars(n: int, lit: int, w: float = 80, x0: float | None = None, x1: float | None = None) -> Mask:
    """n rounded bars, the first lit ones opaque: 4 bars at x 32..72 of 80px, 5 at 18..78 of 86px, as in stock."""
    m = blank(w)
    x0 = x0 if x0 is not None else 32 if n == 4 else 18
    x1 = x1 if x1 is not None else 72 if n == 4 else 78
    bw = 7.5 if n == 4 else 7.6
    gap = (x1 - x0 - n * bw) / (n - 1)
    layers = []
    for i in range(n):
        x = x0 + i * (bw + gap)
        top = BAR_BOTTOM - (BAR_BOTTOM - BAR_TOP) * (i + 1) / n
        layers.append((rrect(m, (x, top, x + bw, BAR_BOTTOM), bw / 2), 1.0 if i < lit else DIM))
    return over(*layers)


@cache
def font(size: float) -> ImageFont.FreeTypeFont:
    """Inter Display Bold, size px (at S x)."""
    return ImageFont.truetype(
        DATA / 'inter/InterDisplay-Bold.ttf', round(size * S), layout_engine=ImageFont.Layout.BASIC
    )


CAP = -font(100).getbbox('H', anchor='ls')[1] / (100 * S)  # cap height, in em
TRACK = -0.04  # letter spacing in em: Inter is wider than Honor's condensed status bar font


def text(m: Mask, s: str, x: float, cap_top: float, cap: float) -> tuple[Mask, float]:
    """Set s with its cap height `cap` px and caps starting at cap_top; returns the mask and the right edge."""
    f = font(cap / CAP)
    base = (cap_top + cap) * S
    xs = [x * S]
    for c in s[:-1]:
        xs.append(xs[-1] + f.getlength(c) + TRACK * f.size)

    def run(d: ImageDraw.ImageDraw) -> None:
        for c, cx in zip(s, xs, strict=True):
            d.text((cx, base), c, font=f, fill=255, anchor='ls')

    return draw(m, run), (xs[-1] + f.getlength(s[-1])) / S


def label(main: str, sup: str = '', w: float = 80) -> Mask:
    """A network type like 4G or H+: main caps 19px tall from (4, 8), sup set small and raised after it.

    As in the stock vectors, main shrinks to stay left of the third bar (x=42), and sup, which sits above the bars'
    tops, shrinks on its own to stay left of the fourth (x=53). w is the canvas width (80, or 86 for some).
    """
    m = blank(w)
    cap = 19.0
    while True:
        a, right = text(m, main, 4, 8, cap)
        if right <= 42 or cap < 12:
            break
        cap -= 0.5
    if not sup:
        return a
    small = cap * 0.45
    while True:
        b, end = text(m, sup, right + 0.6, 8, small)
        if end <= 53 or small < 6:
            return np.maximum(a, b)
        small -= 0.25


LABELS = {  # name: network type (main, raised small part); the canvas width comes from SIZES
    'stat_sys_data_connected_5g_cust': ('5G',),
    'stat_sys_data_connected_5g_cust_available': ('5G',),
    'stat_sys_data_connected_c_2g': ('2G',),
    'stat_sys_data_connected_c1_2g': ('2G',),
    'stat_sys_data_connected_c2_2g': ('2G',),
    'stat_sys_data_connected_c_3g': ('3G',),
    'stat_sys_data_connected_g_for_gsm_gprs': ('G',),
    'stat_sys_data_connected_5g_plus_cust': ('5G', '+'),
    'stat_sys_data_fully_connected_5point5g': ('5.5G',),
    'stat_sys_signal_roam_type_2g': ('2G',),
    'stat_sys_data_connected_2g': ('2G',),
    'stat_sys_data_connected_3g': ('3G',),
    'stat_sys_data_connected_4g': ('4G',),
    'stat_sys_data_connected_4glte': ('4G', 'LTE'),
    'stat_sys_data_connected_5g': ('5G',),
    'stat_sys_data_connected_5ga': ('5G', 'A'),
    'stat_sys_data_connected_c_h': ('H',),
    'stat_sys_data_connected_c_hplus': ('H', '+'),
    'stat_sys_data_connected_h': ('H',),
    'stat_sys_data_connected_hplus': ('H', '+'),
    'stat_sys_data_fully_connected_1x': ('2G',),  # stock shows CDMA 1x as 2G
    'stat_sys_data_fully_connected_2g': ('2G',),
    'stat_sys_data_fully_connected_3g': ('3G',),
    'stat_sys_data_fully_connected_3gplus': ('3G', '+'),
    'stat_sys_data_fully_connected_4g': ('4G',),
    'stat_sys_data_fully_connected_4glte_plus': ('4G', 'LTE'),
    'stat_sys_data_fully_connected_4gplus': ('4G', '+'),
    'stat_sys_data_fully_connected_4point5g': ('4.5G',),
    'stat_sys_data_fully_connected_4point5g_plus': ('4.5G', '+'),
    'stat_sys_data_fully_connected_e': ('E',),
    'stat_sys_data_fully_connected_g': ('G',),
    'stat_sys_data_fully_connected_h': ('H',),
    'stat_sys_data_fully_connected_hplus': ('H', '+'),
    'stat_sys_data_fully_connected_lte': ('LTE',),
    'stat_sys_data_fully_connected_lte_plus': ('LTE', '+'),
    'stat_sys_data_fully_connected_lteplus': ('LTE', '+'),
    'stat_sys_signal_card1_roam_type_2g': ('2G',),
    'stat_sys_signal_card1_roam_type_3g': ('3G',),
    'stat_sys_signal_card1_roam_type_4g': ('4G',),
    'stat_sys_signal_roam_type_3g': ('3G',),
    'stat_sys_signal_roam_type_4g': ('4G',),
    'stat_sys_signal_roam_type_h': ('H',),
    'stat_sys_signal_roam_type_hplus': ('H', '+'),
    'stat_sys_signal_type_2g': ('2G',),
}


def roam(w: float) -> Mask:
    return text(blank(w), 'R', 43, 6, 10)[0]


def arrows(w: float, x: float, up: float, down: float) -> Mask:
    """Data activity: an up and a down triangle stacked at x (as in the stock vectors), with these alphas."""
    m = blank(w)
    tri_up = poly(m, [(x, 42.5), (x + 9.4, 42.5), (x + 4.7, 37)])
    tri_down = poly(m, [(x, 44.5), (x + 9.4, 44.5), (x + 4.7, 50)])
    return over((tri_up, up), (tri_down, down))


# --- wifi: Material's wedge, dim, with the lit part a sector from the bottom point


WIFI_LEVELS = (0, 0.45, 0.64, 0.82, 1)  # lit radius per level, as a fraction of the wedge height


@cache
def wedge(w: float) -> tuple[Mask, float, float]:
    """The full wedge 58px wide, centred in a w px canvas with its bottom at y=51; also its bottom and height."""
    g = symbol('signal_wifi_4_bar', w=58)
    m = blank(w)
    h = g.shape[0] / S
    return paste(m, g, w / 2, 51 - h / 2), 51, h


def wifi(level: int, w: float) -> Mask:
    m, bottom, h = wedge(w)
    r = WIFI_LEVELS[level] * (h + 2)
    cx = w / 2
    disk = draw(m, lambda d: d.ellipse(((cx - r) * S, (bottom - r) * S, (cx + r) * S, (bottom + r) * S), fill=255))
    return over((m, DIM), (m * disk, 1.0))


def no_internet() -> Mask:
    m = blank(71)
    bar = rrect(m, (59, 31, 63, 45), 2)
    dot = draw(m, lambda d: d.ellipse((59 * S, 47 * S, 63 * S, 51 * S), fill=255))
    return np.maximum(bar, dot)


# --- battery: an outline with a level bar inside. The outline is as big as the stock battery (y 8..52), because
# SystemUI can draw the percentage inside the battery, in a 27.7dp box laid over the whole icon


BATT_W = 104
BODY = (6.0, 8.0, 94.0, 52.0)  # outer edge of the outline, without the nub
STROKE = 3.6
INSET = 2.4  # gap between the outline and the level bar
RADIUS = 12.0
BODY_CX = (BODY[0] + BODY[2]) / 2


def frame() -> Mask:
    m = blank(BATT_W)
    x0, y0, x1, y1 = BODY
    outer = rrect(m, BODY, RADIUS)
    inner = rrect(m, (x0 + STROKE, y0 + STROKE, x1 - STROKE, y1 - STROKE), RADIUS - STROKE)
    nub = draw(
        m,
        lambda d: d.rounded_rectangle(
            ((x1 + 1.5) * S, 23 * S, (x1 + 6) * S, 37 * S), 2.5 * S, fill=255, corners=(False, True, True, False)
        ),
    )
    return np.maximum(outer * (1 - inner), nub)


def level(pct: int) -> Mask:
    e = STROKE + INSET
    x0, y0, x1, y1 = BODY[0] + e, BODY[1] + e, BODY[2] - e, BODY[3] - e
    w = (x1 - x0) * pct / 100
    return rrect(blank(BATT_W), (x0, y0, x0 + w, y1), min(RADIUS - e, w / 2))


def bolts(w: float, n: int, h: float, cx: float, step: float, down: bool = False) -> Mask:
    """n bolts h px tall, step px apart side by side (or stacked if down), centred on (cx, H/2)."""
    g = symbol('bolt', h=h)
    out = blank(w)
    for i in range(n):
        d = (i - (n - 1) / 2) * step
        out = np.maximum(out, paste(out, g, cx, H / 2 + d) if down else paste(out, g, cx + d, H / 2))
    return out


# --- bluetooth device battery: a device glyph left of the stock battery outline (the stock level drawables stay)


def device(w: float, glyph: str, check: bool = False) -> Mask:
    """The glyph fills the space left of the battery, whose outline sits at x = w-30..w-8 as in the stock vectors."""
    m = blank(w)
    x = w - 30
    body = rrect(m, (x, 14.24, x + 22, 51.24), 7.6)
    nub = draw(
        m,
        lambda d: d.rounded_rectangle(
            ((x + 7) * S, 9 * S, (x + 15) * S, 12.24 * S), 3.2 * S, fill=255, corners=(True, True, False, False)
        ),
    )
    g = symbol(glyph, h=36)
    gx = x / 2  # centre of 4..x-4
    out = over((np.maximum(body, nub), 0.5), (paste(m, g, gx, 31), 1.0))
    if check:
        out = badge(out, gx + g.shape[1] / S / 2 - 5, 45)
    return out


def badge(m: Mask, cx: float, cy: float) -> Mask:
    """A check badge with a clear ring around it."""
    ring = draw(m, lambda d: d.ellipse(((cx - 10) * S, (cy - 10) * S, (cx + 10) * S, (cy + 10) * S), fill=255))
    return np.maximum(m * (1 - ring), paste(m, symbol('check_circle', h=16), cx, cy))


def standalone(glyph: str, w: float, check: bool = False) -> Mask:
    g = _symbol(glyph, EM)
    out = paste(blank(w), g, w / 2, H / 2)
    if check:
        out = badge(out, w / 2 + g.shape[1] / S / 2 - 7, 46)
    return out


# --- calling: a filled tag with the text knocked out (VoLTE, HD...), and the SIM numbers next to it


def tag(w: float, h: float, top: float, bottom: float, main: str, sup: str = '') -> Mask:
    """A rounded tag over the full width from top to bottom, with main (and a small raised sup) cut out of it."""
    m = blank(w, h)
    box = rrect(m, (0, top, w, bottom), (bottom - top) * 0.22)
    cap = (bottom - top) * 0.62
    while True:
        a, right = text(m, main, 0, 0, cap)
        width = right
        if sup:
            b, width = text(m, sup, right + 0.4, 0, cap * 0.55)
            a = np.maximum(a, b)
        if width <= w - (bottom - top) * 0.22 or cap < 6:
            break
        cap -= 0.25
    # centre the text block: shift the mask
    dx = round(((w - width) / 2) * S)
    dy = round((top + (bottom - top - cap) / 2) * S)
    cut = np.zeros_like(m)
    cut[dy:, dx:] = a[: m.shape[0] - dy, : m.shape[1] - dx]
    return box * (1 - cut)


TAGS = {  # name: (canvas w, h, tag top, bottom, text)
    'ic_statusbar_volte': (64, 60, 8, 52, ('VoLTE',)),
    'ic_statusbar_vo4g': (58, 60, 8, 52, ('Vo4G',)),
    'ic_statusbar_vo5g': (54, 60, 8, 52, ('Vo5G',)),
    'ic_statusbar_vonr': (54, 60, 8, 52, ('VoNR',)),
    'ic_statusbar_vowifi': (76, 60, 8, 52, ('VoWiFi',)),
    'ic_statusbar_voz4g': (68, 60, 8, 52, ('Voz4G',)),
    'ic_statusbar_hd': (44, 60, 10, 50, ('HD',)),
    'ic_statusbar_hd_plus': (54, 60, 8, 52, ('HD', '+')),
    'ic_statusbar_hd_plus_cmcc': (44, 60, 8, 52, ('HD', '+')),
    'ic_statusbar_incall_wlan': (66, 60, 8, 52, ('WLAN',)),
    'stat_sys_hdlt': (60, 60, 8, 52, ('HD',)),
    'stat_sys_hd_plus': (65, 60, 8, 52, ('HD', '+')),
    'ic_statusbar_incall_double_volte': (58, 36, 4, 32, ('VoLTE',)),
    'ic_statusbar_incall_double_hd': (68, 36, 5, 31, ('HD',)),
    'ic_statusbar_incall_double_hd_plus_cmcc': (68, 36, 5, 31, ('HD', '+')),
    'ic_statusbar_incall_double_vo5g': (52, 36, 4, 32, ('Vo5G',)),
    'ic_statusbar_incall_double_vonr': (52, 36, 4, 32, ('VoNR',)),
    'ic_statusbar_incall_double_vowifi': (68, 36, 4, 32, ('VoWiFi',)),
    'ic_statusbar_incall_double_wlan': (59, 36, 4, 32, ('WLAN',)),
}


def ethernet_alert() -> Mask:
    """Ethernet without internet: the symbol moved left, an exclamation mark after it."""
    m = blank(53, 48)
    g = paste(m, _symbol('settings_ethernet', EM * 48 / H), 22, 24)
    bar = rrect(m, (46, 13, 50, 29), 2)
    dot = draw(m, lambda d: d.ellipse((46 * S, 32 * S, 50 * S, 36 * S), fill=255))
    return np.maximum(g, np.maximum(bar, dot))


def digits(h: float, rows: list[tuple[str, float]]) -> Mask:
    """SIM numbers in a 19px wide canvas: (digit, bottom of its caps) for each row, caps 17px tall from x=0."""
    m = blank(19, h)
    out = np.zeros_like(m)
    for d, bottom in rows:
        out = np.maximum(out, text(m, d, 0, bottom - 17, 17)[0])
    return out


# --- everything


def icons() -> dict[str, Image.Image]:
    out: dict[str, Image.Image] = {}

    def width(name: str) -> float:
        return SIZES[name][0]

    for name, glyph in PICTOGRAMS.items():
        out[name] = png(fit(glyph, *SIZES[name]))
    out['stat_sys_ethernet'] = png(ethernet_alert())

    for lit in range(5):
        for suffix in ('', '_fully'):
            out[f'stat_sys_signal_{lit}{suffix}'] = png(bars(4, lit))
    for lit in range(6):
        for prefix in ('stat_sys_signal_five_', 'ic_statusbar_signal_tjt_'):
            for suffix in ('', '_fully', '_small'):
                name = f'{prefix}{lit}{suffix}'
                out[name] = png(bars(5, lit, w=width(name)))
    for name, parts in LABELS.items():
        out[name] = png(label(*parts, w=width(name)))
    # a tiny standalone LTE+ (24 x 24 in stock)
    m = blank(24, 24)
    out['stat_sys_data_fully_connected_lte_plus'] = png(text(m, 'LTE+', 1, 3, 8)[0])
    for name, (w, h, top, bottom, parts) in TAGS.items():
        out[name] = png(tag(w, h, top, bottom, *parts))
    out['ic_statusbar_superscript_double_icon1'] = png(digits(36, [('1', 30)]))
    out['ic_statusbar_superscript_double_icon2'] = png(digits(36, [('2', 30)]))
    out['ic_statusbar_superscript_icon1'] = png(digits(60, [('1', 50)]))
    out['ic_statusbar_superscript_icon2'] = png(digits(60, [('2', 50)]))
    out['ic_statusbar_superscript_icon_double'] = png(digits(60, [('1', 27), ('2', 50)]))
    out['ic_statusbar_wifi_giga'] = png(text(blank(12, 63), 'G', 1, 8, 18)[0])
    m = blank(62)
    out['stat_sys_signal_five_null'] = png(
        np.maximum(bars(5, 0, w=62, x0=16, x1=54), paste(m, symbol('close', h=11), 12, 14))
    )
    m = blank(26, 24)
    out['stat_sys_wifi_signal_null'] = png(paste(m, symbol('signal_wifi_4_bar', w=24), 13, 12) * DIM)
    for name in ('stat_sys_data_connected_roam', 'stat_sys_signal_type_roam'):
        out[name] = png(roam(width(name)))
    out['stat_sys_signal_in'] = png(arrows(80, 6.8, DIM, 1))
    out['stat_sys_signal_out'] = png(arrows(80, 6.8, 1, DIM))
    out['stat_sys_signal_inout'] = png(arrows(80, 6.8, 1, 1))
    out['single_stat_sys_signal_connected'] = png(arrows(80, 6.8, DIM, DIM))
    m = blank(67)
    out['stat_sys_signal_type_waiting'] = png(paste(m, symbol('hourglass_empty', h=18), 15, 17))
    m = blank(40, 40)
    out['stat_sys_data_disabled'] = png(paste(m, symbol('close', h=13), 12, 12))

    kinds = ('wifi', 'wifi2', 'wifi2_6', 'wifi2_6plus', 'wifi2_7', 'wifi6', 'wifi6_plus', 'wifi7', 'wifi7_plus')
    for lvl in range(5):
        names = [f'stat_sys_{k}_signal_{lvl}' for k in kinds]
        names += [f'stat_sys_wifi_signal_{lvl}_fully', f'stat_sys_charged_wifi_signal_{lvl}']
        for name in names:
            out[name] = png(wifi(lvl, width(name)))
    out['stat_sys_wifi_in'] = png(arrows(71, 55.6, DIM, 1))
    out['stat_sys_wifi_out'] = png(arrows(71, 55.6, 1, DIM))
    out['stat_sys_wifi_inout'] = png(arrows(71, 55.6, 1, 1))
    out['stat_sys_wifi_none'] = png(arrows(71, 55.6, DIM, DIM))
    out['stat_sys_wifi_no_internet'] = png(no_internet())
    m = blank(73)
    out['stat_sys_wifi_hotspot'] = png(paste(m, symbol('wifi_tethering', h=16), 11, 45))

    out['ic_statusbar_battery'] = png(frame())
    for pct in (5, 10, 20, 30, 40, 50, 60, 70, 80, 90, 95, 100):
        # SystemUI leaves levels <= 20% untinted, so they show their own colour
        rgb = CRITICAL if pct <= 10 else LOW if pct <= 20 else (0, 0, 0)
        im = png(level(pct), rgb)
        for suffix in ('', '_charge', '_full', '_save'):
            out[f'ic_statusbar_battery_{pct}{suffix}'] = im
    out['ic_statusbar_battery_charge'] = png(bolts(BATT_W, 1, 28, BODY_CX, 0))
    out['ic_statusbar_battery_charge_double'] = png(bolts(BATT_W, 2, 24, BODY_CX, 15))
    out['ic_statusbar_battery_supercharge'] = png(bolts(BATT_W, 3, 22, BODY_CX, 17))
    out['ic_statusbar_battery_charge_figure'] = png(bolts(25, 1, 26, 12.5, 0))
    out['ic_statusbar_battery_charge_double_figure'] = png(bolts(28, 2, 19, 14, 20, down=True))
    out['ic_statusbar_battery_supercharge_figure'] = png(bolts(24, 3, 13, 12, 14, down=True))
    out['ic_statusbar_battery_powersaving'] = png(paste(blank(BATT_W), symbol('add', h=20), BODY_CX, 30))
    out['ic_statusbar_battery_powersaving_figurein'] = png(paste(blank(36), symbol('add', h=18), 18, 30))

    for name, glyph, check in (
        ('ic_hnstatusbar_earphone_battery', 'headphones', False),
        ('ic_hnstatusbar_earservices_battery', 'hearing', False),
        ('ic_hnstatusbar_loudspeaker_battery', 'speaker', False),
        ('ic_hnstatusbar_bluetooth_device_default', 'bluetooth', False),
        ('stat_sys_data_bluetooth_register_battery_bg', 'headphones', True),
        ('stat_sys_data_bluetooth_unregister_battery_bg', 'headphones', False),
    ):
        out[name] = png(device(width(name), glyph, check))
    for name, check in (
        ('stat_sys_data_bluetooth_voice_id_connected', False),
        ('stat_sys_data_bluetooth_voice_id_registered', True),
    ):
        out[name] = png(standalone('headphones', width(name), check))

    # SystemUI stretches each PNG to the stock drawable's bounds, so the sizes must match
    wrong = {n: im.size for n, im in out.items() if im.size != tuple(round(v) for v in SIZES[n])}
    if wrong or out.keys() != SIZES.keys():
        raise SystemExit(
            f'size mismatch {wrong}, missing {SIZES.keys() - out.keys()}, extra {out.keys() - SIZES.keys()}'
        )
    return out


def build(dst: Path) -> None:
    """Write the module zip to dst, and the PNGs to build/statusbar for review."""
    res = BUILD / 'statusbar'
    res.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(dst, 'w', zipfile.ZIP_DEFLATED) as zf:
        zf.writestr('res/', '')
        zf.writestr('res/drawable-xxhdpi/', '')
        zf.write(DATA / 'statusbar/theme.xml', 'theme.xml')
        # SystemUI only checks for this exact entry; night/theme.xml is empty, so dark mode uses the root values too
        zf.writestr('night/', '')
        zf.writestr('night/theme.xml', '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<resources />\n')
        for name, im in sorted(icons().items()):
            im.save(res / f'{name}.png')
            buf = io.BytesIO()
            im.save(buf, 'PNG')
            zf.writestr(f'res/drawable-xxhdpi/{name}.png', buf.getvalue())


if __name__ == '__main__':
    build(BUILD / MODULE)
    print(len(list((BUILD / 'statusbar').glob('*.png'))), 'icons')
