package app.aize.nav

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class OffRouteTest {
    // a straight 1.1 km route heading north along lon 101.7
    private val path = RoutePath(doubleArrayOf(3.100, 3.105, 3.110), doubleArrayOf(101.7, 101.7, 101.7))

    @Test fun `a point on the route projects onto it`() {
        val p = path.project(3.1025, 101.7)
        assertTrue(p.offRoute < 0.5)
        assertEquals(path.lengthMeters / 4, p.along, 2.0)
    }

    @Test fun `a point east of the route is that many metres off`() {
        val p = path.project(3.1025, 101.7 + 100.0 / (111_320.0 * Math.cos(Math.toRadians(3.1025))))
        assertEquals(100.0, p.offRoute, 1.0)
        assertEquals(0, p.segment)
    }

    @Test fun `windowed search avoids jumping to a later pass of a looping route`() {
        // goes north then back south over the same road
        val loop = RoutePath(doubleArrayOf(3.10, 3.11, 3.10), doubleArrayOf(101.7, 101.7, 101.7))
        val early = loop.project(3.105, 101.7, fromSegment = 0, window = 0)
        val late = loop.project(3.105, 101.7, fromSegment = 1, window = 0)
        assertEquals(0, early.segment); assertEquals(1, late.segment)
        assertTrue(late.along > early.along)
    }

    @Test fun `points beyond the ends clamp to the end`() {
        assertEquals(0.0, path.project(3.0, 101.7).along, 0.001)
        assertEquals(path.lengthMeters, path.project(3.2, 101.7).along, 0.001)
    }

    @Test fun `one noisy fix does not re-route but three in a row do`() {
        val d = OffRouteDetector()
        assertFalse(d.update(80.0, 0)); assertFalse(d.update(5.0, 1000))      // blip resets
        assertFalse(d.update(80.0, 2000)); assertFalse(d.update(80.0, 3000))
        assertTrue(d.update(80.0, 4000))
    }

    @Test fun `re-routes are rate limited`() {
        val d = OffRouteDetector()
        repeat(2) { d.update(80.0, it * 1000L) }
        assertTrue(d.update(80.0, 2000))                                       // first re-route
        assertFalse(d.update(80.0, 3000)); assertFalse(d.update(80.0, 4000))
        assertFalse(d.update(80.0, 5000))                                      // 3 strikes, but inside the 15 s cooldown
        assertTrue(d.update(80.0, 17_000))                                     // cooldown over and still off route
    }
}
