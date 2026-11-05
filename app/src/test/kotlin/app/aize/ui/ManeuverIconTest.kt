package app.aize.ui

import app.aize.nav.Maneuver
import org.junit.Assert.assertEquals
import org.junit.Test

/** Valhalla's manoeuvre numbers, pinned so a server change or a typo cannot silently swap left for right. */
class ManeuverIconTest {

    private fun m(type: Int, instruction: String = "") = Maneuver(instruction, type, 0, 100.0, null)

    @Test
    fun theFourWaysToTurnAreDistinct() {
        assertEquals(ManeuverIcons.LEFT, ManeuverIcons.forType(15))
        assertEquals(ManeuverIcons.RIGHT, ManeuverIcons.forType(10))
        assertEquals(ManeuverIcons.SLIGHT_LEFT, ManeuverIcons.forType(16))
        assertEquals(ManeuverIcons.SLIGHT_RIGHT, ManeuverIcons.forType(9))
        assertEquals(ManeuverIcons.SHARP_LEFT, ManeuverIcons.forType(14))
        assertEquals(ManeuverIcons.SHARP_RIGHT, ManeuverIcons.forType(11))
    }

    @Test
    fun uTurnsAreNotTurns() {
        // 12 and 13 are the U-turns; a plain `when (type) { 12 -> LEFT }` would draw a left turn for both
        assertEquals(ManeuverIcons.UTURN, ManeuverIcons.forType(12))
        assertEquals(ManeuverIcons.UTURN, ManeuverIcons.forType(13))
    }

    @Test
    fun arrivingIsItsOwnGlyph() {
        assertEquals(ManeuverIcons.ARRIVE, ManeuverIcons.forType(4))
        assertEquals(ManeuverIcons.STRAIGHT, ManeuverIcons.forType(1))
        assertEquals(ManeuverIcons.ROUNDABOUT, ManeuverIcons.forType(26))
        assertEquals(ManeuverIcons.MERGE, ManeuverIcons.forType(25))
    }

    @Test
    fun anUnknownTypeFallsBackToTheWords() {
        // a newer server sending a type this build has never seen must still draw something right
        assertEquals(ManeuverIcons.LEFT, ManeuverIcons.forManeuver(m(99, "Turn left onto Jalan Ampang")))
        assertEquals(ManeuverIcons.RIGHT, ManeuverIcons.forManeuver(m(99, "Turn right onto Jalan Pudu")))
    }

    @Test
    fun theStreetNameDoesNotChooseTheTurn() {
        // "Turn right onto Jalan Left" is a right turn
        assertEquals(ManeuverIcons.RIGHT, ManeuverIcons.forInstruction("Turn right onto Jalan Left"))
        assertEquals(ManeuverIcons.LEFT, ManeuverIcons.forInstruction("Turn left onto Jalan Right"))
        assertEquals(ManeuverIcons.ROUNDABOUT, ManeuverIcons.forInstruction("Enter the roundabout and take the 2nd exit"))
    }

    @Test
    fun aKnownTypeIsNotOverruledByTheText() {
        // the number is the authority; the words are only a fallback
        assertEquals(ManeuverIcons.LEFT, ManeuverIcons.forManeuver(m(15, "Turn right onto Jalan Ampang")))
    }
}
