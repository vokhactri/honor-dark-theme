# Honor themes

Two icon themes for Honor phones running MagicOS:

- **Dark Flat**: every icon sits on one shared dark plate, so third-party apps match the stock Honor and Google icons. Honor's own apps use the glyphs from Honor's built-in Glory theme.
- **Liquid Glass**: Honor's apps keep the glass icons, wallpaper, live wallpaper and lock screen of Họa Tiếu's Liquid Glass theme (shared by HONOR Việt Nam). Every other app gets its Dark Flat glyph on that theme's see-through glass plate.

The pack covers 106 apps, mostly ones common in Vietnam (banks, Zalo, MoMo, Grab, Shopee) plus Google, Honor and a handful of open-source tools. Liquid Glass adds about 60 more Honor apps.

Both themes also bring:

- **Dynamic icons**: the Clock icon shows the time, Calendar the date and Weather the current conditions. Dark Flat draws them in its own style: Glory's clock split into face and hands, and Liquid Glass's weather glyphs on the dark plate.
- **Status bar icons**: Wi-Fi, signal, battery, alarm and the rest are drawn with Material Symbols Rounded, and the network labels (4G, VoLTE, SIM 1/2) are set in Inter. Notifications and Control Center keep their stock dark look.
- **Fingerprint icon**: the in-screen sensor shows the XANA symbol from Code Lyoko. When a finger touches it, it turns red from the bottom up, like a tower XANA activates.

