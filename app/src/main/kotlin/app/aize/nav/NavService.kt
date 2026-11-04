package app.aize.nav

import android.Manifest
import android.annotation.SuppressLint
import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.app.Service
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.content.pm.ServiceInfo
import android.location.Location
import android.location.LocationListener
import android.location.LocationManager
import android.os.Build
import android.os.IBinder
import android.os.Looper
import android.util.Log
import androidx.core.app.NotificationCompat
import androidx.core.content.ContextCompat
import app.aize.MainActivity
import app.aize.R
import kotlin.math.roundToInt
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow

/**
 * Keeps navigation alive while the app is in the background: location, guidance, voice and a notification
 * that shows the next instruction. This is what makes the phone usable in a car bracket with the screen off.
 *
 * The route itself arrives through [NavSession] (same process). The service owns the hot loop; the UI only
 * draws what the service publishes, so the two can never disagree about where the driver is.
 */
class NavService : Service(), LocationListener {

    private lateinit var voice: Voice
    private lateinit var manager: NotificationManager
    private val announcer = GuidanceAnnouncer()
    private val offRoute = OffRouteDetector()
    private val eta = EtaEngine()
    private var armed = false
    private var currentRoute: Route? = null
    private var baselineOff: Double? = null
    private var lastNotification: String? = null
    private var lastNotificationAt = 0L

    override fun onCreate() {
        super.onCreate()
        voice = Voice(this).also { it.start() }
        manager = getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
        createChannel()
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        when (intent?.action) {
            ACTION_STOP -> { stopSelf(); return START_NOT_STICKY }
            else -> {
                val route = NavSession.route
                if (route == null) { stopSelf(); return START_NOT_STICKY }
                startInForeground("Preparing route…")
                announcer.reset()
                offRoute.reset()
                armed = false
                startLocation()
            }
        }
        return START_NOT_STICKY
    }

