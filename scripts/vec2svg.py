"""Convert a vector drawable inside an APK (e.g. an adaptive-icon foreground) to SVG. Needs aapt2.

uv run scripts/vec2svg.py app.apk res/drawable/fg.xml out.svg [aapt2-resources-dump.txt] [bg-colour]
"""

import re
import subprocess
import sys
from pathlib import Path

apk, res, out = sys.argv[1], sys.argv[2], sys.argv[3]
A = '/Users/trivk/Library/Android/sdk/build-tools/37.0.0/aapt2'
tree = subprocess.run([A, 'dump', 'xmltree', apk, '--file', res], capture_output=True, text=True).stdout
resdump = Path(sys.argv[4]).read_text() if len(sys.argv) > 4 else ''
defs = []


def gradient(f):
    t = subprocess.run([A, 'dump', 'xmltree', apk, '--file', f], capture_output=True, text=True).stdout
    g = dict(re.findall(r'(start[XY]|end[XY])\(0x[0-9a-f]+\)=(\S+)', t))
    stops = re.findall(r'color\(0x[0-9a-f]+\)=#(\w+)\s+A: \S*:offset\(0x[0-9a-f]+\)=(\S+)', t)
    gid = f'g{len(defs)}'
    st = ''.join(
        f'<stop offset="{float(o)}" stop-color="#{c[2:]}" stop-opacity="{int(c[:2], 16) / 255}"/>' for c, o in stops
    )
    x1, y1, x2, y2 = (float(g[k]) for k in ('startX', 'startY', 'endX', 'endY'))
    defs.append(
        f'<linearGradient id="{gid}" gradientUnits="userSpaceOnUse" x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}">'
        f'{st}</linearGradient>'
    )
    return f'url(#{gid})', 1


def color(v):
    if v.startswith('@0x0106000d'):
        return 'none', 0
    if v.startswith('@'):
        mf = re.search(r'resource ' + v[1:] + r' \S+\n\s+\(\)\s+\(file\) (\S+\.xml)', resdump)
        if mf:
            return gradient(mf.group(1))
        m = re.search(r'resource ' + v[1:] + r' \S+\n\s+\(\)\s+(#[0-9a-f]+)', resdump)
        v = m.group(1) if m else '#ff000000'
    v = v.lstrip('#')
    if len(v) == 6:
        v = 'ff' + v
    return '#' + v[2:], int(v[:2], 16) / 255


def num(a, k, d):
    return float(str(a.get(k, d)).rstrip('dp'))


nodes = []  # (indent, tag, attrs)
for line in tree.splitlines():
    m = re.match(r'(\s*)E: (\w[\w-]*)', line)
    if m:
        nodes.append([len(m.group(1)), m.group(2), {}])
        continue
    m = re.match(r'\s*A: \S*:(\w+)\(0x[0-9a-f]+\)=(.*)', line)
    if m and nodes:
        v = m.group(2)
        mm = re.match(r'"(.*?)"( \(Raw.*)?$', v)
        nodes[-1][2][m.group(1)] = mm.group(1) if mm else v.split(' ')[0]
svg = []
stack = []
for ind, tag, a in nodes:
    while stack and stack[-1] >= ind:
        svg.append('</g>')
        stack.pop()
    if tag == 'vector':
        svg.insert(
            0,
            '<svg xmlns="http://www.w3.org/2000/svg" width="1024" height="1024" '
            f'viewBox="0 0 {a["viewportWidth"]} {a["viewportHeight"]}">',
        )
    elif tag == 'group':
        px, py = num(a, 'pivotX', 0), num(a, 'pivotY', 0)
        tx, ty = num(a, 'translateX', 0) + px, num(a, 'translateY', 0) + py
        sx, sy = num(a, 'scaleX', 1), num(a, 'scaleY', 1)
        t = f'translate({tx} {ty}) rotate({num(a, "rotation", 0)}) scale({sx} {sy}) translate({-px} {-py})'
        svg.append(f'<g transform="{t}">')
        stack.append(ind)
    elif tag == 'path':
        fc, fo = color(a.get('fillColor', '@0x0106000d'))
        sc, so = color(a.get('strokeColor', '@0x0106000d'))
        cap = {'0': 'butt', '1': 'round', '2': 'square'}.get(a.get('strokeLineCap', '0'), 'butt')
        join = {'0': 'miter', '1': 'round', '2': 'bevel'}.get(a.get('strokeLineJoin', '0'), 'miter')
        rule = 'evenodd' if a.get('fillType') == '1' else 'nonzero'
        svg.append(
            f'<path d="{a["pathData"]}" fill="{fc}" fill-opacity="{fo}" fill-rule="{rule}" '
            f'stroke="{sc}" stroke-opacity="{so}" stroke-width="{a.get("strokeWidth", "0")}" '
            f'stroke-linecap="{cap}" stroke-linejoin="{join}"/>'
        )
while stack:
    svg.append('</g>')
    stack.pop()
svg.append('</svg>')
bg = sys.argv[5] if len(sys.argv) > 5 else None
svg[0] += (
    '<defs>'
    + ''.join(defs)
    + '</defs>'
    + (f'<rect x="-5000" y="-5000" width="20000" height="20000" fill="{bg}"/>' if bg else '')
)
Path(out).write_text('\n'.join(svg))
