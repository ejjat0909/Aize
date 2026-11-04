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
import org.maplibre.android.style.layers.CircleLayer
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
        private const val POP_IN_STEP_MS = 40
        const val DRIVE_ZOOM = 17.0
        private const val ROUTE_SRC = "aize-route"
        private const val ALTS_SRC = "aize-route-alts"
        private const val PASSED_SRC = "aize-route-passed"
        private const val PUCK_SRC = "aize-puck"
        private const val DEST_SRC = "aize-dest"
        private const val PINS_SRC = "aize-pins"
        private const val PIN_SHADOW_SRC = "aize-pin-shadow"
    }

    private val palette = if (dark) AizeRoute.dark else AizeRoute.light
    private val puckSource = GeoJsonSource(PUCK_SRC)
    private val passedSource = GeoJsonSource(PASSED_SRC)
    /** The grey lines currently drawn, in the order the caller passed them (the tap handler indexes into this). */
    private var alternatives: List<Route> = emptyList()
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
        // the other eight billboard pins: one image each, registered up front so a layer can pick per feature
        for (icon in PinIcons.all) {
            if (icon == PinIcons.DESTINATION) continue
            runCatching { sprites.loadPin(PinIcons.assetFor(icon)).first }
                .onSuccess { style.addImage(icon, it) }
                // a missing pin asset must be loud: silently, the layer just draws nothing
                .onFailure { android.util.Log.w("AizePins", "pin asset missing: $icon", it) }
        }

        style.addSource(GeoJsonSource(ROUTE_SRC))
        style.addSource(GeoJsonSource(ALTS_SRC))
        style.addSource(passedSource)
        style.addSource(GeoJsonSource(DEST_SRC))
        val join = arrayOf(lineCap(Property.LINE_CAP_ROUND), lineJoin(Property.LINE_JOIN_ROUND))
        // alternatives sit underneath the chosen route, so the road you are taking is never hidden
        style.addLayer(
            // solid and thinner than the chosen route: an option, not a different kind of road
            LineLayer("route-alt", ALTS_SRC)
                .withProperties(*join, lineColor(palette.alternative), lineWidth(widthExpr(7f, 3.5f, 10f, 16f))),
        )
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
        setRoute(route)

        // pins: a map-aligned contact shadow (a circle, so it lies on the ground at every pitch) under the
        // billboard itself. Both are added before the puck so the car is never hidden behind a pin.
        style.addSource(GeoJsonSource(PINS_SRC))
        style.addSource(GeoJsonSource(PIN_SHADOW_SRC))
        style.addLayer(
            CircleLayer("pin-shadow", PIN_SHADOW_SRC).withProperties(
                circlePitchAlignment(Property.CIRCLE_PITCH_ALIGNMENT_MAP),
                circleRadius(widthExpr(3f, 2f, 5f, 8f)),
                circleColor("#2A1E5C"), circleOpacity(0.18f), circleBlur(0.4f),
            ),
        )
        style.addLayer(
            SymbolLayer("pins", PINS_SRC).withProperties(
                iconImage(Expression.get("icon")),
                iconAnchor(Property.ICON_ANCHOR_CENTER),
                iconOffset(arrayOf(0f, (0.5f - anchor[1].toFloat()) * 64f)),
                iconAllowOverlap(true), iconIgnorePlacement(true),
                iconPitchAlignment(Property.ICON_PITCH_ALIGNMENT_VIEWPORT),
                iconRotationAlignment(Property.ICON_ROTATION_ALIGNMENT_VIEWPORT),
                iconSize(1f),
            ).apply { minZoom = 12f }  // below this the pins would be pixel soup; the list still shows them
        )

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

    /**
     * Draws the pin set (search results, saved places) and clears whatever was there before.
     *
     * New pins pop in: the icon grows from a third of its size over ~200 ms, in six steps. The ramp runs on the
     * main thread but touches two small GeoJSON documents, so it costs a few hundred microseconds per step —
     * far cheaper than a per-frame animated paint property, which MapLibre would re-evaluate per frame anyway.
     */
    fun setPins(
        pins: List<MapPin>,
        popIn: Boolean = true,
        frame: Boolean = false,
        paddingPx: Int = 0,
        bottomPaddingPx: Int = 0,
    ) {
        val src = style.getSourceAs<GeoJsonSource>(PINS_SRC) ?: return
        val shadow = style.getSourceAs<GeoJsonSource>(PIN_SHADOW_SRC)
        val layer = style.getLayerAs<SymbolLayer>("pins")
        val shadowPoints = pins.map { PinGeoJson.Point(it.lon, it.lat) }
        val json = PinGeoJson.points(pins)
        src.setGeoJson(json)
        shadow?.setGeoJson(PinGeoJson.shadows(shadowPoints))
        if (frame && pins.size > 1) overviewPins(pins, paddingPx, bottomPaddingPx)
        if (pins.isEmpty() || !popIn) {
            layer?.setProperties(iconSize(1.0f))
            return
        }
        val steps = 5
        for (i in 0..steps) {
            val t = i.toFloat() / steps
            // ease-out so it lands rather than stopping dead
            val scale = 0.35f + 0.65f * (1f - (1f - t) * (1f - t))
            layer?.setProperties(iconSize(scale))
            if (i < steps) Thread.sleep(POP_IN_STEP_MS.toLong())
        }
        layer?.setProperties(iconSize(1.0f))
    }

    /**
     * Frames a set of pins so the whole answer is on screen above the sheet. Without this, a category search
     * fills a list with places the driver cannot see: the camera is wherever it was, usually zoomed out.
     */
    fun overviewPins(pins: List<MapPin>, paddingPx: Int = 0, bottomPaddingPx: Int = 0) {
        val b = org.maplibre.android.geometry.LatLngBounds.Builder()
        for (p in pins) b.include(LatLng(p.lat, p.lon))
        runCatching {
            val update = if (paddingPx > 0) {
                org.maplibre.android.camera.CameraUpdateFactory.newLatLngBounds(b.build(), paddingPx, paddingPx, paddingPx, bottomPaddingPx)
            } else {
                org.maplibre.android.camera.CameraUpdateFactory.newLatLngBounds(b.build(), 80)
            }
            map.animateCamera(update, 700)
        }
    }

    /** Called from a map click: the pin under the finger, if any (24 px of slop, so a tap does not have to be exact). */
    fun pinAt(screenPoint: android.graphics.PointF): MapPin? {
        val rect = android.graphics.RectF(
            screenPoint.x - 24f, screenPoint.y - 24f, screenPoint.x + 24f, screenPoint.y + 24f,
        )
        val feature = map.queryRenderedFeatures(rect, "pins").firstOrNull() ?: return null
        val point = feature.geometry() as? Point ?: return null
        return MapPin(
            lat = point.latitude(), lon = point.longitude(),
            icon = feature.getStringProperty("icon") ?: PinIcons.DESTINATION,
            label = feature.getStringProperty("label") ?: "",
            kind = feature.getStringProperty("kind") ?: "",
        )
    }

    /**
     * Draws the other ways to get there, grey and thin, under the chosen route. Passing an empty list
     * clears them: the map should never keep showing a road the driver cannot pick any more.
     */
    fun setAlternatives(routes: List<Route>, paddingPx: Int = 0, bottomPaddingPx: Int = 0) {
        val src = style.getSourceAs<GeoJsonSource>(ALTS_SRC) ?: return
        alternatives = routes
        src.setGeoJson(RouteGeoJson.alternatives(routes))
        if (routes.isNotEmpty() && paddingPx > 0) overviewAll(routes, paddingPx, bottomPaddingPx)
    }

    /**
     * Which grey option was tapped, if any.
     *
     * Tapping a line on the map is the same decision as tapping its row in the chooser, and it is the gesture people
     * reach for first: the routes are the thing they are looking at. Returns an index into the list last passed to
     * [setAlternatives] — not into the sorted chooser list, which may be in a different order.
     */
    fun alternativeAt(screenPoint: android.graphics.PointF, tolerancePx: Float = 26f): Int? {
        if (alternatives.size < 2) return null          // a single route is not a choice
        val paths = alternatives.map { r ->
            val n = r.path.size
            val xs = FloatArray(n)
            val ys = FloatArray(n)
            for (i in 0 until n) {
                val p = map.projection.toScreenLocation(LatLng(r.path.lat[i], r.path.lon[i]))
                xs[i] = p.x
                ys[i] = p.y
            }
            AlternativeHit.decimate(xs, ys)
        }
        return AlternativeHit.nearest(paths, screenPoint.x, screenPoint.y, tolerancePx)
    }

    /**
     * Frames every option together, so the driver can see where they differ before picking one.
     * `newLatLngBounds` takes (left, top, right, bottom): the sheet height goes in the bottom slot,
     * which lifts the routes above the chooser instead of centring them underneath it.
     */
    fun overviewAll(routes: List<Route>, paddingPx: Int, bottomPaddingPx: Int) {
        val b = org.maplibre.android.geometry.LatLngBounds.Builder()
        var any = false
        for (r in routes) {
            for (i in 0 until r.path.size step 4) { b.include(LatLng(r.path.lat[i], r.path.lon[i])); any = true }
            b.include(LatLng(r.path.lat.last(), r.path.lon.last())); any = true
        }
        if (!any) return
        map.animateCamera(
            CameraUpdateFactory.newLatLngBounds(b.build(), paddingPx, paddingPx, paddingPx, bottomPaddingPx),
            700,
        )
    }

    /** Show a route (or clear it with null): line, empty "passed" part, destination pin at its last vertex. */
    fun setRoute(route: Route?) {
        val src = style.getSourceAs<GeoJsonSource>(ROUTE_SRC)
        val dst = style.getSourceAs<GeoJsonSource>(DEST_SRC)
        passedSource.setGeoJson(FeatureCollection.fromFeatures(emptyList<Feature>()))
        if (route == null) {
            src?.setGeoJson(FeatureCollection.fromFeatures(emptyList<Feature>()))
            dst?.setGeoJson(FeatureCollection.fromFeatures(emptyList<Feature>()))
            setAlternatives(emptyList())
            return
        }
        val line = LineString.fromLngLats(List(route.path.size) { Point.fromLngLat(route.path.lon[it], route.path.lat[it]) })
        src?.setGeoJson(Feature.fromGeometry(line))
        dst?.setGeoJson(Point.fromLngLat(route.path.lon.last(), route.path.lat.last()))
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
