package app.aize.ui.icon

/**
 * The Aize icon set, v1.
 *
 * Why a table of SVG path strings instead of a folder of `ImageVector` constants: an icon is data, and data can be
 * tested. [IconCatalogTest] reads this object on the JVM and checks every path parses, stays inside the 24 dp
 * viewport and that no two icons share a name — none of which needs a device or Compose. The vectors are built once,
 * lazily, in [AizeIcons].
 *
 * House rules, so 45 icons look like one family:
 *  - 24 x 24 viewport, 2 u stroke, round caps and joins, no fill (the tint comes from `Icon`).
 *  - the glyph occupies 3..21 u: an icon that touches the edge looks bigger than its neighbours.
 *  - one idea per icon. `nav_sharp_left` and `nav_slight_left` differ in bend angle, not in style.
 *  - arrows point up or in the direction of travel, never down.
 */
object AizeIconData {

    /** Stroked glyphs, drawn with round caps. */
    val paths: Map<String, List<String>> = mapOf(
        // ---- manoeuvres: the turn list, the banner and the lane strip read these -------------------------------
        "nav_straight" to listOf("M12 21V6", "M6 12l6-6 6 6"),
        "nav_left" to listOf("M13 21v-8a5 5 0 0 0-5-5H4", "M8 4L4 8l4 4"),
        "nav_right" to listOf("M11 21v-8a5 5 0 0 1 5-5h4", "M16 4l4 4-4 4"),
        "nav_slight_left" to listOf("M14 21V13l-6-6", "M8 11V7h4"),
        "nav_slight_right" to listOf("M10 21V13l6-6", "M16 11V7h-4"),
        "nav_sharp_left" to listOf("M12 21V8h-6", "M9 5L6 8l3 3"),
        "nav_sharp_right" to listOf("M12 21V8h6", "M15 5l3 3-3 3"),
        "nav_uturn" to listOf("M8 21V10a4 4 0 0 1 8 0v3", "M12 9l4 4 4-4"),
        "nav_roundabout" to listOf("M12 21v-5", "M12 16a4 4 0 1 0 0-8 4 4 0 0 0 0 8z", "M14 6h5v5"),
        "nav_merge" to listOf("M5 21l7-9 7 9", "M12 12V4", "M8 8l4-4 4 4"),
        "nav_exit" to listOf("M5 21V6h9", "M11 3l3 3-3 3", "M14 21V12"),
        "nav_arrive" to listOf("M12 21V4", "M12 4h8l-2 4 2 4h-8"),

        // ---- places: one per pin family, so a list row and a pin agree ----------------------------------------
        "poi_fuel" to listOf("M5 21V5a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v16", "M3 21h12", "M13 9h3a2 2 0 0 1 2 2v6a2 2 0 0 0 4 0v-5l-2-3"),
        // a bowl with steam, not fork-and-knife: three tines inside 20 dp are two pixels apart and read as a flag
        "poi_food" to listOf("M4 12h16a8 8 0 0 1-16 0Z", "M9 9c1-1 1-2 0-3", "M14 9c1-1 1-2 0-3"),
        "poi_cafe" to listOf("M4 8h12v5a5 5 0 0 1-5 5H9a5 5 0 0 1-5-5V8z", "M16 9h2a2 2 0 0 1 0 4h-2", "M4 21h14"),
        "poi_parking" to listOf("M8 21V3h5a5 5 0 0 1 0 10H8"),
        // the categories the server offers that had no glyph: without these, every chip drew the fallback flag
        "poi_hospital" to listOf("M6 4h12a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2Z", "M12 8v8", "M8 12h8"),
        "poi_mall" to listOf("M6 8h12l-1 12H7L6 8Z", "M9 8V6a3 3 0 0 1 6 0v2"),
        "poi_hotel" to listOf("M3 20V8", "M3 14h18v6", "M7 14v-3h5v3"),
        "poi_ev" to listOf("M13 3L5 14h6l-1 7 8-11h-6l1-7Z"),
        "poi_prayer" to listOf("M5 6h14v14H5Z", "M9 20v-5a3 3 0 0 1 6 0v5"),
        "poi_toilets" to listOf("M8 5.5a1.6 1.6 0 1 1 0 3.2 1.6 1.6 0 0 1 0-3.2Z", "M8 9.5v4l-1.5 7", "M8 13.5l1.5 7", "M16 5.5a1.6 1.6 0 1 1 0 3.2 1.6 1.6 0 0 1 0-3.2Z", "M16 9.5v4", "M14 20l2-6.5 2 6.5"),
        "poi_atm" to listOf("M3 7h18v10H3z", "M7 12h4"),
        "poi_pharmacy" to listOf("M5 4h14v16H5z", "M12 8v8", "M8 12h8"),
        "poi_police" to listOf("M12 3l7 3v6c0 5-7 9-7 9s-7-4-7-9V6l7-3z", "M9 12l2 2 4-4"),
        "poi_camera" to listOf("M3 8h4l2-2h6l2 2h4v11H3z", "M12 16a3 3 0 1 0 0-6 3 3 0 0 0 0 6z"),
        "poi_hazard" to listOf("M12 3l9 16H3l9-16z", "M12 9v4", "M12 16v1"),
        "poi_accident" to listOf("M12 4l8 14H4l8-14z", "M12 10v4", "M12 17v1"),
        "poi_jam" to listOf("M4 15l2-5h12l2 5v3H4v-3z", "M7 18v2", "M17 18v2", "M6 15h12"),
        "poi_closure" to listOf("M4 8h16v8H4z", "M9 8v8", "M15 8v8"),

        // ---- interface glyphs ----------------------------------------------------------------------------------
        "ui_close" to listOf("M6 6l12 12", "M18 6L6 18"),
        "ui_search" to listOf("M11 4a7 7 0 1 0 0 14 7 7 0 0 0 0-14z", "M16 16l4 4"),
        "ui_back" to listOf("M15 5l-7 7 7 7"),
        "ui_star" to listOf("M12 3L14.8 9L21 9.9L16.5 14.2L17.6 20.3L12 17.4L6.4 20.3L7.5 14.2L3 9.9L9.2 9L12 3Z"),
        "ui_share" to listOf("M12 16V4", "M8 8l4-4 4 4", "M4 14v5a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-5"),
        "ui_settings" to listOf("M12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8z", "M12 3v3", "M12 18v3", "M3 12h3", "M18 12h3", "M5.6 5.6L7.8 7.8", "M16.2 16.2l2.2 2.2", "M18.4 5.6l-2.2 2.2", "M7.8 16.2l-2.2 2.2"),
        "ui_mic" to listOf("M12 4a3 3 0 0 1 3 3v5a3 3 0 0 1-6 0V7a3 3 0 0 1 3-3z", "M5 11a7 7 0 0 0 14 0", "M12 18v3"),
        "ui_speaker" to listOf("M4 10v4h4l5 4V6l-5 4H4z", "M16 9a4 4 0 0 1 0 6"),
        "ui_speaker_off" to listOf("M4 10v4h4l5 4V6l-5 4H4z", "M16 10l4 4", "M20 10l-4 4"),
        "ui_recenter" to listOf("M12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8z", "M12 3v3", "M12 18v3", "M3 12h3", "M18 12h3"),
        "ui_compass" to listOf("M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18z", "M15.5 8.5l-2 5-5 2 2-5 5-2z"),
        "ui_plus" to listOf("M12 5v14", "M5 12h14"),
        "ui_minus" to listOf("M5 12h14"),
        "ui_check" to listOf("M4 12l5 5L20 6"),
        "ui_chevron" to listOf("M9 5l7 7-7 7"),
        "ui_layers" to listOf("M12 4l8 4-8 4-8-4 8-4Z", "M4 12l8 4 8-4", "M4 16l8 4 8-4"),
        "ui_route" to listOf("M7 19a2 2 0 1 0 0-4 2 2 0 0 0 0 4z", "M17 9a2 2 0 1 0 0-4 2 2 0 0 0 0 4z", "M9 17h3a4 4 0 0 0 4-4V9"),
        "ui_clock" to listOf("M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18z", "M12 7v5l4 2"),
        "ui_stop" to listOf("M7 7h10v10H7z"),
        "ui_delete" to listOf("M5 7h14", "M10 7V4h4v3", "M7 7l1 14h8l1-14"),
        "ui_home" to listOf("M4 11l8-7 8 7", "M6 10v10h12V10"),
        "ui_work" to listOf("M4 8h16v11H4z", "M9 8V5h6v3", "M4 13h16"),
        "ui_more" to listOf("M6 10a2 2 0 1 0 0 4 2 2 0 0 0 0-4z", "M12 10a2 2 0 1 0 0 4 2 2 0 0 0 0-4z", "M18 10a2 2 0 1 0 0 4 2 2 0 0 0 0-4z"),
        "ui_server" to listOf("M4 5h16v6H4z", "M4 13h16v6H4z", "M8 8h.5", "M8 16h.5"),
        "ui_theme" to listOf("M12 7a5 5 0 1 0 0 10 5 5 0 0 0 0-10z", "M12 2v2", "M12 20v2", "M2 12h2", "M20 12h2", "M5 5l1.5 1.5", "M17.5 17.5L19 19", "M19 5l-1.5 1.5", "M6.5 17.5L5 19"),
        "ui_steps" to listOf("M9 6h12", "M9 12h12", "M9 18h12", "M4 6h.5", "M4 12h.5", "M4 18h.5"),
        "ui_destination" to listOf("M6 21V4", "M6 4h11l-2 4 2 4H6"),
        "ui_arrow_up" to listOf("M6 15l6-6 6 6"),
        "ui_play" to listOf("M8 5.5L19 12L8 18.5V5.5Z"),
        "ui_my_location" to listOf("M12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8Z", "M12 2v3", "M12 19v3", "M2 12h3", "M19 12h3"),
        "ui_refresh" to listOf("M20 12a8 8 0 1 1-2.3-5.6", "M20 4v4h-4"),
    )

