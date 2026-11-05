package app.aize.catalogue

/**
 * The pages of the design catalogue.
 *
 * The catalogue exists so that a change to a token, a component or a glyph is *seen* before it ships, and so that
 * seeing it is a script rather than a habit. Each page is one screen: a page that had to be scrolled would capture
 * differently depending on where the scroll happened to stop, and a screenshot test that captures a moving target
 * tests nothing.
 *
 * The ids are also the golden filenames (`docs/catalogue/golden/<id>.png`), so they are part of the test surface:
 * `CatalogueCoverageTest` fails if a page has no golden and if two pages share an id.
 */
enum class CatalogueSection(val id: String, val title: String, val tab: String) {
    Colour("colour", "Colour", "Colour"),
    Type("type", "Type", "Type"),
    Icon("icon", "Icons", "Icons"),
    Button("button", "Buttons", "Buttons"),
    Control("control", "Controls", "Controls"),
    Surface("surface", "Surfaces", "Surfaces"),
    Shape("shape", "Shape and size", "Shape"),
    Motion("motion", "Motion", "Motion"),
    ;

    companion object {
        /** The page an intent names, or null when it names something that does not exist. */
        fun fromId(id: String?): CatalogueSection? = entries.firstOrNull { it.id == id }

        val ids: List<String> = entries.map { it.id }
    }
}
