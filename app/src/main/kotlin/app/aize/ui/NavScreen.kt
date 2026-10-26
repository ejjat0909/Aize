package app.aize.ui

import android.Manifest
import android.annotation.SuppressLint
import android.content.Context
import android.content.pm.PackageManager
import android.location.Location
import android.location.LocationListener
import android.location.LocationManager
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.lifecycle.compose.LocalLifecycleOwner
import androidx.compose.ui.platform.LocalView
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.viewinterop.AndroidView
import androidx.core.content.ContextCompat
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.LifecycleEventObserver
import app.aize.design.AizeRadius
import app.aize.design.AizeSize
import app.aize.map.MapController
import app.aize.map.PuckSprites
import app.aize.map.TileStore
import app.aize.nav.Route
import app.aize.nav.RoutePath
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import org.maplibre.android.MapLibre
import org.maplibre.android.maps.MapLibreMap
import org.maplibre.android.maps.MapView
import org.maplibre.android.maps.Style
import kotlin.math.exp
import kotlin.math.roundToInt

private const val DEMO_SPEED_MPS = 22.0          // ~80 km/h: the 9 km demo route takes ~7 minutes
private val KL_CENTER = doubleArrayOf(3.1466, 101.6990)

@Composable
fun NavScreen() {
    val ctx = LocalContext.current
    val dark = isSystemInDarkTheme()
    val density = LocalView.current.resources.displayMetrics.density

    var map by remember { mutableStateOf<MapLibreMap?>(null) }
    var controller by remember { mutableStateOf<MapController?>(null) }
    var mapView by remember { mutableStateOf<MapView?>(null) }
    var route by remember { mutableStateOf<Route?>(null) }
    var tiles by remember { mutableStateOf<java.io.File?>(null) }
    var error by remember { mutableStateOf<String?>(null) }

    var following by remember { mutableStateOf(false) }
    var demo by remember { mutableStateOf(false) }
    var distance by remember { mutableDoubleStateOf(0.0) }

    // --- one-off loading off the main thread: the bundled PMTiles file and the recorded route -----------------------
    LaunchedEffect(Unit) {
        withContext(Dispatchers.IO) {
            runCatching {
                tiles = TileStore.ensure(ctx)
                route = Route.fromValhallaFixture(ctx.assets.open("route/kl-sentral-to-klcc.valhalla.json").bufferedReader().use { it.readText() })
            }.onFailure { error = "Could not load map data: ${it.message}" }
        }
    }

    // --- (re)build the style whenever the map, the data or the theme changes ---------------------------------------------
    LaunchedEffect(map, tiles, route, dark) {
        val m = map ?: return@LaunchedEffect
        val file = tiles
        if (file == null) {
            if (route != null) error = "This build has no bundled map data (run scripts/fetch-dev-tiles.sh, then rebuild)."
            return@LaunchedEffect
        }
        val styleJson = ctx.assets.open("style/aize-${if (dark) "dark" else "light"}.style.json").bufferedReader().use { it.readText() }
            .replace("{{TILES_URL}}", TileStore.url(file))
        controller = null
        m.setStyle(Style.Builder().fromJson(styleJson)) { style ->
            val c = MapController(m, style, PuckSprites(ctx.assets), dark)
            c.install(route)
            controller = c
        }
    }

    // --- real location (when permitted) ---------------------------------------------------------------------------------
    var hasPermission by remember {
        mutableStateOf(ContextCompat.checkSelfPermission(ctx, Manifest.permission.ACCESS_FINE_LOCATION) == PackageManager.PERMISSION_GRANTED)
    }
    val permissionLauncher = rememberLauncherForActivityResult(ActivityResultContracts.RequestPermission()) { hasPermission = it }
    var fix by remember { mutableStateOf<Location?>(null) }
    DisposableEffect(hasPermission) {
        if (!hasPermission) return@DisposableEffect onDispose { }
        val lm = ctx.getSystemService(Context.LOCATION_SERVICE) as LocationManager
        val listener = LocationListener { fix = it }
        @SuppressLint("MissingPermission")
        fun start() = runCatching {
            lm.getProviders(true).filter { it == LocationManager.GPS_PROVIDER || it == LocationManager.NETWORK_PROVIDER }
                .forEach { lm.requestLocationUpdates(it, 1000L, 0f, listener, android.os.Looper.getMainLooper()) }
        }
        start()
        onDispose { lm.removeUpdates(listener) }
    }

    // --- the real-location puck -------------------------------------------------------------------------------------------
    LaunchedEffect(fix, controller, demo) {
        val c = controller ?: return@LaunchedEffect
        val f = fix ?: return@LaunchedEffect
        if (demo) return@LaunchedEffect
        val m = map ?: return@LaunchedEffect
        val bearing = if (f.hasBearing()) f.bearing.toDouble() else m.cameraPosition.bearing
        c.setPuck(f.latitude, f.longitude, bearing, m.cameraPosition.bearing, m.cameraPosition.tilt)
        if (following) c.follow(f.latitude, f.longitude, bearing, durationMs = 800, topPaddingPx = (mapView?.height ?: 0) * 0.4)
    }

    // --- the demo drive: advance along the recorded route at constant speed, ~60 fps ------------------------------------------
    var bearingNow by remember { mutableDoubleStateOf(0.0) }
    LaunchedEffect(demo, controller, route) {
        val c = controller ?: return@LaunchedEffect
        val r = route ?: return@LaunchedEffect
        val m = map ?: return@LaunchedEffect
        if (!demo) return@LaunchedEffect
        following = true
        if (distance >= r.path.lengthMeters - 1) distance = 0.0
        bearingNow = r.path.headingAhead(distance, 40.0)
        var last = 0L
        while (distance < r.path.lengthMeters) {
            val now = androidx.compose.runtime.withFrameNanos { it }
            if (last != 0L) {
                val dt = (now - last) / 1e9
                distance = minOf(r.path.lengthMeters, distance + DEMO_SPEED_MPS * dt)
                val p = r.path.pointAt(distance)
                val target = r.path.headingAhead(distance, 40.0)
                if (following) {
                    bearingNow = RoutePath.smoothAngle(bearingNow, target, 1 - exp(-dt * 2.5))
                    c.follow(p.lat, p.lon, bearingNow, topPaddingPx = (mapView?.height ?: 0) * 0.4)
                }
                c.setPuck(p.lat, p.lon, p.heading, m.cameraPosition.bearing, m.cameraPosition.tilt)
                c.setPassed(r, distance)
            }
            last = now
        }
        demo = false
    }

    Box(Modifier.fillMaxSize()) {
        AndroidView(
            modifier = Modifier.fillMaxSize(),
            factory = { context ->
                MapLibre.getInstance(context)
                MapView(context).also { mv ->
                    mapView = mv
                    mv.getMapAsync { m ->
                        m.cameraPosition = org.maplibre.android.camera.CameraPosition.Builder()
                            .target(org.maplibre.android.geometry.LatLng(KL_CENTER[0], KL_CENTER[1])).zoom(11.5).build()
                        m.uiSettings.isLogoEnabled = false
                        m.uiSettings.isCompassEnabled = true
                        val dp = context.resources.displayMetrics.density
                        // keep the compass under the instruction banner and the OSM attribution above the bottom sheet (ODbL: must stay visible)
                        m.uiSettings.setCompassMargins(0, (150 * dp).toInt(), (12 * dp).toInt(), 0)
                        m.uiSettings.setAttributionMargins((12 * dp).toInt(), 0, 0, (168 * dp).toInt())
                        m.addOnCameraMoveStartedListener { reason ->
                            if (reason == MapLibreMap.OnCameraMoveStartedListener.REASON_API_GESTURE) following = false
                        }
                        map = m
                    }
                }
            },
        )
        val lifecycle = LocalLifecycleOwner.current.lifecycle
        DisposableEffect(lifecycle, mapView) {
            val mv = mapView
            val obs = LifecycleEventObserver { _, e ->
                when (e) {
                    Lifecycle.Event.ON_START -> mv?.onStart()
                    Lifecycle.Event.ON_RESUME -> mv?.onResume()
                    Lifecycle.Event.ON_PAUSE -> mv?.onPause()
                    Lifecycle.Event.ON_STOP -> mv?.onStop()
                    Lifecycle.Event.ON_DESTROY -> mv?.onDestroy()
                    else -> {}
                }
            }
            lifecycle.addObserver(obs)
            if (lifecycle.currentState.isAtLeast(Lifecycle.State.STARTED)) mv?.onStart()
            if (lifecycle.currentState.isAtLeast(Lifecycle.State.RESUMED)) mv?.onResume()
            onDispose { lifecycle.removeObserver(obs) }
        }

        val r = route
        // ------------------------------------------------------------------ instruction banner
        if (r != null && demo) {
            val g = r.guidanceAt(distance)
            val up = g.next
            Surface(
                modifier = Modifier.align(Alignment.TopCenter).windowInsetsPadding(WindowInsets.safeDrawing).padding(12.dp).fillMaxWidth()
                    .heightIn(min = AizeSize.INSTRUCTION_BANNER_MIN_HEIGHT),
                color = MaterialTheme.colorScheme.primary, contentColor = MaterialTheme.colorScheme.onPrimary,
                shape = RoundedCornerShape(AizeRadius.LG), shadowElevation = 6.dp,
            ) {
                Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.Center) {
                    Text(formatDistance(g.metersToNext), fontSize = 30.sp, fontWeight = FontWeight.Bold)
                    Text(up?.instruction ?: "Arrive at your destination", fontSize = 17.sp, maxLines = 2)
                }
            }
        }

        // ------------------------------------------------------------------ bottom bar
        Surface(
            modifier = Modifier.align(Alignment.BottomCenter).fillMaxWidth(),
            color = MaterialTheme.colorScheme.surface, tonalElevation = 3.dp, shadowElevation = 10.dp,
            shape = RoundedCornerShape(topStart = AizeRadius.SHEET, topEnd = AizeRadius.SHEET),
        ) {
            Column(Modifier.windowInsetsPadding(WindowInsets.navigationBars).padding(horizontal = 16.dp, vertical = 14.dp)) {
                when {
                    error != null -> Text(error!!, color = MaterialTheme.colorScheme.error)
                    r == null || controller == null -> Text("Loading map…", color = MaterialTheme.colorScheme.onSurfaceVariant)
                    else -> {
                        val left = r.path.lengthMeters - distance
                        val secs = r.durationSeconds * (left / r.path.lengthMeters)
                        Text(
                            if (demo) "${formatDistance(left)} · ${(secs / 60).roundToInt().coerceAtLeast(1)} min left" else "KL Sentral → KLCC · ${formatDistance(r.path.lengthMeters)}",
                            fontSize = 18.sp, fontWeight = FontWeight.SemiBold,
                        )
                        Text(
                            if (demo) "Demo drive (recorded route, ${(DEMO_SPEED_MPS * 3.6).roundToInt()} km/h)" else "Aize 0.0.1 · P0 walking skeleton",
                            color = MaterialTheme.colorScheme.onSurfaceVariant, fontSize = 13.sp,
                        )
                    }
                }
                Spacer(Modifier.height(10.dp))
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp), verticalAlignment = Alignment.CenterVertically) {
                    Button(
                        onClick = { demo = !demo },
                        enabled = controller != null && r != null,
                        modifier = Modifier.heightIn(min = AizeSize.TOUCH_TARGET).weight(1f),
                        shape = RoundedCornerShape(AizeRadius.BUTTON_NORMAL),
                    ) { Text(if (demo) "Stop" else "Demo drive") }
                    OutlinedButton(
                        onClick = {
                            val c = controller
                            val m = map
                            when {
                                c == null || m == null -> {}
                                demo || fix != null -> {
                                    following = true
                                    val f = fix
                                    if (!demo && f != null) c.follow(f.latitude, f.longitude, if (f.hasBearing()) f.bearing.toDouble() else 0.0, durationMs = 600, topPaddingPx = (mapView?.height ?: 0) * 0.4)
                                }
                                r != null -> c.overview(r, (24 * density).roundToInt())
                            }
                        },
                        modifier = Modifier.heightIn(min = AizeSize.TOUCH_TARGET),
                        shape = RoundedCornerShape(AizeRadius.BUTTON_NORMAL),
                    ) { Text(if (demo || fix != null) "Recenter" else "Overview") }
                }
                if (!hasPermission) {
                    TextButton(onClick = { permissionLauncher.launch(Manifest.permission.ACCESS_FINE_LOCATION) }) { Text("Enable my location") }
                }
            }
        }
    }
}

private fun formatDistance(m: Double): String = when {
    m >= 10_000 -> "${(m / 1000).roundToInt()} km"
    m >= 1000 -> String.format(java.util.Locale.US, "%.1f km", m / 1000)
    m >= 100 -> "${(m / 10).roundToInt() * 10} m"
    else -> "${m.roundToInt()} m"
}
