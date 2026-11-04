package app.aize.nav

import java.time.Instant
import java.time.ZoneId
import java.time.format.DateTimeFormatter
import java.util.Locale
import kotlin.math.abs
import kotlin.math.roundToInt

/**
 * Remaining time and arrival clock.
 *
 * Two jobs. First, turn a route's own duration (Valhalla's free-flow estimate for the whole leg) into a
 * remaining-time estimate that also listens to how fast the car is actually moving. Second, stop the arrival
 * clock from twitching: a new estimate is published only when it moved by at least [minDeltaSeconds] seconds
 * or [minFraction] of the previous one, whichever is larger.
 *
 * Pure Kotlin on purpose: the smoothing rule is the part worth testing, and it has no Android in it.
 */
class EtaEngine(
    private val minDeltaSeconds: Double = 30.0,
    private val minFraction: Double = 0.05,
) {
    private var published: Double? = null

    fun reset() {
        published = null
    }

    /** The one call the service makes: estimate from the route and the current speed, then smooth it. */
    fun next(route: Route, alongMeters: Double, speedMps: Double): Double =
        smooth(estimate(route, alongMeters, speedMps))

    /** Feeds a raw estimate; returns the value worth showing. */
    fun smooth(remainingSeconds: Double): Double {
        val candidate = remainingSeconds.coerceAtLeast(0.0)
        val previous = published
        val chosen = when {
            previous == null -> candidate
            abs(candidate - previous) >= minDeltaSeconds -> candidate
            abs(candidate - previous) >= previous * minFraction -> candidate
            else -> previous
        }
        published = chosen
        return chosen
    }

    companion object {
        /** Below this the car is standing still (or crawling), and its speed says nothing about the trip. */
        private const val CRAWLING_MPS = 2.0

        /**
         * Blends the route's own pace with the speed the car is doing right now.
         *
         * Valhalla's `time` already assumes typical speeds, so it stays the backbone (70 %). The live speed
         * only nudges it, and is clamped to ±40 % of the backbone: one slow traffic light or one motorway
         * sprint must not swing the arrival clock by ten minutes.
         */
        fun estimate(route: Route, alongMeters: Double, speedMps: Double): Double {
            val length = route.path.lengthMeters
            if (length <= 0.0) return 0.0
            val remaining = (length - alongMeters).coerceIn(0.0, length)
            val base = route.durationSeconds * (remaining / length)
            if (speedMps < CRAWLING_MPS) return base
            val live = remaining / speedMps
            val blended = 0.7 * base + 0.3 * live
            return blended.coerceIn(base * 0.6, base * 1.4)
        }

        /** "1 min", "12 min", "1 h 05 min" — rounded up, because "0 min" is never useful. */
        fun formatMinutes(seconds: Double): String {
            val totalMinutes = (seconds / 60.0).roundToInt().coerceAtLeast(1)
            return if (totalMinutes < 60) {
                "$totalMinutes min"
            } else {
                val hours = totalMinutes / 60
                val minutes = totalMinutes % 60
                if (minutes == 0) "$hours h" else "$hours h ${minutes.toString().padStart(2, '0')} min"
            }
        }

        private val CLOCK: DateTimeFormatter = DateTimeFormatter.ofPattern("h:mm a", Locale.US)

        /** Arrival clock in the phone's own time zone, e.g. "3:42 PM". */
        fun formatArrival(nowMs: Long, remainingSeconds: Double, zone: ZoneId = ZoneId.systemDefault()): String =
            CLOCK.format(Instant.ofEpochMilli(nowMs + (remainingSeconds * 1000).toLong()).atZone(zone))

        /** The single line the banner and the notification share: "12 min · 3:42 PM". */
        fun summary(remainingSeconds: Double, nowMs: Long, zone: ZoneId = ZoneId.systemDefault()): String =
            "${formatMinutes(remainingSeconds)} · ${formatArrival(nowMs, remainingSeconds, zone)}"
    }
}
