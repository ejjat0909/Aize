package app.aize.ui.component

import androidx.compose.ui.unit.dp
import app.aize.design.AizeRadius
import app.aize.design.AizeSize
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

/** The button's geometry comes from the tokens, so the tokens can be asserted without a device. */
class AizeButtonTest {

    @Test
    fun radiusComesFromTheTokens() {
        assertEquals(AizeRadius.BUTTON_SMALL, buttonRadius(AizeButtonSize.Small))
        assertEquals(AizeRadius.BUTTON_NORMAL, buttonRadius(AizeButtonSize.Normal))
        assertEquals(AizeRadius.BUTTON_LARGE, buttonRadius(AizeButtonSize.Large))
        assertEquals(18.dp, buttonRadius(AizeButtonSize.Small))
        assertEquals(24.dp, buttonRadius(AizeButtonSize.Normal))
        assertEquals(32.dp, buttonRadius(AizeButtonSize.Large))
    }

    @Test
    fun theNormalButtonMeetsTheTouchTarget() {
        assertEquals(AizeSize.TOUCH_TARGET, buttonHeight(AizeButtonSize.Normal))
        assertTrue("a 48 dp target is the minimum for a thumb", buttonHeight(AizeButtonSize.Normal).value >= 48f)
    }

    @Test
    fun aBiggerRadiusNeedsABiggerButton() {
        // a 32 dp corner on a 36 dp tall button is a lozenge: the radius must grow with the height, not instead of it
        assertTrue(buttonHeight(AizeButtonSize.Small) < buttonHeight(AizeButtonSize.Normal))
        assertTrue(buttonHeight(AizeButtonSize.Normal) < buttonHeight(AizeButtonSize.Large))
        assertTrue("the corner must stay under half the height", buttonRadius(AizeButtonSize.Large).value * 2 <= buttonHeight(AizeButtonSize.Large).value)
    }
}
