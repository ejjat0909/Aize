package app.aize.nav

/**
 * Decoder for the encoded-polyline format Valhalla uses (precision 6, i.e. 1e-6 degrees).
 * Allocation-light: writes straight into two DoubleArrays (no per-point objects).
 *
 * P2 replaces this with the Rust `aize-core` implementation behind UniFFI; the unit tests stay as the contract.
 */
object Polyline {
    class Decoded(val lat: DoubleArray, val lon: DoubleArray) {
        val size: Int get() = lat.size
    }

    fun decode(encoded: String, precision: Int = 6): Decoded {
        val factor = Math.pow(10.0, precision.toDouble())
        var lats = DoubleArray(maxOf(16, encoded.length / 4))
        var lons = DoubleArray(lats.size)
        var n = 0
        var i = 0
        var lat = 0L
        var lon = 0L
        while (i < encoded.length) {
            var result = 0L
            var shift = 0
            var b: Int
            do {
                require(i < encoded.length) { "truncated polyline" }
                b = encoded[i++].code - 63
                result = result or ((b and 0x1f).toLong() shl shift)
                shift += 5
            } while (b >= 0x20)
            lat += if (result and 1L != 0L) (result shr 1).inv() else result shr 1

            result = 0L
            shift = 0
            do {
                require(i < encoded.length) { "truncated polyline" }
                b = encoded[i++].code - 63
                result = result or ((b and 0x1f).toLong() shl shift)
                shift += 5
            } while (b >= 0x20)
            lon += if (result and 1L != 0L) (result shr 1).inv() else result shr 1

            if (n == lats.size) {
                lats = lats.copyOf(n * 2)
                lons = lons.copyOf(n * 2)
            }
            lats[n] = lat / factor
            lons[n] = lon / factor
            n++
        }
        return Decoded(lats.copyOf(n), lons.copyOf(n))
    }

    /** Encoder: used by the tests (round trip) and by tooling; the app itself only decodes. */
    fun encode(lat: DoubleArray, lon: DoubleArray, precision: Int = 6): String {
        val factor = Math.pow(10.0, precision.toDouble())
        val sb = StringBuilder()
        var pLat = 0L
        var pLon = 0L
        for (k in lat.indices) {
            val a = Math.round(lat[k] * factor)
            val o = Math.round(lon[k] * factor)
            put(sb, a - pLat)
            put(sb, o - pLon)
            pLat = a
            pLon = o
        }
        return sb.toString()
    }

    private fun put(sb: StringBuilder, delta: Long) {
        var v = if (delta < 0) (delta shl 1).inv() else delta shl 1
        while (v >= 0x20) {
            sb.append((((v and 0x1f) or 0x20) + 63).toInt().toChar())
            v = v shr 5
        }
        sb.append((v + 63).toInt().toChar())
    }
}
