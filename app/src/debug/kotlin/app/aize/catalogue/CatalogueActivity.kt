package app.aize.catalogue

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.MaterialTheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import app.aize.AizeTheme
import app.aize.ui.ThemeMode

/**
 * The design catalogue as its own activity, in the debug source set only.
 *
 * It is an activity rather than a screen behind a menu for one reason: a screenshot test should be able to say
 * `am start -n app.aize/.CatalogueActivity --es section icon` and get that page, with no taps, no scroll position
 * and no state left over from a previous run. The release build does not compile this file.
 */
class CatalogueActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        ThemeMode.load(this)
        val start = CatalogueSection.fromId(intent.getStringExtra("section")) ?: CatalogueSection.Colour
        setContent {
            val mode by ThemeMode.mode.collectAsState()
            val dark = ThemeMode.isDark(mode)
            AizeTheme(dark = dark) { Catalogue(start, dark) }
        }
    }
}

@Composable
private fun Catalogue(start: CatalogueSection, dark: Boolean) {
    var section by remember { mutableStateOf(start) }
    androidx.compose.foundation.layout.Box(
        Modifier
            .fillMaxSize()
            .background(MaterialTheme.colorScheme.surface)
            .padding(top = 28.dp),
    ) {
        DesignCatalogue(section = section, onPick = { section = it }, dark = dark)
    }
}
