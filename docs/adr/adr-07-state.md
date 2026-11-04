# ADR-07 · State

**Status:** accepted, partly implemented

## Decision
**UDF/MVI**: `StateFlow` of immutable state, one-shot effects via channels

## Why
Predictable recomposition, testable

## Rejected
MVVM with mutable LiveData

## Revisit when
—

## In the repo today
`NavScreen` holds state in Compose; moves to `StateFlow` + ViewModel with P1-08.
