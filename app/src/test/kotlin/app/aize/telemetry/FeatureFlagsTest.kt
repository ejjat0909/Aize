package app.aize.telemetry

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class FeatureFlagsTest {
    @Test fun `defaults apply when the server says nothing`() {
        assertEquals(FeatureFlags.DEFAULTS, FeatureFlags.parse(null))
        assertEquals(FeatureFlags.DEFAULTS, FeatureFlags.parse(""))
    }

    @Test fun `a known flag overrides its default and untouched keys keep theirs`() {
        val f = FeatureFlags.parse("""{"voice":true,"search":false}""")
        assertTrue(f.voice)
        assertFalse(f.search)
        assertTrue(f.turnByTurn)
    }

    @Test fun `junk is ignored rather than fatal`() {
        assertEquals(FeatureFlags.DEFAULTS, FeatureFlags.parse("""{"search":false"""))
        assertEquals(FeatureFlags.DEFAULTS, FeatureFlags.parse("not json"))
    }

    @Test fun `a non-boolean value keeps the default`() {
        assertTrue(FeatureFlags.parse("""{"search":"yes"}""").search)
    }
}
