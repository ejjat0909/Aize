package app.aize.ui.onboard

import android.Manifest
import android.content.pm.PackageManager
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.animation.AnimatedContent
import androidx.compose.animation.core.tween
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.animation.togetherWith
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.core.content.ContextCompat
import app.aize.net.ServerSettings
import app.aize.BuildConfig
import app.aize.telemetry.Telemetry
import app.aize.ui.component.AizeButton
import app.aize.ui.component.AizeButtonSize
import app.aize.ui.component.AizeSwitch
import app.aize.ui.component.AizeButtonKind
import app.aize.ui.icon.AizeIcons

/**
 * The first run.
 *
 * The order is the argument: what this is, how it works, why it needs location, what it does with your data, then
 * the way in. Asking for a permission before explaining it is how apps get refused, and the permission is asked
 * for here rather than as a surprise on the map.
 */
@Composable
fun OnboardingScreen(onDone: () -> Unit) {
    var step by remember { mutableStateOf(OnboardingStep.Welcome) }
    var permissionAsked by remember { mutableStateOf(false) }
    val context = LocalContext.current
    var granted by remember {
        mutableStateOf(
            ContextCompat.checkSelfPermission(context, Manifest.permission.ACCESS_FINE_LOCATION) == PackageManager.PERMISSION_GRANTED,
        )
    }

    val requestLocation = rememberLauncherForActivityResult(ActivityResultContracts.RequestPermission()) { ok ->
        granted = ok
        permissionAsked = true
    }

    Column(
        Modifier
            .fillMaxSize()
            .background(MaterialTheme.colorScheme.surface)
            .padding(horizontal = 24.dp, vertical = 24.dp),
    ) {
        StepDots(current = step)

        Column(
            Modifier
                .weight(1f)
                .fillMaxWidth()
                .verticalScroll(rememberScrollState()),
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.Center,
        ) {
            AnimatedContent(
                targetState = step,
                transitionSpec = { fadeIn(tween(180)) togetherWith fadeOut(tween(120)) },
                label = "onboarding",
            ) { shown ->
                Column(horizontalAlignment = Alignment.CenterHorizontally) {
                    Box(
                        Modifier
                            .size(96.dp)
                            .background(MaterialTheme.colorScheme.primaryContainer, CircleShape),
                        contentAlignment = Alignment.Center,
                    ) {
                        Icon(iconFor(shown), contentDescription = null, tint = MaterialTheme.colorScheme.onPrimaryContainer, modifier = Modifier.size(48.dp))
                    }
                    Spacer(Modifier.height(24.dp))
                    Text(
                        titleFor(shown),
                        fontSize = 26.sp,
                        fontWeight = FontWeight.Bold,
                        textAlign = TextAlign.Center,
                        color = MaterialTheme.colorScheme.onSurface,
                    )
                    Spacer(Modifier.height(12.dp))
                    Text(
                        bodyFor(shown),
                        fontSize = 15.sp,
                        textAlign = TextAlign.Center,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )

                    if (shown == OnboardingStep.Location && !granted) {
                        Spacer(Modifier.height(20.dp))
                        AizeButton(
                            text = if (permissionAsked) "Ask again" else "Allow location",
                            onClick = { requestLocation.launch(Manifest.permission.ACCESS_FINE_LOCATION) },
                            leading = AizeIcons.Recenter,
                        )
                        if (permissionAsked) {
                            Spacer(Modifier.height(10.dp))
                            Text(
                                "You can turn it on later from the map. Until then Aize can search and show the map, but it cannot follow you.",
                                fontSize = 13.sp,
                                textAlign = TextAlign.Center,
                                color = MaterialTheme.colorScheme.onSurfaceVariant,
                            )
                        }
                    }

                    if (shown == OnboardingStep.Privacy) {
                        Spacer(Modifier.height(20.dp))
                        var telemetryOn by remember { mutableStateOf(Telemetry.isEnabled(context)) }
                        AizeSwitch(
                            checked = telemetryOn,
                            onCheckedChange = { on ->
                                telemetryOn = on
                                Telemetry.setEnabled(context, on)
                            },
                            label = "Share anonymous usage data",
                            description = "Counts of what worked and what failed. No location, no identifiers, no text.",
                            modifier = Modifier.fillMaxWidth(),
                        )
                    }

                    // which server this build talks to is a developer fact, not a user-facing one
                    if (shown == OnboardingStep.Ready && BuildConfig.DEBUG) {
                        Spacer(Modifier.height(20.dp))
                        Text(
                            "Server: ${ServerSettings.get(context)}",
                            fontSize = 12.sp,
                            textAlign = TextAlign.Center,
                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                        )
                    }
                }
            }
        }

        val back = Onboarding.back(step)
        val next = Onboarding.next(step)
        Row(
            Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.spacedBy(12.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            if (back != null) {
                AizeButton("Back", onClick = { step = back }, kind = AizeButtonKind.Ghost, modifier = Modifier.weight(1f))
            }
            AizeButton(
                text = if (next == null) "Start driving" else "Next",
                onClick = {
                    if (next == null) onDone() else step = next
                },
                size = AizeButtonSize.Large,
                modifier = Modifier.weight(if (back == null) 1f else 1.4f),
            )
        }
        // on the last step there is nothing left to skip: "Start driving" is the same door
        if (next != null) {
            Spacer(Modifier.height(8.dp))
            AizeButton(
                "Skip the tour",
                onClick = onDone,
                kind = AizeButtonKind.Ghost,
                size = AizeButtonSize.Small,
                modifier = Modifier.fillMaxWidth(),
            )
        }
    }
}

@Composable
private fun StepDots(current: OnboardingStep) {
    Row(
        Modifier.fillMaxWidth().padding(bottom = 8.dp),
        horizontalArrangement = Arrangement.Center,
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Onboarding.steps.forEach { step ->
            val here = step == current
            Box(
                Modifier
                    .padding(horizontal = 3.dp)
                    .height(6.dp)
                    .width(if (here) 22.dp else 6.dp)
                    .background(
                        if (here) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.surfaceVariant,
                        CircleShape,
                    ),
            )
        }
    }
}

private fun iconFor(step: OnboardingStep): ImageVector = when (step) {
    OnboardingStep.Welcome -> AizeIcons.get("ui_route")
    OnboardingStep.HowItWorks -> AizeIcons.Steps
    OnboardingStep.Location -> AizeIcons.Recenter
    OnboardingStep.Privacy -> AizeIcons.get("ui_settings")
    OnboardingStep.Ready -> AizeIcons.get("ui_check")
}

private fun titleFor(step: OnboardingStep): String = when (step) {
    OnboardingStep.Welcome -> "Welcome to Aize"
    OnboardingStep.HowItWorks -> "Pick a place, follow the line"
    OnboardingStep.Location -> "Aize needs your location"
    OnboardingStep.Privacy -> "Your data stays yours"
    OnboardingStep.Ready -> "You are ready"
}

private fun bodyFor(step: OnboardingStep): String = when (step) {
    OnboardingStep.Welcome ->
        "A navigation app for Malaysia, built to be read at a glance and to never feel laggy."
    OnboardingStep.HowItWorks ->
        "Search a place or long-press the map, choose the route you want, then drive. Aize speaks the turns and re-routes when you leave the line."
    OnboardingStep.Location ->
        "It is used to show where you are, to keep the map centred while you drive, and to know when you have left the route. Only while you are using the app."
    OnboardingStep.Privacy ->
        "Routes and searches go to the Aize server you are pointed at, and nowhere else. There are no ads and no trackers in this build."
    OnboardingStep.Ready ->
        "Long-press the map to set a destination. The grey routes can be tapped on the map as well as in the list."
}
