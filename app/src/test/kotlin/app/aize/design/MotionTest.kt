package app.aize.design

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * "Remove animations" is an accessibility setting, and honouring it is not optional: the duration must become
 * zero, not merely shorter, or the app keeps moving for someone who asked it to stop.
 */
class MotionTest {
    @Test
    fun `animations run at the normal scale`() {
        assertTrue(Motion.enabled(1f))
        assertTrue(Motion.enabled(0.5f))
    }

    @Test
    fun `zero scale means no motion`() {
        assertFalse(Motion.enabled(0f))
        assertEquals(0, Motion.durationMs(700, 0f))
    }

    @Test
    fun `configured duration is used when motion is allowed`() {
        assertEquals(700, Motion.durationMs(700, 1f))
        assertEquals(700, Motion.durationMs(700, 2f))   // a longer system scale does not double our choreography
    }

    @Test
    fun `tokens describe a sane choreography`() {
        // every step of the choreography should be ordered: instant < fast < base < moderate < slow < deliberate
        val ladder = listOf(
            AizeMotion.INSTANT_MS, AizeMotion.FAST_MS, AizeMotion.BASE_MS,
            AizeMotion.MODERATE_MS, AizeMotion.SLOW_MS, AizeMotion.DELIBERATE_MS,
        )
        assertEquals(ladder.sorted(), ladder)
        assertTrue(AizeSprings.SETTLE_DAMPING_RATIO in 0f..1f)
        assertTrue(AizeSprings.SETTLE_STIFFNESS > 0f)
    }
}
