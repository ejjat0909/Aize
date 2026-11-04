# ADR-21 · 3D assets

**Status:** accepted

## Decision
**Blender-rendered sprites** (pointer, vehicle skins: pitch x heading grid + one affine warp + pitch blend) and **single-cell billboards** (pins); the exported glTF is the real-time fallback

## Why
No 3D rendering, no extra GL pipeline and no per-frame allocation on the phone; Cycles gives soft shadow, bevel highlights and global illumination a real-time shader would only fake; every asset is gated by measured error against true renders (`assets3d/RESULTS.md`)

## Rejected
Real-time glTF renderer (another pipeline to keep in sync; kept as the fallback), importing third-party models (licence)

## Revisit when
A model needs exact views at any angle or run-time recolouring

## In the repo today
Implemented: 126 sprite sheets, verified by `assets3d/tools/verify_sprites.py`.
