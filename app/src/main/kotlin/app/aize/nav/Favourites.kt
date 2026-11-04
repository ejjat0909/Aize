package app.aize.nav

import android.content.Context
import org.json.JSONArray
import org.json.JSONObject

/** A place the driver kept. Small enough to live in SharedPreferences as JSON. */
data class SavedPlace(val name: String, val lat: Double, val lon: Double, val kind: String) {
    /**
     * The same spot, whatever it is called: search returns "KLCC" one day and "Suria KLCC" the next, and the
     * driver does not want both. Ten metres of slop covers the differences between the two names' coordinates.
     */
    fun sameAs(other: SavedPlace): Boolean =
        kotlin.math.abs(lat - other.lat) < 1e-4 && kotlin.math.abs(lon - other.lon) < 1e-4
}

/**
 * Saved places, newest first. The encoding is plain JSON so the list survives an app update and can be
 * inspected with `adb shell run-as app.aize cat shared_prefs/aize.xml`.
 */
object Favourites {
    private const val KEY = "saved_places"
    private const val MAX = 50

    fun load(ctx: Context): List<SavedPlace> = decode(prefs(ctx).getString(KEY, null))

    fun add(ctx: Context, place: SavedPlace): List<SavedPlace> {
        val next = (listOf(place) + load(ctx).filterNot { it.sameAs(place) }).take(MAX)
        prefs(ctx).edit().putString(KEY, encode(next)).apply()
        return next
    }

    fun remove(ctx: Context, place: SavedPlace): List<SavedPlace> {
        val next = load(ctx).filterNot { it.sameAs(place) }
        prefs(ctx).edit().putString(KEY, encode(next)).apply()
        return next
    }

    fun isSaved(ctx: Context, place: SavedPlace): Boolean = load(ctx).any { it.sameAs(place) }

    internal fun encode(places: List<SavedPlace>): String {
        val array = JSONArray()
        for (p in places) {
            array.put(JSONObject().put("name", p.name).put("lat", p.lat).put("lon", p.lon).put("kind", p.kind))
        }
        return array.toString()
    }

    /** Never throws: a corrupt list is an empty list, not a crash on launch. */
    fun decode(text: String?): List<SavedPlace> {
        if (text.isNullOrBlank()) return emptyList()
        val out = arrayListOf<SavedPlace>()
        runCatching {
            val array = JSONArray(text)
            for (i in 0 until array.length()) {
                val o = array.optJSONObject(i) ?: continue
                val name = o.optString("name").trim()
                if (name.isEmpty()) continue
                val lat = o.optDouble("lat", Double.NaN)
                val lon = o.optDouble("lon", Double.NaN)
                if (lat.isNaN() || lon.isNaN()) continue
                out += SavedPlace(name, lat, lon, o.optString("kind", "place=locality"))
            }
        }
        return out
    }

    private fun prefs(ctx: Context) = ctx.getSharedPreferences("aize", Context.MODE_PRIVATE)
}
