# ADR-15 · Animation

**Status:** accepted

## Decision
Compose animations from motion tokens; **Lottie** (hardware render) only for rich vector sequences; Rive optional; **no game engine**; 3D-looking assets are pre-rendered (ADR-21)

## Why
Waze's 11.9 MB Godot pack + 8 MB CJK font is avoidable

## Rejected
Godot/Unity overlays

## Revisit when
A 3-D effect needs it

## In the repo today
No game engine, no Lottie yet.
