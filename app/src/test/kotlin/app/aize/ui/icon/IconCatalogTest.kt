package app.aize.ui.icon

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * The icon set is data, so it is tested like data.
 *
 * An icon that does not parse, or that leaves the 24 dp viewport, does not throw when it is drawn — it draws
 * wrong, or draws nothing, and the only way to notice is to look at a screenshot of the one screen that uses it.
 * These checks make that class of mistake fail in CI instead.
 */
class IconCatalogTest {

    private val commands = "MmLlHhVvCcSsQqTtAaZz"

    @Test
    fun everyIconParses() {
        AizeIconData.paths.forEach { (name, paths) ->
            assertTrue("$name has no paths", paths.isNotEmpty())
            paths.forEach { d ->
                assertTrue("$name: path is empty", d.isNotBlank())
                assertTrue("$name: path must start with a move ($d)", d.first() in "Mm")
                val tokens = tokenize(d)
                assertTrue("$name: no numbers in $d", tokens.any { it is Tok.Num })
                // every command letter must be followed by something, and the path must consume its arguments
                tokens.forEachIndexed { i, t ->
                    if (t is Tok.Cmd && t.c.lowercaseChar() != 'z') {
                        assertTrue("$name: command '${t.c}' with no argument in $d", tokens.getOrNull(i + 1) is Tok.Num)
                    }
                }
            }
        }
    }

    @Test
    fun everyIconStaysInsideTheViewport() {
        // Walk the path properly instead of scanning the numbers: after `l6-6` the next pair is relative to the point
        // the first pair moved to, so a raw number is not a coordinate. A glyph that leaves the box is clipped, which
        // reads as a broken icon rather than a misplaced one.
        AizeIconData.paths.forEach { (name, paths) ->
            val box = Box()
            paths.forEach { d -> walk(d, box) }
            assertTrue("$name leaves the viewport: x ${box.minX}..${box.maxX}, y ${box.minY}..${box.maxY}",
                box.minX >= 0.5f && box.maxX <= 23.5f && box.minY >= 0.5f && box.maxY <= 23.5f)
        }
    }

    @Test
    fun theSetIsBigEnoughToCoverTheApp() {
        assertTrue("icon set shrank unexpectedly: ${AizeIconData.paths.size}", AizeIconData.paths.size >= 40)
    }

    @Test
    fun namesFollowTheHouseConvention() {
        val prefixes = setOf("nav_", "poi_", "ui_")
        AizeIconData.paths.keys.forEach { name ->
            assertTrue("$name does not start with one of $prefixes", prefixes.any { name.startsWith(it) })
            assertTrue("$name should be lower_snake_case", name == name.lowercase() && !name.contains(' '))
        }
    }

    @Test
    fun everyKindPointsAtAnIconThatExists() {
        AizeIconData.byKind.forEach { (kind, icon) ->
            assertNotNull("kind '$kind' points at missing icon '$icon'", AizeIconData.paths[icon])
        }
        assertNotNull(AizeIconData.paths[AizeIconData.FALLBACK])
    }

    @Test
    fun forKindReadsTheTagValueNotTheWholeTag() {
        // the search service answers `amenity=fuel`, so matching on the whole string silently finds nothing
        assertEquals("poi_fuel", AizeIconData.forKind("amenity=fuel"))
        assertEquals("poi_camera", AizeIconData.forKind("highway=speed_camera"))
        assertEquals("poi_parking", AizeIconData.forKind("amenity=parking"))
        assertEquals(AizeIconData.FALLBACK, AizeIconData.forKind("amenity=unknown_thing"))
        assertEquals(AizeIconData.FALLBACK, AizeIconData.forKind(""))
    }

    // ---- a very small SVG path reader, enough to bound a glyph -------------------------------------------------

    private sealed class Tok {
        data class Cmd(val c: Char) : Tok()
        data class Num(val v: Float) : Tok()
    }

    private fun tokenize(d: String): List<Tok> {
        val out = mutableListOf<Tok>()
        var i = 0
        while (i < d.length) {
            val c = d[i]
            when {
                c in commands -> { out += Tok.Cmd(c); i++ }
                c.isDigit() || c == '-' || c == '.' -> {
                    val start = i
                    i++
                    while (i < d.length && (d[i].isDigit() || d[i] == '.')) i++
                    out += Tok.Num(d.substring(start, i).toFloat())
                }
                else -> i++ // separators: space, comma
            }
        }
        return out
    }

