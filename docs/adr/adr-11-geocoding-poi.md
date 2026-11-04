# ADR-11 · Geocoding/POI

**Status:** deviation

## Decision
**Photon** (OSM) + on-device FTS for recents/favourites

## Why
Fast, self-hosted, Apache-2.0

## Rejected
Nominatim-only (slow autocomplete)

## Revisit when
Pelias if ranking needs exceed Photon

## In the repo today
Search uses SQLite FTS5 built with pyosmium (`server/search/`), not Photon: Photon needs a Java runtime and an index that does not fit the permanent 1 GiB server. Names only, no house numbers. Revisit when addresses matter.
