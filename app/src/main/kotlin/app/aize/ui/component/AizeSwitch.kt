package app.aize.ui.component

import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.animation.core.tween
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.offset
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.selection.toggleable
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.lerp
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import app.aize.design.rememberMotionEnabled

/**
 * A labelled switch row. The whole row is the touch target and the switch is drawn here rather than taken from
 * Material, so the track and knob follow the same radii and motion tokens as everything else.
 */
@Composable
fun AizeSwitch(
    checked: Boolean,
    onCheckedChange: (Boolean) -> Unit,
    label: String,
    description: String? = null,
    modifier: Modifier = Modifier,
) {
    val motion = rememberMotionEnabled()
    val t by animateFloatAsState(
        targetValue = if (checked) 1f else 0f,
        animationSpec = tween(if (motion) 150 else 0),
        label = "switch",
    )
    Row(
        modifier = modifier
            .fillMaxWidth()
            .background(Color.Transparent)
            .clip(CircleShape.copy())
            .toggleable(value = checked, role = Role.Switch, onValueChange = onCheckedChange)
            .padding(vertical = 12.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Column(Modifier.weight(1f)) {
            Text(label, fontSize = 15.sp, fontWeight = FontWeight.Medium)
            if (description != null) {
                Text(description, fontSize = 13.sp, color = MaterialTheme.colorScheme.onSurfaceVariant)
            }
        }
        Spacer(Modifier.width(12.dp))
        Box(
            Modifier
                .size(width = 48.dp, height = 28.dp)
                .clip(CircleShape)
                .background(lerp(MaterialTheme.colorScheme.surfaceVariant, MaterialTheme.colorScheme.primary, t)),
        ) {
            Box(
                Modifier
                    .padding(3.dp)
                    .offset(x = 20.dp * t)
                    .size(22.dp)
                    // the knob has to be visible against both tracks: dark grey on the off track, white on the on one
                    .background(lerp(MaterialTheme.colorScheme.onSurfaceVariant, MaterialTheme.colorScheme.surface, t), CircleShape),
            )
        }
    }
}
