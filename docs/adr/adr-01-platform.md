# ADR-01 · Platform

**Status:** accepted

## Decision
**Native Android (Kotlin)**; iOS later via the shared Rust core

## Why
Map surface, sensors, foreground service and Android Auto are platform-bound; Waze itself is native shell + native core

## Rejected
Flutter / React Native / KMP-UI

## Revisit when
iOS becomes a goal

## In the repo today
Implemented: native Kotlin app.