    /** Icons the pin layer can ask for, by OSM tag value (the search service answers `amenity=fuel`). */
    val byKind: Map<String, String> = mapOf(
        "fuel" to "poi_fuel",
        // category ids and OSM tags are different vocabularies; both must land on a glyph
        "food" to "poi_food",
        "restaurant" to "poi_food",
        "fast_food" to "poi_food",
        "cafe" to "poi_cafe",
        "hospital" to "poi_hospital",
        "clinic" to "poi_hospital",
        "doctors" to "poi_hospital",
        "mall" to "poi_mall",
        "shop" to "poi_mall",
        "department_store" to "poi_mall",
        "hotel" to "poi_hotel",
        "lodging" to "poi_hotel",
        "ev" to "poi_ev",
        "charging_station" to "poi_ev",
        "prayer" to "poi_prayer",
        "place_of_worship" to "poi_prayer",
        "toilets" to "poi_toilets",
        "parking" to "poi_parking",
        "atm" to "poi_atm",
        "bank" to "poi_atm",
        "pharmacy" to "poi_pharmacy",
        "police" to "poi_police",
        "speed_camera" to "poi_camera",
        "hazard" to "poi_hazard",
        "accident" to "poi_accident",
        "jam" to "poi_jam",
        "closure" to "poi_closure",
    )

    /** The categories the search screen can offer, with the label the chip shows. Kept next to the table it must cover. */
    val builtInCategories: List<Pair<String, String>> = listOf(
        "fuel" to "Fuel", "food" to "Food", "cafe" to "Cafe", "parking" to "Parking", "atm" to "ATM",
        "pharmacy" to "Pharmacy", "hospital" to "Hospital", "mall" to "Mall", "hotel" to "Hotel",
        "prayer" to "Prayer room", "ev" to "EV charging", "toilets" to "Toilets",
    )

    /** Fallback for a kind nobody mapped yet: a pin is still a place. */
    const val FALLBACK = "ui_destination"

    fun forKind(kind: String): String {
        val value = kind.substringAfterLast('=').substringAfterLast(':').lowercase()
        return byKind[value] ?: FALLBACK
    }
}
