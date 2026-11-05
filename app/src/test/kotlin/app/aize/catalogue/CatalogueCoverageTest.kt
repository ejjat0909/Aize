package app.aize.catalogue

import java.io.File
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * The catalogue's pages are part of its test surface, so they are checked like data.
 *
 * Two things can silently rot here: a page added without a golden (the screenshot script would never photograph
 * it, and nobody would notice a missing page), and two pages sharing an id (one golden would overwrite the other
 * and the second page would never be compared). Both fail here instead.
 */
class CatalogueCoverageTest {

    /** Gradle runs unit tests from the module directory (`app/`); the goldens live at the repo root. */
    private fun goldenDir(): File {
        val candidates = listOf(
            File("docs/catalogue/golden"),
            File("../docs/catalogue/golden"),
            File(System.getProperty("user.dir")).resolve("../docs/catalogue/golden"),
        )
        return candidates.firstOrNull { it.isDirectory } ?: candidates[1]
    }

    @Test
    fun everyPageHasAGolden() {
        val dir = goldenDir()
        assertTrue("no golden directory at ${dir.absolutePath}", dir.isDirectory)
        val missing = CatalogueSection.entries.filterNot { File(dir, "${it.id}.png").isFile }
        assertEquals("pages without a golden: ${missing.map { it.id }}", emptyList<CatalogueSection>(), missing)
    }

    @Test
    fun theIdsAreUniqueSlugsBecauseTheyAreFilenames() {
        val ids = CatalogueSection.ids
        assertEquals("duplicate page id", ids.size, ids.toSet().size)
        ids.forEach { id ->
            assertTrue("'$id' is not a lowercase slug", Regex("^[a-z][a-z0-9-]*$").matches(id))
        }
    }

    @Test
    fun theTabLabelsAreShortBecauseTheyShareOneLine() {
        // A tab that does not fit wraps to one character per line and grows the header instead of the page,
        // which is exactly what happened the first time these were drawn.
        CatalogueSection.entries.forEach { section ->
            assertTrue("tab '${section.tab}' is too long for one line", section.tab.length <= 10)
        }
        assertEquals("duplicate tab label", CatalogueSection.entries.size, CatalogueSection.entries.map { it.tab }.toSet().size)
    }

    @Test
    fun anIntentCanNameAPageAndNothingElse() {
        CatalogueSection.entries.forEach { assertEquals(it, CatalogueSection.fromId(it.id)) }
        assertNull(CatalogueSection.fromId("nope"))
        assertNull(CatalogueSection.fromId(null))
    }
}
