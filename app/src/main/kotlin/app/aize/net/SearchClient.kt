package app.aize.net

import org.json.JSONObject
import java.io.IOException
import java.net.HttpURLConnection
import java.net.URL
import java.net.URLEncoder

/** A place from the search service (`GET /search`). */
class PlaceResult(val name: String, val lat: Double, val lon: Double, val kind: String, val distanceMeters: Int)

/** Place search and the same Valhalla server, over plain HTTP. Blocking: call from Dispatchers.IO. */
object SearchClient {

    fun searchUrl(base: String, query: String, lat: Double?, lon: Double?): String = buildString {
        append(ServerSettings.normalize(base))
        append("/search?q=").append(URLEncoder.encode(query, "UTF-8"))
        if (lat != null && lon != null) append("&lat=").append(lat).append("&lon=").append(lon)
        append("&limit=8")
    }

    /** Results, best first. Throws [RouteClient.RouteException] with a readable message on failure. */
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
