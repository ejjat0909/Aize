# ADR-09 · Routing

**Status:** accepted

## Decision
**Valhalla** (self-hosted)

## Why
Time-dependent + live-traffic tile updates, map-matching, many costings, MIT

## Rejected
OSRM (weak live traffic), GraphHopper (viable alternative)

## Revisit when
Quality gap vs incumbents on the pilot region

## In the repo today
Implemented, Dockerless: Valhalla 3.9.1 from the prebuilt `pyvalhalla` wheel (`server/valhalla-setup.sh`).
