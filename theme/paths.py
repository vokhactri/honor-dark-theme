from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'data'  # inputs: base theme, source icons, logo cutouts
BUILD = ROOT / 'build'  # generated icons, mockups, staging dirs
DIST = ROOT / 'dist'  # finished .hnt files

# package -> label, for every app in the theme
APPS = dict(line.split('\t') for line in (DATA / 'apps.tsv').read_text().splitlines())
