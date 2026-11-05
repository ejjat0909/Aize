package app.aize.ui.icon

import app.aize.net.SearchClient
import org.junit.Assert.assertNotEquals
import org.junit.Assert.assertEquals
import org.junit.Test

/**
 * The category ids the app can show must all have an icon.
 *
 * They did not: the server sends "food", the icon table had "restaurant", and every Food chip silently drew the
 * fallback flag. Nothing failed — a flag is a valid icon — so this is the test that would have caught it.
 */
class IconCoverageTest {

    @Test
    fun everyCategoryHasItsOwnIcon() {
        val missing = AizeIconData.builtInCategories
            .filter { AizeIcons.pathFor(it.first) == AizeIconData.FALLBACK }
            .map { it.first }
        assertEquals("categories with no icon: $missing", emptyList<String>(), missing)
    }

    @Test
    fun theSearchScreenCategoriesAllResolve() {
        // the ids the fallback list ships, which are also what an older server answers
        val ids = listOf("fuel", "food", "cafe", "parking", "atm", "pharmacy", "hospital", "mall", "hotel", "prayer", "ev", "toilets")
        ids.forEach { id ->
            assertNotEquals("category '$id' falls back to the generic pin", AizeIconData.FALLBACK, AizeIconData.forKind(id))
        }
    }
}
