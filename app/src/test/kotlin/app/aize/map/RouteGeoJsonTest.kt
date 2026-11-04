package app.aize.map

import app.aize.nav.Route
import app.aize.nav.RoutePath
import org.json.JSONObject
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * The alternatives are drawn from a GeoJSON string, and MapLibre does not complain when that string is
 * wrong: it simply draws nothing. These tests parse it the way the renderer would, so a broken builder
 * fails here instead of producing an empty map on a phone.
 */
class RouteGeoJsonTest {
    private fun route(vararg latLon: Double): Route {
        val lat = latLon.filterIndexed { i, _ -> i % 2 == 0 }.toDoubleArray()
        val lon = latLon.filterIndexed { i, _ -> i % 2 == 1 }.toDoubleArray()
        return Route(RoutePath(lat, lon), emptyList(), durationSeconds = 600.0)
    }

    @Test
    fun `no routes is a valid but empty collection`() {
        val o = JSONObject(RouteGeoJson.alternatives(emptyList()))
        assertEquals("FeatureCollection", o.getString("type"))
        assertEquals(0, o.getJSONArray("features").length())
    }

    @Test
    fun `every route becomes one line of the multi line string`() {
        val a = route(3.1343, 101.6862, 3.1578, 101.7118)
        val b = route(3.1343, 101.6862, 3.1400, 101.7000, 3.1578, 101.7118)
        val o = JSONObject(RouteGeoJson.alternatives(listOf(a, b)))
        val lines = o.getJSONArray("features").getJSONObject(0)
            .getJSONObject("geometry").getJSONArray("coordinates")
        assertEquals(2, lines.length())
        assertEquals(2, lines.getJSONArray(0).length())
        assertEquals(3, lines.getJSONArray(1).length())
    }

    @Test
    fun `coordinates are lon,lat in that order`() {
        // GeoJSON is x,y — swapping these draws the route in the Gulf of Guinea, which is a real bug people ship
        val o = JSONObject(RouteGeoJson.alternatives(listOf(route(3.1343, 101.6862, 3.1578, 101.7118))))
        val first = o.getJSONArray("features").getJSONObject(0).getJSONObject("geometry")
            .getJSONArray("coordinates").getJSONArray(0).getJSONArray(0)
        assertEquals(101.6862, first.getDouble(0), 1e-9)
        assertEquals(3.1343, first.getDouble(1), 1e-9)
    }

    @Test
    fun `a three route set stays one feature`() {
        val routes = (1..3).map { route(3.1 + it / 100.0, 101.6, 3.2, 101.7 + it / 100.0) }
        val o = JSONObject(RouteGeoJson.alternatives(routes))
        assertEquals(1, o.getJSONArray("features").length())
        assertEquals(3, o.getJSONArray("features").getJSONObject(0)
            .getJSONObject("geometry").getJSONArray("coordinates").length())
    }

    @Test
    fun `the string is compact enough to hand to the renderer`() {
        val routes = (1..3).map { route(3.1, 101.6, 3.2, 101.7) }
        val s = RouteGeoJson.alternatives(routes)
        assertTrue("no newlines: $s", !s.contains('\n'))
        assertTrue("starts with an object", s.startsWith("{"))
    }
}