For a system-wide Inter font, see [honor-inter-font](https://github.com/vokhactri/honor-inter-font).

## Install

1. Download a `.hnt` file from [Releases](../../releases).
2. Move it to the `Honor/Themes` folder in the phone's internal storage.
3. Open the Themes app. The theme shows up in your themes, and you can apply it from there.

The Themes app caches the preview card. To see a new cover after an update, delete the old theme in the app, put the new file in `Honor/Themes` and open the app again.

## Build

You need [uv](https://docs.astral.sh/uv/). It runs on macOS and Linux.

```sh
uv run -m theme.build                  # all icons, writes dist/Dark-Flat-Honor.hnt and dist/Liquid-Glass-Honor.hnt
uv run -m theme.build com.zing.zalo    # rebuild only these apps, reuse the rest from build/out
```

A full build takes about 20 seconds. For review, it also writes labeled icon sheets to `build/mockup-flat.png` and `build/mockup-liquid.png`, the status bar icons to `build/statusbar/` and the fingerprint animation frames to `build/fingerprint/`. To redraw only the status bar icons, run `uv run -m theme.statusbar`.

Format and lint with ruff before committing:

```sh
uv run ruff format
uv run ruff check
```

## Release

1. Build, then try both themes on the phone. Delete the old theme in the Themes app first if you want to see the new cover.

   ```sh
   uv run -m theme.build
   adb push dist/Dark-Flat-Honor.hnt dist/Liquid-Glass-Honor.hnt /sdcard/Honor/Themes/
   ```

2. Bump the version: `patch` for icon tweaks, `minor` for new apps or modules, `major` for a new look.

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
  unify.py      image work: cut out the glyph, recolor it, put it on the shared plate
  liquid.py     Liquid Glass icons: its own for Honor apps, the Dark Flat glyph on its glass plate for the rest
  dynamic.py    Dark Flat's dynamic clock, calendar and weather icons and the launcher's calendar colors
  overrides.py  per-app settings such as cutout key, color and size
  previews.py   wallpapers, cover and preview images shown in the Themes app
  mockup.py     labeled icon sheets for review
  statusbar.py  status bar icons (the com.android.systemui and .status modules)
  fingerprint.py  fingerprint icon and touch animation
data/
  apps.tsv      every app in the theme: package and label
  base/         the rest of the theme: description.xml, lock screen
  inter/        Inter fonts (SIL OFL) for the preview images, mockups and status bar labels
  statusbar/    Material Symbols Rounded glyphs (Apache 2.0), stock drawable sizes (sizes.tsv) and the module's theme.xml
  fingerprint/  the XANA symbol, recolored white
  system/       launcher assets from Glory: icon_mask, icon_masks/ (corner styles), icon_folders/ and others
  liquid/       from the Liquid Glass theme: icons/ (Honor app icons, Files, glass plate, rim, dynamic clock, calendar and
                weather icons) and base/ (wallpapers, live wallpaper, lock screen, launcher colors)
  plate_profile.npy  vertical color gradient of the shared plate
scripts/        helpers for making cutouts and checking icon sizes
```

Each app has exactly one source image, `<package>.png` (or `.webp`), in one of these folders. The folder decides how it is processed:

| Folder | Source | Processing |
| --- | --- | --- |
| `data/glory/` | foreground (`<package>.png`) and background (`<package>.bg.png`) layers from Honor's Glory theme | the foreground goes on the shared plate; per-app fixes are in `overrides.py` |
| `data/orig/` | stock pack icon of Google Files | kept as-is, only the plate and rim are swapped for the shared ones |
| `data/pack/` | stock pack icons of other apps | the glyph is lifted off its plate and re-centered |
| `data/google/` | Google's 2025-2026 redesigned icons | the white background is removed |
| `data/store/` | Google Play icons | the glyph is cut out of the background |
| `data/web/` | hand-picked logos and cutouts | cut out like `store/` |

To add an app, add a line to `data/apps.tsv`, drop its icon in `data/store/` (or `data/web/`) and run `uv run -m theme.build <package>`. If the cutout or color looks wrong, add an entry to `overrides.py`.

## The .hnt format

A `.hnt` file is an uncompressed zip. Its layout follows Honor's built-in Glory theme:

- `description.xml` (`<HnTheme>`), `unlock/theme.xml`, `wallpaper/` (a 2800x2800 home wallpaper and a 1280x2800 lock screen wallpaper).
- `icons`, a second, deflated zip with no file extension. Each app is an adaptive icon, `<package>/foreground.png` on `<package>/background.png`, both 294px; the launcher shows the middle 196px through `icon_mask.png`. The background is the shared plate, the foreground is the glyph. An app that shares its package with another app uses its activity class name instead, e.g. `com.android.contacts.activities.DialtactsActivity` for Phone.
  Liquid Glass uses the older flat format instead: one 218px `<package>.png` per app with the plate baked in, on the same 196px squircle, plus its `icon_background.png` (the glass plate), `icon_border.png` (the rim) and `transparent_config.xml`. Its live wallpaper is `wallpaper/video_live_wallpaper.mp4`, played by the wallpaper service named in `livepaper.xml`.
- `icons/dynamic_icons/<package>/`: the live Clock, Calendar and Weather icons, 218px canvases like the flat icons. The clock is `ic_deskclock_dial.png` plus `ic_deskclock_hour`, `_minute` and `_second`, each hand pointing at 12 and turned about the canvas center. The calendar is a bare `calendar_background.png`; the launcher sets the date in `calendar_dynamic_date` and the weekday in `calendar_dynamic`, colors from `theme.xml` in the `com.hihonor.android.launcher` zip. Weather has one icon per condition (`sunny.png`, `rain.png`...). Without this folder the launcher shows the static icon.
- `preview/`: `cover.jpg` (1080x1920, the card in the theme list), `preview_*.jpg` (1280x2800, the detail page), `icon_small.jpg` (510x345) and `icon_small_1.jpg` (612x612) for the icon list, and `icon_thumbnail.png` with the 218px Phone, Gallery and Camera icons that Settings shows.
- `com.android.systemui.status`, a deflated zip of `res/drawable-xxhdpi/<name>.png`, and `com.android.systemui` with `theme.xml` and an empty `night/theme.xml`. Each PNG replaces the SystemUI drawable with that name, using the names from Honor's official 荣耀机器人 theme. The icons are black on transparent and SystemUI tints them. Each canvas has the stock drawable's size, because SystemUI stretches the PNG to it.
- `fingerprint_icon/` and `fingerprint_anim/`, plain directories. The icon is an SVG sized in dp. A pure white SVG gets tinted and filled with the blurred wallpaper, like the stock icon. The animation is up to 30 PNGs in `res/light/`, played once on touch at `<lightfps>` and centered on the sensor at their pixel size. The installer drops either module if it has no `name.xml`, and drops the animation if it has no `res/shortcut/shortcut.png`.

The icons go in `com.android.systemui.status`, as in 荣耀机器人, and the Themes app merges them into `com.android.systemui` when you apply the theme. With the icons placed directly in `com.android.systemui`, every icon showed except the battery, which stayed stock. `com.android.systemui` must keep an exact `night/` entry. Without it SystemUI treats the theme as light-only, so in dark mode it draws notifications, heads-up cards, dialogs and the screenshot UI light. On MagicOS 11 (SDK 37) the merge keeps the entry; older versions dropped it. `theme.xml` also sets `hn_special_transparent_mode_color` to white, SystemUI's flag for a theme that supports transparent mode. Don't add `values-night` colors to the root `theme.xml`: they also apply in daytime and break the lock screen notifications and Control Center tiles.

The theme ships no font. Like Honor's own themes, `description.xml` says `<font>Default</font>` so the system font stays. The phone refuses the theme if `unlock/` and `wallpaper/` are missing (tested together, not one at a time), even when you only want the icons. Keep them, and untick Lock screen and Home screen when you apply the theme instead.

## Credits

Logos and icons belong to their owners.

- Status bar glyphs: [Material Symbols](https://github.com/google/material-design-icons) by Google, Apache 2.0.
- Fonts: [Inter](https://rsms.me/inter/) by Rasmus Andersson, SIL OFL.
- Fingerprint icon: the [XANA symbol](https://codelyoko.com/XANAsymbol.svg) from Code Lyoko.
- Liquid Glass icons, wallpapers and lock screen: Họa Tiếu's Liquid Glass theme ("Chủ đề trong suốt OS11"), shared by HONOR Việt Nam.
