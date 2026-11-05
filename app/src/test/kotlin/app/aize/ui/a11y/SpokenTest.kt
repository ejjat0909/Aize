package app.aize.ui.a11y

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class SpokenTest {

    @Test
    fun theBannerSaysTheDistanceFirstAndTheInstructionOnce() {
        val s = Spoken.banner("52 m", "Bear left onto Jalan Stesen Sentral.", "then Make a left U-turn", null)
        assertTrue("starts with the number a driver wants", s.startsWith("52 m."))
        assertEquals(
            "52 m. Bear left onto Jalan Stesen Sentral. then Make a left U-turn.",
            s,
        )
        // a full stop inside the sentence would be read as a pause in the wrong place
        assertFalse(s.contains(".."))
    }

    @Test
    fun theBannerSurvivesMissingParts() {
        assertEquals("Arrived. You have arrived.", Spoken.banner("Arrived", "You have arrived.", null, null))
    }

    @Test
    fun aRouteSaysWhichOneItIsBeforeHowFastItIs() {
        val s = MenuOf3()
        assertTrue("a screen reader cannot point at a row", s.startsWith("Route 2 of 3."))
        assertTrue(s.contains("9.1 km, 21 minutes"))
        assertTrue(s.contains("via Jalan Tun Sambanthan"))
        assertTrue(s.contains("fastest"))
        assertTrue("the badges are said as words, not shouted", s.contains("fastest, tolls"))
        assertTrue(s.contains("shown on the map"))
    }

    private fun MenuOf3() = Spoken.route(
        index = 2,
        count = 3,
        distance = "9.1 km",
        minutes = 21,
        via = "Jalan Tun Sambanthan",
        badges = listOf("On map", "Fastest", "Tolls"),
        selected = true,
    )

    @Test
    fun oneMinuteIsNotOneMinutes() {
        val s = Spoken.route(1, 1, "300 m", 1, null, emptyList(), false)
        assertTrue("reads \"$s\"", s.contains("1 minute."))
        assertFalse(s.contains("1 minutes"))
    }

    @Test
    fun aRouteThatIsNotOnTheMapDoesNotClaimToBe() {
        val s = Spoken.route(1, 2, "4.2 km", 9, null, emptyList(), false)
        assertFalse(s.contains("shown on the map"))
        assertEquals("Route 1 of 2. 4.2 km, 9 minutes.", s)
    }

    @Test
    fun aPlaceIsNamedBeforeItIsDescribed() {
        assertEquals("Shell Ipoh 3. Fuel, 1.3 km away, saved.", Spoken.place("Shell Ipoh 3", "Fuel", "1.3 km", true))
        assertEquals("KLCC. Mall.", Spoken.place("KLCC", "Mall", null, false))
    }
}
