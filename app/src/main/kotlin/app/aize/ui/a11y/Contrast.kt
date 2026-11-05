package app.aize.ui.a11y

/**
 * Contrast, measured rather than eyeballed.
 *
 * The palette is generated, so "does the secondary line on the banner pass?" is a question with an arithmetic
 * answer, not an opinion. These are plain `Int` ARGB functions on purpose: a unit test can check the theme's own
 * numbers without a device, a Compose runtime or a screenshot.
 *
 * The thresholds are WCAG 2.2 AA: 4.5:1 for body text, 3:1 for large text (>= 18 pt, or >= 14 pt bold) and for
 * the non-text parts of an interface that a user needs to understand what is on screen.
 */
object Contrast {
    const val BODY_TEXT = 4.5
    const val LARGE_TEXT = 3.0
    const val NON_TEXT = 3.0

    /** WCAG relative luminance of an opaque ARGB colour. */
    fun luminance(argb: Int): Double {
        fun channel(v: Int): Double {
            val s = v / 255.0
            return if (s <= 0.03928) s / 12.92 else Math.pow((s + 0.055) / 1.055, 2.4)
        }
        val r = channel((argb shr 16) and 0xFF)
        val g = channel((argb shr 8) and 0xFF)
        val b = channel(argb and 0xFF)
        return 0.2126 * r + 0.7152 * g + 0.0722 * b
    }

    /** Contrast ratio between two opaque ARGB colours, 1.0 (identical) to 21.0 (black on white). */
    fun ratio(a: Int, b: Int): Double {
        val la = luminance(a)
        val lb = luminance(b)
        val hi = maxOf(la, lb)
        val lo = minOf(la, lb)
        return (hi + 0.05) / (lo + 0.05)
    }

    /**
     * What a semi-transparent colour actually looks like on a background: the arithmetic the eye does. The result
     * is opaque — the point of blending is to find the colour that is finally on screen.
     */
    fun blend(foreground: Int, background: Int, alpha: Float): Int {
        var out = 0xFF shl 24
        for (shift in intArrayOf(16, 8, 0)) {
            val f = (foreground shr shift) and 0xFF
            val b = (background shr shift) and 0xFF
            val v = Math.round(f * alpha + b * (1f - alpha))
            out = out or (v shl shift)
        }
        return out
    }

    /** The ratio a colour with [alpha] has once it is drawn on [background]. */
    fun ratioOn(foreground: Int, background: Int, alpha: Float): Double =
        ratio(blend(foreground, background, alpha), background)
}

/**
 * The opacities the interface uses for secondary text, in one place so a test can check the *effective* colour
 * rather than the opaque one. 0.8 of white on Aize purple is 4.00:1 — under the body-text floor — which is why
 * these are 0.92 and up.
 */
object AizeAlpha {
    /** The `then …` line in the instruction banner: 13 sp, so it needs the body-text floor. */
    const val BANNER_SECONDARY = 0.92f

    /** The remaining distance and clock line: 13 sp, same floor. */
    const val BANNER_TERTIARY = 0.92f
}
