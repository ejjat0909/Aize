package app.aize.map

import android.content.res.AssetManager
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import org.json.JSONObject
import kotlin.math.abs

/**
 * Loads the pre-rendered Blender sprites (assets3d/dist, synced into assets/sprites by Gradle) as map images.
 *
 * P0 draws the NEAREST pitch bucket and NEAREST heading bucket only. The two-bucket affine blend described in
 * assets3d/README.md (P2-05) is deliberately not implemented yet; with the camera presets (overview 0 deg,
 * drive 45 deg) the steady states are exactly on-grid, so the warp only matters while the pitch animates.
 */
class PuckSprites(private val assets: AssetManager) {

    class Sheet(val pitch: Double, val yaws: Int, val frameDp: Double)

    /** Frames decoded for one pitch bucket, keyed by the image name registered on the style. */
    class Loaded(val sheet: Sheet, val images: Map<String, Bitmap>)

    private fun manifest(asset: String): JSONObject =
        JSONObject(assets.open("sprites/$asset/$asset.sprites.json").bufferedReader().use { it.readText() })

    /** Pitches the asset ships (0, 7.5, ... 60). */
    fun pitches(asset: String): List<Double> {
        val a = manifest(asset).getJSONArray("pitches")
        return List(a.length()) { a.getDouble(it) }
    }

    fun name(asset: String, pitch: Double, k: Int) = "$asset-p${pitch.toInt()}-$k"

    /** Image name for a heading (degrees clockwise from screen-up) at a bucket pitch: nearest of `yaws` buckets. */
    fun imageName(asset: String, pitch: Double, yawDeg: Double, yaws: Int = 24): String {
        val step = 360.0 / yaws
        val norm = ((yawDeg % 360.0) + 360.0) % 360.0
        return name(asset, pitch, Math.floorMod(Math.round(norm / step).toInt(), yaws))
    }

    /** Decode one pitch bucket's sheet and cut it into frames. Call off the main thread. */
    fun load(asset: String, pitch: Double): Loaded {
        val m = manifest(asset)
        val tier = m.getJSONObject("tiers").getJSONObject("xxhdpi")
        val key = if (pitch % 1.0 == 0.0) pitch.toInt().toString() else pitch.toString()
        val sheetJson = tier.getJSONObject("sheets").getJSONObject(key)
        val framePx = tier.getInt("frame_px")
        val cols = sheetJson.getInt("cols")
        val yaws = m.getInt("yaws")
        val scale = tier.getInt("scale")
        val sheet = assets.open("sprites/$asset/${sheetJson.getString("file")}").use { BitmapFactory.decodeStream(it) }
            ?: error("cannot decode sprite sheet for $asset @ $pitch")
        val out = LinkedHashMap<String, Bitmap>(yaws)
        try {
            for (k in 0 until yaws) {
                val frame = Bitmap.createBitmap(sheet, (k % cols) * framePx, (k / cols) * framePx, framePx, framePx)
                frame.density = 160 * scale            // xxhdpi: MapLibre then draws the frame at frame_dp density-independent pixels
                out[name(asset, pitch, k)] = frame
            }
        } finally {
            sheet.recycle()
        }
        return Loaded(Sheet(pitch, yaws, m.getDouble("frame_dp")), out)
    }

    /** Single-frame asset (map pins); returns the bitmap and the anchor from the manifest. */
    fun loadPin(asset: String): Pair<Bitmap, DoubleArray> {
        val m = manifest(asset)
        val tier = m.getJSONObject("tiers").getJSONObject("xxhdpi")
        val sheetJson = tier.getJSONObject("sheets").getJSONObject("0")
        val bmp = assets.open("sprites/$asset/${sheetJson.getString("file")}").use { BitmapFactory.decodeStream(it) }
            ?: error("cannot decode pin $asset")
        bmp.density = 160 * tier.getInt("scale")
        val a = m.getJSONArray("anchor")
        return bmp to doubleArrayOf(a.getDouble(0), a.getDouble(1))
    }
}
