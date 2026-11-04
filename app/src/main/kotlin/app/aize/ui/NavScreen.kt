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
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material3.OutlinedTextField
import androidx.compose.ui.text.input.ImeAction
import androidx.core.content.ContextCompat
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.LifecycleEventObserver
import app.aize.design.AizeRadius
import app.aize.design.AizeSize
import app.aize.map.MapController
import app.aize.map.PuckSprites
import app.aize.map.TileStore
import app.aize.nav.EtaEngine
import app.aize.nav.NavService
import app.aize.nav.NavSession
import app.aize.nav.OffRouteDetector
import app.aize.nav.Route
import app.aize.net.PlaceResult
import app.aize.net.RouteClient
import app.aize.net.SearchClient
import app.aize.net.ServerSettings
import app.aize.nav.RoutePath
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import org.maplibre.android.geometry.LatLng
import org.maplibre.android.MapLibre
import org.maplibre.android.maps.MapLibreMap
import org.maplibre.android.maps.MapView
import org.maplibre.android.maps.Style
import kotlin.math.exp
import kotlin.math.roundToInt

private const val DEMO_SPEED_MPS = 22.0          // ~80 km/h: the 9 km demo route takes ~7 minutes
private val KL_CENTER = doubleArrayOf(3.1466, 101.6990)
private val KL_SENTRAL = doubleArrayOf(3.1343, 101.6862)

