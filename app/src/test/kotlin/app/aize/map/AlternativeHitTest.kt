package app.aize.map

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

class AlternativeHitTest {

    private fun path(vararg xy: Float) = xy

    @Test
    fun `tap on a segment midpoint hits that route`() {
        // a straight horizontal line from (0,0) to (100,0); the tap sits on it
        val d = AlternativeHit.distanceToPath(path(0f, 0f, 100f, 0f), 50f, 0f)
        assertEquals(0.0, d, 1e-9)
    }

    @Test
    fun `distance is measured to the segment, not to the nearest vertex`() {
        // tap 3 px above the middle of a 100 px segment: no vertex is anywhere near it
        val d = AlternativeHit.distanceToPath(path(0f, 0f, 100f, 0f), 50f, 3f)
        assertEquals(9.0, d, 1e-6)
    }

    @Test
    fun `a tap beyond the end of a segment measures to the endpoint`() {
        // 4 px past the end and 3 px off the line: sqrt(16 + 9) = 5
        val d = AlternativeHit.distanceToPath(path(0f, 0f, 100f, 0f), 104f, 3f)
        assertEquals(25.0, d, 1e-6)
    }

    @Test
    fun `the nearer of two parallel routes wins`() {
        val near = path(0f, 0f, 100f, 0f)
        val far = path(0f, 20f, 100f, 20f)
        assertEquals(1, AlternativeHit.nearest(listOf(far, near), 50f, 4f, tolerancePx = 10f) ?: -1)
        assertEquals(0, AlternativeHit.nearest(listOf(near, far), 50f, 4f, tolerancePx = 10f) ?: -1)
    }

    @Test
    fun `a tap outside the tolerance selects nothing`() {
        val a = path(0f, 0f, 100f, 0f)
        val b = path(0f, 40f, 100f, 40f)
        assertNull(AlternativeHit.nearest(listOf(a, b), 50f, 200f, tolerancePx = 26f))
    }

    @Test
    fun `an exact tie goes to the first path, which is the one the chooser lists first`() {
        val same = path(0f, 0f, 100f, 0f)
        assertEquals(0, AlternativeHit.nearest(listOf(same, same.copyOf()), 50f, 0f, tolerancePx = 26f) ?: -1)
    }

    @Test
    fun `a path with fewer than two points is never hit`() {
        assertEquals(Double.MAX_VALUE, AlternativeHit.distanceToPath(FloatArray(2), 0f, 0f), 0.0)
        assertNull(AlternativeHit.nearest(listOf(FloatArray(0)), 0f, 0f, tolerancePx = 26f))
    }

    @Test
    fun `decimate keeps the ends and stays under the cap`() {
        val n = 1000
        val xs = FloatArray(n) { it.toFloat() }
        val ys = FloatArray(n) { 0f }
        val p = AlternativeHit.decimate(xs, ys, maxPoints = 100)
        val count = p.size / 2
        assertTrue(count <= 101)                 // cap, plus the destination vertex if the stride does not land on it
        assertEquals(0f, p[0], 0f)
        assertEquals(999f, p[p.size - 2], 0f)            // the last point is always the route's end
    }

    @Test
    fun `decimate of a short path keeps every point`() {
        val p = AlternativeHit.decimate(floatArrayOf(0f, 10f, 20f), floatArrayOf(0f, 10f, 20f), maxPoints = 256)
        assertEquals(6, p.size)
    }

    @Test
    fun `a zero-length segment still yields a finite distance`() {
        val d = AlternativeHit.distanceToPath(path(5f, 5f, 5f, 5f), 8f, 9f)
        assertEquals(25.0, d, 1e-9)
    }
}
