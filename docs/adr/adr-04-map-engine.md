# ADR-04 · Map engine

**Status:** accepted

## Decision
**MapLibre Native** Android (the changelog on `main` lists 13.7.1 — pin the latest *released* version from Maven Central in P0-03) in **SurfaceView** mode; benchmark the **Vulkan** artifact (`android-sdk-vulkan`) vs OpenGL ES on the device matrix; PMTiles supported natively

## Why
GPU vector rendering on a dedicated thread, on-demand frames, offline cache, expression-driven styling, `global-state` toggling, per-frame stats (`OnDidFinishRenderingFrameWithStatsListener`)

## Rejected
Google Maps SDK (cost/ToS/styling limits), Mapbox (licence), custom wgpu engine (cost), embedding a game engine like Waze (size/complexity)

## Revisit when
Custom effects can't be done with style layers → try the experimental *plugin API* (custom layer types)

## In the repo today
Implemented with MapLibre Native 13.7.1, OpenGL ES. The Vulkan artifact has not been benchmarked yet (needs a real device).