@Composable
fun NavScreen() {
    val ctx = LocalContext.current
    // day/night follows the ThemeMode policy (auto = clock, or the driver's manual choice)
    val themeMode by ThemeMode.mode.collectAsState()
    val dark = ThemeMode.isDark(themeMode)
    val density = LocalView.current.resources.displayMetrics.density

    var map by remember { mutableStateOf<MapLibreMap?>(null) }
    var controller by remember { mutableStateOf<MapController?>(null) }
    var mapView by remember { mutableStateOf<MapView?>(null) }
    var route by remember { mutableStateOf<Route?>(null) }
    var tiles by remember { mutableStateOf<java.io.File?>(null) }
    var error by remember { mutableStateOf<String?>(null) }

    var routeLabel by remember { mutableStateOf("KL Sentral → KLCC (recorded)") }
    var serverUrl by remember { mutableStateOf(ServerSettings.get(ctx)) }
    var showServer by remember { mutableStateOf(false) }
    var routing by remember { mutableStateOf(false) }
    var notice by remember { mutableStateOf<String?>(null) }
    var pendingDest by remember { mutableStateOf<LatLng?>(null) }
    var destination by remember { mutableStateOf<LatLng?>(null) }      // where the live route is heading; kept for re-routing
    var segmentHint by remember { mutableIntStateOf(0) }
    val offRoute = remember { OffRouteDetector() }
    var armed by remember { mutableStateOf(false) }
    var showSearch by remember { mutableStateOf(false) }
    var query by remember { mutableStateOf("") }
    var results by remember { mutableStateOf<List<PlaceResult>>(emptyList()) }
    var searching by remember { mutableStateOf(false) }
    var arrived by remember { mutableStateOf(false) }          // a route starts on the nearest road, which can be far from the fix: only judge "off route" after being on it
    val scope = rememberCoroutineScope()

    // the foreground service owns the hot loop while a route is active; the UI draws what it publishes
    val nav by NavSession.state.collectAsState()
    val notifyPermission = rememberLauncherForActivityResult(ActivityResultContracts.RequestPermission()) { }

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

    /** Hands the route to the foreground service so guidance, voice and the notification survive the screen going off. */
    fun startNavigation(r: Route) {
        NavSession.start(r)
        if (android.os.Build.VERSION.SDK_INT >= 33 &&
            ContextCompat.checkSelfPermission(ctx, Manifest.permission.POST_NOTIFICATIONS) != PackageManager.PERMISSION_GRANTED
        ) {
            notifyPermission.launch(Manifest.permission.POST_NOTIFICATIONS)
        }
        runCatching { NavService.start(ctx) }
            .onFailure { notice = "Could not start background navigation: ${it.message}" }
    }

    // --- show whichever route is current ---------------------------------------------------------------------------------
    LaunchedEffect(route, controller) { controller?.setRoute(route) }

    // --- pick a destination (long-press) -> ask the Valhalla server for a route from here --------------------------------------
    var fix by remember { mutableStateOf<Location?>(null) }
    LaunchedEffect(pendingDest) {
        val dest = pendingDest ?: return@LaunchedEffect
        val origin = fix?.let { doubleArrayOf(it.latitude, it.longitude) } ?: doubleArrayOf(KL_SENTRAL[0], KL_SENTRAL[1])
        demo = false; distance = 0.0; routing = true; notice = null; destination = dest; segmentHint = 0; offRoute.reset(); armed = false
        val result = withContext(Dispatchers.IO) {
            runCatching { RouteClient.route(serverUrl, origin[0], origin[1], dest.latitude, dest.longitude) }
        }
        routing = false
        result.onSuccess {
            android.util.Log.i("Aize", "route dest=${dest.latitude},${dest.longitude} len=${it.path.lengthMeters.roundToInt()}m")
            route = it
            routeLabel = (if (fix != null) "Your location" else "KL Sentral") + " → pin · live route"
            controller?.overview(it, (24 * density).roundToInt())
            startNavigation(it)
        }.onFailure { notice = it.message ?: "Routing failed" }
    }

    // --- the service decides the driver has left the route (it keeps working with the screen off) -------------------
    // One sequential worker: a tick that arrives while a re-route is in flight is ignored rather than cancelling
    // the request, and the loading flag is always cleared in `finally`.
    var rerouting by remember { mutableStateOf(false) }
    LaunchedEffect(Unit) {
        NavSession.rerouteTicks.collect { tick ->
            if (tick <= 0 || rerouting) return@collect
            val dest = destination ?: return@collect
            val here = fix ?: return@collect
            rerouting = true; routing = true; notice = "Off route — finding a new one…"
            try {
                val res = withContext(Dispatchers.IO) {
                    runCatching { RouteClient.route(serverUrl, here.latitude, here.longitude, dest.latitude, dest.longitude) }
                }
                res.onSuccess {
                    android.util.Log.i("Aize", "rerouted len=${it.path.lengthMeters.roundToInt()}m")
                    route = it; armed = false; segmentHint = 0; distance = 0.0; notice = null
                    routeLabel = "Your location → pin · re-routed"
                    startNavigation(it)
                }.onFailure { notice = it.message ?: "Re-routing failed" }
            } finally {
                routing = false; rerouting = false
            }
        }
    }

    // --- place search: debounce typing, ask the server, keep the last good results -------------------------------
    LaunchedEffect(query, serverUrl) {
        if (query.trim().length < 2) { results = emptyList(); return@LaunchedEffect }
        searching = true
        kotlinx.coroutines.delay(280)
        val r = withContext(Dispatchers.IO) {
            runCatching { SearchClient.search(serverUrl, query.trim(), fix?.latitude, fix?.longitude) }
        }
        searching = false
        r.onSuccess { results = it }.onFailure { results = emptyList() }
    }

    // --- real location (when permitted) ---------------------------------------------------------------------------------
    var hasPermission by remember {
        mutableStateOf(ContextCompat.checkSelfPermission(ctx, Manifest.permission.ACCESS_FINE_LOCATION) == PackageManager.PERMISSION_GRANTED)
    }
    val permissionLauncher = rememberLauncherForActivityResult(ActivityResultContracts.RequestPermission()) { hasPermission = it }
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

        // follow a live route: snap the fix onto it (drives the banner and the greyed-out part), re-route when really off it
        val r = route
        val dest = destination
        if (r != null && dest != null && !routing) {
            val proj = r.path.project(f.latitude, f.longitude, fromSegment = maxOf(0, segmentHint - 2), window = 200)
            val away = if (proj.offRoute > 40.0) r.path.project(f.latitude, f.longitude) else proj      // lost it? search the whole route
            segmentHint = away.segment
            distance = away.along
            c.setPassed(r, away.along)
            if (away.offRoute <= 40.0) armed = true
            arrived = r.path.lengthMeters - away.along < 30.0
            if (armed && offRoute.update(away.offRoute, System.currentTimeMillis())) {
                routing = true; notice = "Off route — finding a new one…"
                scope.launch {
                    val res = withContext(Dispatchers.IO) { runCatching { RouteClient.route(serverUrl, f.latitude, f.longitude, dest.latitude, dest.longitude) } }
                    routing = false
                    res.onSuccess { android.util.Log.i("Aize", "rerouted len=${it.path.lengthMeters.roundToInt()}m"); route = it; armed = false; segmentHint = 0; distance = 0.0; notice = null; routeLabel = "Your location → pin · re-routed" }
                        .onFailure { notice = it.message ?: "Re-routing failed" }
                }
            }
        }
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
                        m.addOnMapLongClickListener { pendingDest = it; true }
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
        if (r != null && !showSearch) {
            val g = r.guidanceAt(distance)
            val up = g.next
            val serviceOwned = nav.active
            Surface(
                modifier = Modifier.align(Alignment.TopCenter).windowInsetsPadding(WindowInsets.safeDrawing).padding(12.dp).fillMaxWidth()
                    .heightIn(min = AizeSize.INSTRUCTION_BANNER_MIN_HEIGHT),
                color = MaterialTheme.colorScheme.primary, contentColor = MaterialTheme.colorScheme.onPrimary,
                shape = RoundedCornerShape(AizeRadius.LG), shadowElevation = 6.dp,
            ) {
                Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.Center) {
                    val isArrived = arrived || nav.arrived
                    Text(
                        if (isArrived) "Arrived" else formatDistance(if (serviceOwned) nav.metersToInstruction else g.metersToNext),
                        fontSize = 30.sp, fontWeight = FontWeight.Bold,
                    )
                    Text(
                        if (isArrived) (if (serviceOwned) nav.instruction ?: g.current.instruction else g.current.instruction)
                        else (if (serviceOwned) nav.instruction ?: (up?.instruction ?: "Arrive at your destination") else (up?.instruction ?: "Arrive at your destination")),
                        fontSize = 17.sp, maxLines = 2,
                    )
                    val after = r.maneuvers.getOrNull(r.maneuvers.indexOf(g.next) + 1)
                    if (!arrived && after != null) {
                        Text("then ${after.instruction}", fontSize = 13.sp, maxLines = 1,
                            color = LocalContentColor.current.copy(alpha = 0.8f))
                    }
                    // remaining distance, time left and arrival clock, from the service when it is driving
                    val remainingMeters = if (serviceOwned) nav.remainingMeters else r.path.lengthMeters - distance
                    val etaLine = if (serviceOwned && nav.eta != null) {
                        "${formatDistance(remainingMeters)} · ${nav.eta}"
                    } else {
                        val secs = EtaEngine.estimate(r, distance, 0.0)
                        "${formatDistance(remainingMeters)} · ${EtaEngine.summary(secs, System.currentTimeMillis())}"
                    }
                    if (!isArrived) {
                        Text(etaLine, fontSize = 13.sp, fontWeight = FontWeight.Medium,
                            color = LocalContentColor.current.copy(alpha = 0.9f))
                    }
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
                    routing -> Text("Finding a route…", color = MaterialTheme.colorScheme.onSurfaceVariant)
                    notice != null -> Text(notice!!, color = MaterialTheme.colorScheme.error)
                    r == null || controller == null -> Text("Loading map…", color = MaterialTheme.colorScheme.onSurfaceVariant)
                    else -> {
                        val left = r.path.lengthMeters - distance
                        val secs = r.durationSeconds * (left / r.path.lengthMeters)
                        Text(
                            if (demo) "${formatDistance(left)} · ${(secs / 60).roundToInt().coerceAtLeast(1)} min left" else "$routeLabel · ${formatDistance(r.path.lengthMeters)}",
                            fontSize = 18.sp, fontWeight = FontWeight.SemiBold,
                        )
                        Text(
                            if (demo) "Demo drive (recorded route, ${(DEMO_SPEED_MPS * 3.6).roundToInt()} km/h)" else "Search or long-press the map for a destination",
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
                Row {
                    if (nav.active) {
                        TextButton(onClick = {
                            NavService.stop(ctx)
                            NavSession.stop()
                            controller?.setRoute(null)
                            route = null
                            demo = false
                        }) { Text("End navigation") }
                    }
                    if (!hasPermission) {
                        TextButton(onClick = { permissionLauncher.launch(Manifest.permission.ACCESS_FINE_LOCATION) }) { Text("Enable my location") }
                    }
                    TextButton(onClick = { showSearch = true }) { Text("Search") }
                    TextButton(onClick = { showServer = true }) { Text("Server") }
                    TextButton(onClick = { ThemeMode.cycle(ctx) }) { Text(ThemeMode.label(themeMode)) }
                    val muted by NavSession.muted.collectAsState()
                    TextButton(onClick = {
                        NavSession.setMuted(!muted)
                        ctx.getSharedPreferences("aize", Context.MODE_PRIVATE).edit().putBoolean("voice_muted", !muted).apply()
                    }) { Text(if (muted) "Voice off" else "Voice on") }
                }
            }
        }
        // ------------------------------------------------------------------ search
        if (showSearch) {
            Surface(Modifier.fillMaxSize().windowInsetsPadding(WindowInsets.safeDrawing), color = MaterialTheme.colorScheme.surface) {
                Column(Modifier.padding(12.dp)) {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        OutlinedTextField(
                            value = query, onValueChange = { query = it }, modifier = Modifier.weight(1f),
                            singleLine = true, placeholder = { Text("Search a place in Malaysia") },
                            keyboardOptions = KeyboardOptions(imeAction = ImeAction.Search),
                        )
                        TextButton(onClick = { showSearch = false; query = ""; results = emptyList() }) { Text("Close") }
                    }
                    if (searching) LinearProgressIndicator(Modifier.fillMaxWidth().padding(vertical = 6.dp))
                    if (results.isEmpty() && !searching && query.trim().length >= 2) {
                        Text("No places found", color = MaterialTheme.colorScheme.onSurfaceVariant, modifier = Modifier.padding(12.dp))
                    }
                    LazyColumn(Modifier.fillMaxSize()) {
                        items(results) { p ->
                            ListItem(
                                headlineContent = { Text(p.name) },
                                supportingContent = {
                                    val bits = mutableListOf(kindLabel(p.kind))
                                    if (p.distanceMeters > 0) bits += formatDistance(p.distanceMeters.toDouble())
                                    Text(bits.joinToString(" \u00b7 "))
                                },
                                modifier = Modifier.clickable {
                                    pendingDest = LatLng(p.lat, p.lon); showSearch = false; query = ""; results = emptyList()
                                },
                            )
                            HorizontalDivider()
                        }
                    }
                }
            }
        }
    }

    if (showServer) {
        var text by remember { mutableStateOf(serverUrl) }
        var testResult by remember { mutableStateOf<String?>(null) }
        var testing by remember { mutableStateOf(false) }
        AlertDialog(
            onDismissRequest = { showServer = false },
            title = { Text("Routing server") },
            text = {
                Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    Text("Address of a Valhalla server, e.g. https://example.com or 192.168.1.20:8002. The emulator reaches the host at 10.0.2.2.", fontSize = 13.sp)
                    OutlinedTextField(value = text, onValueChange = { text = it; testResult = null }, singleLine = true, label = { Text("Server address") })
                    TextButton(enabled = !testing, onClick = {
                        testing = true; testResult = "Testing…"
                        scope.launch {
                            val r = withContext(Dispatchers.IO) { runCatching { RouteClient.status(text) } }
                            testResult = r.fold({ "Connected: $it" }, { "Failed: ${it.message}" }); testing = false
                        }
                    }) { Text("Test connection") }
                    testResult?.let { Text(it, fontSize = 13.sp, color = if (it.startsWith("Failed")) MaterialTheme.colorScheme.error else MaterialTheme.colorScheme.primary) }
                }
            },
            confirmButton = { TextButton(onClick = { ServerSettings.set(ctx, text); serverUrl = ServerSettings.get(ctx); showServer = false }) { Text("Save") } },
            dismissButton = { TextButton(onClick = { showServer = false }) { Text("Cancel") } },
        )
    }
}

/** "shop=mall" -> "Mall"; "highway=residential" -> "Road". */
private fun kindLabel(kind: String): String {
    val v = kind.substringAfter('=', "").substringBefore(';').replace('_', ' ')
    return when {
        v.isBlank() -> "Place"
        kind.startsWith("highway=") -> if (v == "bus stop") "Bus stop" else "Road"
        kind.startsWith("place=") -> v.replaceFirstChar { it.uppercase() }
        else -> v.replaceFirstChar { it.uppercase() }
    }
}

private fun formatDistance(m: Double): String = when {
    m >= 10_000 -> "${(m / 1000).roundToInt()} km"
    m >= 1000 -> String.format(java.util.Locale.US, "%.1f km", m / 1000)
    m >= 100 -> "${(m / 10).roundToInt() * 10} m"
    else -> "${m.roundToInt()} m"
}
