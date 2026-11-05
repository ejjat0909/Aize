package app.aize.ui.a11y

/**
 * What a screen reader should hear, as plain strings the JVM can assert on.
 *
 * The visual layout says things with layout — a big number above a line of text, a badge on the right of a row.
 * A screen reader has none of that, so the same facts have to be said in an order that makes sense out loud, and
 * said once. These functions are the single place that ordering lives.
 */
object Spoken {

    /**
     * The instruction banner: distance first (that is the number a driver wants), then the manoeuvre, then what
     * comes after it, then the trip line.
     *
     * Deliberately **not** a live region. The distance counts down every second, and a polite live region on a
     * node that changes every second turns a phone into a chatterbox. Voice guidance already speaks the turns;
     * this is for when someone swipes to the banner and asks what it says.
     */
    fun banner(distance: String, instruction: String, then: String?, eta: String?): String = buildString {
        append(distance)
        append(". ")
        append(instruction.trimEnd('.'))
        append('.')
        if (!then.isNullOrBlank()) {
            append(' ')
            append(then.trimEnd('.'))
            append('.')
        }
        if (!eta.isNullOrBlank()) {
            append(' ')
            append(eta)
            append('.')
        }
    }

    /**
     * One route in the chooser: which one of how many, how far, how long, the road, the badges, and whether it is
     * the one already drawn on the map. "1 of 3" first, because without it "the fastest" is a guess.
     */
    fun route(
        index: Int,
        count: Int,
        distance: String,
        minutes: Int,
        via: String?,
        badges: List<String>,
        selected: Boolean,
    ): String = buildString {
        append("Route ")
        append(index)
        append(" of ")
        append(count)
        append(". ")
        append(distance)
        append(", ")
        append(minutes)
        append(if (minutes == 1) " minute" else " minutes")
        if (!via.isNullOrBlank()) {
            append(", via ")
            append(via)
        }
        if (badges.isNotEmpty()) {
            append(", ")
            append(badges.joinToString(", ").lowercase())
        }
        if (selected) append(", shown on the map")
        append('.')
    }

    /**
     * A place: the name, then what it is and how far. The kind comes from an OSM tag ("shop=mall"), so it is
     * turned into words first — a screen reader must never spell out "shop equals mall".
     */
    fun place(name: String, kindLabel: String, distance: String?, saved: Boolean): String = buildString {
        append(name.trimEnd('.'))
        append(". ")
        append(kindLabel)
        if (!distance.isNullOrBlank()) {
            append(", ")
            append(distance)
            append(" away")
        }
        if (saved) append(", saved")
        append('.')
    }
}
