# assets3d — Blender-rendered 3D assets for the Aize map

The 3D view needs a pointer, vehicle skins and map pins that look three-dimensional at every camera tilt. Aize draws them as
**pre-rendered sprites**: Blender (Cycles, headless) renders each model once, offline, from every camera pitch and heading the map can reach.
On the phone a sprite is one textured quad, so there is no 3D rendering at run time, no extra GL pipeline and no per-frame allocation.

![pointer and pins](preview/aize-3d-contact-sheet.png)

Everything here is **original**: models are built procedurally from primitives (no imported meshes, textures or fonts); colours come from
[`design/tokens`](../design/tokens/aize-purple.tokens.json), so a token change re-colours every asset. Nothing is derived from Waze assets
(the Waze pack that inspired the *kinds* of assets — pointer, car skins, alert pins — was only inventoried, see
[`docs/01`](../docs/01-waze-apk-structure-report.md) §8).

**Measured quality, sizes and every check's result: [`RESULTS.md`](RESULTS.md)** (generated from the pipeline output, not typed by hand).

## What is here

| Family | Assets | Frames per asset | How it is drawn |
|---|---|---|---|
| **Pointer** | `arrow` (heading known), `puck` (no heading) | arrow: 9 pitches × 24 yaws; puck: 9 × 1 (rotationally symmetric) | two bracketing pitch buckets, each warped by one affine matrix, blended ([runtime](#runtime-algorithm)) |
| **Vehicle skins** | `car_sedan`, `car_taxi`, `car_suv` rendered; `car_hatch`, `car_van` build and export but are not pre-rendered | 5 pitches × 24 yaws (15° pitch spacing, blended) | same |
| **Map pins** | `pin_police`, `pin_hazard`, `pin_accident`, `pin_jam`, `pin_closure`, `pin_camera`, `pin_gas`, `pin_parking`, `pin_destination` | 1 | viewport-aligned billboard, no warp |
| **Models** | one `.glb` per solid asset (`dist/*/*.glb`) | – | optional real-time path / design review |

Pitch is the camera tilt from straight-down (0°) towards the horizon (60°) — MapLibre's `pitch`. Yaw is the object's heading relative to the
map (clockwise from screen-up). One consistent light (upper-left, fixed to the screen) is baked into every sprite, so shadows always fall to the lower right.

## Build

```bash
python3 -m pip install --target .pylib numpy pillow && export PYTHONPATH=$PWD/.pylib    # Pillow >= 11, numpy
bash assets3d/build_all.sh pointer           # arrow + puck + camera calibration (about 30 min on 4 vCPU)
bash assets3d/build_all.sh pins              # the nine pins (about 3 min)
bash assets3d/build_all.sh vehicles          # sedan, taxi, suv (about 25 min each)
QUICK=1 bash assets3d/build_all.sh pointer   # 16 samples, 2 pitches: a one-minute smoke test
python3 assets3d/tests/test_warp.py          # the runtime warp, proven against independent vector maths
```

`install_blender.sh` downloads a pinned, checksum-verified **Blender 4.5 LTS** (CPU only — no GPU, no display). Renders are deterministic (fixed seed, Cycles CPU).

## Why sprites, and when not

* **Cost on the phone:** a sprite is one `drawBitmap` under a matrix. The alternative — rendering the glTF in real time — adds a GL/Vulkan
  pipeline for ~260 vertices (the arrow) to ~5 000 (a car): cheap, but it is *another renderer* to keep in sync with the map, and it cannot match
  Cycles' soft shadow, bevel highlights and global illumination without baking them anyway.
* **Where sprites are weaker:** a pre-rendered grid reconstructs *off-grid* views approximately (see below). If a model needs exact views at any
  angle — or colours changed at run time — use the exported `.glb` with a small real-time renderer instead. The `.glb` files are valid, tested
  (`reproject_error.py` parses them) and tiny, so that option stays open.
* **Size:** the 3× tier of the whole pointer family is small next to the 45 MB per-ABI download budget in the build plan; vehicle skins are
  best delivered as on-demand asset packs, not in the base APK.

## Conventions

| | |
|---|---|
| Units | 1 world unit `u` is arbitrary; `unit_dp` in each manifest converts to dp (arrow 22.0 dp/u) |
| Axes | +Z up, +Y forward (screen-up at yaw 0), origin = the point on the ground the sprite is anchored to |
| Camera | perspective with a long lens (distance 28 × the frame half-extent ≈ orthographic), looks at the origin; `pitch` from nadir |
| Anchor | manifest `anchor` = where the origin lands in the frame, as a fraction of width/height from the top-left: `[0.5, 0.5]` for solids, `[0.5, 0.88]` for pins |
| Frame | square, `frame_dp` dp wide, the same pixels-per-unit for every frame of an asset (so any frame can be swapped for another without rescaling) |
| Frame size | chosen from the geometry so the object **and its shadow** never touch the edge at any pitch/yaw (gate: max alpha in the 2 px border ≤ 3) |
| Packing | one WebP sheet per pitch per density tier; sheet cells row-major by yaw index `k`; lossy q92 with lossless alpha; resampling in **premultiplied float** space (no dark fringes — see the self-test) |
| Colour | token-driven; arrow body = `purple.600` (hue within 3° of the token, lightness within 0.05 — checked on the rendered pixels) |

## Runtime algorithm

This is the specification the Android overlay implements; the Python reference is [`tools/simulate_runtime.py`](tools/simulate_runtime.py)
(`SpriteSet`, `plane_affine`, `forward_matrix`, `blend_premult`) and the maths is unit-tested in [`tests/test_warp.py`](tests/test_warp.py).

1. **Select.** `lo, hi` = the two pitch buckets that bracket the camera pitch φ and `t` = the fractional position between them (`t = 0` on a bucket);
   `k = round(relYaw / yawStep) mod yaws`; `residual ρ = wrap180(relYaw − k·yawStep)`. `relYaw` is the vehicle's bearing minus the map bearing (≈ 0 in heading-up navigation).
2. **Warp each bucket to the true view with one affine matrix.** A sprite is exact for its own bucket; for the true pitch φ and residual ρ, re-project the
   horizontal plane `z = h` (`h` = `reprojection.plane_h_u` in the manifest, calibrated per asset) — unsquash by 1/cos(φb), rotate by ρ, squash to cos φ.
   With sprite pixels relative to the frame centre (y down) and `h_px = h · unit_dp · density`, for a bucket of pitch φb:

   ```text
   A =  cos ρ                    B = −sin ρ / cos φb            C = −h_px · tan φb · sin ρ
   D =  sin ρ · cos φ            E =  cos ρ · cos φ / cos φb    F =  h_px · (tan φb · cos ρ · cos φ − sin φ)
   x' = A·x + B·y + C            y' = D·x + E·y + F
   ```

   ```kotlin
   // Android — illustrative, NOT compiled or run (no Android code exists yet; the matrix itself is tested, see tests/test_warp.py)
   // draw a bucket's cell with its centre on the screen anchor
   fun drawCell(canvas: Canvas, sheet: Bitmap, cell: Rect, anchor: PointF, m: FloatArray /* A,B,C,D,E,F */, alpha: Int, paint: Paint) {
       val mx = Matrix().apply { setValues(floatArrayOf(m[0], m[1], m[2], m[3], m[4], m[5], 0f, 0f, 1f)) }
       paint.alpha = alpha
       canvas.save(); canvas.translate(anchor.x, anchor.y); canvas.concat(mx)
       canvas.drawBitmap(sheet, cell, RectF(-half, -half, half, half), paint)      // half = frame px / 2
       canvas.restore()
   }
   ```
3. **Blend the two pitches.** Draw the lower bucket at alpha `(1 − t)` and the upper at alpha `t` with `BlendMode.Plus` (`PorterDuff.ADD`) on premultiplied pixels — an exact
   linear blend. On a bucket pitch (`t ≈ 0` or `1`) that is **one** draw. Pitch is therefore continuous: no pop when the camera crosses a bucket.
4. **Optionally dissolve on a heading-bucket change** (~100 ms): draw the old and new heading cells with the same matrix form while cross-fading. A flip changes the sprite by about as much as one frame of real rotation in a turn; the dissolve lowers that by roughly 30 % on average (see `RESULTS.md` §2.4) — cheap, but not essential.
5. **Cheaper fallback:** nearest bucket + the same matrix, always one draw — about 3 dB worse on off-grid pitches and with a visible pop at pitch crossings.
6. **Pins:** none of the above — draw the single cell unrotated and unscaled at the anchor, and add the contact shadow as a separate
   map-aligned circle (`circle-pitch-alignment: map`) so it squashes with the pitch for free.

**Make the camera presets coincide with bucket pitches** (overview 0°, browse 30°, drive 45°, navigate 60°). In every steady state the pitch is then on
the grid, and the only error left is the yaw residual. Pitch 0° is exact for any heading (an in-plane rotation of a top-down sprite is exact).

### Why the plane height is calibrated in image space

A first version chose `h` to minimise the **maximum vertex error** in geometry (it picked 0.5 u). Measured against true renders it was the *worst*
choice: that criterion over-weights the interior ridge, while the eye is dominated by the high-contrast outline (the rim at ground level). Choosing
`h` by **PSNR against true renders of off-grid views, penalising the visible pop at bucket switches** (`simulate_runtime.py tune-h`, run for the strategy that ships) puts the plane at
the rim height: the outline is then reconstructed to a fraction of a dp and the interior ridge takes the error. The manifest records both
numbers (`base_*` = outline-level, `worst_*` = all vertices) plus the image-space figures. See [`RESULTS.md`](RESULTS.md).

## Cars: what the numbers say

Cars reconstruct less exactly than the arrow, and it is worth knowing why. A car has real parallax between its wheels (ground level) and its roof (1.4 u up), and
the sprite's single re-projection plane can only be right for one of them. The image-space calibration picks the plane that scores best against true renders — at the
body/roof, `h = 0.8 u` — so the **wheels and underbody carry the error**: the lowest 20 % of the mesh is off by up to 3.1–3.4 dp (the arrow's outline: 0.56 dp), and the
blended reconstruction matches true renders at 26–27 dB mean PSNR (arrow: 30.4 dB). In practice a blend between two pitch buckets shows slight ghosting at the glass, wheels
and tail-lights (see `RESULTS.md`). Why the gates differ: `silhouette` is 1.0 dp for flat assets and 4.0 dp for cars — a **regression ceiling set from the measurement, not a quality claim**.

Would a finer grid fix it? Measured on the sedan mesh, geometry only (`tools/pitch_sweep.py`): 7.5° pitch spacing lowers the worst case from 3.41 to 2.59 dp for 1.8× the frames;
36 headings instead of 24 gives 3.00 dp for 1.5×. Not rendered — the gain is modest for the cost. Use the exported `.glb` instead if a skin must be exact at every angle.

## Quality gates (`tools/verify_sprites.py`, exit status 1 on any required failure)

| Gate | What it proves |
|---|---|
| `anchor`, `pitch` | camera maths: the world origin lands on the declared anchor (< 1 px), disc area scales as cos(pitch) (< 1 %) — measured on a calibration target |
| `clip` | no sprite (object **and** shadow) touches its frame edge at any pitch/yaw |
| `yaw` | silhouette at yaw k equals the yaw-0 silhouette rotated by k·step (IoU ≥ 0.95) |
| `brand` | rendered body colour is the token colour (hue ±3°, lightness ±0.05) |
| `fringe` | premultiplied resampling adds no dark halo; the naive path is shown to (self-test) |
| `roundtrip` | the packed WebP matches the composed master (alpha-weighted PSNR ≥ 38 dB) for every frame and tier |
| `budget` | per-tier size limit |
| `silhouette`, `raised` | outline-level and all-vertex re-projection error, from the mesh (dp) |
| `image`, `pop-pitch`, `pop-yaw` | reconstruction of off-grid views vs **true Blender renders** of those views; image change at a pitch-bucket crossing and at a heading-bucket flip |
| `steady` | top-down overview error is 0 |

## Layout

```text
assets3d/
├─ blender/    lib_aize.py (scene, rig, camera, materials) · asset_pointer.py · asset_vehicles.py · asset_pins.py · render_sprites.py · install_blender.sh
├─ tools/      pack_atlas.py · verify_sprites.py · reproject_error.py · simulate_runtime.py · pitch_sweep.py · merge_frames.py · summarize.py · sprite_lib.py · maptex.py
├─ tests/      test_warp.py
├─ dist/       packed sprite sheets (xhdpi/xxhdpi/xxxhdpi), manifests (*.sprites.json), models (*.glb), verification, validation and tuning JSON   (all committed; master frames are not: re-render with build_all.sh)
├─ preview/    contact sheet, runtime simulation video and stills
├─ RESULTS.md  generated: sizes, error bounds, check results
└─ build/      (git-ignored) render frames, queue scripts
```

## Licence notes

* Models, sprites and `.glb` files are original works; there is no third-party geometry, texture or font in them.
* **Blender is GPL-3.0-or-later.** The Blender Foundation's FAQ says the *output* of Blender is the author's. Whether the `blender/*.py` scripts, which
  `import bpy`, must be distributed under a GPL-compatible licence is a question to settle together with the repository licence (plan decision D5).
* Fonts in previews are DejaVu (free licence); Aize's UI typeface is decided in the build plan.

## Limits and next steps

* Reconstruction of off-grid views is approximate (numbers in `RESULTS.md`); specular highlights depend on the exact view and are not reproduced.
* `car_hatch` and `car_van` are modelled and exported but not rendered; run `build_all.sh vehicles` with them added to the loop.
* Not done: an Android implementation (build plan task P2-05), 3D buildings (MapLibre `fill-extrusion` needs no Blender), animated pin pop-in
  (it is a transform of the single cell), and dark-theme variants of the pins (the badge colours already pass contrast on both map themes).
