package app.aize.net

import android.content.Context

/** Where the Valhalla router lives. Editable in the app so the same APK works against any server. */
object ServerSettings {
    /** Emulator -> host machine. Real devices: set the address under "Server" in the app (the shared APK is built with a temporary public link). */
    const val DEFAULT_URL = "http://10.0.2.2:8002"
    private const val PREFS = "aize"
    private const val KEY = "server_url"

    fun get(ctx: Context): String = ctx.getSharedPreferences(PREFS, Context.MODE_PRIVATE).getString(KEY, null) ?: DEFAULT_URL

    fun set(ctx: Context, raw: String) {
        ctx.getSharedPreferences(PREFS, Context.MODE_PRIVATE).edit().putString(KEY, normalize(raw)).apply()
    }

    /** "192.168.1.5:8002" -> "http://192.168.1.5:8002"; trailing slashes and a trailing "/route" are dropped. */
    fun normalize(raw: String): String {
        var s = raw.trim()
        if (s.isEmpty()) return DEFAULT_URL
        if (!s.contains("://")) s = "http://$s"
        s = s.trimEnd('/')
        if (s.endsWith("/route")) s = s.removeSuffix("/route")
        return s
    }
}
