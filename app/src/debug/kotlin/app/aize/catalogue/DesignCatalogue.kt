package app.aize.catalogue

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.toArgb
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import app.aize.design.AizeChoreography
import app.aize.design.AizeExtraColors
import app.aize.design.AizeMotion
import app.aize.design.AizeRadius
import app.aize.design.AizeRoute
import app.aize.design.AizeSize
import app.aize.design.AizeSprings
import app.aize.design.AizeTraffic
import app.aize.ui.component.AizeButton
import app.aize.ui.component.AizeButtonKind
import app.aize.ui.component.AizeButtonSize
import app.aize.ui.component.AizeCard
import app.aize.ui.component.AizeChoiceChip
import app.aize.ui.component.AizeDivider
import app.aize.ui.component.AizeIconButton
import app.aize.ui.component.AizeListRow
import app.aize.ui.component.AizeSwitch
import app.aize.ui.component.AizeTextField
import app.aize.ui.icon.AizeIconData
import app.aize.ui.icon.AizeIcons

/**
 * Every visual decision the app has, on one screen per decision.
 *
 * This is a debug-only activity: it is compiled into `src/debug`, so the release build does not contain it. It is
 * not a style guide for its own sake — it is the thing `scripts/screenshot_catalogue.py` photographs, which turns
 * "the components look right" into a diff against a golden image.
 */
@Composable
fun DesignCatalogue(section: CatalogueSection, onPick: (CatalogueSection) -> Unit, dark: Boolean) {
    Column(
        Modifier
            .fillMaxWidth()
            .verticalScroll(rememberScrollState())
            .padding(16.dp),
    ) {
        Text("Aize design catalogue", fontSize = 22.sp, fontWeight = FontWeight.SemiBold)
        Text(
            "${section.title} · ${section.id}",
            fontSize = 13.sp,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )
        Spacer(Modifier.height(6.dp))
        // One line of text tabs, not a chip row: this is navigation for a developer, and a strip that wraps
        // onto two rows costs every page the height it needs to fit on one screen.
        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(12.dp)) {
            CatalogueSection.entries.forEach { s ->
                Text(
                    s.tab,
                    fontSize = 11.sp,
                    maxLines = 1,
                    softWrap = false,
                    fontWeight = if (s == section) FontWeight.SemiBold else FontWeight.Normal,
                    color = if (s == section) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.onSurfaceVariant,
                    modifier = Modifier.clickable { onPick(s) },
                )
            }
        }
        Spacer(Modifier.height(12.dp))
        when (section) {
            CatalogueSection.Colour -> ColourPage(dark)
            CatalogueSection.Type -> TypePage()
            CatalogueSection.Icon -> IconPage()
            CatalogueSection.Button -> ButtonPage()
            CatalogueSection.Control -> ControlPage()
            CatalogueSection.Surface -> SurfacePage()
            CatalogueSection.Shape -> ShapePage()
            CatalogueSection.Motion -> MotionPage()
        }
    }
}

@Composable
private fun Heading(text: String) {
    Text(
        text,
        fontSize = 12.sp,
        fontWeight = FontWeight.SemiBold,
        color = MaterialTheme.colorScheme.primary,
        modifier = Modifier.padding(top = 10.dp, bottom = 4.dp),
    )
}

/** `#RRGGBB` — the alpha channel is not interesting here, every token is opaque. */
private fun hex(c: Color): String = "#%06X".format(c.toArgb() and 0xFFFFFF)

@Composable
private fun Swatch(name: String, colour: Color) {
    Row(verticalAlignment = Alignment.CenterVertically, modifier = Modifier.padding(vertical = 2.dp)) {
        Box(
            Modifier
                .size(24.dp)
                .background(colour, RoundedCornerShape(AizeRadius.SM))
                .border(1.dp, MaterialTheme.colorScheme.outline.copy(alpha = 0.35f), RoundedCornerShape(AizeRadius.SM)),
        )
        Spacer(Modifier.width(8.dp))
        Text(name, fontSize = 11.sp, maxLines = 1, modifier = Modifier.weight(1f))
        Text(hex(colour), fontSize = 10.sp, color = MaterialTheme.colorScheme.onSurfaceVariant)
    }
}

/** Two swatches per row: a colour list is wide and short, and the page has to fit one screen. */
@Composable
private fun SwatchGrid(entries: List<Pair<String, Color>>) {
    entries.chunked(2).forEach { row ->
        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(16.dp)) {
            row.forEach { (name, colour) -> Box(Modifier.weight(1f)) { Swatch(name, colour) } }
            if (row.size == 1) Spacer(Modifier.weight(1f))
        }
    }
}

