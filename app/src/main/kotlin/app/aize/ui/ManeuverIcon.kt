package app.aize.ui

import app.aize.nav.Maneuver

/**
 * Which glyph a turn gets, from Valhalla's manoeuvre type.
 *
 * Valhalla numbers its manoeuvres rather than naming them, and the numbers are not in the order a reader expects
 * (12 and 13 are the two U-turns, 14 is a sharp left, 25 is a merge). Keeping the table here, pure, means the turn
 * list can be tested without a device and the mapping is one place instead of a `when` inside a composable.
 */
object ManeuverIcons {
    const val STRAIGHT = "nav_straight"
    const val LEFT = "nav_left"
    const val RIGHT = "nav_right"
    const val SLIGHT_LEFT = "nav_slight_left"
    const val SLIGHT_RIGHT = "nav_slight_right"
    const val SHARP_LEFT = "nav_sharp_left"
    const val SHARP_RIGHT = "nav_sharp_right"
    const val UTURN = "nav_uturn"
    const val ROUNDABOUT = "nav_roundabout"
    const val MERGE = "nav_merge"
    const val EXIT = "nav_exit"
    const val ARRIVE = "nav_arrive"

    fun forType(type: Int): String = when (type) {
        1, 2, 3 -> STRAIGHT          // start, start right, start left
        4, 5, 6 -> ARRIVE            // destination, destination right, destination left
        7, 8, 22 -> STRAIGHT         // becomes, continue, stay straight
        9, 23 -> SLIGHT_RIGHT        // slight right, stay right
        10 -> RIGHT
        11 -> SHARP_RIGHT
        12, 13 -> UTURN              // u-turn right, u-turn left
        14 -> SHARP_LEFT
        15, 24 -> LEFT               // left, stay left
        16 -> SLIGHT_LEFT
        20, 21 -> EXIT               // exit right, exit left
        25 -> MERGE
        26, 27 -> ROUNDABOUT         // enter roundabout, exit roundabout
        else -> STRAIGHT
    }

    /**
     * The same question, asked of the instruction text, for servers that send a type this build does not know.
     * Text matching is a fallback, never the first answer: "Turn right onto Jalan Left" must not become a left turn
     * because of the street name.
     */
    fun forInstruction(instruction: String): String {
        val head = instruction.substringBefore(" onto ").lowercase()
        return when {
            head.contains("roundabout") || head.contains("rotary") -> ROUNDABOUT
            head.contains("u-turn") || head.contains("uturn") -> UTURN
            head.contains("sharp left") -> SHARP_LEFT
            head.contains("sharp right") -> SHARP_RIGHT
            head.contains("slight left") || head.contains("bear left") -> SLIGHT_LEFT
            head.contains("slight right") || head.contains("bear right") -> SLIGHT_RIGHT
            head.contains("turn left") || head.contains("left") -> LEFT
            head.contains("turn right") || head.contains("right") -> RIGHT
            head.contains("merge") -> MERGE
            head.contains("exit") -> EXIT
            head.contains("arrive") || head.contains("destination") -> ARRIVE
            else -> STRAIGHT
        }
    }

    fun forManeuver(m: Maneuver): String {
        val byType = forType(m.type)
        return if (byType == STRAIGHT) forInstruction(m.instruction) else byType
    }
}
