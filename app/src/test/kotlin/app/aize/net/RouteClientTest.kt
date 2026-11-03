package app.aize.net

import org.json.JSONObject
import java.net.URLDecoder
import org.junit.Test
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull

class RouteClientTest {
    @Test fun `addresses are normalised`() {
        assertEquals("http://192.168.1.5:8002", ServerSettings.normalize("192.168.1.5:8002"))
        assertEquals("https://aize.example.com", ServerSettings.normalize("  https://aize.example.com/  "))
        assertEquals("http://host:8002", ServerSettings.normalize("http://host:8002/route"))
        assertEquals(ServerSettings.DEFAULT_URL, ServerSettings.normalize("   "))
    }

    @Test fun `route request carries both points and the auto costing`() {
        val url = RouteClient.routeUrl("host:8002/", 3.1343, 101.6862, 3.1579, 101.7116)
        org.junit.Assert.assertTrue(url.startsWith("http://host:8002/route?json="))
        val json = JSONObject(URLDecoder.decode(url.substringAfter("json="), "UTF-8"))
        assertEquals("auto", json.getString("costing"))
        val locs = json.getJSONArray("locations")
        assertEquals(101.7116, locs.getJSONObject(1).getDouble("lon"), 1e-9)
        assertEquals(3.1343, locs.getJSONObject(0).getDouble("lat"), 1e-9)
        assertEquals("kilometers", json.getJSONObject("directions_options").getString("units"))
    }

    @Test fun `valhalla error bodies give a readable message`() {
        assertEquals("No suitable edges near location", RouteClient.serverMessage("""{"error_code":171,"error":"No suitable edges near location","status_code":400}"""))
        assertNull(RouteClient.serverMessage("<html>502</html>"))
    }
}
