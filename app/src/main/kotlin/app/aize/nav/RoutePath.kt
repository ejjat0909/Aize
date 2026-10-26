package app.aize.nav

import kotlin.math.PI
import kotlin.math.atan2
import kotlin.math.cos
import kotlin.math.sin
import kotlin.math.sqrt

/** A position on the route: coordinates, travel heading (degrees clockwise from north) and the segment it lies on. */
class RoutePoint(val lat: Double, val lon: Double, val heading: Double, val segment: Int)

/**
 * Immutable polyline with cumulative distances, for O(log n) "where am I after d metres" queries.
 * Distances use the haversine formula (accurate everywhere); per-frame interpolation is linear in lat/lon,
 * which is exact enough over a segment (metres to a few hundred metres).
 */
class RoutePath(val lat: DoubleArray, val lon: DoubleArray) {
    init {
        require(lat.size == lon.size && lat.size >= 2) { "a route needs at least two points" }
    }

    val size: Int get() = lat.size

    /** cumulative[i] = metres from the start to vertex i */
    val cumulative: DoubleArray = DoubleArray(lat.size).also { c ->
        for (i in 1 until lat.size) c[i] = c[i - 1] + haversine(lat[i - 1], lon[i - 1], lat[i], lon[i])
    }
    val lengthMeters: Double get() = cumulative[size - 1]

    /** Index of the segment [i, i+1] containing distance d (clamped to the route). */
    fun segmentAt(d: Double): Int {
        if (d <= 0.0) return 0
        if (d >= lengthMeters) return size - 2
        var lo = 0
        var hi = size - 1
        while (hi - lo > 1) {
            val mid = (lo + hi) ushr 1
            if (cumulative[mid] <= d) lo = mid else hi = mid
        }
        return lo
    }

    fun pointAt(d: Double): RoutePoint {
        val s = segmentAt(d)
        val segLen = cumulative[s + 1] - cumulative[s]
        val t = if (segLen <= 0.0) 0.0 else ((d.coerceIn(0.0, lengthMeters) - cumulative[s]) / segLen).coerceIn(0.0, 1.0)
        return RoutePoint(
            lat = lat[s] + (lat[s + 1] - lat[s]) * t,
            lon = lon[s] + (lon[s + 1] - lon[s]) * t,
            heading = bearing(lat[s], lon[s], lat[s + 1], lon[s + 1]),
            segment = s,
        )
    }

    /** Heading looking `ahead` metres forward from d: smoother than the raw segment heading through bends. */
    fun headingAhead(d: Double, ahead: Double): Double {
        val a = pointAt(d)
        val b = pointAt(minOf(d + ahead, lengthMeters))
        return if (a.lat == b.lat && a.lon == b.lon) a.heading else bearing(a.lat, a.lon, b.lat, b.lon)
    }

    companion object {
        private const val R = 6_371_008.8
        private fun rad(d: Double) = d * PI / 180.0

        fun haversine(lat1: Double, lon1: Double, lat2: Double, lon2: Double): Double {
            val dLat = rad(lat2 - lat1)
            val dLon = rad(lon2 - lon1)
            val a = sin(dLat / 2) * sin(dLat / 2) + cos(rad(lat1)) * cos(rad(lat2)) * sin(dLon / 2) * sin(dLon / 2)
            return 2 * R * atan2(sqrt(a), sqrt(1 - a))
        }

        /** Initial great-circle bearing in degrees [0, 360). */
        fun bearing(lat1: Double, lon1: Double, lat2: Double, lon2: Double): Double {
            val p1 = rad(lat1)
            val p2 = rad(lat2)
            val dl = rad(lon2 - lon1)
            val y = sin(dl) * cos(p2)
            val x = cos(p1) * sin(p2) - sin(p1) * cos(p2) * cos(dl)
            return (Math.toDegrees(atan2(y, x)) + 360.0) % 360.0
        }

        /** Shortest signed difference b - a in degrees, in (-180, 180]. */
        fun angleDelta(a: Double, b: Double): Double {
            var d = (b - a) % 360.0
            if (d > 180.0) d -= 360.0
            if (d <= -180.0) d += 360.0
            return d
        }

        /** Move `current` toward `target` by a fraction of the remaining angle (exponential smoothing), wrap-safe. */
        fun smoothAngle(current: Double, target: Double, fraction: Double): Double =
            (current + angleDelta(current, target) * fraction.coerceIn(0.0, 1.0) + 360.0) % 360.0
    }
}