@Composable
private fun ColourPage(dark: Boolean) {
    val s = MaterialTheme.colorScheme
    val extra = if (dark) AizeExtraColors.dark else AizeExtraColors.light
    val route = if (dark) AizeRoute.dark else AizeRoute.light
    val traffic = if (dark) AizeTraffic.dark else AizeTraffic.light

    Heading("Theme roles (the pair is what the contrast gate checks)")
    SwatchGrid(
        listOf(
            "primary" to s.primary,
            "onPrimary" to s.onPrimary,
            "primaryContainer" to s.primaryContainer,
            "onPrimaryContainer" to s.onPrimaryContainer,
            "surface" to s.surface,
            "onSurface" to s.onSurface,
            "surfaceVariant" to s.surfaceVariant,
            "onSurfaceVariant" to s.onSurfaceVariant,
            "outline" to s.outline,
            "error" to s.error,
            "success" to extra.success,
            "warning" to extra.warning,
            "info" to extra.info,
        ),
    )
    Heading("Map: route")
    SwatchGrid(
        listOf(
            "selected" to Color(route.selected),
            "selectedCasing" to Color(route.selectedCasing),
            "alternative" to Color(route.alternative),
            "alternativeCasing" to Color(route.alternativeCasing),
            "passed" to Color(route.passed),
            "navArrow" to Color(route.navArrow),
        ),
    )
    Heading("Map: traffic")
    SwatchGrid(
        listOf(
            "free" to Color(traffic.free),
            "light" to Color(traffic.light),
            "moderate" to Color(traffic.moderate),
            "heavy" to Color(traffic.heavy),
            "standstill" to Color(traffic.standstill),
        ),
    )
}

@Composable
private fun TypeRow(name: String, size: Int, weight: FontWeight, sample: String) {
    Row(verticalAlignment = Alignment.CenterVertically, modifier = Modifier.padding(vertical = 5.dp)) {
        Text(name, fontSize = 11.sp, color = MaterialTheme.colorScheme.onSurfaceVariant, modifier = Modifier.width(96.dp))
        Text(
            sample,
            fontSize = size.sp,
            fontWeight = weight,
            maxLines = 1,
            overflow = TextOverflow.Ellipsis,
            modifier = Modifier.weight(1f),
        )
        Spacer(Modifier.width(8.dp))
        Text("${size}sp", fontSize = 11.sp, color = MaterialTheme.colorScheme.onSurfaceVariant)
    }
}

@Composable
private fun TypePage() {
    Heading("The ramp the interface actually uses")
    TypeRow("instruction", 24, FontWeight.SemiBold, "Bear left onto Jalan Stesen")
    TypeRow("distance", 24, FontWeight.Bold, "300 m")
    TypeRow("title", 22, FontWeight.SemiBold, "Aize design catalogue")
    TypeRow("body", 15, FontWeight.Normal, "A navigation app for Malaysia")
    TypeRow("button", 15, FontWeight.SemiBold, "Start driving")
    TypeRow("label", 13, FontWeight.Normal, "via Jalan Ampang")
    TypeRow("caption", 12, FontWeight.Medium, "On map · Fastest · Tolls")
    TypeRow("micro", 11, FontWeight.Normal, "48 dp")
    Heading("Note")
    Text(
        "Platform face, no bundled typeface yet (P1-01).",
        fontSize = 12.sp,
        color = MaterialTheme.colorScheme.onSurfaceVariant,
    )
}

@Composable
private fun IconPage() {
    val names = AizeIconData.paths.keys.sorted()
    Text(
        "${names.size} glyphs, 24 dp grid, 1.9 unit stroke. Labels drop the nav_/poi_/ui_ prefix.",
        fontSize = 12.sp,
        color = MaterialTheme.colorScheme.onSurfaceVariant,
    )
    Spacer(Modifier.height(8.dp))
    names.chunked(7).forEach { row ->
        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(4.dp)) {
            row.forEach { name ->
                Column(
                    Modifier.weight(1f).padding(vertical = 1.dp),
                    horizontalAlignment = Alignment.CenterHorizontally,
                ) {
                    Icon(
                        AizeIcons[name],
                        contentDescription = null,
                        tint = MaterialTheme.colorScheme.onSurface,
                        modifier = Modifier.size(AizeSize.ICON_SMALL),
                    )
                    Spacer(Modifier.height(1.dp))
                    Text(
                        name.substringAfter('_'),
                        fontSize = 8.sp,
                        maxLines = 1,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                }
            }
            repeat(7 - row.size) { Spacer(Modifier.weight(1f)) }
        }
    }
}

