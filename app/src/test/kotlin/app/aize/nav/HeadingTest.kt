package app.aize.nav

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * The puck turns with the car. GPS bearings arrive about once a second and can jump, so they are eased — but
 * easing a compass angle by averaging numbers is wrong at the wrap: 350° and 10° are 20° apart, not 340°.
 */
class HeadingTest {
    @Test
    fun `difference across north is short, not long`() {
        assertEquals(20.0, Heading.shortestDelta(350.0, 10.0), 1e-9)
        assertEquals(-20.0, Heading.shortestDelta(10.0, 350.0), 1e-9)
    }

    @Test
    fun `difference is never more than half a turn`() {
        for (from in 0..350 step 10) for (to in 0..350 step 10) {
            assertTrue("$from -> $to", kotlin.math.abs(Heading.shortestDelta(from.toDouble(), to.toDouble())) <= 180.0)
        }
    }

    @Test
    fun `smoothing turns the short way round`() {
        // half way from 350 to 10 must be 0, not 180
        assertEquals(0.0, Heading.smooth(350.0, 10.0, 0.5), 1e-9)
    }

    @Test
    fun `smoothing stays in range and converges`() {
        var h = 0.0
        repeat(20) { h = Heading.smooth(h, 90.0, 0.35) }
        assertEquals(90.0, h, 0.5)
        assertTrue(h in 0.0..360.0)
    }

    @Test
    fun `alpha one snaps and alpha zero holds`() {
        assertEquals(123.0, Heading.smooth(0.0, 123.0, 1.0), 1e-9)
        assertEquals(0.0, Heading.smooth(0.0, 123.0, 0.0), 1e-9)
    }
}
