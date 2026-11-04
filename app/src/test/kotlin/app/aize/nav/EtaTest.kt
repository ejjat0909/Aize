package app.aize.nav

import java.time.ZoneId
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class EtaTest {
    private val utc = ZoneId.of("UTC")

    @Test
    fun `the first estimate is published as-is`() {
        val eta = EtaEngine()
        assertEquals(600.0, eta.smooth(600.0), 0.001)
    }

    @Test
    fun `small movements do not move the arrival clock`() {
        val eta = EtaEngine()
        eta.smooth(600.0)
        // 20 s is under the 30 s floor and under 5 % of 600 s, so it is noise
        assertEquals(600.0, eta.smooth(580.0), 0.001)
        assertEquals(600.0, eta.smooth(620.0), 0.001)
    }

    @Test
    fun `a thirty second move is published`() {
        val eta = EtaEngine()
        eta.smooth(600.0)
        assertEquals(570.0, eta.smooth(570.0), 0.001)
    }

    @Test
    fun `five percent of a long trip is enough on its own`() {
        val eta = EtaEngine()
        eta.smooth(7_200.0)          // two hours
        assertEquals(6_840.0, eta.smooth(6_840.0), 0.001)   // 5 % exactly
    }

    @Test
    fun `reset forgets the published value`() {
        val eta = EtaEngine()
        eta.smooth(600.0)
        eta.reset()
        assertEquals(120.0, eta.smooth(120.0), 0.001)
    }

    @Test
    fun `free flow estimate scales with the distance left`() {
        val route = routeWith(totalMetres = 10_000.0, seconds = 600.0)
        assertEquals(600.0, EtaEngine.estimate(route, 0.0, 0.0), 1.0)
        assertEquals(300.0, EtaEngine.estimate(route, 5_000.0, 0.0), 1.0)
        assertEquals(0.0, EtaEngine.estimate(route, 10_000.0, 0.0), 0.01)
    }

    @Test
    fun `a crawling car is ignored and a fast one is clamped`() {
        val route = routeWith(totalMetres = 10_000.0, seconds = 600.0)
        val standing = EtaEngine.estimate(route, 0.0, 0.5)     // crawling: free flow wins
        assertEquals(600.0, standing, 1.0)

        val flying = EtaEngine.estimate(route, 0.0, 60.0)      // 216 km/h: live time would be 167 s
        assertTrue("clamped to 40 % of free flow, was $flying", flying >= 360.0 - 0.01)
    }

    @Test
    fun `minutes and hours read like a person would say them`() {
        assertEquals("1 min", EtaEngine.formatMinutes(10.0))
        assertEquals("12 min", EtaEngine.formatMinutes(12 * 60.0))
        assertEquals("59 min", EtaEngine.formatMinutes(59 * 60.0))
        assertEquals("1 h", EtaEngine.formatMinutes(60 * 60.0))
        assertEquals("1 h 05 min", EtaEngine.formatMinutes(65 * 60.0))
    }

    @Test
    fun `arrival clock is formatted in the given zone`() {
        val now = 0L                                  // 1970-01-01T00:00:00Z
        assertEquals("12:10 AM", EtaEngine.formatArrival(now, 600.0, utc))
        assertEquals("1:00 PM", EtaEngine.formatArrival(now, 13 * 3600.0, utc))
        assertEquals("12 min · 12:12 AM", EtaEngine.summary(720.0, now, utc))
    }

    private fun routeWith(totalMetres: Double, seconds: Double): Route {
        // A straight two-point line, which is all the estimate needs: a length and a duration.
        val path = RoutePath(doubleArrayOf(3.13, 3.13), doubleArrayOf(101.68, 101.68 + totalMetres / 111_320.0))
        return Route(path, emptyList(), seconds)
    }
}
