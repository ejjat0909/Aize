# Architecture decision records

One file per decision, taken from §4 of `docs/02-aize-build-plan.md`. *Status* says whether the repo actually does it today.

| ADR | Decision | Status |
|---|---|---|
| [ADR-01](adr-01-platform.md) | Platform: **Native Android | accepted |
| [ADR-02](adr-02-core-language.md) | Core language: **Rust** | accepted, not yet implemented |
| [ADR-03](adr-03-ffi.md) | FFI: **UniFFI** + protobuf byte payloads for bulk data | accepted, not yet implemented |
| [ADR-04](adr-04-map-engine.md) | Map engine: **MapLibre Native** Android | accepted |
| [ADR-05](adr-05-ui-toolkit.md) | UI toolkit: **Jetpack Compose + Material 3** | accepted |
| [ADR-06](adr-06-di.md) | DI: **Hilt** | accepted, not yet implemented |
| [ADR-07](adr-07-state.md) | State: **UDF/MVI**: `StateFlow` of immutable state, one-shot effects via chan | accepted, partly implemented |
| [ADR-08](adr-08-storage.md) | Storage: **Room** | accepted, not yet implemented |
| [ADR-09](adr-09-routing.md) | Routing: **Valhalla** | accepted |
| [ADR-10](adr-10-tiles.md) | Tiles: **OpenMapTiles-schema vector tiles via Planetiler → PMTiles** on objec | accepted, deviation |
| [ADR-11](adr-11-geocoding-poi.md) | Geocoding/POI: **Photon** | deviation |
| [ADR-12](adr-12-backend.md) | Backend: **Rust | accepted, scaffold only |
| [ADR-13](adr-13-wire-protocol.md) | Wire protocol: **gRPC/protobuf over HTTP/2** | accepted, not yet implemented |
| [ADR-14](adr-14-voice.md) | Voice: Prompt-ID system | accepted, not yet implemented |
| [ADR-15](adr-15-animation.md) | Animation: Compose animations from motion tokens | accepted |
| [ADR-16](adr-16-typeface.md) | Typeface: **Figtree** + Roboto fallback, subset and bundled | accepted, not yet implemented |
| [ADR-17](adr-17-auth.md) | Auth: OIDC + passkeys | accepted, not yet implemented |
| [ADR-18](adr-18-build-size.md) | Build & size: R8 full mode, baseline + startup profiles, resource shrinking, **per-A | accepted, partly implemented |
| [ADR-19](adr-19-telemetry.md) | Telemetry: Opt-in, aggregated, self-hosted | accepted, not yet implemented |
| [ADR-20](adr-20-testing.md) | Testing: Paparazzi/Roborazzi, Macrobenchmark + Perfetto, JankStats, proptest, c | accepted, partly implemented |
| [ADR-21](adr-21-3d-assets.md) | 3D assets: **Blender-rendered sprites** | accepted |
