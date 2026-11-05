package app.aize.ui.component

import androidx.compose.foundation.background
import androidx.compose.ui.draw.shadow
import androidx.compose.ui.draw.clip
import androidx.compose.foundation.clickable
import androidx.compose.foundation.selection.selectable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.defaultMinSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.BasicTextField
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.LocalTextStyle
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.SolidColor
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.heading
import androidx.compose.ui.semantics.selected
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import app.aize.design.AizeRadius
import app.aize.design.AizeSize
import app.aize.ui.icon.AizeIcons

/**
 * Round icon button. Used for the things that sit over the map (recenter, close, layers) where a labelled button
 * would cover the thing the driver is looking at.
 */
@Composable
fun AizeIconButton(
    icon: ImageVector,
    contentDescription: String,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
    filled: Boolean = true,
    tint: androidx.compose.ui.graphics.Color = MaterialTheme.colorScheme.onSurface,
) {
    // One node: the click and the name must land on the same semantics node, or a screen reader focuses a named
    // node with no action and a clickable node with no name. Surface(onClick) does not merge its children, so this
    // is a Box with its own background instead.
    Box(
        modifier = modifier
            .size(AizeSize.TOUCH_TARGET)
            .then(if (filled) Modifier.shadow(3.dp, CircleShape) else Modifier)
            .clip(CircleShape)
            .background(if (filled) MaterialTheme.colorScheme.surface else androidx.compose.ui.graphics.Color.Transparent)
            .clickable(role = Role.Button, onClick = onClick)
            .semantics(mergeDescendants = true) { this.contentDescription = contentDescription },
        contentAlignment = Alignment.Center,
    ) {
        Icon(icon, contentDescription = null, tint = tint, modifier = Modifier.size(AizeSize.ICON_MEDIUM))
    }
}

/**
 * A pill that filters. Selected state is carried by fill *and* by the label's weight, so it survives a
 * colour-blind viewer and a washed-out screen in sunlight.
 */
