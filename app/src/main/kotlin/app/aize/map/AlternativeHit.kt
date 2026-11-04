package app.aize.map

import kotlin.math.max
import kotlin.math.min

/**
 * Which of several drawn routes did the driver tap?
 *
 * Screen space, not metres: the tolerance a finger needs is constant in pixels, while the metres those pixels cover
 * change by a factor of ten between zoom 13 and zoom 18. MapLibre-free and pure so the arithmetic is unit-tested —
 * a hit test that is off by a sign silently selects the wrong road, which looks like a routing bug, not a tap bug.
 *
 * A path is a flat [x0, y0, x1, y1, ...] array (a polyline's screen projection).
 */
object AlternativeHit {

    /** Squared distance from (px, py) to the segment (ax, ay)-(bx, by). Squared, because only the ordering matters. */
    fun segmentDistanceSq(px: Float, py: Float, ax: Float, ay: Float, bx: Float, by: Float): Double {
        val vx = (bx - ax).toDouble()
        val vy = (by - ay).toDouble()
        val len = vx * vx + vy * vy
        val t = if (len <= 1e-9) 0.0 else (((px - ax) * vx + (py - ay) * vy) / len).coerceIn(0.0, 1.0)
        val dx = px - (ax + t * vx)
        val dy = py - (ay + t * vy)
        return dx * dx + dy * dy
    }

    /** Shortest distance from the tap to the polyline, or [Double.MAX_VALUE] for a path with fewer than two points. */
    fun distanceToPath(path: FloatArray, px: Float, py: Float): Double {
        if (path.size < 4) return Double.MAX_VALUE
        var best = Double.MAX_VALUE
        var i = 0
        while (i + 3 < path.size) {
            val d = segmentDistanceSq(px, py, path[i], path[i + 1], path[i + 2], path[i + 3])
            if (d < best) best = d
            i += 2
        }
        return best
    }

    /**
     * Index of the closest path within [tolerancePx], or null.
     *
     * On an exact tie the earlier path wins: alternatives share their first and last kilometres, so near the start every
     * route is equidistant and "the first one you drew" is the stable answer (the same route the chooser lists first).
     */
    fun nearest(paths: List<FloatArray>, px: Float, py: Float, tolerancePx: Float): Int? {
        val limit = (tolerancePx.toDouble() * tolerancePx)
        var bestIndex: Int? = null
        var best = Double.MAX_VALUE
        for ((i, p) in paths.withIndex()) {
            val d = distanceToPath(p, px, py)
            if (d <= limit && d < best) {
                best = d
                bestIndex = i
            }
        }
        return bestIndex
    }

    /**
     * Flattens a route's screen projection into a path, keeping at most `maxPoints` vertices.
     *
     * A 60 km route has thousands of vertices and a tap happens once; decimating keeps the hit test under a millisecond
     * while staying within a pixel or two of the drawn line, which is far inside a finger's tolerance.
     */
    fun decimate(xs: FloatArray, ys: FloatArray, maxPoints: Int = 256): FloatArray {
        val n = min(xs.size, ys.size)
        if (n == 0) return FloatArray(0)
        val stride = max(1, (n + maxPoints - 1) / maxPoints)
        val keep = ArrayList<Float>(2 * (n / stride + 2))
        var i = 0
        while (i < n) {
            keep.add(xs[i]); keep.add(ys[i])
            i += stride
        }
        if ((n - 1) % stride != 0) { keep.add(xs[n - 1]); keep.add(ys[n - 1]) }   // always keep the destination end
        return keep.toFloatArray()
    }
}
