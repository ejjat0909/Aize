package app.aize.nav

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class FavouritesTest {
    private fun place(name: String, lat: Double = 3.1578, lon: Double = 101.7123, kind: String = "amenity=cafe") =
        SavedPlace(name, lon = lon, lat = lat, kind = kind)

    @Test
    fun `a saved place survives the round trip`() {
        val list = listOf(place("Kopi & Co"), place("KLCC", 3.1578, 101.7116, "shop=mall"))
        val back = Favourites.decode(Favourites.encode(list))
        assertEquals(list, back)
    }

    @Test
    fun `a corrupt list is empty, not a crash`() {
        assertEquals(emptyList<SavedPlace>(), Favourites.decode("{not json"))
        assertEquals(emptyList<SavedPlace>(), Favourites.decode(null))
        assertEquals(emptyList<SavedPlace>(), Favourites.decode(""))
    }

    @Test
    fun `an entry without coordinates is dropped rather than pinned at zero zero`() {
        val raw = """[{"name":"Nowhere","kind":"x"},{"name":"Somewhere","lat":3.1,"lon":101.6,"kind":"road"}]"""
        val list = Favourites.decode(raw)
        assertEquals(1, list.size)
        assertEquals("Somewhere", list[0].name)
    }

    @Test
    fun `the same spot with a different name is still the same place to compare`() {
        assertTrue(place("KLCC").sameAs(place("Suria KLCC")))
        assertFalse(place("KLCC").sameAs(place("KLCC", lat = 3.2)))
    }
}
