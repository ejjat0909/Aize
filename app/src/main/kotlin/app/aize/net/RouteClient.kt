package app.aize.net

import app.aize.nav.Route
import org.json.JSONArray
import org.json.JSONObject
import java.io.IOException
import java.net.HttpURLConnection
import java.net.URL
import java.net.URLEncoder

/** Talks to a Valhalla server (`GET /route?json=…`, `GET /status`). Blocking: call from Dispatchers.IO. */
object RouteClient {
    class RouteException(message: String, cause: Throwable? = null) : Exception(message, cause)

    fun routeUrl(
        base: String,
        fromLat: Double,
        fromLon: Double,
        toLat: Double,
        toLon: Double,
        alternates: Int = 0,
    ): String {
        val req = JSONObject()
            .put("locations", JSONArray()
                .put(JSONObject().put("lat", fromLat).put("lon", fromLon))
                .put(JSONObject().put("lat", toLat).put("lon", toLon)))
            .put("costing", "auto")
            .put("directions_options", JSONObject().put("units", "kilometers").put("language", "en-US"))
        if (alternates > 0) req.put("alternates", alternates)
        return ServerSettings.normalize(base) + "/route?json=" + URLEncoder.encode(req.toString(), "UTF-8")
    }

    fun route(base: String, fromLat: Double, fromLon: Double, toLat: Double, toLon: Double): Route =
        routes(base, fromLat, fromLon, toLat, toLon, alternates = 0).first()

    /**
     * Every route the server is willing to offer, best first. Valhalla returns the chosen route plus up to
     * [alternates] others; a server that does not know the parameter still answers, so this never fails just
     * because alternates are unsupported.
     */
    fun routes(
        base: String,
        fromLat: Double,
        fromLon: Double,
        toLat: Double,
        toLon: Double,
        alternates: Int = 2,
    ): List<Route> {
        val url = routeUrl(base, fromLat, fromLon, toLat, toLon, alternates)
        val body = try {
            get(url, readTimeoutMs = 20_000)
        } catch (e: RouteException) {
            // "alternates" is not universal: retry plainly rather than failing the whole trip
            if (alternates > 0 && e.message?.contains("alternate", ignoreCase = true) == true) {
                get(routeUrl(base, fromLat, fromLon, toLat, toLon, 0), readTimeoutMs = 20_000)
            } else {
                throw e
            }
        }
        return try {
            parseRoutes(body)
        } catch (e: Exception) {
            throw RouteException("The server answered, but not with a route", e)
        }
    }

    /** The primary trip plus any alternates, in the order the server ranked them. */
    internal fun parseRoutes(body: String): List<Route> {
        val root = JSONObject(body)
        val list = arrayListOf(Route.fromValhalla(body))
        val alts = root.optJSONArray("alternates") ?: return list
        for (i in 0 until alts.length()) {
            val alt = alts.optJSONObject(i) ?: continue
            runCatching { Route.fromValhalla(alt.toString()) }.onSuccess { list += it }
        }
        return list
    }

    /** Returns the server's version string, or throws. */
    fun status(base: String): String {
        val json = JSONObject(get(ServerSettings.normalize(base) + "/status", readTimeoutMs = 8_000))
        return "Valhalla " + json.optString("version", "?")
    }

    private fun get(url: String, readTimeoutMs: Int): String {
        val c = try { URL(url).openConnection() as HttpURLConnection } catch (e: Exception) { throw RouteException("Not a valid server address", e) }
        try {
            c.connectTimeout = 6_000
            c.readTimeout = readTimeoutMs
            c.setRequestProperty("Accept", "application/json")
            c.setRequestProperty("User-Agent", "Aize-Android/0.1")
            val code = try { c.responseCode } catch (e: IOException) { throw RouteException("Cannot reach the server (${e.javaClass.simpleName}: ${e.message})", e) }
            val stream = if (code in 200..299) c.inputStream else c.errorStream
            val text = stream?.bufferedReader()?.use { it.readText() }.orEmpty()
            if (code !in 200..299) throw RouteException(serverMessage(text) ?: "Server error $code")
            return text
        } finally {
            c.disconnect()
        }
    }

    /** Valhalla errors look like {"error_code":171,"error":"No suitable edges near location","status_code":400}. */
    internal fun serverMessage(text: String): String? = runCatching { JSONObject(text).optString("error").takeIf { it.isNotBlank() } }.getOrNull()
}
