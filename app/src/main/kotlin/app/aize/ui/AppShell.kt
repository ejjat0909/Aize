package app.aize.ui

import androidx.compose.animation.AnimatedContent
import androidx.compose.animation.core.tween
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.animation.togetherWith
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.platform.LocalContext
import app.aize.design.rememberMotionEnabled
import app.aize.ui.onboard.Onboarding
import app.aize.ui.onboard.OnboardingScreen

/**
 * What the app shows first.
 *
 * Two screens, and the choice between them is a stored flag rather than a navigation graph: the map is not a
 * destination you navigate back to, it is where the app lives. The first run is the only other place.
 *
 * The flag is read once per composition from `SharedPreferences`, so a first run that finishes does not have to
 * wait for a restart to show the map.
 */
@Composable
fun AizeApp() {
    val ctx = LocalContext.current
    var onboarded by remember { mutableStateOf(Onboarding.isDone(ctx)) }
    val motion = rememberMotionEnabled()

    AnimatedContent(
        targetState = onboarded,
        transitionSpec = {
            fadeIn(tween(if (motion) 220 else 0)) togetherWith fadeOut(tween(if (motion) 140 else 0))
        },
        label = "shell",
    ) { done ->
        if (done) {
            NavScreen(
                onReplayTour = {
                    Onboarding.reset(ctx)
                    onboarded = false
                },
            )
        } else {
            OnboardingScreen(
                onDone = {
                    Onboarding.markDone(ctx)
                    onboarded = true
                },
            )
        }
    }
}