@Composable
fun AizeChoiceChip(
    label: String,
    selected: Boolean,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
    leading: ImageVector? = null,
) {
    val bg = if (selected) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.surfaceVariant
    val fg = if (selected) MaterialTheme.colorScheme.onPrimary else MaterialTheme.colorScheme.onSurfaceVariant
    Row(
        modifier = modifier
            .height(AizeSize.TOUCH_TARGET)
            .background(bg, CircleShape)
            // selectable, not clickable: a chip that is on has to say so, or the only cue is the fill colour
            .selectable(selected = selected, role = Role.Checkbox, onClick = onClick)
            .padding(horizontal = 16.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        if (leading != null) {
            Icon(leading, contentDescription = null, tint = fg, modifier = Modifier.size(18.dp))
            Spacer(Modifier.width(6.dp))
        }
        Text(
            label,
            color = fg,
            fontSize = 14.sp,
            fontWeight = if (selected) FontWeight.SemiBold else FontWeight.Medium,
            maxLines = 1,
        )
    }
}

/** A card: the place card, a route row, a saved place. One radius, one shadow, everywhere. */
@Composable
fun AizeCard(
    modifier: Modifier = Modifier,
    onClick: (() -> Unit)? = null,
    selected: Boolean = false,
    contentDescription: String? = null,
    content: @Composable () -> Unit,
) {
    val shape = RoundedCornerShape(AizeRadius.XL)
    val colour = if (selected) MaterialTheme.colorScheme.primaryContainer else MaterialTheme.colorScheme.surface
    if (onClick != null) {
        // Surface(onClick) does not merge its children, so a route row would read as three loose labels and
        // never say which one is on the map. Merge, and carry the selected state on the same node as the click.
        val semantics = modifier.semantics(mergeDescendants = true) {
            this.selected = selected
            if (contentDescription != null) this.contentDescription = contentDescription
        }
        Surface(onClick = onClick, modifier = semantics, shape = shape, color = colour, shadowElevation = 4.dp) { content() }
    } else {
        Surface(modifier = modifier, shape = shape, color = colour, shadowElevation = 4.dp) { content() }
    }
}

/**
 * A row in a list. Leading icon, headline, optional supporting line, optional trailing text.
 *
 * The whole row is one touch target (56 dp minimum) and one accessibility node, so TalkBack says "Shell Ipoh 3,
 * Fuel · 1.3 km" instead of reading three separate labels.
 */
@Composable
fun AizeListRow(
    headline: String,
    modifier: Modifier = Modifier,
    supporting: String? = null,
    leading: ImageVector? = null,
    leadingTint: androidx.compose.ui.graphics.Color = MaterialTheme.colorScheme.primary,
    trailing: String? = null,
    trailingTint: androidx.compose.ui.graphics.Color = MaterialTheme.colorScheme.onSurfaceVariant,
    onClick: (() -> Unit)? = null,
) {
    Row(
        modifier = modifier
            .fillMaxWidth()
            .defaultMinSize(minHeight = 56.dp)
            .then(
                if (onClick != null) {
                    Modifier
                        .clickable(role = Role.Button, onClick = onClick)
                        .semantics(mergeDescendants = true) { }
                } else {
                    Modifier
                },
            )
            .padding(horizontal = 16.dp, vertical = 10.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        if (leading != null) {
            Icon(leading, contentDescription = null, tint = leadingTint, modifier = Modifier.size(AizeSize.ICON_MEDIUM))
            Spacer(Modifier.width(14.dp))
        }
        Column(Modifier.weight(1f)) {
            Text(headline, fontSize = 15.sp, fontWeight = FontWeight.Medium, maxLines = 1, overflow = TextOverflow.Ellipsis)
            if (supporting != null) {
                Text(supporting, fontSize = 13.sp, color = MaterialTheme.colorScheme.onSurfaceVariant, maxLines = 1, overflow = TextOverflow.Ellipsis)
            }
        }
        if (trailing != null) {
            Spacer(Modifier.width(10.dp))
            Text(trailing, fontSize = 12.sp, color = trailingTint, fontWeight = FontWeight.Medium)
        }
    }
}

@Composable
fun AizeDivider() {
    HorizontalDivider(color = MaterialTheme.colorScheme.surfaceVariant, thickness = 1.dp)
}

/**
 * The search field. Not a Material text field: the default one draws its own outline, its own label animation and its
 * own 56 dp box, and none of those are in the design. This is a rounded container with a leading glyph, a clear
 * button and a caret.
 */
@Composable
fun AizeTextField(
    value: String,
    onValueChange: (String) -> Unit,
    placeholder: String,
    modifier: Modifier = Modifier,
    leading: ImageVector = AizeIcons.Search,
    onClear: (() -> Unit)? = null,
) {
    Surface(
        modifier = modifier.height(AizeSize.TOUCH_TARGET + 4.dp),
        shape = RoundedCornerShape(AizeRadius.BUTTON_NORMAL),
        color = MaterialTheme.colorScheme.surfaceVariant,
    ) {
        Row(Modifier.padding(horizontal = 16.dp), verticalAlignment = Alignment.CenterVertically) {
            Icon(leading, contentDescription = null, tint = MaterialTheme.colorScheme.onSurfaceVariant, modifier = Modifier.size(20.dp))
            Spacer(Modifier.width(10.dp))
            Box(Modifier.weight(1f)) {
                if (value.isEmpty()) {
                    Text(placeholder, fontSize = 15.sp, color = MaterialTheme.colorScheme.onSurfaceVariant, maxLines = 1, overflow = TextOverflow.Ellipsis)
                }
                BasicTextField(
                    value = value,
                    onValueChange = onValueChange,
                    singleLine = true,
                    textStyle = LocalTextStyle.current.copy(fontSize = 15.sp, color = MaterialTheme.colorScheme.onSurface),
                    cursorBrush = SolidColor(MaterialTheme.colorScheme.primary),
                    modifier = Modifier.fillMaxWidth(),
                )
            }
            if (value.isNotEmpty() && onClear != null) {
                Icon(
                    AizeIcons.Close,
                    contentDescription = "Clear the search",
                    tint = MaterialTheme.colorScheme.onSurfaceVariant,
                    modifier = Modifier
                        .size(AizeSize.TOUCH_TARGET)
                        .clickable(onClick = onClear)
                        .padding(14.dp),
                )
            }
        }
    }
}

/**
 * Full-height sheet: the search screen and the turn list are both this. A handle, a title row with a close button,
 * then whatever the caller draws. Height animation lives in the caller so the sheet stays a layout, not a policy.
 */
@Composable
fun AizeSheet(
    title: String,
    onClose: () -> Unit,
    modifier: Modifier = Modifier,
    subtitle: String? = null,
    content: @Composable () -> Unit,
) {
    Surface(
        modifier = modifier,
        color = MaterialTheme.colorScheme.surface,
        shape = RoundedCornerShape(topStart = AizeRadius.SHEET, topEnd = AizeRadius.SHEET),
    ) {
        Column(Modifier.padding(horizontal = 16.dp, vertical = 12.dp)) {
            Box(Modifier.fillMaxWidth(), contentAlignment = Alignment.Center) {
                Box(
                    Modifier
                        .width(36.dp)
                        .height(4.dp)
                        .background(MaterialTheme.colorScheme.surfaceVariant, CircleShape),
                )
            }
            Spacer(Modifier.height(10.dp))
            Row(verticalAlignment = Alignment.Top, horizontalArrangement = Arrangement.SpaceBetween) {
                Column(Modifier.weight(1f)) {
                    Text(
                        title,
                        fontSize = 18.sp,
                        fontWeight = FontWeight.SemiBold,
                        maxLines = 1,
                        overflow = TextOverflow.Ellipsis,
                        modifier = Modifier.semantics { heading() },
                    )
                    if (subtitle != null) {
                        Text(subtitle, fontSize = 13.sp, color = MaterialTheme.colorScheme.onSurfaceVariant, maxLines = 1, overflow = TextOverflow.Ellipsis)
                    }
                }
                AizeIconButton(AizeIcons.Close, contentDescription = "Close", onClick = onClose, filled = false)
            }
            Spacer(Modifier.height(4.dp))
            content()
        }
    }
}
