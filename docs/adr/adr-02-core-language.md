# ADR-02 · Core language

**Status:** accepted, not yet implemented

## Decision
**Rust** (`aize-core`): matching, progress, guidance, ETA, alerts look-ahead, probe batching

## Why
No GC pauses or JIT warm-up in the 1–10 Hz hot loop; memory-safe (a navigation library must not UAF); one language with the backend (shared `aize-proto`)

## Rejected
Kotlin-only (GC/JIT in hot path), C++ (safety), Go (FFI/GC)

## Revisit when
Profiling shows no gain vs Kotlin for a given module

## In the repo today
`core/` workspace exists with the polyline codec (5 tests). The app still uses its Kotlin implementation; the UniFFI bridge (P4-06) needs the Android NDK, which is not installed on the build machine.
