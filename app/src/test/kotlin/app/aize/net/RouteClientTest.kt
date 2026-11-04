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

class RouteChoicesTest {
    private fun fixture(): String =
        javaClass.classLoader!!.getResourceAsStream("route-alternates.json")!!.bufferedReader().readText()

    @Test fun `every route the server offers is parsed, best first`() {
        val routes = RouteClient.parseRoutes(fixture())
        assertEquals(3, routes.size)
        assertEquals(6341.0, routes[0].summary!!.distanceMeters, 5.0)
        assertEquals(4370.0, routes[1].summary!!.distanceMeters, 5.0)
        assertEquals(5566.0, routes[2].summary!!.distanceMeters, 5.0)
        // the geometry is the driver's real distance, the summary is the server's: both are kept
        assertEquals(2261.0, routes[0].path.lengthMeters, 5.0)
    }

    @Test fun `a route without alternates is still a list of one`() {
        val only = JSONObject(fixture()).getJSONObject("trip").toString()
        assertEquals(1, RouteClient.parseRoutes("""{"trip":$only}""").size)
    }

    @Test fun `toll and motorway flags survive parsing`() {
        val routes = RouteClient.parseRoutes(fixture())
        assertEquals(false, choices(0)?.hasTolls)
        val toll = routes[1].summary!!
        org.junit.Assert.assertTrue("the second route uses the toll road", toll.hasTolls)
        org.junit.Assert.assertTrue(toll.usesMotorway)
        org.junit.Assert.assertFalse(toll.usesFerry)
    }

    @Test fun `the card names the road the driver spends the most time on`() {
        assertEquals("Jalan Sultan Sulaiman", RouteClient.parseRoutes(fixture())[1].mainRoad)
    }

    private fun choices(i: Int) = RouteClient.parseRoutes(fixture())[i].summary
}

class SearchFailureTest {
    @Test fun `an unreachable server says so instead of looking like no matches`() {
        val error = runCatching { SearchClient.search("http://127.0.0.1:1", "klcc", 3.1343, 101.6862) }.exceptionOrNull()
        org.junit.Assert.assertNotNull("search must throw, not return an empty list", error)
        org.junit.Assert.assertTrue(
            "message should name the problem, got: ${error?.message}",
            error?.message?.contains("Cannot reach the server") == true,
        )
    }

    @Test fun `a server that answers with an error body is reported as such`() {
        val body = """{"error":"No suitable edges near location","error_code":171}"""
        org.junit.Assert.assertEquals("No suitable edges near location", RouteClient.serverMessage(body))
    }
}