    private fun startInForeground(text: String) {
        val n = buildNotification(text, "", 0)
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            startForeground(NOTIFICATION_ID, n, ServiceInfo.FOREGROUND_SERVICE_TYPE_LOCATION)
        } else {
            startForeground(NOTIFICATION_ID, n)
        }
    }

    private fun createChannel() {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.O) return
        val ch = NotificationChannel(CHANNEL_ID, "Navigation", NotificationManager.IMPORTANCE_LOW).apply {
            description = "Turn-by-turn guidance while navigating"
            setShowBadge(false)
            enableVibration(false)
            setSound(null, null)
        }
        manager.createNotificationChannel(ch)
    }

    private fun buildNotification(instruction: String, distance: String, progress: Int): Notification {
        val open = PendingIntent.getActivity(
            this, 0, Intent(this, MainActivity::class.java).addFlags(Intent.FLAG_ACTIVITY_SINGLE_TOP),
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE,
        )
        val stop = PendingIntent.getService(
            this, 1, Intent(this, NavService::class.java).setAction(ACTION_STOP),
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE,
        )
        return NotificationCompat.Builder(this, CHANNEL_ID)
            .setSmallIcon(R.drawable.ic_launcher_foreground)
            .setContentTitle(instruction.ifEmpty { "Aize navigation" })
            .setContentText(distance)
            .setContentIntent(open)
            .addAction(0, "Stop", stop)
            .setOngoing(true)
            .setOnlyAlertOnce(true)
            .setSilent(true)
            .setCategory(NotificationCompat.CATEGORY_NAVIGATION)
            .setVisibility(NotificationCompat.VISIBILITY_PUBLIC)
            .setProgress(100, progress, false)
            .build()
    }

    @SuppressLint("MissingPermission")
    private fun startLocation() {
        if (ContextCompat.checkSelfPermission(this, Manifest.permission.ACCESS_FINE_LOCATION) != PackageManager.PERMISSION_GRANTED) {
            Log.w("AizeNav", "no location permission: the service cannot follow the route")
            return
        }
        val lm = getSystemService(Context.LOCATION_SERVICE) as LocationManager
        val providers = lm.getProviders(true).filter { it == LocationManager.GPS_PROVIDER || it == LocationManager.NETWORK_PROVIDER }
        providers.forEach { lm.requestLocationUpdates(it, 1000L, 0f, this, Looper.getMainLooper()) }
        Log.i("AizeNav", "listening on $providers")
    }

    override fun onLocationChanged(location: Location) = onFix(location)

    /** The hot loop: one fix in, state + voice + notification out. Visible for tests. */
    fun onFix(fix: Location) {
        val route = NavSession.route ?: return
        if (route !== currentRoute) {
            // a new route (first one, or a reroute): forget what was announced for the old one
            currentRoute = route
            announcer.reset()
            offRoute.reset()
            eta.reset()
            armed = false
            baselineOff = null
        }
        val proj = route.path.project(fix.latitude, fix.longitude)
        val along = proj.along
        val off = proj.offRoute
        // Valhalla starts a route on the nearest road, which can be tens of metres from the first fix. Arm
        // off-route detection once the driver is as close as that first snap, and has actually moved along.
        val baseline = baselineOff ?: off.also { baselineOff = it }
        if (!armed && off <= maxOf(40.0, baseline + 20.0) && proj.along >= 20.0) armed = true

        val ahead = route.aheadAt(along)
        val remaining = (route.path.lengthMeters - along).coerceAtLeast(0.0)
        val arrived = route.path.lengthMeters - along < 30.0

        val speedMps = if (fix.hasSpeed()) fix.speed.toDouble() else 0.0
        val remainingSeconds = eta.next(route, along, speedMps)
        val etaText = EtaEngine.formatMinutes(remainingSeconds)
        val arrival = EtaEngine.formatArrival(System.currentTimeMillis(), remainingSeconds)
        val p = announcer.update(route, along, speedMps, System.currentTimeMillis())
        if (p != null) {
            NavSession.lastPrompt = p.text
            if (NavSession.muted.value) Log.i("AizeVoice", "muted: ${p.text}") else voice.say(p.text)
        }

        NavSession.publish(
            NavSession.State(
                active = true,
                alongMeters = along,
                lengthMeters = route.path.lengthMeters,
                remainingMeters = remaining,
                offRouteMeters = off,
                arrived = arrived,
                instruction = ahead?.maneuver?.instruction ?: "Arrive at your destination",
                metersToInstruction = ahead?.metersToStart ?: 0.0,
                after = ahead?.after?.instruction,
                remainingSeconds = remainingSeconds,
                eta = "$etaText · $arrival",
                fixes = NavSession.state.value.fixes + 1,
            ),
        )

        if (offRoute.update(off, System.currentTimeMillis())) {
            if (armed) {
                Log.i("AizeNav", "off route by ${off.roundToInt()} m after ${NavSession.state.value.fixes} fixes: re-routing")
                NavSession.requestReroute()
            } else {
                Log.i("AizeNav", "off route by ${off.roundToInt()} m but not armed yet (never been on the route)")
            }
        }

        if (arrived) {
            stopSelf()
            return
        }
        updateNotification(ahead?.maneuver?.instruction ?: "Arrive at your destination", remaining, etaText, arrival)
    }

    private fun updateNotification(instruction: String, remaining: Double, etaText: String, arrival: String) {
        val text = "${formatDistance(remaining)} · $etaText · $arrival"
        val now = System.currentTimeMillis()
        // one update per second at most, and only when the text actually changed
        if (text == lastNotification && now - lastNotificationAt < 5_000) return
        lastNotification = text
        lastNotificationAt = now
        val total = NavSession.route?.path?.lengthMeters ?: 0.0
        val along = NavSession.state.value.alongMeters
        val progress = if (total <= 0.0) 0 else ((along / total) * 100).toInt().coerceIn(0, 100)
        manager.notify(NOTIFICATION_ID, buildNotification(instruction, text, progress))
    }

    override fun onDestroy() {
        val lm = getSystemService(Context.LOCATION_SERVICE) as? LocationManager
        runCatching { lm?.removeUpdates(this) }
        voice.stop()
        NavSession.stop()
        Log.i("AizeNav", "service stopped")
        super.onDestroy()
    }

    override fun onBind(intent: Intent?): IBinder? = null

    companion object {
        const val ACTION_START = "app.aize.nav.START"
        const val ACTION_STOP = "app.aize.nav.STOP"
        private const val CHANNEL_ID = "aize-navigation"
        private const val NOTIFICATION_ID = 42

        fun start(ctx: Context) {
            val i = Intent(ctx, NavService::class.java).setAction(ACTION_START)
            ContextCompat.startForegroundService(ctx, i)
        }

        fun stop(ctx: Context) {
            ctx.stopService(Intent(ctx, NavService::class.java))
        }

        fun formatDistance(meters: Double): String = when {
            meters >= 1000.0 -> String.format(java.util.Locale.US, "%.1f km", meters / 1000.0)
            else -> "${(meters / 10).toInt() * 10} m"
        }
    }
}
