"""Build the icons and pack dist/Dark-Flat-Honor.hnt and dist/Liquid-Glass-Honor.hnt.

uv run -m theme.build                  # every app
uv run -m theme.build com.zing.zalo    # only these apps, reuse the rest from build/out
"""

import shutil
import sys
import zipfile
from pathlib import Path

from PIL import Image

from . import charging, dynamic, fingerprint, liquid, mockup, previews, statusbar
from .overrides import GLORY, GOOGLE, OVERRIDES
from .paths import APPS, BUILD, DATA, DIST
from .unify import App, compose, from_glory, from_orig, from_pack, from_store, layers

VARIANTS = {'flat': 'Dark Flat', 'liquid': 'Liquid Glass'}
# optional modules: Liquid Glass's live wallpaper and lock screen, the launcher's calendar colors
EXTRA = ('livepaper.xml', 'livepaper_config.xml', 'lockscreen', 'com.hihonor.android.launcher')
# where each app's source image lives, see the README
SOURCES = ('web', 'glory', 'orig', 'pack', 'google', 'store')


def source(p: str) -> Path:
    found = [f for d in SOURCES for f in (DATA / d).glob(f'{p}.*') if f.stem == p]
    if len(found) != 1:
        raise SystemExit(f'{p}: expected one source image, found {[str(f.relative_to(DATA)) for f in found]}')
    return found[0]


def render(p: str) -> None:
    """Write the foreground layer of <p>'s Dark Flat icon to build/out/flat/<p>.png. Liquid Glass reuses its glyph,
    or takes build/out/glass/<p>.png where that exists."""
    src = source(p)
    kind = src.parent.name
    out = BUILD / f'out/flat/{p}.png'
    glass = BUILD / f'out/glass/{p}.png'
    glass.unlink(missing_ok=True)
    if kind == 'glory':
        from_glory(src, src.with_suffix('.bg.png'), GLORY.get(p)).save(out)
    elif kind == 'orig':
        from_orig(src).save(out)
        # the Dark Flat icon keeps its dark plate, so Liquid Glass gets the glyph lifted off it
        compose(from_pack(src), App()).save(glass)
    elif kind == 'pack':
        compose(from_pack(src), OVERRIDES.get(p, App())).save(out)
    else:
        app = OVERRIDES.get(p, GOOGLE if kind == 'google' else App())
        compose(from_store(src, app), app).save(out)
        # Liquid Glass shows the wallpaper behind the glyph, so it keeps the colors Dark Flat lifts for its dark plate
        compose(from_store(src, app, bright=False), app).save(glass)


def zipdir(zf: zipfile.ZipFile, root: Path, rel: str) -> None:
    """Add a file or directory (with its directory entries, like `zip -r`)."""
    path = root / rel
    if path.is_dir():
        zf.write(path, rel + '/')
        for c in sorted(path.iterdir()):
            zipdir(zf, root, f'{rel}/{c.name}')
    else:
        zf.write(path, rel)


def flat_icons(icons: Path) -> None:
    """Dark Flat: launcher assets (mask, folder plate) from Glory, then one adaptive icon per app, as in Glory:
    <package>/foreground.png on <package>/background.png"""
    shutil.copytree(DATA / 'system', icons)
    for p in sorted(APPS):
        (icons / p).mkdir()
        front, back = layers(Image.open(BUILD / f'out/flat/{p}.png'))
        front.save(icons / p / 'foreground.png')
        back.save(icons / p / 'background.png')


def liquid_icons(icons: Path) -> None:
    """Liquid Glass: its launcher assets and Honor app icons, then a flat <package>.png for every other app."""
    shutil.copytree(liquid.ICONS, icons)
    for p in sorted(APPS.keys() - liquid.HONOR):
        liquid.glass(p).save(icons / f'{p}.png')


def pack(v: str) -> None:
    title = VARIANTS[v]
    stage = BUILD / f'stage_{v}'
    shutil.rmtree(stage, ignore_errors=True)
    outer = stage / 'outer'
    icons = stage / 'icons'
    if v == 'liquid':
        # Liquid Glass's wallpapers, live wallpaper, lock screen and launcher colors
        shutil.copytree(DATA / 'liquid/base', outer)
        liquid_icons(icons)
    else:
        shutil.copytree(DATA / 'base', outer)
        previews.wallpapers(outer / 'wallpaper')
        flat_icons(icons)
        dynamic.build(icons, outer)

    desc = outer / 'description.xml'
    desc.write_text(desc.read_text().replace('{title}', title))
    (outer / 'preview').mkdir()
    previews.render(v, outer / 'preview')
    statusbar.build(outer)
    fingerprint.build(outer, title)
    charging.build(outer)
    # `icons` is a deflated zip without an extension, stored inside the outer zip
    with zipfile.ZipFile(outer / 'icons', 'w', zipfile.ZIP_DEFLATED) as zf:
        for c in sorted(icons.iterdir()):
            zipdir(zf, icons, c.name)
    DIST.mkdir(exist_ok=True)
    hnt = DIST / f'{title.replace(" ", "-")}-Honor.hnt'
    with zipfile.ZipFile(hnt, 'w', zipfile.ZIP_STORED) as zf:
        for rel in (
            'unlock',
            'wallpaper',
            'description.xml',
            'icons',
            *(e for e in EXTRA if (outer / e).exists()),
            *statusbar.MODULES,
            *fingerprint.MODULES,
            'charging',
            'preview',
        ):
            zipdir(zf, outer, rel)
    with zipfile.ZipFile(hnt) as zf:
        assert zf.testzip() is None
    print(f'{hnt.name}: {len(list(icons.iterdir()))} entries in icons, {hnt.stat().st_size} bytes')


def main() -> None:
    for d in ('flat', 'glass'):
        (BUILD / f'out/{d}').mkdir(parents=True, exist_ok=True)
    for p in sys.argv[1:] or sorted(APPS):
        render(p)
    for v, title in VARIANTS.items():
        mockup.render(v, title)
        pack(v)


if __name__ == '__main__':
    main()
