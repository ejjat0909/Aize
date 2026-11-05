# The design catalogue and its screenshots

Eight pages, one per design decision: `colour`, `type`, `icon`, `button`, `control`, `surface`, `shape`,
`motion`. They live in `app/src/debug/kotlin/app/aize/catalogue/`, in the **debug** source set, so a release
build contains none of it.

## Look at it

```bash
./gradlew assembleDebug -Paize.server=http://127.0.0.1:8020
adb install -r app/build/outputs/apk/debug/app-debug.apk
adb shell am start -n app.aize/.catalogue.CatalogueActivity --es section icon
```

Without the extra the catalogue opens on `colour`; the tabs at the top switch pages. The app's own theme mode
(light/dark) applies, so the same page can be inspected in both.

## The gate

```bash
python3 scripts/screenshot_catalogue.py            # compare against docs/catalogue/golden/*.png
python3 scripts/screenshot_catalogue.py --update   # rewrite the goldens after an intended change
python3 scripts/screenshot_catalogue.py --sections colour,button
```

It needs a running emulator or device with the debug APK installed. For each page it forces the conditions a
golden was taken under — light mode, font scale 1.0, no system error dialogs, screen awake — captures the
screen, and reports two numbers:

| Number | What it catches |
|---|---|
| **mean** absolute difference over every channel | a page-wide change: a background, a theme role, a type scale |
| **percentage of pixels** whose worst channel moves by more than 8/255 | a small change: one button, one chip state, one glyph |

A single number cannot do both. A button recoloured is under 1 % of the screen and barely moves the mean; a
background shifted a few points moves the mean everywhere and no pixel past 8/255.

Thresholds: **0.60** mean and **0.10 %** of pixels. A repeat run on the same emulator measures ≤ 0.02 and
≤ 0.02 %, so there is roughly a 30× margin — the thresholds are not tuned to pass.

The comparison excludes the bottom 72 px of the screen. The system gesture bar animates on its own, and a gate
that fails on pixels the app does not own is a gate people turn off.

On failure the screenshot is saved next to the golden as `<name>.actual.png`, so the difference can be looked
at instead of guessed at. `scripts/test_screenshot_catalogue.py` proves the thresholds catch what they claim to
(`python -m pytest` is not used here: `python3 -m unittest discover -s scripts`).

## Adding a screen

1. Add the page to `CatalogueSection` (id doubles as the golden's filename).
2. Draw it in `DesignCatalogue`.
3. `python3 scripts/screenshot_catalogue.py --update` and **look at the image** before committing it. A golden
   records what the app does, not what it should do.
4. `python3 scripts/screenshot_catalogue.py` — it should now match.
5. `CatalogueCoverageTest` fails until the golden exists, so the two cannot drift apart.
