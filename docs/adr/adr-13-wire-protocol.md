# ADR-13 · Wire protocol

**Status:** accepted, not yet implemented

## Decision
**gRPC/protobuf over HTTP/2**; evaluate Cronet for HTTP/3

## Why
Same typed contract style as Waze; streaming uploads/alerts

## Rejected
REST/JSON

## Revisit when
Proxy constraints

## In the repo today
The app talks plain HTTP/JSON to Valhalla and the search service today. `proto/` is the future contract.
