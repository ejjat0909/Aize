package app.aize.ui.a11y

import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * Contrast is arithmetic, so it is tested as arithmetic against the palette the app actually ships.
 *
 * The colours are repeated here as ARGB ints rather than read from `AizeColorSchemes`: that class is generated and
 * a test that read it would pass by definition when someone changed a token. The point of this file is to fail
 * when a token changes into something unreadable, so the numbers have to be written down twice, once in the token
 * JSON and once here, and a mismatch is the test doing its job. `docs/M3-STATUS.md` says the same thing.
 */
class ContrastTest {

    private class Palette(
        val name: String,
        val surface: Int,
        val onSurface: Int,
        val surfaceVariant: Int,
        val onSurfaceVariant: Int,
        val background: Int,
        val onBackground: Int,
        val primary: Int,
        val onPrimary: Int,
        val primaryContainer: Int,
        val onPrimaryContainer: Int,
        val error: Int,
        val onError: Int,
        val outline: Int,
        val land: Int,
    )

    private val light = Palette(
        name = "light",
        surface = 0xFFFFFFFF.toInt(),
        onSurface = 0xFF1F1D25.toInt(),
        surfaceVariant = 0xFFEEEBF7.toInt(),
        onSurfaceVariant = 0xFF5D5A64.toInt(),
        background = 0xFFF7F5FE.toInt(),
        onBackground = 0xFF1F1D25.toInt(),
        primary = 0xFF8937F1.toInt(),
        onPrimary = 0xFFFFFFFF.toInt(),
        primaryContainer = 0xFFEEE9FF.toInt(),
        onPrimaryContainer = 0xFF3E0B75.toInt(),
        error = 0xFFD6111C.toInt(),
        onError = 0xFFFFFFFF.toInt(),
        outline = 0xFF8E8C96.toInt(),
        land = 0xFFF3F1F7.toInt(),
    )

    private val dark = Palette(
        name = "dark",
        surface = 0xFF1F1D25.toInt(),
        onSurface = 0xFFEEEBF7.toInt(),
        surfaceVariant = 0xFF323039.toInt(),
        onSurfaceVariant = 0xFFC6C4CF.toInt(),
        background = 0xFF0C0A10.toInt(),
        onBackground = 0xFFEEEBF7.toInt(),
        primary = 0xFFCCB9FE.toInt(),
        onPrimary = 0xFF3E0B75.toInt(),
        primaryContainer = 0xFF56179E.toInt(),
        onPrimaryContainer = 0xFFEEE9FF.toInt(),
        error = 0xFFFEAEA4.toInt(),
        onError = 0xFF630005.toInt(),
        outline = 0xFF8E8C96.toInt(),
        land = 0xFF0C0A10.toInt(),
    )

    private val both = listOf(light, dark)

    @Test
    fun bodyTextClearsTheFourAndAHalfFloor() {
        both.forEach { p ->
            val pairs = mapOf(
                "onSurface on surface" to (p.onSurface to p.surface),
                "onSurfaceVariant on surface" to (p.onSurfaceVariant to p.surface),
                "onSurfaceVariant on surfaceVariant" to (p.onSurfaceVariant to p.surfaceVariant),
                "onBackground on background" to (p.onBackground to p.background),
                "onPrimary on primary" to (p.onPrimary to p.primary),
                "onPrimaryContainer on primaryContainer" to (p.onPrimaryContainer to p.primaryContainer),
                "error on surface" to (p.error to p.surface),
                "onError on error" to (p.onError to p.error),
            )
            pairs.forEach { (what, pair) ->
                val r = Contrast.ratio(pair.first, pair.second)
                assertTrue(
                    "${p.name}: $what is %.2f:1, needs %.1f".format(r, Contrast.BODY_TEXT),
                    r >= Contrast.BODY_TEXT,
                )
            }
        }
    }

    @Test
    fun theBannerSecondaryLinesClearTheFloorAtTheAlphaTheCodeUses() {
        // the banner draws onPrimary at AizeAlpha.BANNER_SECONDARY over primary. At 0.8 this was 4.00:1 in light.
        both.forEach { p ->
            listOf(AizeAlpha.BANNER_SECONDARY, AizeAlpha.BANNER_TERTIARY).forEach { alpha ->
                val r = Contrast.ratioOn(p.onPrimary, p.primary, alpha)
                assertTrue(
                    "${p.name}: onPrimary at alpha $alpha on primary is %.2f:1".format(r),
                    r >= Contrast.BODY_TEXT,
                )
            }
        }
    }

    @Test
    fun graphicsThatCarryMeaningClearThreeToOne() {
        // a route line is a graphical object a driver has to find, not decoration
        both.forEach { p ->
            val selected = Contrast.ratio(p.primary, p.land)
            assertTrue("${p.name}: chosen route on land is %.2f:1".format(selected), selected >= Contrast.NON_TEXT)
            val outline = Contrast.ratio(p.outline, p.surface)
            assertTrue("${p.name}: outline on surface is %.2f:1".format(outline), outline >= Contrast.NON_TEXT)
        }
    }

    @Test
    fun theRouteColoursAreReadableAgainstTheMap() {
        // AizeRoute is generated from the tokens, so this is the value the map actually draws with
        val lightAlt = app.aize.design.AizeRoute.light.alternative
        val lightSelected = app.aize.design.AizeRoute.light.selected
        val darkAlt = app.aize.design.AizeRoute.dark.alternative
        val darkSelected = app.aize.design.AizeRoute.dark.selected

        val lightAltRatio = Contrast.ratio(lightAlt, light.land)
        val darkAltRatio = Contrast.ratio(darkAlt, dark.land)
        assertTrue(
            "light alternative route on land is %.2f:1, needs %.1f".format(lightAltRatio, Contrast.NON_TEXT),
            lightAltRatio >= Contrast.NON_TEXT,
        )
        assertTrue(
            "dark alternative route on land is %.2f:1, needs %.1f".format(darkAltRatio, Contrast.NON_TEXT),
            darkAltRatio >= Contrast.NON_TEXT,
        )
        assertTrue(
            "light chosen route on land is %.2f:1".format(Contrast.ratio(lightSelected, light.land)),
            Contrast.ratio(lightSelected, light.land) >= Contrast.NON_TEXT,
        )
        assertTrue(
            "dark chosen route on land is %.2f:1".format(Contrast.ratio(darkSelected, dark.land)),
            Contrast.ratio(darkSelected, dark.land) >= Contrast.NON_TEXT,
        )
    }

    @Test
    fun blendingIsTheArithmeticTheEyeDoes() {
        assertTrue(Contrast.blend(0xFFFFFFFF.toInt(), 0xFF000000.toInt(), 1f) == 0xFFFFFFFF.toInt())
        assertTrue(Contrast.blend(0xFFFFFFFF.toInt(), 0xFF000000.toInt(), 0f) == 0xFF000000.toInt())
        val half = Contrast.blend(0xFFFFFFFF.toInt(), 0xFF000000.toInt(), 0.5f)
        assertTrue("0.5 white on black is 128", (half and 0xFF) in 126..130)
        assertTrue(Contrast.ratio(0xFF123456.toInt(), 0xFF123456.toInt()) >= 1.0)
    }
}
