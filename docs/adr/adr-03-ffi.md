# ADR-03 · FFI

**Status:** accepted, not yet implemented

## Decision
**UniFFI** + protobuf byte payloads for bulk data

## Why
Mirrors Waze's coarse-grained, typed JNI; avoids hand-written JNI and per-field calls

## Rejected
Hand-rolled JNI

## Revisit when
UniFFI overhead measurable in P4-13

## In the repo today
Waits on the NDK and `cargo-ndk`. `proto/` (buf-linted) holds the first messages.
