package app.aize.nav

import android.content.SharedPreferences

/**
 * The last few things the driver searched for, newest first.
 *
 * Kept next to the favourites in the same `aize` preferences file, as plain JSON. The list is
 * deliberately short (10) and case-insensitive on duplicates: typing "KLCC" twice should move the
 * existing entry to the top, not add a second one.
 */
object Recents {

    const val PREFS = "aize"
    const val KEY = "recent_searches"
    const val MAX = 10

    /** Loads the saved list; a corrupt or missing value reads as empty rather than crashing. */
    fun load(prefs: SharedPreferences): List<String> = decode(prefs.getString(KEY, null))

    /** Adds [term] to the front of [existing], dropping any earlier copy and trimming to [MAX]. */
    fun add(existing: List<String>, term: String): List<String> {
        val t = term.trim()
        if (t.length < 2) return existing
        return (listOf(t) + existing.filterNot { it.equals(t, ignoreCase = true) }).take(MAX)
    }

    fun encode(list: List<String>): String =
        list.joinToString(prefix = "[", postfix = "]", separator = ",") { quote(it) }

    fun decode(raw: String?): List<String> {
        if (raw.isNullOrBlank()) return emptyList()
        val out = mutableListOf<String>()
        var i = 0
        while (i < raw.length) {
            val open = raw.indexOf('"', i)
            if (open < 0) break
            val sb = StringBuilder()
            var j = open + 1
            while (j < raw.length && raw[j] != '"') {
                if (raw[j] == '\\' && j + 1 < raw.length) {
                    when (val c = raw[j + 1]) {
                        'n' -> sb.append('\n'); 't' -> sb.append('\t'); '"' -> sb.append('"')
                        '\\' -> sb.append('\\')
                        else -> sb.append(c)
                    }
                    j += 2
                } else {
                    sb.append(raw[j]); j++
                }
            }
            if (sb.isNotBlank()) out += sb.toString()
            i = j + 1
        }
        return out.take(MAX)
    }

    private fun quote(s: String): String = buildString {
        append('"')
        for (c in s) when (c) {
            '"' -> append("\\\"")
            '\\' -> append("\\\\")
            '\n' -> append("\\n")
            '\t' -> append("\\t")
            else -> append(c)
        }
        append('"')
    }
}
