package app.aize.telemetry

import android.content.Context
import org.json.JSONObject

/**
 * Server-driven switches (plan P0-10) with local defaults, so a broken or missing flags file can never
 * brick a feature: parse failure means "use the defaults".
 */
data class FeatureFlags(
    val search: Boolean = true,
    val turnByTurn: Boolean = true,
    val voice: Boolean = false,
    val reports: Boolean = false,
) {
    companion object {
        val DEFAULTS = FeatureFlags()

        /** Parses a JSON object; anything unparseable yields the defaults. Missing keys keep their default. */
        fun parse(json: String?): FeatureFlags {
            if (json.isNullOrBlank()) return DEFAULTS
            val o = runCatching { JSONObject(json) }.getOrNull() ?: return DEFAULTS
            return FeatureFlags(
                search = o.optBoolean("search", DEFAULTS.search),
                turnByTurn = o.optBoolean("turnByTurn", DEFAULTS.turnByTurn),
                voice = o.optBoolean("voice", DEFAULTS.voice),
                reports = o.optBoolean("reports", DEFAULTS.reports),
            )
        }

        private const val PREFS = "aize"
        private const val KEY = "flags_json"

        /** Last flags fetched from the server (or null). Never blocks; the network refresh is P0-10's job. */
        fun cached(ctx: Context): FeatureFlags =
            parse(ctx.getSharedPreferences(PREFS, Context.MODE_PRIVATE).getString(KEY, null))

        fun store(ctx: Context, json: String?) {
            ctx.getSharedPreferences(PREFS, Context.MODE_PRIVATE).edit().putString(KEY, json).apply()
        }
    }
}
