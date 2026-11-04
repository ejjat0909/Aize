# ADR-12 · Backend

**Status:** accepted, scaffold only

## Decision
**Rust (Axum + Tonic)**, PostgreSQL/PostGIS, Redis, NATS JetStream, S3-compatible storage, OpenTelemetry; Docker Compose → Kubernetes

## Why
Low memory/latency per probe; shares types with the core

## Rejected
Go/Node

## Revisit when
Team skills

## In the repo today
`backend/` workspace exists (empty crate). Nothing in it is deployed.
