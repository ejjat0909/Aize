package app.aize.nav

/**
 * Decides what the voice should say, and when. Pure logic, no Android: the service feeds it a position on
 * the route and a speed, and it returns a prompt or nothing.
 *
 * Two prompts per maneuver, as drivers expect:
 *  - a **prepare** prompt at a distance that grows with speed (about 8 s of travel, never under 150 m), so a
 *    motorway turn is announced early and a city turn is not announced three streets too soon;
 *  - an **imminent** prompt ("In 40 metres, …") at [imminentMeters], which is what the driver acts on.
 *
 * A maneuver is announced at most once per stage, and the imminent prompt is skipped when the prepare prompt
 * was spoken less than [minGapMs] ago (a very short street between two turns).
 */
class GuidanceAnnouncer(
    private val prepareBaseMeters: Double = 150.0,
    private val prepareSeconds: Double = 8.0,
    private val imminentMeters: Double = 45.0,
    private val minGapMs: Long = 4_000,
    private val arriveMeters: Double = 30.0,
) {
    enum class Kind { PREPARE, IMMINENT, ARRIVED }

    class Prompt(val kind: Kind, val text: String, val maneuverIndex: Int)

    private val prepared = HashSet<Int>()
    private val imminentDone = HashSet<Int>()
    private var lastSpokenAt = Long.MIN_VALUE / 2
    private var arrivedAnnounced = false

    fun reset() {
        prepared.clear()
        imminentDone.clear()
        lastSpokenAt = Long.MIN_VALUE / 2
        arrivedAnnounced = false
    }

    /** How far ahead the prepare prompt goes at this speed: 8 s of travel, but never closer than 150 m. */
    fun prepareDistance(speedMps: Double): Double =
        maxOf(prepareBaseMeters, speedMps.coerceAtLeast(0.0) * prepareSeconds)

    /**
     * @param along metres travelled along the route
     * @param speedMps current ground speed; 0 when unknown (stationary or no fix)
     * @return the prompt to speak now, or null
     */
    fun update(route: Route, along: Double, speedMps: Double, nowMs: Long): Prompt? {
        val left = route.path.lengthMeters - along

        if (left <= arriveMeters) {
            if (arrivedAnnounced) return null
            arrivedAnnounced = true
            lastSpokenAt = nowMs
            return Prompt(Kind.ARRIVED, "You have arrived at your destination.", route.maneuvers.lastIndex)
        }

        // The maneuver being approached is the first one that starts further along than we are. The last
        // maneuver usually sits on the final vertex (the arrival pseudo-maneuver) and is handled above.
        val ahead = route.aheadAt(along) ?: return null
        val next = ahead.maneuver
        val index = route.maneuvers.indexOfFirst { it === next }
        val start = route.path.cumulative[next.beginShapeIndex.coerceIn(0, route.path.size - 1)]
        if (index < 0 || start >= route.path.lengthMeters - 1e-6) return null   // the arrival pseudo-maneuver
        val toNext = ahead.metersToStart

        // First sight of a maneuver that is already close (a late route, a fast road, a skipped GPS fix):
        // say the useful "in X metres" line rather than the bare name a moment before the turn.
        if (toNext <= imminentMeters && index !in imminentDone && nowMs - lastSpokenAt >= minGapMs) {
            prepared += index
            imminentDone += index
            lastSpokenAt = nowMs
            val rounded = roundToTen(toNext)
            // "In 0 metres" is worse than useless: at that range say the instruction itself.
            val text = if (rounded < 10) speakable(next) else "In $rounded metres, ${speakable(next)}"
            return Prompt(Kind.IMMINENT, text, index)
        }

        if (toNext <= prepareDistance(speedMps) && index !in prepared) {
            prepared += index
            lastSpokenAt = nowMs
            return Prompt(Kind.PREPARE, speakable(next), index)
        }
        return null
    }

    private fun speakable(m: Maneuver): String = m.instruction.trim().ifEmpty { "continue" }

    private fun roundToTen(meters: Double): Int = ((meters + 5) / 10).toInt() * 10
}
