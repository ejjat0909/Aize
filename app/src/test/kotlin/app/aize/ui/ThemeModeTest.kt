package app.aize.ui

import java.time.LocalTime
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class ThemeModeTest {
    @Test
    fun `auto is light between half past six and seven in the evening`() {
        assertTrue("before sunrise it is dark", ThemeMode.isDark(ThemeMode.Mode.AUTO, LocalTime.of(6, 29)))
        assertFalse("at sunrise it is light", ThemeMode.isDark(ThemeMode.Mode.AUTO, LocalTime.of(6, 30)))
        assertFalse(ThemeMode.isDark(ThemeMode.Mode.AUTO, LocalTime.of(12, 0)))
        assertFalse("one minute before sunset it is light", ThemeMode.isDark(ThemeMode.Mode.AUTO, LocalTime.of(18, 59)))
        assertTrue("at sunset it is dark", ThemeMode.isDark(ThemeMode.Mode.AUTO, LocalTime.of(19, 0)))
        assertTrue(ThemeMode.isDark(ThemeMode.Mode.AUTO, LocalTime.of(23, 30)))
        assertTrue(ThemeMode.isDark(ThemeMode.Mode.AUTO, LocalTime.of(3, 0)))
    }

    @Test
    fun `manual modes ignore the clock`() {
        assertFalse(ThemeMode.isDark(ThemeMode.Mode.LIGHT, LocalTime.of(23, 0)))
        assertTrue(ThemeMode.isDark(ThemeMode.Mode.DARK, LocalTime.of(12, 0)))
    }

    @Test
    fun `labels are short enough for the sheet`() {
        assertEquals("Auto", ThemeMode.label(ThemeMode.Mode.AUTO))
        assertEquals("Day", ThemeMode.label(ThemeMode.Mode.LIGHT))
        assertEquals("Night", ThemeMode.label(ThemeMode.Mode.DARK))
    }
}
