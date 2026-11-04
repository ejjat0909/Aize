package app.aize.telemetry

import android.content.Context
import android.util.Log

/**
 * Opt-in, aggregate-only telemetry (plan ADR-19). Nothing is collected until the user turns it on in
 * Settings, and nothing leaves the device in this build: the only sink is logcat in debug builds.
 *
 * Rules, so this stays honest as sinks are added:
 *  - no location, no identifiers, no free text; counts and durations only
 *  - every event carries [env] so staging noise never lands in production numbers
 *  - a disabled client is a no-op, not a queue that flushes later
 */
object Telemetry {
    private const val PREFS = "aize"
    private const val KEY = "telemetry_opt_in"

    /** A sink is where events go. Swap in a self-hosted collector at P0-10 follow-up; never an ad SDK. */
    fun interface Sink {
        fun record(name: String, fields: Map<String, Any>)
    }

    private var sink: Sink? = null

    fun isEnabled(ctx: Context): Boolean = ctx.getSharedPreferences(PREFS, Context.MODE_PRIVATE).getBoolean(KEY, false)

    fun setEnabled(ctx: Context, on: Boolean) {
        ctx.getSharedPreferences(PREFS, Context.MODE_PRIVATE).edit().putBoolean(KEY, on).apply()
        if (!on) sink = null
    }

    /** Installs a sink. Debug builds default to logcat; release builds have none. */
    fun install(s: Sink?) { sink = s }

    fun event(ctx: Context, name: String, fields: Map<String, Any> = emptyMap()) {
        if (!isEnabled(ctx)) return
        sink?.record(name, fields + ("env" to BuildInfo.env))
    }
}

/** Build-time facts that are safe to report. */
object BuildInfo {
    val env: String get() = app.aize.BuildConfig.ENV
}
