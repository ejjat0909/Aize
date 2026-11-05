package app.aize.ui.onboard

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

class OnboardingTest {

    @Test
    fun theFlowStartsAtWelcomeAndEndsAtReady() {
        assertEquals(OnboardingStep.Welcome, Onboarding.steps.first())
        assertEquals(OnboardingStep.Ready, Onboarding.steps.last())
        assertNull("nothing comes before the first step", Onboarding.back(Onboarding.steps.first()))
        assertNull("the last step is finished, not followed", Onboarding.next(Onboarding.steps.last()))
    }

    @Test
    fun everyStepIsReachableByWalkingForward() {
        var step: OnboardingStep? = Onboarding.steps.first()
        val seen = mutableListOf<OnboardingStep>()
        while (step != null) {
            seen += step
            step = Onboarding.next(step)
        }
        assertEquals(Onboarding.steps, seen)
    }

    @Test
    fun backUndoesNext() {
        Onboarding.steps.drop(1).forEach { step ->
            assertEquals(step, Onboarding.next(Onboarding.back(step)!!))
        }
    }

    @Test
    fun progressIsMonotonicAndEndsAtOne() {
        var last = 0f
        Onboarding.steps.forEach { s ->
            val p = Onboarding.progress(s)
            assertTrue("progress went backwards at $s", p >= last)
            last = p
        }
        assertEquals(1f, last, 0.0001f)
        assertEquals(1, Onboarding.position(Onboarding.steps.first()))
    }

    @Test
    fun thePermissionIsAskedAfterItIsExplained() {
        // the whole point of the order: the step that says why comes before the one that asks
        val why = Onboarding.steps.indexOf(OnboardingStep.Location)
        val privacy = Onboarding.steps.indexOf(OnboardingStep.Privacy)
        assertTrue("privacy must follow the location step", privacy > why)
        assertFalse(Onboarding.isLast(OnboardingStep.Location))
    }
}
