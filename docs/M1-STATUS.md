# M1 — "Drive with it": status

Milestone M1 is the first one where the app is worth putting on a dashboard: guidance
keeps running with the screen off, and it tells you where to turn instead of only
showing it.

This note records what was built, how it was verified, and what is deliberately still
missing. Phase and milestone status lives in the generated
[`docs/03-roadmap.md`](03-roadmap.md); change it there via `scripts/generate_roadmap.py`,
never by hand.

## What changed

| Piece | Where | What it does |
| --- | --- | --- |
| Navigation engine | `app/src/main/kotlin/app/aize/nav/NavService.kt` | Foreground service (`android:foregroundServiceType="location"`). Owns the fix stream (`LocationManager`, GPS + network, 1 s / 0 m), projects onto the route, runs the guidance trigger, speaks, updates the notification. |
| Shared state | `nav/NavSession.kt` | One process-wide `StateFlow<Snapshot>`; the service writes, the UI reads. Also carries a reroute tick so the UI can re-plan over the network and hand the new route back. |
| Announcement logic | `nav/GuidanceAnnouncer.kt` | Pure Kotlin, no Android types: two prompts per maneuver (prepare at `max(150 m, speed × 8 s)`, imminent at 45 m), dedupe per maneuver, 4 s quiet gap, arrival inside 30 m. |
| Voice | `nav/Voice.kt` | System TTS with `USAGE_ASSISTANCE_NAVIGATION_GUIDANCE`, speech content type, `AUDIOFOCUS_GAIN_TRANSIENT_MAY_DUCK` (ducking, not pausing), `QUEUE_FLUSH` and a stable utterance id so a new instruction replaces an old one. |
| Route helper | `nav/Route.kt` | `aheadAt(d)` returns the maneuver ahead, the metres to it and the one after — so nothing ever displays a negative distance. |

## How it was verified

On the `api34` emulator (x86_64, software rendering), against the permanent server at
`https://56399b2f75b741eaa53cf4456e42703c.bxcpreview.site`:

* A long-press on the map produced a live route (`route dest=… len=9811m`) and the
  service logged `listening on [network, gps]`.
* `dumpsys activity services app.aize` reported
  `isForeground=true foregroundId=42 types=00000008` (location) and the notification
  read `Bear left onto Jalan Stesen Sentral.` / `9.8 km left · 0 m done`.
* With the display **dozing** (`mWakefulness=Dozing`), replaying the route's own shape
  through `adb emu geo fix` produced fresh prompts: `Bear right.`, then
  `Bear right onto Jalan Stesen Sentral 5.` — guidance survives screen-off.
* After driving part of the route the notification read `9.2 km left · 580 m done`,
  i.e. it counts down rather than repeating the total.
* Driving 400 m off the route produced `off route by 459 m after 33 fixes: re-routing`, the UI re-planned
  (`rerouted len=10092m`) and the service picked the new route up and kept guiding. One sequential worker
  performs re-routes, so a notification that arrives mid-request can no longer cancel it.
* "End navigation" in the sheet stopped the service (`isForeground` count 0) and removed
  the notification.
* 31 JVM tests pass, including the announcer suite and the new `aheadAt` property test
  ("never reports a maneuver behind the driver").

## Still missing for a finished M1

* ETA clock in the notification (P4-05) — the notification shows distance only.
* Lane guidance, roundabout exits, speed limits and camera zones in the prompt text (P4-04).
* Prompt catalogue, voice modes (off / alerts / brief / smart / full) and Bluetooth or
  car routing (P4-08); today every prompt is spoken at full length.
* Simulation harness with GPX/NMEA replay (P4-11) — the verification above drives the
  emulator's GPS instead, which is enough to prove the loop but not to regress it.
* Android Auto (P7) needs `NavService` to outlive the Activity completely, including a
  process restart path.
