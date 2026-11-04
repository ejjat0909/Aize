package app.aize.net

import org.json.JSONObject
import java.io.IOException
import java.net.HttpURLConnection
import java.net.URL
import java.net.URLEncoder

/** A place from the search service (`GET /search`). */
class PlaceResult(val name: String, val lat: Double, val lon: Double, val kind: String, val distanceMeters: Int)

/** One chip on the search sheet (`GET /categories`): fuel, parking, hospital, and so on. */
class Category(val id: String, val label: String, val count: Int)

/** Place search and the same Valhalla server, over plain HTTP. Blocking: call from Dispatchers.IO. */
object SearchClient {

    fun searchUrl(base: String, query: String, lat: Double?, lon: Double?): String = buildString {
        append(ServerSettings.normalize(base))
        append("/search?q=").append(URLEncoder.encode(query, "UTF-8"))
        if (lat != null && lon != null) append("&lat=").append(lat).append("&lon=").append(lon)
        append("&limit=8")
    }

    /** Results, best first. Throws [RouteClient.RouteException] with a readable message on failure. */
    fun categoryUrl(base: String, id: String, lat: Double?, lon: Double?, limit: Int = 8): String = buildString {
        append(ServerSettings.normalize(base))
        append("/search?category=").append(URLEncoder.encode(id, "UTF-8"))
        if (lat != null && lon != null) append("&lat=").append(lat).append("&lon=").append(lon)
        append("&limit=").append(limit)
    }

    fun categoriesUrl(base: String): String = ServerSettings.normalize(base) + "/categories"

    /** Nearest places of one category, best first. Throws like [search]. */
    fun byCategory(base: String, id: String, lat: Double?, lon: Double?): List<PlaceResult> {
        val body = get(categoryUrl(base, id, lat, lon))
        return try {
            parse(body)
        } catch (e: Exception) {
            throw RouteClient.RouteException("The search server sent something unexpected", e)
        }
    }

    /**
     * The server's category list. An older server has no `/categories`, so callers get the built-in
     * list instead of an error — the chips still work, they just may not match what that server knows.
     */
    fun categories(base: String): List<Category> = try {
        val body = get(categoriesUrl(base))
        val arr = JSONObject(body).getJSONArray("categories")
        (0 until arr.length()).map { i ->
            val o = arr.getJSONObject(i)
            Category(o.getString("id"), o.getString("label"), o.optInt("count"))
        }
    } catch (e: Exception) {
        DEFAULT_CATEGORIES
    }

    /** Shown until the server answers, and forever if it is an older build without `/categories`. */
    val DEFAULT_CATEGORIES = listOf(
        Category("fuel", "Fuel", 0),
        Category("food", "Food", 0),
        Category("cafe", "Cafe", 0),
        Category("parking", "Parking", 0),
        Category("atm", "ATM", 0),
        Category("pharmacy", "Pharmacy", 0),
        Category("hospital", "Hospital", 0),
        Category("mall", "Mall", 0),
        Category("hotel", "Hotel", 0),
        Category("prayer", "Prayer room", 0),
        Category("ev", "EV charging", 0),
        Category("toilets", "Toilets", 0),
    )

    fun search(base: String, query: String, lat: Double?, lon: Double?): List<PlaceResult> {
        if (query.isBlank()) return emptyList()
        val body = get(searchUrl(base, query, lat, lon))
        return try {
            parse(body)
        } catch (e: Exception) {
            throw RouteClient.RouteException("The search server sent something unexpected", e)
        }
    }

    /** Parses the search server's JSON without touching the network (unit-tested). */
    internal fun parse(body: String): List<PlaceResult> {
        val arr = JSONObject(body).getJSONArray("results")
        return (0 until arr.length()).map { i ->
            val o = arr.getJSONObject(i)
            PlaceResult(o.getString("name"), o.getDouble("lat"), o.getDouble("lon"), o.optString("kind"), o.optInt("dist_m"))
        }
    }

    private fun get(url: String): String {
        val c = URL(url).openConnection() as HttpURLConnection
        try {
            c.connectTimeout = 5_000
            c.readTimeout = 10_000
            c.setRequestProperty("Accept", "application/json")
            c.setRequestProperty("User-Agent", "Aize-Android/0.1")
            val code = try { c.responseCode } catch (e: IOException) {
                throw RouteClient.RouteException("Cannot reach the server (${e.javaClass.simpleName})", e)
            }
            val text = (if (code in 200..299) c.inputStream else c.errorStream)?.bufferedReader()?.use { it.readText() }.orEmpty()
            if (code !in 200..299) throw RouteClient.RouteException(RouteClient.serverMessage(text) ?: "Search error $code")
            return text
        } finally {
            c.disconnect()
        }
    }
}