@Composable
private fun ButtonPage() {
    Heading("Kinds")
    Row(horizontalArrangement = Arrangement.spacedBy(10.dp), verticalAlignment = Alignment.CenterVertically) {
        AizeButton("Primary", {}, kind = AizeButtonKind.Primary)
        AizeButton("Tonal", {}, kind = AizeButtonKind.Tonal)
        AizeButton("Ghost", {}, kind = AizeButtonKind.Ghost)
    }
    Heading("Sizes")
    Row(horizontalArrangement = Arrangement.spacedBy(10.dp), verticalAlignment = Alignment.CenterVertically) {
        AizeButton("Small", {}, size = AizeButtonSize.Small)
        AizeButton("Normal", {}, size = AizeButtonSize.Normal)
        AizeButton("Large", {}, size = AizeButtonSize.Large)
    }
    Heading("With a glyph, and disabled")
    Row(horizontalArrangement = Arrangement.spacedBy(10.dp), verticalAlignment = Alignment.CenterVertically) {
        AizeButton("Directions", {}, leading = AizeIcons.Destination)
        AizeButton("Share", {}, kind = AizeButtonKind.Tonal, leading = AizeIcons.Share)
        AizeButton("Disabled", {}, enabled = false)
    }
    Row(
        Modifier.padding(top = 10.dp),
        horizontalArrangement = Arrangement.spacedBy(10.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        AizeButton("Small ghost", {}, kind = AizeButtonKind.Ghost, size = AizeButtonSize.Small)
        AizeButton("Disabled tonal", {}, kind = AizeButtonKind.Tonal, enabled = false)
    }
    Heading("The rule the test enforces")
    Text(
        "A corner is never more than half the height, which is why Large is 64 dp: a 32 dp corner on a 56 dp " +
            "button is a lozenge.",
        fontSize = 12.sp,
        color = MaterialTheme.colorScheme.onSurfaceVariant,
    )
}

@Composable
private fun ControlPage() {
    Heading("Chips: off, on, with a glyph")
    Row(horizontalArrangement = Arrangement.spacedBy(8.dp), verticalAlignment = Alignment.CenterVertically) {
        AizeChoiceChip("Fuel", false, {})
        AizeChoiceChip("Food", true, {})
        AizeChoiceChip("Parking", false, {}, leading = AizeIcons.get("poi_parking"))
    }
    Heading("Icon buttons")
    Row(horizontalArrangement = Arrangement.spacedBy(10.dp), verticalAlignment = Alignment.CenterVertically) {
        AizeIconButton(AizeIcons.Recenter, "Recenter", {})
        AizeIconButton(AizeIcons.Speaker, "Sound on", {}, filled = false)
        AizeIconButton(AizeIcons.Close, "Close", {})
    }
    Heading("Switches")
    AizeSwitch(checked = true, onCheckedChange = {}, label = "Share anonymous usage", description = "Off unless you turn it on")
    AizeSwitch(checked = false, onCheckedChange = {}, label = "Spoken directions")
    Heading("Field")
    AizeTextField(value = "", onValueChange = {}, placeholder = "Search a place")
    Spacer(Modifier.height(10.dp))
    AizeTextField(value = "KLCC", onValueChange = {}, placeholder = "Search a place", onClear = {})
}

@Composable
private fun SurfacePage() {
    Heading("Card: plain, selected")
    Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
        AizeCard(Modifier.weight(1f)) {
            Column(Modifier.padding(12.dp)) {
                Text("Plain", fontSize = 14.sp, fontWeight = FontWeight.Medium)
                Text("One radius, one shadow", fontSize = 11.sp, color = MaterialTheme.colorScheme.onSurfaceVariant)
            }
        }
        AizeCard(Modifier.weight(1f), selected = true) {
            Column(Modifier.padding(12.dp)) {
                Text("Selected", fontSize = 14.sp, fontWeight = FontWeight.Medium)
                Text("primaryContainer, no border", fontSize = 11.sp, color = MaterialTheme.colorScheme.onSurfaceVariant)
            }
        }
    }
    Heading("List rows")
    AizeListRow(headline = "Shell Ipoh", supporting = "Fuel · 1.3 km", leading = AizeIcons.get("poi_fuel"), trailing = "Open")
    AizeListRow(headline = "KLCC", supporting = "Mall · 9.1 km", leading = AizeIcons.get("poi_mall"), onClick = {})
    Heading("Card containing rows")
    AizeCard(Modifier.fillMaxWidth()) {
        Column {
            AizeListRow(headline = "Saved place", supporting = "Work", leading = AizeIcons.Work, trailing = "Star")
            AizeDivider()
            AizeListRow(headline = "Recent", supporting = "KL Sentral", leading = AizeIcons.Clock)
        }
    }
}

