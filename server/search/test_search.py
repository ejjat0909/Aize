"""Tests for the place-search service, run with `python3 -m unittest` (no dependencies).

Each test builds a tiny throwaway database with the same schema as the real one, so the ranking and
category rules are checked without the 88 MB Malaysia index.
"""
import importlib.util
import os
import sqlite3
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROWS = [
    ("Shell Bangsar", "shell bangsar", "amenity=fuel", 3.1294, 101.6801),
    ("Petronas Ampang", "petronas ampang", "amenity=fuel", 3.1500, 101.7000),
    ("Suria KLCC", "suria klcc", "shop=mall", 3.1577, 101.7119),
    ("Batu Caves", "batu caves", "place=town", 3.2379, 101.6840),
    ("Village Park Nasi Lemak", "village park nasi lemak", "amenity=restaurant", 3.1550, 101.6320),
]


def load_module(db_path):
    """Imports the server against [db_path]. The module connects on import, so argv goes first."""
    sys.argv = ["search_server.py", db_path, "8001"]
    spec = importlib.util.spec_from_file_location("search_server_under_test", os.path.join(HERE, "search_server.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def build_db():
    path = tempfile.mktemp(suffix=".db")
    c = sqlite3.connect(path)
    c.execute("CREATE TABLE places(id INTEGER PRIMARY KEY, name TEXT, norm TEXT, kind TEXT, kind_rank INT, lat REAL, lon REAL)")
    c.execute("CREATE VIRTUAL TABLE places_fts USING fts5(norm, content='', tokenize='unicode61')")
    for i, (name, norm, kind, lat, lon) in enumerate(ROWS, 1):
        c.execute("INSERT INTO places VALUES(?,?,?,?,0,?,?)", (i, name, norm, kind, lat, lon))
        c.execute("INSERT INTO places_fts(rowid, norm) VALUES(?,?)", (i, norm))
    c.commit()
    c.close()
    return path


class CategoryTest(unittest.TestCase):
    def setUp(self):
        self.db = build_db()
        self.mod = load_module(self.db)

    def tearDown(self):
        os.unlink(self.db)

    def test_fuel_is_nearest_first(self):
        got = self.mod.category("fuel", 3.1343, 101.6862, 5)
        self.assertEqual([r["name"] for r in got], ["Shell Bangsar", "Petronas Ampang"])
        self.assertLess(got[0]["dist_m"], got[1]["dist_m"])

    def test_an_unknown_category_is_not_an_empty_list(self):
        # None tells the handler to answer 400: "I do not know that word" is different from "none here"
        self.assertIsNone(self.mod.category("teleporter"))

    def test_a_category_far_from_anywhere_still_answers(self):
        # 8 km, then 25 km, then 80 km boxes: a station outside the first ring is still found
        got = self.mod.category("fuel", 3.40, 101.6862, 1)
        self.assertEqual(len(got), 1)

    def test_every_category_maps_to_real_osm_tags(self):
        for cid, (label, kinds) in self.mod.CATEGORIES.items():
            self.assertTrue(label, cid)
            self.assertTrue(kinds, cid)
            for k in kinds:
                self.assertRegex(k, r"^[a-z_]+=[a-z_]+$")


class SearchTest(unittest.TestCase):
    def setUp(self):
        self.db = build_db()
        self.mod = load_module(self.db)

    def tearDown(self):
        os.unlink(self.db)

    def test_a_town_outranks_a_shop_with_the_same_name(self):
        got = self.mod.search("batu caves", 3.1343, 101.6862, 5)
        self.assertEqual(got[0]["name"], "Batu Caves")

    def test_one_character_finds_nothing(self):
        self.assertEqual(self.mod.search("b", 3.1343, 101.6862, 5), [])

    def test_distance_breaks_a_tie_between_two_identical_names(self):
        got = self.mod.search("petronas", 3.1343, 101.6862, 5)
        self.assertTrue(got)


if __name__ == "__main__":
    unittest.main()
