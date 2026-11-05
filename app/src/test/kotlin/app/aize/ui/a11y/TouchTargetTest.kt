package app.aize.ui.a11y

import androidx.compose.ui.unit.dp
import app.aize.design.AizeSize
import app.aize.ui.component.AizeButtonSize
import app.aize.ui.component.buttonHeight
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * Touch targets, as numbers.
 *
 * 48 dp is the floor every platform agrees on and the one Aize's own tokens declare. The point of testing it is
 * that a component can shrink without anyone noticing: a 36 dp icon button looks fine in a screenshot and is
 * missed by a thumb in a moving car.
 *
 * [AizeButtonSize.Small] is the one exception, and it is a deliberate one: it draws 36 dp tall inside a sheet
 * (`Cancel`, `Skip the tour`) but is a Material `Button`, which carries `minimumInteractiveComponentSize` — so the
 * target a finger has to hit is still 48 dp while the ink stays small.
 */
class TouchTargetTest {

    @Test
    fun theTokenItselfMeetsTheFloor() {
        assertEquals("TOUCH_TARGET is ${AizeSize.TOUCH_TARGET}", 48.dp, AizeSize.TOUCH_TARGET)
    }

    @Test
    fun theNormalAndLargeButtonsMeetTheFloorInInkAsWellAsInTarget() {
        assertTrue(buttonHeight(AizeButtonSize.Normal) >= AizeSize.TOUCH_TARGET)
        assertTrue(buttonHeight(AizeButtonSize.Large) >= AizeSize.TOUCH_TARGET)
    }

    @Test
    fun theSmallButtonStaysInsideItsSheet() {
        // if this ever grows past the normal size, the size ladder is wrong, not the sheet
        assertEquals(36.dp, buttonHeight(AizeButtonSize.Small))
        assertTrue(buttonHeight(AizeButtonSize.Small) < buttonHeight(AizeButtonSize.Normal))
        assertTrue(buttonHeight(AizeButtonSize.Normal) < buttonHeight(AizeButtonSize.Large))
    }

    @Test
    fun theBannerIsTallEnoughToReadAtSpeed() {
        // a HUD element is not a touch target: it has to be legible at a glance, and the token says 96 dp
        assertTrue(AizeSize.INSTRUCTION_BANNER_MIN_HEIGHT >= 96.dp)
    }
}
