"""Build the icons and pack dist/Dark-Glare-Honor.hnt and dist/Dark-Flat-Honor.hnt.

uv run -m theme.build                  # every app
uv run -m theme.build com.zing.zalo    # only these apps, reuse the rest from build/out
"""

import shutil
import sys
import zipfile
from pathlib import Path

from PIL import Image

from . import charging, fingerprint, mockup, previews, statusbar
from .overrides import GLORY, GOOGLE, OVERRIDES
from .paths import APPS, BUILD, DATA, DIST
from .unify import App, compose, from_glory, from_orig, from_pack, from_store, layers

VARIANTS = {'glare': 'Dark Glare', 'flat': 'Dark Flat'}
# where each app's source image lives, see the README
SOURCES = ('web', 'glory', 'orig', 'pack', 'google', 'store')


def source(p: str) -> Path:
    found = [f for d in SOURCES for f in (DATA / d).glob(f'{p}.*') if f.stem == p]
    if len(found) != 1:
        raise SystemExit(f'{p}: expected one source image, found {[str(f.relative_to(DATA)) for f in found]}')
    return found[0]


def render(p: str) -> None:
    """Write the foreground layer of <p>'s icon to build/out/<variant>/<p>.png for both variants."""
    src = source(p)
    kind = src.parent.name
    out = {v: BUILD / f'out/{v}/{p}.png' for v in VARIANTS}
    if kind == 'glory':
        for v, f in out.items():
            from_glory(src, src.with_suffix('.bg.png'), GLORY.get(p), glare=v == 'glare').save(f)
        return
    if kind == 'orig':
        for v, f in out.items():
            from_orig(src, glare=v == 'glare').save(f)
        return
    app = OVERRIDES.get(p, GOOGLE if kind == 'google' else App())
    fg = from_pack(src) if kind == 'pack' else from_store(src, app)
    for v, f in out.items():
        compose(fg, app, glare=v == 'glare').save(f)


def zipdir(zf: zipfile.ZipFile, root: Path, rel: str) -> None:
    """Add a file or directory (with its directory entries, like `zip -r`)."""
    path = root / rel
    if path.is_dir():
        zf.write(path, rel + '/')
        for c in sorted(path.iterdir()):
            zipdir(zf, root, f'{rel}/{c.name}')
    else:
        zf.write(path, rel)


def pack(v: str) -> None:
    title = VARIANTS[v]
    stage = BUILD / f'stage_{v}'
    shutil.rmtree(stage, ignore_errors=True)
    outer = stage / 'outer'
    shutil.copytree(DATA / 'base', outer)
    # launcher assets (mask, folder plate) from Glory, then one adaptive icon per app, as in Glory:
    # <package>/foreground.png on <package>/background.png
    icons = shutil.copytree(DATA / 'system', stage / 'icons')
    for f in sorted((BUILD / f'out/{v}').glob('*.png')):
        (icons / f.stem).mkdir()
        front, back = layers(Image.open(f))
        front.save(icons / f.stem / 'foreground.png')
        back.save(icons / f.stem / 'background.png')

    desc = outer / 'description.xml'
    desc.write_text(desc.read_text().replace('{title}', title))
    previews.wallpapers(outer / 'wallpaper')
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
    for v in VARIANTS:
        (BUILD / f'out/{v}').mkdir(parents=True, exist_ok=True)
    for p in sys.argv[1:] or sorted(APPS):
        render(p)
    for v, title in VARIANTS.items():
        mockup.render(v, title)
        pack(v)


if __name__ == '__main__':
    main()
