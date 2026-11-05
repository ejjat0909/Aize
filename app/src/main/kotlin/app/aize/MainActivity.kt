package app.aize

import android.os.Bundle
import android.util.Log
import androidx.metrics.performance.JankStats
import androidx.metrics.performance.PerformanceMetricsState
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import app.aize.design.AizeColorSchemes
import app.aize.ui.AizeApp
import app.aize.ui.ThemeMode

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        ThemeMode.load(this)
        app.aize.nav.NavSession.setMuted(getSharedPreferences("aize", MODE_PRIVATE).getBoolean("voice_muted", false))
        setContent {
            val mode by ThemeMode.mode.collectAsState()
            AizeTheme(dark = ThemeMode.isDark(mode)) { AizeApp() }
        }
        if (BuildConfig.DEBUG) startJankStats()
    }

    private var jank: JankStats? = null

    /** Debug builds log every janky frame under the tag "AizeJank" (read with `adb logcat -s AizeJank`). */
    private fun startJankStats() {
        PerformanceMetricsState.getHolderForHierarchy(window.decorView)
        jank = JankStats.createAndTrack(window) { f ->
            if (f.isJank) Log.w("AizeJank", "frame ${f.frameDurationUiNanos / 1_000_000} ms")
        }.also { it.isTrackingEnabled = true }
    }
}

@Composable
fun AizeTheme(dark: Boolean = isSystemInDarkTheme(), content: @Composable () -> Unit) {
    MaterialTheme(colorScheme = if (dark) AizeColorSchemes.dark else AizeColorSchemes.light, content = content)
}