@Composable
private fun RadiusRow(name: String, radius: androidx.compose.ui.unit.Dp) {
    Row(verticalAlignment = Alignment.CenterVertically, modifier = Modifier.padding(vertical = 4.dp)) {
        Box(
            Modifier
                .size(width = 56.dp, height = 24.dp)
                .background(MaterialTheme.colorScheme.primaryContainer, RoundedCornerShape(radius)),
        )
        Spacer(Modifier.width(8.dp))
        Text(name, fontSize = 11.sp, maxLines = 1, modifier = Modifier.weight(1f))
        Text("${radius.value.toInt()} dp", fontSize = 11.sp, color = MaterialTheme.colorScheme.onSurfaceVariant)
    }
}

@Composable
private fun SizeRow(name: String, value: androidx.compose.ui.unit.Dp) {
    Row(verticalAlignment = Alignment.CenterVertically, modifier = Modifier.padding(vertical = 3.dp)) {
        Box(
            Modifier
                .width(value.coerceAtMost(120.dp))
                .height(8.dp)
                .background(MaterialTheme.colorScheme.primary, RoundedCornerShape(4.dp)),
        )
        Spacer(Modifier.width(12.dp))
        Text(name, fontSize = 11.sp, modifier = Modifier.width(150.dp))
        Text("${value.value.toInt()} dp", fontSize = 11.sp, color = MaterialTheme.colorScheme.onSurfaceVariant)
    }
}

@Composable
private fun ShapePage() {
    Heading("Radii")
    val radii = listOf(
        "XS" to AizeRadius.XS,
        "SM" to AizeRadius.SM,
        "MD" to AizeRadius.MD,
        "LG" to AizeRadius.LG,
        "XL · card" to AizeRadius.XL,
        "Button small" to AizeRadius.BUTTON_SMALL,
        "Button normal" to AizeRadius.BUTTON_NORMAL,
        "Button large" to AizeRadius.BUTTON_LARGE,
        "Sheet" to AizeRadius.SHEET,
    )
    radii.chunked(2).forEach { row ->
        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(16.dp)) {
            row.forEach { (name, radius) -> Box(Modifier.weight(1f)) { RadiusRow(name, radius) } }
            if (row.size == 1) Spacer(Modifier.weight(1f))
        }
    }
    Heading("Sizes")
    SizeRow("Touch target", AizeSize.TOUCH_TARGET)
    MotionRow(
        "Icon sizes",
        "${AizeSize.ICON_SMALL.value.toInt()} / ${AizeSize.ICON_MEDIUM.value.toInt()} / ${AizeSize.ICON_LARGE.value.toInt()} dp",
    )
    SizeRow("Report button", AizeSize.REPORT_BUTTON)
    SizeRow("ETA bar", AizeSize.ETA_BAR_HEIGHT)
    SizeRow("Banner min", AizeSize.INSTRUCTION_BANNER_MIN_HEIGHT)
    SizeRow("Sheet peek", AizeSize.BOTTOM_SHEET_PEEK)
}

@Composable
private fun MotionRow(name: String, value: String) {
    Row(Modifier.padding(vertical = 2.dp)) {
        Text(name, fontSize = 11.sp, modifier = Modifier.width(190.dp))
        Text(value, fontSize = 11.sp, color = MaterialTheme.colorScheme.onSurfaceVariant)
    }
}

@Composable
private fun MotionPage() {
    Heading("Durations")
    MotionRow("instant", "${AizeMotion.INSTANT_MS} ms")
    MotionRow("fast", "${AizeMotion.FAST_MS} ms")
    MotionRow("base", "${AizeMotion.BASE_MS} ms")
    MotionRow("moderate", "${AizeMotion.MODERATE_MS} ms")
    MotionRow("slow", "${AizeMotion.SLOW_MS} ms")
    MotionRow("deliberate", "${AizeMotion.DELIBERATE_MS} ms")
    Heading("Easings (not visible in a still, so named not drawn)")
    Text(
        "standard · decelerate · accelerate · silky in · silky out",
        fontSize = 11.sp,
        color = MaterialTheme.colorScheme.onSurfaceVariant,
    )
    Heading("Springs")
    MotionRow("pop in", "damping ${AizeSprings.POP_IN_DAMPING_RATIO}, stiffness ${AizeSprings.POP_IN_STIFFNESS.toInt()}")
    MotionRow("settle", "damping ${AizeSprings.SETTLE_DAMPING_RATIO}, stiffness ${AizeSprings.SETTLE_STIFFNESS.toInt()}")
    Heading("Choreography")
    MotionRow("alert pop-in", "${AizeChoreography.ALERT_POP_IN_ALPHA} ms, scale ${AizeChoreography.ALERT_POP_IN_SCALE}")
    MotionRow("sheet slide", "${AizeChoreography.SHEET_SLIDE_MS} ms")
    MotionRow("page forward / back", "${AizeChoreography.PAGE_FORWARD_MS} / ${AizeChoreography.PAGE_BACK_MS} ms")
    MotionRow("sheet up", "${AizeChoreography.SHEET_UP_MS} ms")
}
