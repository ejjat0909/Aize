package app.aize.ui.component

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import app.aize.design.AizeRadius
import app.aize.design.AizeSize

/**
 * The one button in the app.
 *
 * Three sizes because the radii come from the design tokens (18 / 24 / 32 dp) and a 32 dp corner on a 36 dp tall
 * button is a lozenge, not a button. Three kinds because a screen needs one obvious action and several quiet ones,
 * and "quiet" must not mean "invisible": the ghost kind keeps the touch target and the label contrast, and drops
 * only the fill.
 */
enum class AizeButtonSize { Small, Normal, Large }

enum class AizeButtonKind { Primary, Tonal, Ghost }

/** Corner radius for a size. Pure, so a unit test can assert it instead of an eye on a device. */
fun buttonRadius(size: AizeButtonSize): Dp = when (size) {
    AizeButtonSize.Small -> AizeRadius.BUTTON_SMALL
    AizeButtonSize.Normal -> AizeRadius.BUTTON_NORMAL
    AizeButtonSize.Large -> AizeRadius.BUTTON_LARGE
}

/**
 * Minimum height for a size. [AizeButtonSize.Normal] is the smallest that still meets the 48 dp touch target.
 *
 * Large is 64 dp and not 56: the token radius for it is 32 dp, and a 32 dp corner on a 56 dp button is a lozenge.
 * The test asserts corner <= half the height, so this is a rule, not a preference.
 */
fun buttonHeight(size: AizeButtonSize): Dp = when (size) {
    AizeButtonSize.Small -> 36.dp
    AizeButtonSize.Normal -> AizeSize.TOUCH_TARGET
    AizeButtonSize.Large -> 64.dp
}

@Composable
fun AizeButton(
    text: String,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
    kind: AizeButtonKind = AizeButtonKind.Primary,
    size: AizeButtonSize = AizeButtonSize.Normal,
    enabled: Boolean = true,
    leading: ImageVector? = null,
) {
    val shape = RoundedCornerShape(buttonRadius(size))
    val height = buttonHeight(size)
    val padding = PaddingValues(horizontal = if (size == AizeButtonSize.Small) 14.dp else 20.dp)
    when (kind) {
        AizeButtonKind.Primary -> Button(
            onClick = onClick,
            modifier = modifier.heightIn(min = height),
            enabled = enabled,
            shape = shape,
            contentPadding = padding,
        ) { ButtonBody(text, size, leading) }

        AizeButtonKind.Tonal -> Button(
            onClick = onClick,
            modifier = modifier.heightIn(min = height),
            enabled = enabled,
            shape = shape,
            contentPadding = padding,
            colors = ButtonDefaults.buttonColors(
                containerColor = MaterialTheme.colorScheme.primaryContainer,
                contentColor = MaterialTheme.colorScheme.onPrimaryContainer,
            ),
        ) { ButtonBody(text, size, leading) }

        AizeButtonKind.Ghost -> TextButton(
            onClick = onClick,
            modifier = modifier.heightIn(min = height),
            enabled = enabled,
            shape = shape,
            contentPadding = padding,
        ) { ButtonBody(text, size, leading) }
    }
}

@Composable
private fun ButtonBody(text: String, size: AizeButtonSize, leading: ImageVector?) {
    Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.Center) {
        if (leading != null) {
            Icon(leading, contentDescription = null, modifier = Modifier.size(AizeSize.ICON_SMALL))
            Spacer(Modifier.width(8.dp))
        }
        Text(
            text,
            fontSize = if (size == AizeButtonSize.Small) 13.sp else 15.sp,
            fontWeight = FontWeight.SemiBold,
            maxLines = 1,
        )
    }
}
