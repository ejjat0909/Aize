package app.aize.design

import android.provider.Settings
import androidx.compose.animation.core.FiniteAnimationSpec
import androidx.compose.animation.core.spring
import androidx.compose.runtime.Composable
import androidx.compose.runtime.remember
import androidx.compose.ui.platform.LocalContext

/**
 * Motion policy, kept separate from the motion tokens.
 *
 * The tokens say how long a transition *wants* to take; this says whether it should run at all. Android lets
 * people turn animations off (Settings > Accessibility > Remove animations), and an app that ignores that is
 * both rude and slow for them: `ANIMATOR_DURATION_SCALE` is 0 when they have asked for no motion.
 */
object Motion {
    /** True when animations should run, given the system's animator duration scale. */
    fun enabled(animatorDurationScale: Float): Boolean = animatorDurationScale > 0f

    /** Duration to actually use: zero when the system asks for no motion, so nothing is merely slowed down. */
    fun durationMs(configuredMs: Int, animatorDurationScale: Float): Int =
        if (enabled(animatorDurationScale)) configuredMs else 0
}

/** The "settle" spring for whatever is being animated (Float, IntSize, offset): quick, no overshoot. */
fun <T> settleSpec(): FiniteAnimationSpec<T> =
    spring(dampingRatio = AizeSprings.SETTLE_DAMPING_RATIO, stiffness = AizeSprings.SETTLE_STIFFNESS)

/** The "pop in" spring: a little bounce, for things that appear under the finger. */
fun <T> popInSpec(): FiniteAnimationSpec<T> =
    spring(dampingRatio = AizeSprings.POP_IN_DAMPING_RATIO, stiffness = AizeSprings.POP_IN_STIFFNESS)

/** Reads the system animator scale once per composition; cheap enough to call in every animated composable. */
@Composable
fun rememberMotionEnabled(): Boolean {
    val ctx = LocalContext.current
    return remember(ctx) {
        val scale = runCatching {
            Settings.Global.getFloat(ctx.contentResolver, Settings.Global.ANIMATOR_DURATION_SCALE)
        }.getOrDefault(1f)
        Motion.enabled(scale)
    }
}
