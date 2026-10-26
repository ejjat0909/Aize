package app.aize.nav

import org.json.JSONObject

/** One Valhalla maneuver ("Turn right onto Jalan X"), positioned on the route by its shape index. */
class Maneuver(
    val instruction: String,
    val type: Int,
    val beginShapeIndex: Int,
    val lengthMeters: Double,
    val streetName: String?,
)

class Route(val path: RoutePath, val maneuvers: List<Maneuver>, val durationSeconds: Double) {

    /** The maneuver in force at route distance d, and the metres left until the next one starts. */
    class Guidance(val current: Maneuver, val next: Maneuver?, val metersToNext: Double)

    fun guidanceAt(d: Double): Guidance {
        // the final maneuver ("arrive") begins at the last vertex, which no segment contains: at the end, report it
        val seg = if (d >= path.lengthMeters) path.size - 1 else path.segmentAt(d)
        var idx = 0
        for (i in maneuvers.indices) if (maneuvers[i].beginShapeIndex <= seg) idx = i else break
        val next = maneuvers.getOrNull(idx + 1)
        val toNext = if (next == null) path.lengthMeters - d else path.cumulative[next.beginShapeIndex.coerceAtMost(path.size - 1)] - d
        return Guidance(maneuvers[idx], next, toNext.coerceAtLeast(0.0))
    }

    companion object {
        /**
         * Parse the recorded Valhalla /route response (assets/route/kl-sentral-to-klcc.valhalla.json) used by the walking skeleton.
         * Valhalla reports lengths in the request's units (kilometres here), so they are converted to metres.
         */
        fun fromValhallaFixture(json: String): Route {
            val root = JSONObject(json)
            val leg = root.getJSONArray("legs").getJSONObject(0)
            val dec = Polyline.decode(leg.getString("shape"), precision = 6)
            val toMeters = if (root.optString("units", "kilometers").startsWith("mi")) 1609.344 else 1000.0
            val ms = leg.getJSONArray("maneuvers")
            val list = ArrayList<Maneuver>(ms.length())
            for (i in 0 until ms.length()) {
                val m = ms.getJSONObject(i)
                val streets = m.optJSONArray("street_names")
                list += Maneuver(
                    instruction = m.getString("instruction"),
                    type = m.optInt("type"),
                    beginShapeIndex = m.getInt("begin_shape_index"),
                    lengthMeters = m.optDouble("length", 0.0) * toMeters,
                    streetName = if (streets != null && streets.length() > 0) streets.getString(0) else null,
                )
            }
            return Route(RoutePath(dec.lat, dec.lon), list, root.getJSONObject("summary").optDouble("time", 0.0))
        }
    }
}
