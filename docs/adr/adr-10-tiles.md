# ADR-10 · Tiles

**Status:** accepted, deviation

## Decision
**OpenMapTiles-schema vector tiles via Planetiler → PMTiles** on object storage/CDN

## Why
Single-file archive, cheap to host on object storage/CDN; MapLibre Native has supported PMTiles sources since 11.7.0 (remote range-request behaviour and cache hit-rate to be confirmed in the P0-08 spike)

## Rejected
Raster tiles; paid tile APIs as primary

## Revisit when
Region > 20 GB

## In the repo today
Basemap is a downloaded Protomaps KL extract (ODbL). Own Planetiler profile still to do (P2-03).
