package app.aize.nav

import org.junit.Assert.assertEquals
import org.junit.Test

class RecentsTest {

    @Test
    fun `a new term goes to the front`() {
        assertEquals(listOf("mid valley", "klcc"), Recents.add(listOf("klcc"), "mid valley"))
    }

    @Test
    fun `searching the same thing twice moves it up instead of duplicating`() {
        val list = Recents.add(listOf("pavilion", "klcc"), "KLCC")
        assertEquals(listOf("KLCC", "pavilion"), list)
    }

    @Test
    fun `the list is capped`() {
        val list = (1..25).fold(emptyList<String>()) { acc, i -> Recents.add(acc, "place $i") }
        assertEquals(Recents.MAX, list.size)
        assertEquals("place 25", list.first())
    }

    @Test
    fun `a single character is not worth remembering`() {
        assertEquals(listOf("klcc"), Recents.add(listOf("klcc"), " k "))
    }

    @Test
    fun `round trip survives quotes and commas`() {
        val list = listOf("Jalan Ampang, \"KL\"", "batu caves")
        assertEquals(list, Recents.decode(Recents.encode(list)))
    }

    @Test
    fun `a corrupt value reads as empty`() {
        assertEquals(emptyList<String>(), Recents.decode("[[[not json"))
        assertEquals(emptyList<String>(), Recents.decode(null))
    }
}
