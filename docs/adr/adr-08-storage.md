# ADR-08 · Storage

**Status:** accepted, not yet implemented

## Decision
**Room** (user data), **DataStore** (settings); Rust core keeps hot caches in memory-mapped files

## Why
Keeps SQLite off the navigation hot path

## Rejected
Room everywhere

## Revisit when
—

## In the repo today
Only `SharedPreferences` for the server address so far.
