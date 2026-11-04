package app.aize.map

/**
 * A pin drawn on the map, and the GeoJSON for the whole set.
 *
 * Kept free of MapLibre types so the string that reaches the map can be tested on the JVM: a malformed
 * FeatureCollection fails silently on a device (the layer simply draws nothing), which is the worst kind of bug.
 */
data class MapPin(
    val lat: Double,
    val lon: Double,
    val icon: String,
    val label: String,
    val kind: String = "",
)

object PinGeoJson {
    /**
     * One FeatureCollection of points, each carrying its icon and label so a single symbol layer can draw the
     * whole set: `icon-image: ["get", "icon"]`. GeoJSON is lon-first, the classic source of pins in the ocean.
     */
    fun points(pins: List<MapPin>): String {
        if (pins.isEmpty()) return """{"type":"FeatureCollection","features":[]}"""
        val features = pins.joinToString(",") { p ->
            """{"type":"Feature","geometry":{"type":"Point","coordinates":[${num(p.lon)},${num(p.lat)}]},""" +
                """"properties":{"icon":${quote(p.icon)},"label":${quote(p.label)},"kind":${quote(p.kind)}}}"""
        }
        return """{"type":"FeatureCollection","features":[$features]}"""
    }

    /** Same points, for the contact-shadow layer (it only needs the position). */
    fun shadows(pins: List<Point>): String {
        if (pins.isEmpty()) return """{"type":"FeatureCollection","features":[]}"""
        val features = pins.joinToString(",") { p ->
            """{"type":"Feature","geometry":{"type":"Point","coordinates":[${num(p.lon)},${num(p.lat)}]},"properties":{}}"""
        }
        return """{"type":"FeatureCollection","features":[$features]}"""
    }

    data class Point(val lon: Double, val lat: Double)

    private fun num(v: Double): String {
        // never emit NaN/Infinity: JSON.parse on the native side rejects the whole document
        require(!v.isNaN() && !v.isInfinite()) { "coordinate must be finite" }
        return if (v == v.toLong().toDouble()) v.toLong().toString() else v.toString()
    }

    private fun quote(s: String): String {
        val b = StringBuilder("\"")
        for (c in s) when {
            c == '"' -> b.append("\\\"")
            c == '\\' -> b.append("\\\\")
            c == '\n' -> b.append("\\n")
            c == '\r' -> b.append("\\r")
            c == '\t' -> b.append("\\t")
            c < ' ' -> b.append("\\u%04x".format(c.code))
            else -> b.append(c)
        }
        return b.append("\"").toString()
    }
}

/** Which of the nine billboard pins a place kind gets. Unknown kinds fall back to the destination pin. */
object PinIcons {
    const val POLICE = "pin-police"
    const val HAZARD = "pin-hazard"
    const val ACCIDENT = "pin-accident"
    const val JAM = "pin-jam"
    const val CLOSURE = "pin-closure"
    const val CAMERA = "pin-camera"
    const val GAS = "pin-gas"
    const val PARKING = "pin-parking"
    const val DESTINATION = "pin-destination"

    val all = listOf(POLICE, HAZARD, ACCIDENT, JAM, CLOSURE, CAMERA, GAS, PARKING, DESTINATION)

    /**
     * OSM `kind` to pin. The search service reports the full tag (`amenity=fuel`), so the value after the `=`
     * is what matters: matching the whole string silently gave every pin the fallback destination flag.
     */
    fun forKind(kind: String): String = when (kind.substringAfterLast('=').lowercase()) {
        "fuel", "gas", "fuel_station", "charging_station" -> GAS
        "parking", "parking_entrance", "parking_space" -> PARKING
        "police" -> POLICE
        "speed_camera", "camera" -> CAMERA
        else -> DESTINATION
    }

    /** The asset name in assets3d/dist, i.e. `pin-gas` -> `pin_gas`. */
    fun assetFor(icon: String): String = icon.replace('-', '_')
}
