package app.aize.map

import android.content.Context
import java.io.File

/**
 * The walking skeleton reads vector tiles from a PMTiles archive bundled in the debug APK
 * (a .pmtiles file in data/dev/assets/tiles, produced by scripts/fetch-dev-tiles.sh, never committed).
 * MapLibre needs a real file for range reads, so it is copied out of the APK once.
 */
object TileStore {
    const val ASSET_DIR = "tiles"

    /** Returns the archive on disk, or null when this build has no bundled map data. */
    fun ensure(context: Context): File? {
        val name = context.assets.list(ASSET_DIR)?.firstOrNull { it.endsWith(".pmtiles") } ?: return null
        val dir = File(context.filesDir, ASSET_DIR).apply { mkdirs() }
        val target = File(dir, name)
        val size = context.assets.openFd("$ASSET_DIR/$name").use { it.length }      // stored uncompressed (noCompress)
        if (target.exists() && target.length() == size) return target
        val tmp = File(dir, "$name.part")
        context.assets.open("$ASSET_DIR/$name").use { input -> tmp.outputStream().use { input.copyTo(it, 1 shl 16) } }
        check(tmp.renameTo(target)) { "cannot move $tmp into place" }
        return target
    }

    /** MapLibre source URL for a local PMTiles file. */
    fun url(file: File) = "pmtiles://file://${file.absolutePath}"
}
