# Privacy note (skeleton)

*This is an engineering draft, not legal advice. It has to be reviewed before the app is published, and it must stay true: if the app changes, change this file in the same commit.*

## What Aize sends, and to whom

| Data | Where it goes | Why | Retention |
|---|---|---|---|
| The route request: start and destination coordinates | The routing server you configure (yours, or a host you trust) | To compute the route | Not logged by the server as shipped (`server/`) |
| Search text typed into the search box | The same server | To find a place | Not logged |
| Nothing else | — | No analytics, no crash reporter, no advertising SDK is bundled | — |

The app has **no account**, no identifier and no telemetry in this build. Opt-in telemetry (P0-10) is off by default and, when enabled, is designed to carry counts and durations only: no coordinates, no identifiers, no free text.

## Location

Location is read only while the app is in the foreground and only to draw the puck, follow the route and detect that you have left it. It is never stored beyond the current session and never sent anywhere except as the start point of a route request you asked for.

## What is on the device

| Item | Purpose | Cleared by |
|---|---|---|
| `SharedPreferences` `aize` | Your server address, telemetry and flag preferences | Uninstalling the app |
| Map tiles | The bundled basemap; no personal data | Uninstalling the app |

There is no history of places you have been, because none is written.

## Your rights and how to exercise them

Everything the app knows about you is on your device and is removed when you uninstall it. There is nothing to request from a server, because the server holds nothing about you.

## Before publishing

- [ ] Review by someone qualified, for the regions you ship in (PDPA in Malaysia, GDPR if the EU is in scope).
- [ ] Fill in the Play data-safety form from the table above, not from memory.
- [ ] Add the privacy policy URL to the store listing and to Settings.
- [ ] Re-read this file whenever a new network call, SDK or stored field is added.
