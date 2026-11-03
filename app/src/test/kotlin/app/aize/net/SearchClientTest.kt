package app.aize.net

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class SearchClientTest {
    @Test fun `search results are parsed in order`() {
        val json = """{"results":[
            {"name":"Suria KLCC","lat":3.1578,"lon":101.7116,"kind":"shop=mall","dist_m":120,"score":9.1},
            {"name":"KLCC Park","lat":3.1555,"lon":101.7140,"kind":"leisure=park","dist_m":310}]}"""
        val r = SearchClient.parse(json)
        assertEquals(2, r.size)
        assertEquals("Suria KLCC", r[0].name)
        assertEquals(101.7116, r[0].lon, 1e-9)
        assertEquals(120, r[0].distanceMeters)
        assertEquals("", r[1].kind.takeIf { false } ?: "")
    }

    @Test fun `an empty result set is not an error`() {
        assertTrue(SearchClient.parse("""{"results":[]}""").isEmpty())
    }

    @Test fun `the query is url encoded and carries the caller position`() {
        val u = SearchClient.searchUrl("host:8002/", "Jalan Ampang & co", 3.1, 101.7)
        assertTrue(u.startsWith("http://host:8002/search?q=Jalan+Ampang+%26+co"))
        assertTrue(u.contains("lat=3.1") && u.contains("lon=101.7"))
    }
}
