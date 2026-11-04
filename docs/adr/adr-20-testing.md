# ADR-20 · Testing

**Status:** accepted, partly implemented

## Decision
Paparazzi/Roborazzi, Macrobenchmark + Perfetto, JankStats, proptest, criterion, GPX replay

## Why
Performance and correctness are testable offline

## Rejected
Manual QA only

## Revisit when
—

## In the repo today
JVM unit tests, `:benchmark` Macrobenchmark module, JankStats in debug. No Paparazzi, proptest or GPX replay yet.
