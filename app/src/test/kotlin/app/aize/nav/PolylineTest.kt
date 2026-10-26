package app.aize.nav

import org.junit.Assert.assertArrayEquals
import org.junit.Assert.assertEquals
import org.junit.Assert.assertThrows
import org.junit.Test

class PolylineTest {
    @Test
    fun `decodes the canonical precision-5 example from the polyline spec`() {
        // https://developers.google.com/maps/documentation/utilities/polylinealgorithm
        val d = Polyline.decode("_p~iF~ps|U_ulLnnqC_mqNvxq`@", precision = 5)
        assertArrayEquals(doubleArrayOf(38.5, 40.7, 43.252), d.lat, 1e-9)
        assertArrayEquals(doubleArrayOf(-120.2, -120.95, -126.453), d.lon, 1e-9)
    }

    @Test
    fun `round trip at precision 6 with negative coordinates and long jumps`() {
        val lat = doubleArrayOf(3.134300, 3.134301, -33.868820, 89.999999, 0.0, -0.000001)
        val lon = doubleArrayOf(101.686200, 101.686199, 151.209296, -179.999999, 0.0, 179.999999)
        val d = Polyline.decode(Polyline.encode(lat, lon))
        assertArrayEquals(lat, d.lat, 1e-9)
        assertArrayEquals(lon, d.lon, 1e-9)
    }

    @Test
    fun `empty string is an empty line and a truncated one is rejected`() {
        assertEquals(0, Polyline.decode("").size)
        assertThrows(IllegalArgumentException::class.java) { Polyline.decode("_p~iF~ps|U_") }
    }

    @Test
    fun `grows its buffers for long routes`() {
        val n = 5000
        val lat = DoubleArray(n) { 3.0 + it * 1e-5 }
        val lon = DoubleArray(n) { 101.0 + it * 2e-5 }
        assertEquals(n, Polyline.decode(Polyline.encode(lat, lon)).size)
    }
}
