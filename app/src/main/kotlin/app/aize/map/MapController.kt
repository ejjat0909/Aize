package app.aize.map

import android.content.Context
import android.graphics.Bitmap
import app.aize.design.AizeRoute
import app.aize.nav.Route
import app.aize.nav.RoutePath
import org.maplibre.android.camera.CameraPosition
import org.maplibre.android.camera.CameraUpdateFactory
import org.maplibre.android.geometry.LatLng
import org.maplibre.android.maps.MapLibreMap
import org.maplibre.android.maps.Style
import org.maplibre.android.style.expressions.Expression
import org.maplibre.android.style.layers.LineLayer
import org.maplibre.android.style.layers.Property
import org.maplibre.android.style.layers.PropertyFactory.*
import org.maplibre.android.style.layers.SymbolLayer
import org.maplibre.android.style.sources.GeoJsonSource
import org.maplibre.geojson.Feature
import org.maplibre.geojson.FeatureCollection
import org.maplibre.geojson.LineString
import org.maplibre.geojson.Point

/**
 * Owns everything drawn on top of the basemap: the route (casing + line + passed part), the location puck
 * (pre-rendered 3D arrow) and the destination pin. UI state lives in the ViewModel; this only draws.
 */
class MapController(
    private val map: MapLibreMap,
    private val style: Style,
    private val sprites: PuckSprites,
    private val dark: Boolean,
) {
    companion object {
        const val DRIVE_PITCH = 45.0
        const val DRIVE_ZOOM = 17.0
        private const val ROUTE_SRC = "aize-route"
        private const val PASSED_SRC = "aize-route-passed"
        private const val PUCK_SRC = "aize-puck"
        private const val DEST_SRC = "aize-dest"
    }

    private val palette = if (dark) AizeRoute.dark else AizeRoute.light
    private val puckSource = GeoJsonSource(PUCK_SRC)
    private val passedSource = GeoJsonSource(PASSED_SRC)
    private var loadedPitches = emptyList<Double>()
    private var puckAsset = "arrow"

    /** Adds layers + images. Decodes sprite sheets, so call off the main thread is NOT required: ~50 ms for two sheets. */
    fun install(route: Route?) {
        val pitchesToLoad = listOf(0.0, DRIVE_PITCH)
        for (p in pitchesToLoad) {
            val loaded = sprites.load(puckAsset, p)
            loaded.images.forEach { (n, bmp: Bitmap) -> style.addImage(n, bmp) }
        }
        loadedPitches = pitchesToLoad

        val (pin, anchor) = sprites.loadPin("pin_destination")
        style.addImage("pin-destination", pin)

        if (route != null) {
            val line = LineString.fromLngLats(List(route.path.size) { Point.fromLngLat(route.path.lon[it], route.path.lat[it]) })
            style.addSource(GeoJsonSource(ROUTE_SRC, Feature.fromGeometry(line)))
            style.addSource(passedSource)
            style.addSource(GeoJsonSource(DEST_SRC, Point.fromLngLat(route.path.lon.last(), route.path.lat.last())))
            val join = arrayOf(lineCap(Property.LINE_CAP_ROUND), lineJoin(Property.LINE_JOIN_ROUND))
            style.addLayer(LineLayer("route-casing", ROUTE_SRC).withProperties(*join, lineColor(palette.selectedCasing), lineWidth(widthExpr(15f, 7f, 22f, 36f))))
            style.addLayer(LineLayer("route", ROUTE_SRC).withProperties(*join, lineColor(palette.selected), lineWidth(widthExpr(10f, 4f, 16f, 26f))))
            style.addLayer(LineLayer("route-passed", PASSED_SRC).withProperties(*join, lineColor(palette.passed), lineWidth(widthExpr(10f, 4f, 16f, 26f))))
            style.addLayer(
                SymbolLayer("dest-pin", DEST_SRC).withProperties(
                    iconImage("pin-destination"), iconAnchor(Property.ICON_ANCHOR_CENTER),
                    iconOffset(arrayOf(0f, (0.5f - anchor[1].toFloat()) * 64f)),      // frame is 64 dp: shift so the pin's tip sits on the point
                    iconAllowOverlap(true), iconIgnorePlacement(true),
                    iconPitchAlignment(Property.ICON_PITCH_ALIGNMENT_VIEWPORT), iconRotationAlignment(Property.ICON_ROTATION_ALIGNMENT_VIEWPORT),
                ),
            )
        } else {
            style.addSource(passedSource)
        }

        style.addSource(puckSource)
        style.addLayer(
            SymbolLayer("puck", PUCK_SRC).withProperties(
                iconImage(Expression.get("img")),
                iconRotate(Expression.get("rot")),
                iconAllowOverlap(true), iconIgnorePlacement(true),
                iconPitchAlignment(Property.ICON_PITCH_ALIGNMENT_VIEWPORT),      // the sprite already has its pitch baked in
                iconRotationAlignment(Property.ICON_ROTATION_ALIGNMENT_VIEWPORT),
            ),
        )
    }

    private fun widthExpr(z10: Float, z14: Float, z17: Float, z20: Float): Expression =
        Expression.interpolate(Expression.exponential(1.5f), Expression.zoom(),
            Expression.stop(10, z10 * 0.35f), Expression.stop(14, z14 + 2f), Expression.stop(17, z17 * 0.8f), Expression.stop(20, z20 * 0.8f))

    /** Move the puck. `heading` = course over ground (deg clockwise from north); screen yaw = heading - map bearing. */
    fun setPuck(lat: Double, lon: Double, heading: Double, mapBearing: Double, mapPitch: Double) {
        val pitch = loadedPitches.minByOrNull { Math.abs(it - mapPitch) } ?: 0.0
        val yaw = ((heading - mapBearing) % 360.0 + 360.0) % 360.0
        val step = 360.0 / 24
        val bucket = Math.floorMod(Math.round(yaw / step).toInt(), 24)
        val residual = RoutePath.angleDelta(bucket * step, yaw)               // < 7.5 deg: rotate the sprite by the remainder
        val f = Feature.fromGeometry(Point.fromLngLat(lon, lat))
        f.addStringProperty("img", sprites.name(puckAsset, pitch, bucket))
        f.addNumberProperty("rot", residual)
        puckSource.setGeoJson(f)
    }

    fun setPassed(route: Route, upToMeters: Double) {
        val p = route.path
        val s = p.segmentAt(upToMeters)
        val pts = ArrayList<Point>(s + 2)
        for (i in 0..s) pts += Point.fromLngLat(p.lon[i], p.lat[i])
        val cur = p.pointAt(upToMeters)
        pts += Point.fromLngLat(cur.lon, cur.lat)
        if (pts.size >= 2) passedSource.setGeoJson(Feature.fromGeometry(LineString.fromLngLats(pts))) else passedSource.setGeoJson(FeatureCollection.fromFeatures(emptyList<Feature>()))
    }

    /** Heading-up follow camera: puck sits in the lower third of the screen. */
    fun follow(lat: Double, lon: Double, bearing: Double, zoom: Double = DRIVE_ZOOM, pitch: Double = DRIVE_PITCH, durationMs: Int = 0, topPaddingPx: Double = 0.0, bottomPaddingPx: Double = 0.0) {
        val cam = CameraPosition.Builder().target(LatLng(lat, lon)).bearing(bearing).tilt(pitch).zoom(zoom)
            .padding(0.0, topPaddingPx, 0.0, bottomPaddingPx).build()
        if (durationMs <= 0) map.moveCamera(CameraUpdateFactory.newCameraPosition(cam)) else map.animateCamera(CameraUpdateFactory.newCameraPosition(cam), durationMs)
    }

    /** North-up top-down view of the whole route. */
    fun overview(route: Route, paddingPx: Int) {
        val b = org.maplibre.android.geometry.LatLngBounds.Builder()
        for (i in 0 until route.path.size step 4) b.include(LatLng(route.path.lat[i], route.path.lon[i]))
        b.include(LatLng(route.path.lat.last(), route.path.lon.last()))
        val cam = map.getCameraForLatLngBounds(b.build(), intArrayOf(paddingPx, paddingPx * 2, paddingPx, paddingPx * 3), 0.0, 0.0)
        if (cam != null) map.animateCamera(CameraUpdateFactory.newCameraPosition(cam), 700)
    }
}
