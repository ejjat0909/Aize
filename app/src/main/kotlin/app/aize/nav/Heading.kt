package app.aize.nav

/**
 * Heading smoothing for the puck.
 *
 * GPS reports a bearing about once a second, and consecutive bearings can jump (a fix in a car park, a slow
 * crawl at a junction). Drawing each one as it arrives makes the arrow step and flick. Interpolating along the
 * *short arc* fixes that — but 350° to 10° must go forwards through 0°, not backwards through 180°, which is
 * the bug a naive average produces.
 */
object Heading {
    /** Difference from [from] to [to] in (-180, 180]. */
    fun shortestDelta(from: Double, to: Double): Double {
        var d = (to - from) % 360.0
        if (d <= -180.0) d += 360.0
        if (d > 180.0) d -= 360.0
        return d
    }

    /**
     * One step of a low-pass filter towards [target]. [alpha] is the weight of the new value: 1 snaps,
     * 0.25 is a visible smoothing that still settles within a few fixes.
     */
    fun smooth(previous: Double, target: Double, alpha: Double): Double {
        require(alpha in 0.0..1.0) { "alpha must be in [0,1], was $alpha" }
        val next = previous + shortestDelta(previous, target) * alpha
        return ((next % 360.0) + 360.0) % 360.0
    }
}
