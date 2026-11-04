package app.aize.benchmark

import androidx.benchmark.macro.junit4.BaselineProfileRule
import androidx.test.ext.junit.runners.AndroidJUnit4
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

/**
 * Records the classes and methods used on the critical path (launch, first map frame).
 * scripts/baseline-profile.sh runs this and copies the result to app/src/main/baseline-prof.txt.
 */
@RunWith(AndroidJUnit4::class)
class BaselineProfileGenerator {
    @get:Rule val rule = BaselineProfileRule()

    @Test fun launchAndFirstFrame() = rule.collect(packageName = "app.aize") {
        pressHome()
        startActivityAndWait()
        device.waitForIdle()
    }
}
