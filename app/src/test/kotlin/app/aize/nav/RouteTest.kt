package app.aize.nav

import java.io.File
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertTrue
import org.junit.Test

class RouteTest {
    /** Unit tests run with the module directory as the working directory. */
    private fun fixture(): String = File("src/main/assets/route/kl-sentral-to-klcc.valhalla.json").readText()

    @Test
    fun `fixture endpoints are where the request asked and the length matches Valhalla's own summary`() {
        val r = Route.fromValhallaFixture(fixture())
        val p = r.path
        // request: KL Sentral (3.1343, 101.6862) -> KLCC (3.1579, 101.7116); the router snaps to the road network
        assertTrue(RoutePath.haversine(p.lat[0], p.lon[0], 3.1343, 101.6862) < 80.0)
        assertTrue(RoutePath.haversine(p.lat[p.size - 1], p.lon[p.size - 1], 3.1579, 101.7116) < 80.0)
        assertEquals(9075.0, p.lengthMeters, 9075.0 * 0.01)            // summary.length = 9.075 km, within 1 %
        assertEquals(14, r.maneuvers.size)
        assertEquals(0, r.maneuvers.first().beginShapeIndex)
    }

    @Test
    fun `pointAt is continuous, monotone and stays on the route`() {
        val p = Route.fromValhallaFixture(fixture()).path
        var prev = p.pointAt(0.0)
        var d = 0.0
        while (d < p.lengthMeters) {
            d += 25.0
            val cur = p.pointAt(d)
            // 25 m of route can never be more than 25 m of crow-flies distance (+ rounding)
            assertTrue(RoutePath.haversine(prev.lat, prev.lon, cur.lat, cur.lon) <= 25.5)
            assertTrue(cur.heading in 0.0..360.0)
            prev = cur
        }
        val end = p.pointAt(p.lengthMeters + 1000.0)                    // clamped
        assertEquals(p.lat[p.size - 1], end.lat, 1e-9)
    }

    @Test
    fun `guidance advances through every maneuver in order`() {
        val r = Route.fromValhallaFixture(fixture())
        val seen = LinkedHashSet<String>()
        var d = 0.0
        while (d <= r.path.lengthMeters) {
            val g = r.guidanceAt(d)
            assertTrue("distance to next must be >= 0", g.metersToNext >= 0.0)
            seen += g.current.instruction
            d += 10.0
        }
        seen += r.guidanceAt(r.path.lengthMeters).current.instruction       // the loop steps by 10 m and never lands exactly on the end
        assertEquals(r.maneuvers.map { it.instruction }.toSet(), seen)
        assertNotNull(r.guidanceAt(0.0).next)
        assertEquals(null, r.guidanceAt(r.path.lengthMeters).next)
    }

    @Test
    fun `angle helpers are wrap-safe`() {
        assertEquals(20.0, RoutePath.angleDelta(350.0, 10.0), 1e-9)
        assertEquals(-20.0, RoutePath.angleDelta(10.0, 350.0), 1e-9)
        assertEquals(0.0, RoutePath.smoothAngle(350.0, 10.0, 1.0) - 10.0, 1e-9)
        val s = RoutePath.smoothAngle(350.0, 10.0, 0.5)
        assertEquals(0.0, RoutePath.angleDelta(0.0, s), 1e-9)          // halfway between 350 and 10 is 0, not 180
        assertEquals(90.0, RoutePath.bearing(0.0, 0.0, 0.0, 1.0), 1e-6) // due east
        assertEquals(0.0, RoutePath.bearing(0.0, 0.0, 1.0, 0.0), 1e-6)  // due north
    }
}
