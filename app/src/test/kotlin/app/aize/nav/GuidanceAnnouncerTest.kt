package app.aize.nav

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

/** Contract for the voice: what is said, and when. The service only feeds it positions. */
class GuidanceAnnouncerTest {

    /** A straight 1 km route with a turn at 300 m and the arrival maneuver at the end. */
    private fun route(): Route {
        val lat = DoubleArray(3) { 3.0 }
        val lon = doubleArrayOf(101.0, 101.005, 101.010)   // ~0.005 deg ≈ 555 m per hop
        val path = RoutePath(lat, lon)
        val turn = Maneuver("Turn right onto Jalan Ampang", 10, 1, 0.0, "Jalan Ampang")
        val arrive = Maneuver("You have arrived", 4, 2, 0.0, null)
        return Route(path, listOf(turn, arrive), durationSeconds = 60.0)
    }

    @Test
    fun `announces the turn once when the prepare distance is reached`() {
        val r = route()
        val a = GuidanceAnnouncer()
        val turnAt = r.path.cumulative[1]
        val first = a.update(r, turnAt - 140.0, speedMps = 15.0, nowMs = 0)   // inside the 150 m prepare window
        assertNotNull(first)
        assertEquals(GuidanceAnnouncer.Kind.PREPARE, first!!.kind)
        assertTrue(first.text.contains("Jalan Ampang"))
        assertNull("the same turn is not announced twice", a.update(r, turnAt - 130.0, 15.0, 1_000))
    }

    @Test
    fun `the prepare distance grows with speed and never drops below the base`() {
        val a = GuidanceAnnouncer()
        assertEquals(150.0, a.prepareDistance(0.0), 1e-9)
        assertEquals(150.0, a.prepareDistance(10.0), 1e-9)   // 10 m/s * 8 s = 80 m < 150 m
        assertEquals(240.0, a.prepareDistance(30.0), 1e-9)   // 30 m/s * 8 s = 240 m
    }

    @Test
    fun `a fast driver is warned earlier than a slow one`() {
        val r = route()
        val turnAt = r.path.cumulative[1]
        val fast = GuidanceAnnouncer()
        val slow = GuidanceAnnouncer()
        // 200 m before the turn: 30 m/s (108 km/h) should already have been warned, 10 m/s should not
        assertNotNull(fast.update(r, turnAt - 200.0, speedMps = 30.0, nowMs = 0))
        assertNull(slow.update(r, turnAt - 200.0, speedMps = 10.0, nowMs = 0))
    }

    @Test
    fun `the imminent prompt fires at forty-five metres and respects the quiet gap`() {
        val r = route()
        val turnAt = r.path.cumulative[1]
        val a = GuidanceAnnouncer()
        a.update(r, turnAt - 160.0, speedMps = 20.0, nowMs = 0)                    // prepare
        assertNull("too soon after the prepare prompt", a.update(r, turnAt - 44.0, 20.0, 1_000))
        val now = a.update(r, turnAt - 44.0, 20.0, 10_000)                          // gap elapsed
        assertNotNull(now)
        assertEquals(GuidanceAnnouncer.Kind.IMMINENT, now!!.kind)
        assertTrue(now.text.startsWith("In 4"))
    }

    @Test
    fun `announces arrival once, within thirty metres of the end`() {
        val r = route()
        val a = GuidanceAnnouncer()
        assertNull("the arrival pseudo-maneuver is not announced early", a.update(r, r.path.lengthMeters - 100.0, 10.0, 0))
        val arrived = a.update(r, r.path.lengthMeters - 10.0, 10.0, 1_000)
        assertNotNull(arrived)
        assertEquals(GuidanceAnnouncer.Kind.ARRIVED, arrived!!.kind)
        assertNull("arrival is not repeated", a.update(r, r.path.lengthMeters, 10.0, 60_000))
    }

    @Test
    fun `reset makes the route speakable again, as a new route should be`() {
        val r = route()
        val a = GuidanceAnnouncer()
        val turnAt = r.path.cumulative[1]
        assertNotNull(a.update(r, turnAt - 140.0, 15.0, 0))
        a.reset()
        assertNotNull(a.update(r, turnAt - 140.0, 15.0, 1_000))
    }
}
