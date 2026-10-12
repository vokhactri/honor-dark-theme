# Honor dark theme

Two dark icon themes for Honor phones running MagicOS:

- **Dark Glare** has a glare rim baked into every icon.
- **Dark Flat** is the same set without the glare.

Every icon sits on one shared dark plate, so third-party apps match the stock Honor and Google icons. The pack covers 106 apps, mostly ones common in Vietnam (banks, Zalo, MoMo, Grab, Shopee) plus Google, Honor and a handful of open-source tools. Honor's own apps use the glyphs from Honor's built-in Glory theme.

## Install

1. Download a `.hnt` file from [Releases](../../releases).
2. Move it to the `Honor/Themes` folder in the phone's internal storage.
3. Open the Themes app. The theme shows up in your themes, and you can apply it from there.

The Themes app caches the preview card. To see a new cover after an update, delete the old theme in the app, put the new file in `Honor/Themes` and open the app again.

## Build

You need [uv](https://docs.astral.sh/uv/). It runs on macOS and Linux.

```sh
uv run -m theme.build                  # all icons, writes dist/Dark-Glare-Honor.hnt and dist/Dark-Flat-Honor.hnt
uv run -m theme.build com.zing.zalo    # rebuild only these apps, reuse the rest from build/out
```

A full build takes about 20 seconds. It also writes labelled icon sheets to `build/mockup-glare.png` and `build/mockup-flat.png` for review.

Format and lint with ruff before committing:

```sh
uv run ruff format
uv run ruff check
```

## Release

1. Build, then try both themes on the phone. Delete the old theme in the Themes app first if you want to see the new cover.

   ```sh
   uv run -m theme.build
   adb push dist/Dark-Glare-Honor.hnt dist/Dark-Flat-Honor.hnt /sdcard/Honor/Themes/
   ```

2. Bump the version: `patch` for icon tweaks, `minor` for new apps, `major` for a new look.

   ```sh
   uv version --bump minor    # updates pyproject.toml and uv.lock
   ```

3. Commit, tag and push. The tag comes from the version, so the two always match.

   ```sh
   V=v$(uv version --short)
   git commit -am "release: $V"
   git tag "$V" && git push origin main "$V"
   ```

GitHub Actions then builds both themes on Linux and publishes them as a release with generated notes. Follow it with `gh run watch`. Linux and macOS builds are pixel-identical. To check a CI build without releasing, run the Release workflow by hand and download the `themes` artifact.

## Layout

```
theme/
  build.py      builds each app's icon, then packs both .hnt files
  unify.py      image work: cut out the glyph, recolour it, put it on the shared plate, add glare
  overrides.py  per-app settings such as cutout key, colour and size
  previews.py   wallpapers, cover and preview images shown in the Themes app
  mockup.py     labelled icon sheets for review
data/
  apps.tsv      every app in the theme: package and label
  base/         the rest of the theme: description.xml, lock screen
  inter/        Inter fonts (SIL OFL) for the preview images and mockups
  system/       launcher assets from Glory: icon_mask, icon_masks/ (corner styles), icon_folders/ and others
  icon_border.png    the glare rim baked into the Dark Glare icons
  plate_profile.npy  vertical colour gradient of the shared plate
scripts/        helpers for making cutouts and checking icon sizes
```

Each app has exactly one source image, `<package>.png` (or `.webp`), in one of these folders. The folder decides how it is processed:

| Folder | Source | Processing |
| --- | --- | --- |
| `data/glory/` | foreground (`<package>.png`) and background (`<package>.bg.png`) layers from Honor's Glory theme | the foreground goes on the shared plate; per-app fixes are in `overrides.py` |
| `data/orig/` | stock pack icons of GmsCore and Google Files | kept as-is, only the plate and rim are swapped for the shared ones |
| `data/pack/` | stock pack icons of other apps | the glyph is lifted off its plate and re-centred |
| `data/google/` | Google's 2025-2026 redesigned icons | the white background is removed |
| `data/store/` | Google Play icons | the glyph is cut out of the background |
| `data/web/` | hand-picked logos and cutouts | cut out like `store/` |

To add an app, add a line to `data/apps.tsv`, drop its icon in `data/store/` (or `data/web/`) and run `uv run -m theme.build <package>`. If the cutout or colour looks wrong, add an entry to `overrides.py`.

## The .hnt format

A `.hnt` file is an uncompressed zip. Its layout follows Honor's built-in Glory theme:

- `description.xml` (`<HnTheme>`), `unlock/theme.xml`, `wallpaper/` (a 2800x2800 home wallpaper and a 1280x2800 lock screen wallpaper).
- `icons`, a second, deflated zip with no file extension. Each app is an adaptive icon, `<package>/foreground.png` on `<package>/background.png`, both 294px; the launcher shows the middle 196px through `icon_mask.png`. The background is the shared plate, the foreground is the glyph (with the glare baked in for Dark Glare). An app that shares its package with another app uses its activity class name instead, e.g. `com.android.contacts.activities.DialtactsActivity` for Phone.
- `preview/`: `cover.jpg` (1080x1920, the card in the theme list), `preview_*.jpg` (1280x2800, the detail page), `icon_small.jpg` (510x345) and `icon_small_1.jpg` (612x612) for the icon list, and `icon_thumbnail.png` with the 218px Phone, Gallery and Camera icons that Settings shows.

The theme ships no font. Like Honor's own themes, `description.xml` says `<font>Default</font>` so the system font stays. The phone refuses the theme if `unlock/` and `wallpaper/` are missing (tested together, not one at a time), even when you only want the icons. Keep them, and untick Lock screen and Home screen when you apply the theme instead.

## Credits

Logos and icons belong to their owners.
