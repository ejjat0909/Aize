# ADR-06 · DI

**Status:** accepted, not yet implemented

## Decision
**Hilt** (compile-time)

## Why
No runtime reflection or service lookup at startup (Waze appears to use a Koin-style runtime container)

## Rejected
Koin

## Revisit when
Build-time cost dominates

## In the repo today
The app has no DI container yet; wiring is by hand in `NavScreen`. Introduce Hilt with the first ViewModel (P1-08).
