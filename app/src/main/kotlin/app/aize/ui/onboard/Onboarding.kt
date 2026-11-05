package app.aize.ui.onboard

import android.content.Context

/**
 * The first run, as a list of steps rather than a boolean.
 *
 * The order is the argument: what this is, how it works, why it wants your location, what it does with it. Asking
 * for a permission before explaining it is how apps get denied.
 */
enum class OnboardingStep {
    Welcome,
    HowItWorks,
    Location,
    Privacy,
    Ready,
}

/**
 * The step machine, kept pure so the flow can be tested without a device.
 *
 * [next] and [back] return null at the ends instead of wrapping: a first step has nothing behind it, and the last
 * step is finished by the caller, not by another step.
 */
object Onboarding {
    val steps: List<OnboardingStep> = OnboardingStep.entries

    fun next(step: OnboardingStep): OnboardingStep? = steps.getOrNull(step.ordinal + 1)

    fun back(step: OnboardingStep): OnboardingStep? = steps.getOrNull(step.ordinal - 1)

    /** 1-based, for "2 of 5" and for the dot row. */
    fun position(step: OnboardingStep): Int = step.ordinal + 1

    fun progress(step: OnboardingStep): Float = position(step).toFloat() / steps.size

    fun isLast(step: OnboardingStep): Boolean = step == steps.last()

    private const val PREFS = "aize"
    private const val KEY = "onboarding_done_v1"

    fun isDone(ctx: Context): Boolean = ctx.getSharedPreferences(PREFS, Context.MODE_PRIVATE).getBoolean(KEY, false)

    fun markDone(ctx: Context) {
        ctx.getSharedPreferences(PREFS, Context.MODE_PRIVATE).edit().putBoolean(KEY, true).apply()
    }

    /** For the settings screen's "show the tour again", and for tests. */
    fun reset(ctx: Context) {
        ctx.getSharedPreferences(PREFS, Context.MODE_PRIVATE).edit().remove(KEY).apply()
    }
}
