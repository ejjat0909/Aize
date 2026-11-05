package app.aize.ui.icon

import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.SolidColor
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.StrokeJoin
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.graphics.vector.addPathNodes
import androidx.compose.ui.unit.dp

/**
 * Builds the [AizeIconData] table into `ImageVector`s, once each.
 *
 * `ImageVector` construction parses the path strings, so it must not happen per frame: every icon is built once
 * and cached, never per frame. The vectors carry no colour of their own (black fill/stroke); `Icon`
 * tints them, which is how one icon works on the purple banner and on a white sheet.
 */
object AizeIcons {

    private const val STROKE = 1.9f

    private val cache = HashMap<String, ImageVector>()

    operator fun get(name: String): ImageVector = cache.getOrPut(name) { build(name) }

    private fun build(name: String): ImageVector {
        val paths = AizeIconData.paths[name]
            ?: error("Unknown Aize icon '$name'. Add it to AizeIconData so the catalogue test can see it.")
        val builder = ImageVector.Builder(
            name = name,
            defaultWidth = 24.dp,
            defaultHeight = 24.dp,
            viewportWidth = 24f,
            viewportHeight = 24f,
        )
        paths.forEach { d ->
            builder.addPath(
                pathData = addPathNodes(d),
                fill = null,
                stroke = SolidColor(Color.Black),
                strokeLineWidth = STROKE,
                strokeLineCap = StrokeCap.Round,
                strokeLineJoin = StrokeJoin.Round,
            )
        }
        return builder.build()
    }

    /** The icon for an OSM tag (`amenity=fuel`, `highway=speed_camera`, …). */
    /** The glyph name for a kind, without building the vector: what the coverage test asks. */
    fun pathFor(kind: String): String = AizeIconData.forKind(kind)

    fun forKind(kind: String): ImageVector = get(AizeIconData.forKind(kind))

    // The ones the app names directly. Everything else goes through [get] with a string, which the catalogue test
    // covers; these exist so a typo is a compile error rather than a crash at draw time.
    val Close = get("ui_close")
    val Search = get("ui_search")
    val Back = get("ui_back")
    val Star = get("ui_star")
    val Share = get("ui_share")
    val Settings = get("ui_settings")
    val Mic = get("ui_mic")
    val Speaker = get("ui_speaker")
    val SpeakerOff = get("ui_speaker_off")
    val Recenter = get("ui_recenter")
    val Compass = get("ui_compass")
    val Check = get("ui_check")
    val Chevron = get("ui_chevron")
    val Clock = get("ui_clock")
    val Stop = get("ui_stop")
    val Route = get("ui_route")
    val Server = get("ui_server")
    val Theme = get("ui_theme")
    val Steps = get("ui_steps")
    val Destination = get("ui_destination")
    val Home = get("ui_home")
    val Work = get("ui_work")
}
