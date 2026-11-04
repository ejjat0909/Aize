package app.aize.map

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * Pins reach the map as one GeoJSON document. If that document is malformed the layer draws *nothing* and says
 * nothing, so the string itself is what gets tested here — including the lon/lat order, which is the mistake
 * that puts a Kuala Lumpur pin in the Indian Ocean.
 */
class PinGeoJsonTest {
    private val gas = MapPin(3.1577, 101.7016, PinIcons.GAS, "Petronas \u00b7 Jalan Stesen", "fuel")

    @Test
    fun `empty set is a valid, empty collection`() {
        assertEquals("""{"type":"FeatureCollection","features":[]}""", PinGeoJson.points(emptyList()))
    }

    @Test
    fun `coordinates are lon first`() {
        val json = PinGeoJson.points(listOf(gas))
        assertTrue(json, json.contains("[101.7016,3.1577]"))
    }

    @Test
    fun `icon, label and kind travel with the point`() {
        val json = PinGeoJson.points(listOf(gas))
        assertTrue(json.contains("\"icon\":\"pin-gas\""))
        assertTrue(json.contains("\"kind\":\"fuel\""))
        assertTrue(json.contains("Petronas"))
    }

    @Test
    fun `quotes and control characters are escaped, not emitted raw`() {
        val json = PinGeoJson.points(listOf(gas.copy(label = "He said \"hi\"\n\tthere")))
        assertTrue(json.contains("\\\"hi\\\""))
        assertTrue(json.contains("\\n"))
        assertTrue(json.contains("\\t"))
        // no raw newline inside a JSON string
        assertFalse(json.substringAfter("\"label\":").substringBefore("\"").contains("\n"))
    }

    @Test
    fun `a non-finite coordinate is refused instead of poisoning the document`() {
        var threw = false
        try {
            PinGeoJson.points(listOf(gas.copy(lat = Double.NaN)))
        } catch (e: IllegalArgumentException) {
            threw = true
        }
        assertTrue("NaN must not reach the map", threw)
    }

    @Test
    fun `whole numbers are written without a decimal tail`() {
        val json = PinGeoJson.points(listOf(gas.copy(lat = 3.0, lon = 101.0)))
        assertTrue(json, json.contains("[101,3]"))
    }

    @Test
    fun `kind maps to one of the nine pins`() {
        assertEquals(PinIcons.GAS, PinIcons.forKind("fuel"))
        // the search service reports the full OSM tag, not the bare value
        assertEquals(PinIcons.GAS, PinIcons.forKind("amenity=fuel"))
        assertEquals(PinIcons.PARKING, PinIcons.forKind("amenity=parking"))
        assertEquals(PinIcons.CAMERA, PinIcons.forKind("highway=speed_camera"))
        assertEquals(PinIcons.PARKING, PinIcons.forKind("parking"))
        assertEquals(PinIcons.POLICE, PinIcons.forKind("police"))
        assertEquals(PinIcons.CAMERA, PinIcons.forKind("speed_camera"))
        assertEquals(PinIcons.DESTINATION, PinIcons.forKind("restaurant"))
        assertEquals(PinIcons.DESTINATION, PinIcons.forKind(""))
        assertEquals(9, PinIcons.all.size)
    }

    @Test
    fun `every icon has an asset behind it`() {
        // a typo here means an invisible pin, not a crash: pin-gas -> pin_gas
        assertEquals("pin_gas", PinIcons.assetFor(PinIcons.GAS))
        for (icon in PinIcons.all) assertTrue(icon, PinIcons.assetFor(icon).startsWith("pin_"))
    }
}
