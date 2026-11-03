package app.aize.nav

/**
 * Decides when a driver has really left the route. A single noisy fix must not trigger a re-route, so it needs
 * [strikes] consecutive fixes farther than [thresholdMeters], and at most one re-route per [cooldownMs].
 */
class OffRouteDetector(
    private val thresholdMeters: Double = 40.0,
    private val strikes: Int = 3,
    private val cooldownMs: Long = 15_000,
) {
    private var count = 0
    private var lastFired = Long.MIN_VALUE / 2

    /** Feed one fix (distance from the route, wall-clock ms). Returns true exactly when a re-route should be requested. */
    fun update(offRouteMeters: Double, nowMs: Long): Boolean {
        if (offRouteMeters <= thresholdMeters) { count = 0; return false }
        count++
        if (count >= strikes && nowMs - lastFired >= cooldownMs) { lastFired = nowMs; count = 0; return true }
        return false
    }

    fun reset() { count = 0 }
}
