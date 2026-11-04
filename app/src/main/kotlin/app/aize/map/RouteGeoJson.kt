package app.aize.map

import app.aize.nav.Route

/**
 * GeoJSON for the options under the route chooser.
 *
 * Kept free of MapLibre types so it can be unit-tested: the renderer only ever sees the string, and a
 * malformed one fails silently on a phone (nothing is drawn, no error is logged), which is exactly the
 * kind of bug that is worth catching in a JVM test instead.
 */
object RouteGeoJson {
    /** One MultiLineString covering every route: a single feature is cheaper than one per route. */
    fun alternatives(routes: List<Route>): String {
        if (routes.isEmpty()) return """{"type":"FeatureCollection","features":[]}"""
        val sb = StringBuilder("""{"type":"FeatureCollection","features":[{"type":"Feature","properties":{},"geometry":{"type":"MultiLineString","coordinates":[""")
        routes.forEachIndexed { ri, r ->
            if (ri > 0) sb.append(',')
            sb.append('[')
            for (i in 0 until r.path.size) {
                if (i > 0) sb.append(',')
                sb.append('[').append(r.path.lon[i]).append(',').append(r.path.lat[i]).append(']')
            }
            sb.append(']')
        }
        sb.append("]}}]}")
        return sb.toString()
    }
}