    private class Box {
        var minX = Float.MAX_VALUE
        var minY = Float.MAX_VALUE
        var maxX = -Float.MAX_VALUE
        var maxY = -Float.MAX_VALUE
        fun add(x: Float, y: Float) {
            if (x < minX) minX = x
            if (x > maxX) maxX = x
            if (y < minY) minY = y
            if (y > maxY) maxY = y
        }
    }

    /** Argument count per command; curves contribute their control points, which is a conservative bound. */
    private fun arity(c: Char): Int = when (c.lowercaseChar()) {
        'm', 'l', 't' -> 2
        'h', 'v' -> 1
        'c' -> 6
        's', 'q' -> 4
        'a' -> 7
        else -> 0 // z
    }

    private fun walk(d: String, box: Box) {
        val tokens = tokenize(d)
        var x = 0f
        var y = 0f
        var cmd = 'M'
        var i = 0
        while (i < tokens.size) {
            val t = tokens[i]
            if (t is Tok.Cmd) { cmd = t.c; i++; continue }
            val n = arity(cmd)
            if (n == 0) { i++; continue }
            if (i + n > tokens.size) break
            val a = (0 until n).map { (tokens[i + it] as Tok.Num).v }
            val rel = cmd.isLowerCase()
            when (cmd.lowercaseChar()) {
                'm', 'l', 't' -> {
                    x = if (rel) x + a[0] else a[0]
                    y = if (rel) y + a[1] else a[1]
                    box.add(x, y)
                    if (cmd.lowercaseChar() == 'm') cmd = if (rel) 'l' else 'L' // implicit lineto after a move
                }
                'h' -> { x = if (rel) x + a[0] else a[0]; box.add(x, y) }
                'v' -> { y = if (rel) y + a[0] else a[0]; box.add(x, y) }
                'c' -> {
                    val pts = listOf(0, 2, 4).map { k ->
                        val px = if (rel) x + a[k] else a[k]
                        val py = if (rel) y + a[k + 1] else a[k + 1]
                        px to py
                    }
                    pts.forEach { box.add(it.first, it.second) }
                    x = pts[2].first; y = pts[2].second
                }
                's', 'q' -> {
                    val pts = listOf(0, 2).map { k ->
                        val px = if (rel) x + a[k] else a[k]
                        val py = if (rel) y + a[k + 1] else a[k + 1]
                        px to py
                    }
                    pts.forEach { box.add(it.first, it.second) }
                    x = pts[1].first; y = pts[1].second
                }
                'a' -> {
                    // rx ry rotation large-arc sweep x y: the radii are sizes, the last two are the point
                    val px = if (rel) x + a[5] else a[5]
                    val py = if (rel) y + a[6] else a[6]
                    // An arc is a slice of a circle of radius r through both points. Bound it by that circle: take the
                    // chord, and both candidate centres (which side the arc bulges towards is the sweep flag's job,
                    // and either centre gives a box that contains the slice).
                    val r = maxOf(a[0], a[1])
                    val dx = px - x
                    val dy = py - y
                    val chord = kotlin.math.sqrt(dx * dx + dy * dy)
                    val half = chord / 2f
                    val rr = if (chord <= 2f * r) r else half
                    val h = kotlin.math.sqrt((rr * rr - half * half).coerceAtLeast(0f))
                    val mx = (x + px) / 2f
                    val my = (y + py) / 2f
                    val nx = if (chord == 0f) 0f else -dy / chord
                    val ny = if (chord == 0f) 0f else dx / chord
                    // which of the two centres the arc belongs to is the large-arc/sweep pair's job
                    val sign = if (a[3] != a[4]) 1f else -1f
                    val cx = mx + sign * nx * h
                    val cy = my + sign * ny * h
                    box.add(cx - rr, cy - rr)
                    box.add(cx + rr, cy + rr)
                    x = px; y = py
                }
            }
            i += n
        }
    }
}
