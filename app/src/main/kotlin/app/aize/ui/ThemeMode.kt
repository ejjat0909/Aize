package app.aize.ui

import android.content.Context
import java.time.LocalTime
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow

/**
 * Day/night policy (P2-11).
 *
 * `AUTO` follows the clock: light between [DAY_START] and [NIGHT_START], dark otherwise. Those are the
 * tropics' roughly constant sunrise and sunset, and the pilot region is Malaysia — there is no summer to
 * track. The manual modes exist because a driver in a tunnel, or someone testing the dark map at noon,
 * should not have to change the phone's system setting.
 *
 * The choice is remembered; the state is a [StateFlow] so the map style and the Compose theme both follow it.
 */
object ThemeMode {
    enum class Mode { AUTO, LIGHT, DARK }

    val DAY_START: LocalTime = LocalTime.of(6, 30)
    val NIGHT_START: LocalTime = LocalTime.of(19, 0)

    private const val PREFS = "aize"
    private const val KEY = "theme_mode"

    private val _mode = MutableStateFlow(Mode.AUTO)
    val mode: StateFlow<Mode> = _mode

    fun load(ctx: Context) {
        val stored = ctx.getSharedPreferences(PREFS, Context.MODE_PRIVATE).getString(KEY, null)
        _mode.value = runCatching { Mode.valueOf(stored ?: "") }.getOrDefault(Mode.AUTO)
    }

    fun set(ctx: Context, mode: Mode) {
        _mode.value = mode
        ctx.getSharedPreferences(PREFS, Context.MODE_PRIVATE).edit().putString(KEY, mode.name).apply()
    }

    fun cycle(ctx: Context): Mode {
        val next = when (_mode.value) {
            Mode.AUTO -> Mode.LIGHT
            Mode.LIGHT -> Mode.DARK
            Mode.DARK -> Mode.AUTO
        }
        set(ctx, next)
        return next
    }

    /** Whether the UI and the map should be dark right now. */
    fun isDark(mode: Mode = _mode.value, now: LocalTime = LocalTime.now()): Boolean = when (mode) {
        Mode.LIGHT -> false
        Mode.DARK -> true
        Mode.AUTO -> !isDaytime(now)
    }

    fun isDaytime(now: LocalTime): Boolean = !now.isBefore(DAY_START) && now.isBefore(NIGHT_START)

    fun label(mode: Mode): String = when (mode) {
        Mode.AUTO -> "Auto"
        Mode.LIGHT -> "Day"
        Mode.DARK -> "Night"
    }
}
